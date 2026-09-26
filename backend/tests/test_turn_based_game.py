"""Turn-based room behaviour: scheduling, action costs, and mode isolation.

Covers the layer above `test_turn_scheduler.py` (which tests the heap in
isolation): the 40Hz pump, the room-global pause, the cost of each kind of
action, the world-upkeep cadence, and the guarantee that a real-time room is
untouched.

Each test drives the same loop the server does: construct the room, then call
`update_tick()` as the global game loop would.
"""

import random
import time
import typing

import pytest
from pydantic import BaseModel

from app.api import ws_handlers  # noqa: F401  (registers dispatcher handlers)
from app.api.dispatcher import dispatcher
from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.game.constants import (
    GAME_MODE_REALTIME,
    GAME_MODE_TURNBASED,
    TICK_DURATION,
    TICKS_PER_TURN,
    TIME_TO_ATTACK,
    TIME_TO_EAT,
    TIME_TO_IDLE,
    TIME_TO_MOVE_BASE,
    TIME_TO_REST,
    TIME_TO_SEARCH,
    TIME_TO_WAIT,
)
from app.engine.manager import GameInstance
from app.engine.entities.mobs.sewers import Rat
from app.engine.turn.actions import _BUILDERS, _msg_type, build_turn_action
from app.engine.turn.instance import TurnBasedGameInstance
from app.schemas import messages as msg
from app.schemas.common import Direction

TICK = TICK_DURATION


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _isolated_global_rng():
    """Stop floor generation from leaking the stdlib RNG into later tests.

    `_generate_floor_spd` runs its trinket/moss/trap post-processing against
    the module-level `random` rather than the seeded `SPDRandom`, so every
    game built here would advance the global sequence and change which floors
    the level-generation tests downstream happen to generate.
    """
    saved = random.getstate()
    random.seed(0x7A4E)
    try:
        yield
    finally:
        random.setstate(saved)


@pytest.fixture
def turn_game():
    """A turn room on an open floor, with one hero and no mobs."""
    g = TurnBasedGameInstance("turn-test")
    g.players = {}
    floor = g._get_or_create_floor(1)
    floor.grid = [[TileType.FLOOR for _ in range(20)] for _ in range(20)]
    floor.rebuild_flags()
    for mob in list(floor.mobs.values()):
        floor.mobs.pop(mob.id, None)
    return g


def _pump(game, ticks=4):
    for _ in range(ticks):
        game.update_tick(TICK)


def _add_hero(game, x=5, y=5):
    player = game.add_player("p1", "Hero")
    player.pos = Position(x=x, y=y)
    player.floor_id = 1
    return player


def _add_mob(game, x, y, mob_cls=None):
    floor = game._get_or_create_floor(1)
    mob = game._spawn_mob_at(mob_cls or Rat, x, y)
    mob.pos = Position(x=x, y=y)
    mob.floor_id = 1
    floor.mobs[mob.id] = mob
    return mob


def _wall_at(game, x, y):
    floor = game._get_or_create_floor(1)
    floor.grid[y][x] = TileType.WALL
    floor.rebuild_flags()


# --- room-global pause ----------------------------------------------------


def test_room_pauses_on_hero_and_waits_for_input(turn_game):
    hero = _add_hero(turn_game)
    _pump(turn_game)

    state = turn_game.turn_state_for(hero.id)
    assert state["is_my_turn"] is True
    assert turn_game.scheduler.now == 0.0
    # The hero is the head of the order and is blocking on input.
    assert state["order"][0]["id"] == hero.id
    assert state["order"][0]["needs_input"] is True


def test_hero_cannot_act_out_of_turn(turn_game):
    hero = _add_hero(turn_game)
    _add_mob(turn_game, 7, 5)
    _pump(turn_game)

    # Let the hero act, so the next head is a mob mid-cascade.
    turn_game.submit_turn_action(hero.id, msg.Wait(type="WAIT"))
    _pump(turn_game)
    head = turn_game.scheduler.peek()
    assert head is not None

    if not isinstance(head, type(turn_game._player_actors[hero.id])):
        # A mob holds the room: the hero's input must be refused outright.
        assert turn_game.submit_turn_action(hero.id, msg.Wait(type="WAIT")) is False


def test_second_player_cannot_act_while_first_is_active(turn_game):
    first = _add_hero(turn_game, 5, 5)
    second = turn_game.add_player("p2", "Other")
    second.pos = Position(x=6, y=6)
    second.floor_id = 1
    _pump(turn_game)

    active = turn_game.turn_state_for(first.id)
    other = turn_game.turn_state_for(second.id)
    assert active["is_my_turn"] is True
    assert other["is_my_turn"] is False

    # Exactly one of them is owed the turn, and only that one may submit.
    accepted = [
        turn_game.submit_turn_action(pid, msg.Wait(type="WAIT"))
        for pid in (first.id, second.id)
    ]
    assert sum(accepted) == 1


# --- action costs ---------------------------------------------------------


def test_move_costs_one_over_speed(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    action = build_turn_action(
        turn_game, hero, msg.Move(type="MOVE", direction=Direction.RIGHT)
    )
    assert action is not None
    speed = hero.get_movement_speed(enemies_nearby=False)
    assert action.cost == pytest.approx(TIME_TO_MOVE_BASE / speed)


def test_move_advances_hero_by_one_tile_per_turn(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    turn_game.submit_turn_action(
        hero.id, msg.Move(type="MOVE", direction=Direction.RIGHT)
    )
    _pump(turn_game)

    assert (hero.pos.x, hero.pos.y) == (6, 5)
    assert turn_game.scheduler.now == pytest.approx(1.0)


def test_two_turns_of_moving_cost_two_time_units(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    for _ in range(2):
        turn_game.submit_turn_action(
            hero.id, msg.Move(type="MOVE", direction=Direction.RIGHT)
        )
        _pump(turn_game)

    assert (hero.pos.x, hero.pos.y) == (7, 5)
    assert turn_game.scheduler.now == pytest.approx(2.0)


def test_attack_and_search_costs_match_spd(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    built = [
        build_turn_action(turn_game, hero, msg.Attack(type="ATTACK", target_id="x")),
        build_turn_action(turn_game, hero, msg.Search(type="SEARCH")),
        build_turn_action(turn_game, hero, msg.Wait(type="WAIT")),
    ]
    for action in built:
        assert action is not None
    assert [a.cost for a in built if a is not None] == [
        TIME_TO_ATTACK,
        TIME_TO_SEARCH,
        TIME_TO_WAIT,
    ]
    assert TIME_TO_ATTACK == 1.0 and TIME_TO_SEARCH == 2.0


def test_eating_costs_three_time_units(turn_game):
    hero = _add_hero(turn_game)
    food = next(i for i in hero.belongings.all_items() if i.type == "food")
    _pump(turn_game)

    action = build_turn_action(
        turn_game,
        hero,
        msg.ExecuteItemAction(type="EXECUTE_ITEM_ACTION", item_id=food.id, action="EAT"),
    )
    assert action is not None
    assert action.cost == TIME_TO_EAT == 3.0


def test_menu_actions_cost_nothing_and_keep_the_turn(turn_game):
    hero = _add_hero(turn_game)
    _pump(turn_game)

    action = build_turn_action(
        turn_game, hero, msg.SendChat(type="SEND_CHAT", channel="global", text="hi")
    )
    assert action is not None and action.cost == 0.0

    before = len(turn_game.events)
    turn_game.submit_turn_action(
        hero.id, msg.SendChat(type="SEND_CHAT", channel="global", text="hi")
    )
    # It runs on the click, not on some later turn.
    assert len(turn_game.events) == before + 1
    _pump(turn_game)
    # A free action neither spends time nor releases the room.
    assert turn_game.scheduler.now == 0.0
    assert turn_game.turn_state_for(hero.id)["is_my_turn"] is True


def test_free_action_is_allowed_out_of_turn(turn_game):
    """Chat and menus are not turns, so they are never blocked by the room."""
    first = _add_hero(turn_game, 5, 5)
    second = turn_game.add_player("p2", "Other")
    second.pos = Position(x=6, y=6)
    second.floor_id = 1
    _pump(turn_game)

    assert turn_game.turn_state_for(first.id)["is_my_turn"] is True
    assert turn_game.turn_state_for(second.id)["is_my_turn"] is False

    # The waiting player may still talk.
    assert turn_game.submit_turn_action(
        second.id, msg.SendChat(type="SEND_CHAT", channel="global", text="hi")
    ) is True
    # But a real action from the same player is refused.
    assert turn_game.submit_turn_action(
        second.id, msg.Wait(type="WAIT")
    ) is False


def test_bumping_a_wall_is_not_a_turn(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _wall_at(turn_game, 6, 5)
    _pump(turn_game)

    assert turn_game.submit_turn_action(
        hero.id, msg.Move(type="MOVE", direction=Direction.RIGHT)
    ) is False
    _pump(turn_game)

    assert (hero.pos.x, hero.pos.y) == (5, 5)
    assert turn_game.scheduler.now == 0.0
    # Still the hero's turn, so they can immediately try a legal move.
    assert turn_game.turn_state_for(hero.id)["is_my_turn"] is True


def test_moving_into_a_mob_is_a_turn_that_attacks(turn_game):
    """The bump is how a turn room attacks: a tap, a click or a key press.

    The client sends one `MOVE` and the server turns the occupied tile into the
    strike, so nothing here may depend on the real-time `MOVE_STEP` plumbing a
    turn room drops -- and the hero does not step into the mob.
    """
    hero = _add_hero(turn_game, 5, 5)
    mob = _add_mob(turn_game, 6, 5)
    _pump(turn_game)
    hp_before = mob.hp

    assert turn_game.submit_turn_action(
        hero.id, msg.Move(type="MOVE", direction=Direction.RIGHT)
    ) is True
    _pump(turn_game)

    assert mob.hp < hp_before
    assert (hero.pos.x, hero.pos.y) == (5, 5)
    assert any(
        e["type"] == "ATTACK" and e["data"]["source"] == hero.id
        for e in turn_game.events
    )
    assert turn_game.scheduler.now == pytest.approx(TIME_TO_MOVE_BASE)


# --- dropped movement plumbing -------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        msg.MoveIntent(type="MOVE_INTENT", dx=1, dy=0),
        msg.MoveStep(type="MOVE_STEP", seq=1, dx=1, dy=0),
        msg.MoveStop(type="MOVE_STOP", last_seq=1),
    ],
)
def test_movement_plumbing_is_dropped_in_turn_mode(turn_game, message):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    assert build_turn_action(turn_game, hero, message) is None
    assert turn_game.submit_turn_action(hero.id, message) is False
    _pump(turn_game)
    assert (hero.pos.x, hero.pos.y) == (5, 5)


def test_every_client_message_type_is_accounted_for():
    """No message may silently vanish: registered, or deliberately dropped.

    Guards the two lists against drifting apart as messages are added -- an
    unhandled type in a turn room fails silently at runtime, since the turn
    dispatcher reports nothing back to the client.
    """
    from app.schemas.messages import ClientMessage

    inner = typing.get_args(typing.get_args(ClientMessage)[0])
    models = [a for a in inner if isinstance(a, type) and issubclass(a, BaseModel)]
    types = {_msg_type(m) for m in models}

    # PATH_STEPS is absent on purpose: it is not plumbing but the far-tap
    # request, and a turn room drains it one tile per turn.
    deliberately_dropped = {"MOVE_INTENT", "MOVE_STEP", "MOVE_STOP"}

    assert types - set(_BUILDERS) == deliberately_dropped
    assert set(_BUILDERS) - types == set()


# --- world upkeep cadence -------------------------------------------------


def test_upkeep_runs_once_per_spd_time_unit_not_per_pump(turn_game):
    """A paused room must not burn world upkeep on idle pumps."""
    _add_hero(turn_game, 5, 5)
    _pump(turn_game, ticks=40)

    assert turn_game.scheduler.now == 0.0
    assert turn_game._upkeep_units == 0


def test_upkeep_advances_one_unit_per_elapsed_turn(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)
    assert turn_game._upkeep_units == 0

    turn_game.submit_turn_action(hero.id, msg.Wait(type="WAIT"))
    _pump(turn_game)
    assert turn_game._upkeep_units == 1

    turn_game.submit_turn_action(hero.id, msg.Wait(type="WAIT"))
    _pump(turn_game)
    assert turn_game._upkeep_units == 2
    assert turn_game.scheduler.now == pytest.approx(2.0)


def test_sim_units_are_spd_scales():
    turn = TurnBasedGameInstance("t")
    assert turn.sim_unit == 1.0
    assert turn.sim_ticks == TICKS_PER_TURN

    real = GameInstance("r")
    assert real.sim_unit == TICK_DURATION
    assert real.sim_ticks == 1
    assert real.game_mode == GAME_MODE_REALTIME


# --- turn timer -----------------------------------------------------------


def test_turn_timer_arms_only_while_waiting_on_a_hero(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    remaining = turn_game.turn_timer_remaining()
    assert remaining is not None
    assert 0 < remaining <= turn_game.turn_timer_seconds


def test_expired_turn_timer_auto_waits_the_hero(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)
    assert turn_game.scheduler.now == 0.0

    turn_game._turn_deadline = time.monotonic() - 1.0
    _pump(turn_game, ticks=6)

    # The room moved on by exactly the wait cost, and upkeep caught up with it.
    assert turn_game.scheduler.now == pytest.approx(TIME_TO_WAIT)
    assert turn_game._upkeep_units == 1
    assert turn_game.turn_state_for(hero.id)["is_my_turn"] is True


def test_unexpired_turn_timer_does_not_force_a_wait(turn_game):
    _add_hero(turn_game, 5, 5)
    _pump(turn_game, ticks=20)

    assert turn_game.scheduler.now == 0.0
    assert turn_game._forced_wait_pending is False


# --- mob turns ------------------------------------------------------------


def test_mob_takes_its_turn_and_the_room_resumes_for_the_hero(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    rat = _add_mob(turn_game, 7, 5)
    rat.ai_state = "hunting"
    _pump(turn_game)

    turn_game.submit_turn_action(hero.id, msg.Wait(type="WAIT"))
    _pump(turn_game)

    actor = turn_game._mob_actors[rat.id]
    assert actor.scheduled_time > 0.0, "mob must be rescheduled after acting"
    # The mob is behind the hero again, so the room is waiting on the hero.
    assert turn_game.turn_state_for(hero.id)["is_my_turn"] is True


def test_mob_step_cost_follows_spd_one_over_speed(turn_game):
    """SPD Char.move() charges `1 / speed()`, so a fast mob acts more often."""
    _add_hero(turn_game, 5, 5)
    slow = _add_mob(turn_game, 8, 5)
    fast = _add_mob(turn_game, 9, 5)
    slow.speed = 1.0
    fast.speed = 2.0

    # Stub the AI: this is about the cost wiring, not the mob's pathing.
    def _step(mob, floor, floor_id):
        mob.pos.x += 1

    turn_game._tick_mob = _step

    assert turn_game._mob_take_turn(slow) == pytest.approx(
        TIME_TO_MOVE_BASE / slow.speed
    )
    assert turn_game._mob_take_turn(fast) == pytest.approx(
        TIME_TO_MOVE_BASE / fast.speed
    )


def test_fast_mob_gets_its_next_turn_sooner(turn_game):
    _add_hero(turn_game, 5, 5)
    slow = _add_mob(turn_game, 8, 5)
    fast = _add_mob(turn_game, 9, 5)
    slow.speed, fast.speed = 1.0, 2.0
    slow.ai_state = fast.ai_state = "idle"
    turn_game._tick_mob = lambda mob, floor, floor_id: None
    _pump(turn_game)

    turn_game.submit_turn_action("p1", msg.Wait(type="WAIT"))
    # One step only, so the fast mob is caught mid-cascade at 0.5 while the
    # slow one has only just been charged a full 1.0.
    turn_game._drain_actor_turns(budget=2)

    fast_actor = turn_game._mob_actors[fast.id]
    slow_actor = turn_game._mob_actors[slow.id]
    assert fast_actor.scheduled_time < slow_actor.scheduled_time


def test_idle_mob_charges_time_to_idle(turn_game):
    _add_hero(turn_game, 5, 5)
    idle_mob = _add_mob(turn_game, 15, 15)
    idle_mob.ai_state = "sleeping"
    floor = turn_game._get_or_create_floor(1)

    assert turn_game._mob_take_turn(idle_mob) == TIME_TO_IDLE


def test_dead_mob_turn_is_free_to_ignore(turn_game):
    _add_hero(turn_game, 5, 5)
    mob = _add_mob(turn_game, 8, 5)
    mob.is_alive = False

    assert turn_game._mob_take_turn(mob) == TIME_TO_WAIT


# --- actor registry -------------------------------------------------------


def test_actors_are_reconciled_on_join_and_leave(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    rat = _add_mob(turn_game, 7, 5)
    _pump(turn_game)
    assert set(turn_game._player_actors) == {hero.id}
    assert set(turn_game._mob_actors) == {rat.id}

    hero.is_alive = False
    _pump(turn_game)
    assert hero.id not in turn_game._player_actors


def test_killed_mob_is_dropped_from_the_scheduler(turn_game):
    _add_hero(turn_game, 5, 5)
    rat = _add_mob(turn_game, 7, 5)
    _pump(turn_game)

    rat.is_alive = False
    _pump(turn_game)
    assert rat.id not in turn_game._mob_actors


def test_downed_hero_stops_holding_the_room(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)
    assert turn_game.turn_state_for(hero.id)["is_my_turn"] is True

    hero.is_downed = True
    _pump(turn_game)
    assert turn_game.turn_state_for(hero.id)["is_my_turn"] is False


# --- departed actors must not keep the room busy -------------------------


def test_dead_actors_stop_consuming_the_step_budget(turn_game):
    """A corpse left in the heap would burn MAX_TURN_STEPS_PER_TICK every pump."""
    _add_hero(turn_game, 5, 5)
    rat = _add_mob(turn_game, 7, 5)
    _pump(turn_game)

    hero = turn_game.players["p1"]
    rat.is_alive = False
    hero.is_alive = False
    _pump(turn_game)

    assert turn_game._drain_actor_turns() == 0
    assert turn_game.scheduler.peek() is None


def test_revived_hero_gets_a_fresh_actor(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    hero.is_downed = True
    _pump(turn_game)
    assert hero.id not in turn_game._player_actors

    hero.is_downed = False
    _pump(turn_game)
    actor = turn_game._player_actors[hero.id]
    assert actor.cancelled is False
    assert turn_game.turn_state_for(hero.id)["is_my_turn"] is True


def test_cancelled_actor_never_reaches_the_turn_order(turn_game):
    _add_hero(turn_game, 5, 5)
    rat = _add_mob(turn_game, 7, 5)
    _pump(turn_game)
    assert rat.id in [a.entity_id for a in turn_game.scheduler.preview(8)]

    rat.is_alive = False
    _pump(turn_game)
    assert rat.id not in [a.entity_id for a in turn_game.scheduler.preview(8)]


# --- broadcast gating -----------------------------------------------------


def test_paused_room_reports_clean_after_the_first_broadcast(turn_game):
    _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    # The bootstrap frame is always sent, then the room goes quiet.
    assert turn_game.should_broadcast() is True
    for _ in range(20):
        turn_game.update_tick(TICK)
        assert turn_game.should_broadcast() is False


def test_acting_marks_the_room_dirty(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)
    turn_game.should_broadcast()

    turn_game.submit_turn_action(hero.id, msg.Wait(type="WAIT"))
    assert turn_game.should_broadcast() is True


# --- mode isolation -------------------------------------------------------


def test_realtime_room_is_unaffected_by_the_turn_seams(open_game_factory):
    game = open_game_factory(width=20, height=20)
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=3, y=3)

    assert game.game_mode == GAME_MODE_REALTIME
    assert game.turn_state_for(player.id) is None
    assert game.submit_turn_action(player.id, msg.Wait(type="WAIT")) is False
    # The real-time loop still rate-limits with wall clock.
    assert game.action_blocked(type("E", (), {"action_until": time.time() + 5})()) is True
    assert game.attack_ready(type("E", (), {"last_attack_time": 0.0})(), 1.0) is True


def test_turn_room_never_blocks_on_wall_clock_limits(turn_game):
    entity = type("E", (), {"action_until": time.time() + 99, "last_attack_time": 0.0})()
    assert turn_game.action_blocked(entity) is False
    assert turn_game.attack_ready(entity, 99.0) is True


def test_turn_room_clock_is_the_scheduler_cursor(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)
    assert turn_game.clock() == turn_game.scheduler.now == 0.0

    turn_game.submit_turn_action(hero.id, msg.Wait(type="WAIT"))
    _pump(turn_game)
    assert turn_game.clock() == pytest.approx(1.0)


@pytest.mark.anyio
async def test_dispatcher_routes_turn_rooms_to_the_scheduler(turn_game):
    """A turn room must never reach the real-time handlers."""
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    reached_handler = []
    original = dispatcher._handlers[msg.Wait]
    dispatcher._handlers[msg.Wait] = lambda *a: reached_handler.append(a)
    try:
        await dispatcher.dispatch(turn_game, hero.id, msg.Wait(type="WAIT"), None)
    finally:
        dispatcher._handlers[msg.Wait] = original

    assert reached_handler == []
    assert turn_game._player_actors[hero.id].pending_action is not None


@pytest.mark.anyio
async def test_dispatcher_keeps_using_handlers_in_realtime_rooms(open_game_factory):
    game = open_game_factory(width=20, height=20)
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=3, y=3)

    reached_handler = []
    original = dispatcher._handlers[msg.Wait]
    dispatcher._handlers[msg.Wait] = lambda *a: reached_handler.append(a)
    try:
        await dispatcher.dispatch(game, player.id, msg.Wait(type="WAIT"), None)
    finally:
        dispatcher._handlers[msg.Wait] = original

    assert len(reached_handler) == 1


# --- tap to travel --------------------------------------------------------


def _walk(turn_game, hero, steps):
    return turn_game.submit_turn_action(
        hero.id, msg.PathSteps(type="PATH_STEPS", steps=[list(s) for s in steps])
    )


def test_far_tap_walks_one_tile_then_keeps_walking(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    assert _walk(turn_game, hero, [(0, 1), (0, 1), (1, 0)]) is True
    # One tap is one turn: a single tile, charged as a move.
    _pump(turn_game, ticks=1)
    assert (hero.pos.x, hero.pos.y) == (5, 6)
    assert turn_game.scheduler.now == pytest.approx(TIME_TO_MOVE_BASE)

    _pump(turn_game, ticks=1)
    assert (hero.pos.x, hero.pos.y) == (5, 7)
    _pump(turn_game, ticks=1)
    assert (hero.pos.x, hero.pos.y) == (6, 7)
    assert turn_game.scheduler.now == pytest.approx(3 * TIME_TO_MOVE_BASE)

    # Arrival hands the turn back to the player.
    assert hero.movement.has_path() is False
    assert turn_game.turn_state_for(hero.id)["is_my_turn"] is True
    assert turn_game.turn_state_for(hero.id)["order"][0]["needs_input"] is True


def test_far_tap_costs_one_move_regardless_of_path_length(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    action = build_turn_action(
        turn_game, hero, msg.PathSteps(type="PATH_STEPS", steps=[[0, 1], [0, 1], [0, 1]])
    )
    assert action is not None
    assert action.cost == pytest.approx(TIME_TO_MOVE_BASE)


def test_far_tap_with_no_route_spends_no_turn(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    assert build_turn_action(turn_game, hero, msg.PathSteps(type="PATH_STEPS", steps=[])) is None
    assert _walk(turn_game, hero, []) is False
    _pump(turn_game)
    assert (hero.pos.x, hero.pos.y) == (5, 5)
    assert turn_game.scheduler.now == 0.0
    assert turn_game.turn_state_for(hero.id)["is_my_turn"] is True


def test_walk_drops_deltas_that_are_not_one_tile(turn_game):
    """A delta larger than a tile is the one input that could skip a wall."""
    hero = _add_hero(turn_game, 5, 5)
    _wall_at(turn_game, 6, 5)
    _pump(turn_game)

    # The long delta is discarded, the unit one below still walks.
    assert _walk(turn_game, hero, [(4, 0), (0, 1)]) is True
    _pump(turn_game, ticks=1)
    assert (hero.pos.x, hero.pos.y) == (5, 6)
    assert hero.movement.has_path() is False

    assert _walk(turn_game, hero, [(4, 0)]) is False
    assert _walk(turn_game, hero, [(0, 0)]) is False


def test_walk_stops_at_a_mob_and_never_attacks_it(turn_game):
    """SPD only ever attacks from an explicit click, so a walk must not."""
    hero = _add_hero(turn_game, 5, 5)
    mob = _add_mob(turn_game, 5, 6)
    hp_before = mob.hp
    _pump(turn_game)

    _walk(turn_game, hero, [(0, 1), (0, 1)])
    _pump(turn_game, ticks=1)

    assert hero.movement.has_path() is False
    assert mob.hp == hp_before
    assert (hero.pos.x, hero.pos.y) == (5, 5)


def test_walk_stops_when_a_hostile_comes_into_view(turn_game):
    """`Hero.checkVisibleMobs`: an enemy that appears stops the trip."""
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)
    _walk(turn_game, hero, [(0, 1), (0, 1), (0, 1)])
    _pump(turn_game, ticks=1)
    assert (hero.pos.x, hero.pos.y) == (5, 6)

    # Spawned inside the hero's sight radius, so the next step sees it as new.
    _add_mob(turn_game, 7, 5)
    # Two ticks: the rat is reconciled into the order and takes its own turn
    # before the hero's next tile, so the interrupt lands on the tick after.
    _pump(turn_game, ticks=2)

    assert hero.movement.has_path() is False
    assert (hero.pos.x, hero.pos.y) == (5, 6)
    # The turn is still spent, so the room resumes rather than stalling.
    assert turn_game.turn_state_for(hero.id)["is_my_turn"] is True


def test_walk_is_not_interrupted_by_an_enemy_already_in_view(turn_game):
    """Edge-triggered, like SPD: only a *new* arrival stops the walk."""
    hero = _add_hero(turn_game, 5, 5)
    _add_mob(turn_game, 7, 5)
    _pump(turn_game)

    _walk(turn_game, hero, [(0, 1), (0, 1)])
    _pump(turn_game, ticks=1)
    _pump(turn_game, ticks=1)

    assert (hero.pos.x, hero.pos.y) == (5, 7)


def test_another_action_replaces_a_walk_in_progress(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)
    _walk(turn_game, hero, [(0, 1), (0, 1), (0, 1)])
    _pump(turn_game, ticks=1)
    assert (hero.pos.x, hero.pos.y) == (5, 6)

    turn_game.submit_turn_action(hero.id, msg.Move(type="MOVE", direction=Direction.LEFT))
    assert hero.movement.has_path() is False

    _pump(turn_game, ticks=1)
    assert (hero.pos.x, hero.pos.y) == (4, 6)


def test_a_second_far_tap_retargets_the_first(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)
    _walk(turn_game, hero, [(0, 1), (0, 1), (0, 1)])
    _pump(turn_game, ticks=1)
    assert (hero.pos.x, hero.pos.y) == (5, 6)

    _walk(turn_game, hero, [(0, -1)])
    _pump(turn_game, ticks=1)
    assert (hero.pos.x, hero.pos.y) == (5, 5)
    assert hero.movement.has_path() is False


def test_walk_keeps_the_turn_available_so_the_player_can_interrupt(turn_game):
    """`canActNow` is derived from `is_my_turn`, so a silent walk would trap
    the player: every input is gated on that flag."""
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)
    _walk(turn_game, hero, [(0, 1), (0, 1), (0, 1)])
    _pump(turn_game, ticks=1)

    state = turn_game.turn_state_for(hero.id)
    assert state["is_my_turn"] is True
    # The room is not parked on the hero, so no countdown is offered.
    assert state["order"][0]["needs_input"] is False
    assert state["timer"] is None


def test_walk_is_dropped_when_the_hero_changes_floor(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)
    _walk(turn_game, hero, [(0, 1), (0, 1)])
    _pump(turn_game, ticks=1)
    assert hero.movement.has_path() is True

    hero.floor_id = 2
    _pump(turn_game, ticks=1)

    assert hero.movement.has_path() is False
    assert turn_game.turn_state_for(hero.id)["is_my_turn"] is True


def test_realtime_room_still_queues_a_path_for_the_tick_pump(open_game_factory):
    """The turn builder is additive: real-time keeps `set_path` untouched."""
    game = open_game_factory(width=20, height=20)
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=3, y=3)

    handler = dispatcher._handlers[msg.PathSteps]
    handler(game, player.id, msg.PathSteps(type="PATH_STEPS", steps=[[0, 1], [0, 1]]))

    assert list(player.movement.path_queue) == [(0, 1), (0, 1)]


def test_turn_state_payload_shape(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    state = turn_game.turn_state_for(hero.id)
    assert state["game_mode"] == GAME_MODE_TURNBASED
    assert state["turn"] == 0
    assert state["is_my_turn"] is True
    assert isinstance(state["order"], list)
    assert state["order"][0]["kind"] == "player"
    assert 0 < state["timer"] <= turn_game.turn_timer_seconds
