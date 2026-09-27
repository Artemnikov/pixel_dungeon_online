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
        for p in game.players.values():
            p.movement._cooldown_until = 0.0
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


def test_all_players_can_act_simultaneously_in_player_turn(turn_game):
    first = _add_hero(turn_game, 5, 5)
    second = turn_game.add_player("p2", "Other")
    second.pos = Position(x=6, y=6)
    second.floor_id = 1
    _pump(turn_game)

    active = turn_game.turn_state_for(first.id)
    other = turn_game.turn_state_for(second.id)
    assert active["is_my_turn"] is True
    assert other["is_my_turn"] is True

    # Both players may submit actions at the same time
    assert turn_game.submit_turn_action(first.id, msg.Wait(type="WAIT")) is True
    assert turn_game.turn_state_for(first.id)["is_my_turn"] is False
    assert turn_game.turn_state_for(second.id)["is_my_turn"] is True

    # First player cannot submit a second costed turn action in the same round
    assert turn_game.submit_turn_action(first.id, msg.Wait(type="WAIT")) is False

    # Second player submits their action
    assert turn_game.submit_turn_action(second.id, msg.Wait(type="WAIT")) is True
    _pump(turn_game)

    # Next player turn starts for both players
    assert turn_game.turn_state_for(first.id)["is_my_turn"] is True
    assert turn_game.turn_state_for(second.id)["is_my_turn"] is True


def test_multiple_players_move_and_mobs_act_in_dungeon_phase(turn_game):
    p1 = _add_hero(turn_game, 5, 5)
    p2 = turn_game.add_player("p2", "Hero2")
    p2.pos = Position(x=8, y=8)
    p2.floor_id = 1
    rat = _add_mob(turn_game, 5, 8)
    rat.ai_state = "hunting"
    _pump(turn_game)

    assert turn_game.turn_state_for(p1.id)["is_my_turn"] is True
    assert turn_game.turn_state_for(p2.id)["is_my_turn"] is True

    # Player 1 moves RIGHT
    assert turn_game.submit_turn_action(p1.id, msg.Move(type="MOVE", direction=Direction.RIGHT)) is True
    # Player 2 moves UP
    assert turn_game.submit_turn_action(p2.id, msg.Move(type="MOVE", direction=Direction.UP)) is True

    # Pump resolves actions and dungeon faction phase
    _pump(turn_game)

    assert (p1.pos.x, p1.pos.y) == (6, 5)
    assert (p2.pos.x, p2.pos.y) == (8, 7)
    # Dungeon mob moved towards p1 or p2
    assert (rat.pos.x, rat.pos.y) != (5, 8)
    # Turn clock incremented
    assert turn_game.scheduler.now == pytest.approx(1.0)
    # New player turn is ready for both players
    assert turn_game.turn_state_for(p1.id)["is_my_turn"] is True
    assert turn_game.turn_state_for(p2.id)["is_my_turn"] is True


def test_turn_timer_auto_waits_only_unacted_players(turn_game):
    p1 = _add_hero(turn_game, 5, 5)
    p2 = turn_game.add_player("p2", "Hero2")
    p2.pos = Position(x=8, y=8)
    p2.floor_id = 1
    _pump(turn_game)

    # p1 moves
    assert turn_game.submit_turn_action(p1.id, msg.Move(type="MOVE", direction=Direction.RIGHT)) is True
    # p2 does nothing and lets timer expire
    turn_game._turn_deadline = time.monotonic() - 1.0
    _pump(turn_game, ticks=4)

    # p1 moved, p2 was auto-waited
    assert (p1.pos.x, p1.pos.y) == (6, 5)
    assert (p2.pos.x, p2.pos.y) == (8, 8)
    assert turn_game.scheduler.now == pytest.approx(1.0)
    assert turn_game.turn_state_for(p1.id)["is_my_turn"] is True
    assert turn_game.turn_state_for(p2.id)["is_my_turn"] is True


def test_one_player_autowalks_while_another_moves_manually(turn_game):
    p1 = _add_hero(turn_game, 5, 5)
    p2 = turn_game.add_player("p2", "Hero2")
    p2.pos = Position(x=8, y=8)
    p2.floor_id = 1
    _pump(turn_game)

    # p1 starts a 2-step auto-walk
    assert _walk(turn_game, p1, [(1, 0), (1, 0)]) is True
    # p2 makes a single step
    assert turn_game.submit_turn_action(p2.id, msg.Move(type="MOVE", direction=Direction.UP)) is True

    _pump(turn_game, ticks=1)
    assert (p1.pos.x, p1.pos.y) == (6, 5)
    assert (p2.pos.x, p2.pos.y) == (8, 7)
    assert turn_game.scheduler.now == pytest.approx(1.0)

    # Turn 2: p1 continues auto-walk; p2 makes another step
    # Reset movement cooldown for step pacing in pump
    p1.movement._cooldown_until = 0.0
    assert turn_game.submit_turn_action(p2.id, msg.Move(type="MOVE", direction=Direction.LEFT)) is True

    _pump(turn_game, ticks=1)
    assert (p1.pos.x, p1.pos.y) == (7, 5)
    assert (p2.pos.x, p2.pos.y) == (7, 7)
    assert turn_game.scheduler.now == pytest.approx(2.0)
    assert p1.movement.has_path() is False


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

    # Second player commits an action, putting them in the "already acted" state
    assert turn_game.submit_turn_action(second.id, msg.Wait(type="WAIT")) is True
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

    # Mob took its turn and stepped closer to hero
    assert rat.pos.x < 7 or (rat.pos.x, rat.pos.y) != (7, 5)
    # The room resumes for the hero:
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


def test_all_mobs_take_turns_in_dungeon_phase(turn_game):
    _add_hero(turn_game, 5, 5)
    rat1 = _add_mob(turn_game, 8, 5)
    rat2 = _add_mob(turn_game, 9, 5)
    stepped = []
    turn_game._tick_mob = lambda mob, floor, floor_id: stepped.append(mob.id)
    _pump(turn_game)

    turn_game.submit_turn_action("p1", msg.Wait(type="WAIT"))
    _pump(turn_game)

    assert rat1.id in stepped
    assert rat2.id in stepped


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
    """Dead actors are dropped and do not act during rounds."""
    hero = _add_hero(turn_game, 5, 5)
    rat = _add_mob(turn_game, 7, 5)
    _pump(turn_game)

    hero = turn_game.players["p1"]
    rat.is_alive = False
    hero.is_alive = False
    _pump(turn_game)

    assert set(turn_game._player_actors) == set()
    assert set(turn_game._mob_actors) == set()


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


def test_turn_based_walk_is_paced_by_step_duration(turn_game):
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    assert _walk(turn_game, hero, [(0, 1), (0, 1)]) is True
    # First step executes immediately on the submitted action
    turn_game.update_tick(TICK)
    assert (hero.pos.x, hero.pos.y) == (5, 6)
    assert hero.movement.has_path() is True
    assert hero.movement._cooldown_until > time.time()

    # Second step does NOT execute while on cooldown
    turn_game.update_tick(TICK)
    assert (hero.pos.x, hero.pos.y) == (5, 6)

    # Once cooldown expires, step 2 executes
    hero.movement._cooldown_until = 0.0
    turn_game.update_tick(TICK)
    assert (hero.pos.x, hero.pos.y) == (5, 7)
    assert hero.movement.has_path() is False


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

    turn_game._get_or_create_floor(2)
    hero.floor_id = 2
    _pump(turn_game, ticks=2)

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


def test_weapon_attack_delays_match_spd(turn_game):
    from app.engine.entities.items.equip import Dagger, make_named_melee_weapon, Ring
    hero = _add_hero(turn_game, 5, 5)
    _pump(turn_game)

    # Standard starting worn shortsword (delay = 1.0)
    action = build_turn_action(turn_game, hero, msg.Attack(type="ATTACK", target_id="mob1"))
    assert action is not None
    assert action.cost == pytest.approx(1.0)

    # Dagger (delay = 0.84)
    dagger = Dagger(id="dag1")
    hero.belongings.weapon = dagger
    action = build_turn_action(turn_game, hero, msg.Attack(type="ATTACK", target_id="mob1"))
    assert action is not None
    assert action.cost == pytest.approx(0.84)

    # Spear (tier 2, delay = 1.5, reach = 2)
    spear = make_named_melee_weapon("Spear")
    hero.belongings.weapon = spear
    hero.strength = 12
    action = build_turn_action(turn_game, hero, msg.Attack(type="ATTACK", target_id="mob1"))
    assert action is not None
    assert action.cost == pytest.approx(1.5)

    # Spear augmented for speed: 1.5 * (2/3) = 1.0
    spear.augment = "speed"
    action = build_turn_action(turn_game, hero, msg.Attack(type="ATTACK", target_id="mob1"))
    assert action is not None
    assert action.cost == pytest.approx(1.0)

    # Ring of Furor (+2 -> buffed bonus L = 3 -> 1.09051^3)
    furor_ring = Ring(id="furor1", buff_class="furor", level=2, level_known=True, cursed=False)
    hero.belongings.ring = furor_ring
    spear.augment = None
    action = build_turn_action(turn_game, hero, msg.Attack(type="ATTACK", target_id="mob1"))
    assert action is not None
    assert action.cost == pytest.approx(1.5 / (1.09051 ** 3))

    # Lethal Momentum buff reduces attack delay to 0
    hero.add_buff("lethal_momentum", duration=5)
    action = build_turn_action(turn_game, hero, msg.Attack(type="ATTACK", target_id="mob1"))
    assert action is not None
    assert action.cost == 0.0


def test_equip_and_drop_costs_match_spd(turn_game):
    from app.engine.entities.items.equip import ClothArmor, Dagger
    from app.engine.entities.talent_enum import Talent
    from app.engine.game.constants import TIME_TO_DROP, TIME_TO_EQUIP
    hero = _add_hero(turn_game, 5, 5)
    armor = ClothArmor(id="arm1")
    hero.belongings.backpack.collect(armor)
    _pump(turn_game)

    # Equipping costs TIME_TO_EQUIP (1.0)
    equip_act = build_turn_action(turn_game, hero, msg.EquipItem(type="EQUIP_ITEM", item_id="arm1"))
    assert equip_act is not None
    assert equip_act.cost == TIME_TO_EQUIP == 1.0

    # Dropping costs TIME_TO_DROP (1.0)
    drop_act = build_turn_action(turn_game, hero, msg.DropItem(type="DROP_ITEM", item_id="arm1"))
    assert drop_act is not None
    assert drop_act.cost == TIME_TO_DROP == 1.0

    # Swift Equip talent allows 0-turn weapon equip
    dagger = Dagger(id="dag2")
    hero.belongings.backpack.collect(dagger)
    hero.talent_info.talents[Talent.SWIFT_EQUIP] = 1
    hero.swift_equip_charges = 1
    equip_dag = build_turn_action(turn_game, hero, msg.EquipItem(type="EQUIP_ITEM", item_id="dag2"))
    assert equip_dag is not None
    assert equip_dag.cost == 0.0


def test_use_item_dynamic_costs(turn_game):
    from app.engine.entities.items.potions import HealthPotion
    from app.engine.game.constants import TIME_TO_DRINK, TIME_TO_EAT
    hero = _add_hero(turn_game, 5, 5)
    pot = HealthPotion(id="pot1")
    hero.belongings.backpack.collect(pot)
    food = next(i for i in hero.belongings.all_items() if i.type == "food")
    _pump(turn_game)

    # UseItem for potion charges TIME_TO_DRINK (1.0)
    use_pot = build_turn_action(turn_game, hero, msg.UseItem(type="USE_ITEM", item_id="pot1"))
    assert use_pot is not None
    assert use_pot.cost == TIME_TO_DRINK == 1.0

    # UseItem for food charges TIME_TO_EAT (3.0)
    use_food = build_turn_action(turn_game, hero, msg.UseItem(type="USE_ITEM", item_id=food.id))
    assert use_food is not None
    assert use_food.cost == TIME_TO_EAT == 3.0


def test_targeted_scrolls_and_stones_do_not_double_charge(turn_game):
    from app.engine.entities.items.scrolls import ScrollOfUpgrade, ScrollOfTeleportation
    from app.engine.entities.runestones import StoneOfIntuition
    from app.engine.game.constants import TIME_TO_ABILITY, TIME_TO_READ
    hero = _add_hero(turn_game, 5, 5)
    scroll_up = ScrollOfUpgrade(id="up1")
    scroll_tp = ScrollOfTeleportation(id="tp1")
    stone_int = StoneOfIntuition(id="st1")
    hero.belongings.backpack.collect(scroll_up)
    hero.belongings.backpack.collect(scroll_tp)
    hero.belongings.backpack.collect(stone_int)
    _pump(turn_game)

    # Reading a targeted scroll (Upgrade) opens target menu for 0.0 turns
    act_read_up = build_turn_action(
        turn_game, hero, msg.ExecuteItemAction(type="EXECUTE_ITEM_ACTION", item_id="up1", action="READ")
    )
    assert act_read_up is not None
    assert act_read_up.cost == 0.0

    # Selecting the target charges TIME_TO_READ (1.0)
    act_sel = build_turn_action(
        turn_game, hero, msg.SelectScrollTarget(type="SELECT_SCROLL_TARGET", scroll_id="up1", item_id=hero.belongings.weapon.id)
    )
    assert act_sel is not None
    assert act_sel.cost == TIME_TO_READ == 1.0

    # Self-cast scroll (Teleportation) charges TIME_TO_READ (1.0) directly on read
    act_read_tp = build_turn_action(
        turn_game, hero, msg.ExecuteItemAction(type="EXECUTE_ITEM_ACTION", item_id="tp1", action="READ")
    )
    assert act_read_tp is not None
    assert act_read_tp.cost == TIME_TO_READ == 1.0

    # Using Stone of Intuition opens selection for 0.0 turns
    act_stone_use = build_turn_action(
        turn_game, hero, msg.ExecuteItemAction(type="EXECUTE_ITEM_ACTION", item_id="st1", action="USE")
    )
    assert act_stone_use is not None
    assert act_stone_use.cost == 0.0

    # Choosing candidate item is a menu step (0.0 turns)
    act_stone_pick = build_turn_action(
        turn_game, hero, msg.StoneIntuitionChooseItem(type="STONE_INTUITION_CHOOSE_ITEM", stone_id="st1", item_id="x")
    )
    assert act_stone_pick is not None
    assert act_stone_pick.cost == 0.0

    # Submitting guess charges TIME_TO_ABILITY (1.0)
    act_stone_guess = build_turn_action(
        turn_game, hero, msg.StoneIntuitionGuess(type="STONE_INTUITION_GUESS", stone_id="st1", item_id="x", guessed_kind="scroll_of_upgrade")
    )
    assert act_stone_guess is not None
    assert act_stone_guess.cost == TIME_TO_ABILITY == 1.0


def test_mob_attack_delay_and_ranged_attacks(turn_game):
    from app.engine.entities.mobs.caves import Monk
    from app.engine.entities.mobs.prison import Thief
    from app.engine.game.constants import TIME_TO_ATTACK
    hero = _add_hero(turn_game, 5, 5)
    hero.hp = 1000
    hero.max_hp = 1000

    # Normal mob melee attack cost
    rat = _add_mob(turn_game, 5, 6)
    _pump(turn_game)
    cost = turn_game._mob_take_turn(rat)
    assert cost == pytest.approx(TIME_TO_ATTACK)

    # Monk with faster attack_cooldown
    monk = _add_mob(turn_game, 5, 4, mob_cls=Monk)
    cost_monk = turn_game._mob_take_turn(monk)
    assert cost_monk == pytest.approx(0.5)

    # Chilled / slowed mob attacks with double delay
    rat.add_buff("chill", duration=5)
    cost_chilled = turn_game._mob_take_turn(rat)
    assert cost_chilled == pytest.approx(TIME_TO_ATTACK * 2.0)


# --- surprise attack mechanics in turn-based mode -------------------------


def test_turn_based_doorway_break_los_surprise_crit(turn_game):
    """When a mob loses LOS behind a door and opens it, hero's first strike is a surprise crit."""
    floor = turn_game._get_or_create_floor(1)
    hero = _add_hero(turn_game, 4, 5)
    hero.attack_skill = 100

    # Put a closed door at (5, 5) and wall around it
    floor.grid[5][5] = TileType.DOOR
    floor.grid[4][5] = TileType.WALL
    floor.grid[6][5] = TileType.WALL
    floor.rebuild_flags()

    # Place mob at (6, 5) in hunting state
    mob = _add_mob(turn_game, 6, 5)
    mob.ai_state = "hunting"
    mob.hp = 100
    mob.max_hp = 100
    mob.defense_skill = 50

    _pump(turn_game)

    # Turn 1: Mob takes turn from (6, 5). It cannot see hero at (4, 5) through closed door.
    # Mob's enemy_seen becomes False, and mob moves to (5, 5) opening the door.
    turn_game._mob_take_turn(mob)
    assert (mob.pos.x, mob.pos.y) == (5, 5)
    assert mob.enemy_seen.get(hero.id) is False

    # Turn 2: Hero at (4, 5) attacks mob at (5, 5)
    turn_game.events.clear()
    turn_game.submit_turn_action(
        hero.id, msg.Attack(type="ATTACK", target_id=mob.id)
    )
    _pump(turn_game)

    attack_events = [
        ev for ev in turn_game.events
        if ev["type"] == "ATTACK" and ev["data"].get("target") == mob.id
    ]
    assert attack_events, "Attack event should be emitted"
    assert attack_events[-1]["data"]["surprise"] is True
    assert attack_events[-1]["data"]["crit"] is True

    # Turn 3: Mob takes its next turn from (5, 5). Now in LOS of hero at (4, 5).
    # Mob sees hero, so enemy_seen becomes True.
    turn_game._mob_take_turn(mob)
    assert mob.enemy_seen.get(hero.id) is True

    # Turn 4: Hero attacks mob again -> no longer a surprise attack
    turn_game.events.clear()
    turn_game.submit_turn_action(
        hero.id, msg.Attack(type="ATTACK", target_id=mob.id)
    )
    _pump(turn_game)

    attack_events2 = [
        ev for ev in turn_game.events
        if ev["type"] == "ATTACK" and ev["data"].get("target") == mob.id
    ]
    assert attack_events2, "Second attack event should be emitted"
    assert attack_events2[-1]["data"]["surprise"] is False
    assert attack_events2[-1]["data"]["crit"] is False


def test_turn_based_corner_break_los_surprise_crit(turn_game):
    """When a mob loses LOS around a corner, hero's attack is a surprise attack."""
    floor = turn_game._get_or_create_floor(1)
    hero = _add_hero(turn_game, 4, 4)
    hero.attack_skill = 100

    # Wall at (5, 4) and (5, 5)
    floor.grid[4][5] = TileType.WALL
    floor.grid[5][5] = TileType.WALL
    floor.rebuild_flags()

    # Mob at (6, 5) in hunting state
    mob = _add_mob(turn_game, 6, 5)
    mob.ai_state = "hunting"
    mob.hp = 100
    mob.max_hp = 100

    _pump(turn_game)

    # Mob takes turn: starts at (6, 5) with no LOS to (4, 4).
    # Mob's enemy_seen becomes False.
    turn_game._mob_take_turn(mob)
    assert mob.enemy_seen.get(hero.id) is False

    # Hero steps to (4, 5) and attacks mob
    turn_game.events.clear()
    # Hero melee attack
    from app.engine.systems.combat import resolve_melee_attack
    result = resolve_melee_attack(
        hero, mob, floor.mobs, hero.pos.x, hero.pos.y,
        is_in_los=lambda a, b: turn_game._is_in_los(a, b, floor_id=1),
        game=turn_game,
    )
    assert result["hit"] is True
    assert result["surprise"] is True
    assert result["crit"] is True


def test_turn_based_waiting_gives_mob_vision_cancels_surprise(turn_game):
    """If hero waits after mob enters doorway, mob gains vision and surprise is lost."""
    floor = turn_game._get_or_create_floor(1)
    hero = _add_hero(turn_game, 4, 5)

    floor.grid[5][5] = TileType.DOOR
    floor.rebuild_flags()

    mob = _add_mob(turn_game, 6, 5)
    mob.ai_state = "hunting"
    mob.hp = 100
    mob.max_hp = 100

    _pump(turn_game)

    # Mob steps into doorway, opening door. enemy_seen is False.
    turn_game._mob_take_turn(mob)
    assert (mob.pos.x, mob.pos.y) == (5, 5)
    assert mob.enemy_seen.get(hero.id) is False

    # Hero decides to WAIT instead of attacking
    turn_game.submit_turn_action(hero.id, msg.Wait(type="WAIT"))
    _pump(turn_game)

    # Mob takes turn from (5, 5), seeing hero at (4, 5). enemy_seen becomes True.
    turn_game._mob_take_turn(mob)
    assert mob.enemy_seen.get(hero.id) is True

    # Hero attacks now -> not surprise
    turn_game.events.clear()
    turn_game.submit_turn_action(
        hero.id, msg.Attack(type="ATTACK", target_id=mob.id)
    )
    _pump(turn_game)

    attack_events = [
        ev for ev in turn_game.events
        if ev["type"] == "ATTACK" and ev["data"].get("target") == mob.id
    ]
    assert attack_events
    assert attack_events[-1]["data"]["surprise"] is False
    assert attack_events[-1]["data"]["crit"] is False


def test_turn_based_flail_cannot_surprise_attack(turn_game):
    """Hero with a Flail cannot make surprise attacks even when mob lost LOS."""
    from app.engine.entities.items.equip import make_named_melee_weapon
    hero = _add_hero(turn_game, 4, 5)
    hero.strength = 18
    hero.belongings.weapon = make_named_melee_weapon("Flail")

    mob = _add_mob(turn_game, 5, 5)
    mob.ai_state = "hunting"
    mob.enemy_seen[hero.id] = False

    from app.engine.systems.combat import resolve_melee_attack
    result = resolve_melee_attack(
        hero, mob, {}, hero.pos.x, hero.pos.y,
        is_in_los=lambda a, b: True,
        game=turn_game,
    )
    assert result["surprise"] is False
    assert result["crit"] is False


def test_turn_based_wand_surprise_attack_on_los_break(turn_game):
    """Wand zap on a mob that lost LOS lands as a surprise crit in turn-based mode."""
    from app.engine.entities.items.wands import WandOfMagicMissile
    from app.engine.systems.combat import resolve_ranged_attack
    hero = _add_hero(turn_game, 2, 5)
    mob = _add_mob(turn_game, 5, 5)
    mob.ai_state = "hunting"
    mob.enemy_seen[hero.id] = False
    mob.hp = 50
    mob.max_hp = 50

    wand = WandOfMagicMissile(id="w1", charges=3)
    result = resolve_ranged_attack(
        hero, mob, wand, {}, hero.pos.x, hero.pos.y,
        is_in_los=lambda a, b: True,
        game=turn_game,
    )
    assert result["hit"] is True
    assert result["surprise"] is True
    assert result["crit"] is True


def test_turn_based_multiplayer_per_player_surprise_isolation(turn_game):
    """In multiplayer, a mob losing LOS on player 1 but not player 2 is surprised only by player 1."""
    floor = turn_game._get_or_create_floor(1)
    p1 = _add_hero(turn_game, 4, 5)
    p2 = turn_game.add_player("p2", "Hero2")
    p2.pos = Position(x=8, y=5)
    p2.floor_id = 1

    floor.grid[5][5] = TileType.DOOR
    floor.rebuild_flags()

    mob = _add_mob(turn_game, 6, 5)
    mob.ai_state = "hunting"
    mob.hp = 100
    mob.max_hp = 100

    _pump(turn_game)

    # Mob takes turn from (6, 5):
    # p1 at (4, 5) is behind closed door -> in_los is False -> enemy_seen[p1] is False.
    # p2 at (8, 5) is in open corridor -> in_los is True -> enemy_seen[p2] is True.
    turn_game._mob_take_turn(mob)
    assert mob.enemy_seen.get(p1.id) is False
    assert mob.enemy_seen.get(p2.id) is True

    from app.engine.systems.combat import resolve_melee_attack
    # p1 attacks mob: surprise attack!
    res1 = resolve_melee_attack(
        p1, mob, floor.mobs, p1.pos.x, p1.pos.y,
        is_in_los=lambda a, b: True,
        game=turn_game,
    )
    assert res1["surprise"] is True
    assert res1["crit"] is True

    # p2 attacks mob: mob saw p2 on its turn -> not surprise!
    res2 = resolve_melee_attack(
        p2, mob, floor.mobs, p2.pos.x, p2.pos.y,
        is_in_los=lambda a, b: True,
        game=turn_game,
    )
    assert res2["surprise"] is False
    assert res2["crit"] is False


def test_turn_based_sleeping_mob_is_surprise_attack(turn_game):
    """Attacking a sleeping/idle mob in turn-based mode is always a surprise attack."""
    hero = _add_hero(turn_game, 4, 5)
    mob = _add_mob(turn_game, 5, 5)
    mob.ai_state = "sleeping"
    mob.hp = 50
    mob.max_hp = 50

    from app.engine.systems.combat import resolve_melee_attack
    res = resolve_melee_attack(
        hero, mob, {}, hero.pos.x, hero.pos.y,
        is_in_los=lambda a, b: True,
        game=turn_game,
    )
    assert res["hit"] is True
    assert res["surprise"] is True
    assert res["crit"] is True


def test_turn_based_afk_player_does_not_block_round_progression(turn_game):
    p1 = _add_hero(turn_game, 5, 5)
    p2 = turn_game.add_player("p2", "Hero2")
    p2.pos = Position(x=8, y=8)
    p2.floor_id = 1
    _pump(turn_game)

    # p2 disconnects / is marked AFK
    p2.is_afk = True
    _pump(turn_game)

    # Turn state for p2 shows not their turn and empty order
    p2_state = turn_game.turn_state_for(p2.id)
    assert p2_state["is_my_turn"] is False
    assert p2_state["order"] == []

    # Turn state for p1 only lists active players in turn order
    p1_state = turn_game.turn_state_for(p1.id)
    assert p1_state["is_my_turn"] is True
    assert [entry["id"] for entry in p1_state["order"] if entry["kind"] == "player"] == [p1.id]

    # p1 moves: round resolves immediately without waiting for p2 or timer
    assert turn_game.submit_turn_action(p1.id, msg.Move(type="MOVE", direction=Direction.RIGHT)) is True
    _pump(turn_game)

    assert (p1.pos.x, p1.pos.y) == (6, 5)
    assert turn_game.scheduler.now == pytest.approx(1.0)
    assert turn_game.turn_state_for(p1.id)["is_my_turn"] is True


def test_turn_based_player_and_mob_walk_through_afk_player(turn_game):
    p1 = _add_hero(turn_game, 5, 5)
    p2 = turn_game.add_player("p2", "Hero2")
    p2.pos = Position(x=6, y=5)
    p2.floor_id = 1
    p2.is_afk = True

    _pump(turn_game)

    # p1 steps right into p2's tile
    assert turn_game.submit_turn_action(p1.id, msg.Move(type="MOVE", direction=Direction.RIGHT)) is True
    _pump(turn_game)

    assert (p1.pos.x, p1.pos.y) == (6, 5), "p1 should step right onto the AFK player's tile"

    # Move p1 away from p2's tile
    assert turn_game.submit_turn_action(p1.id, msg.Move(type="MOVE", direction=Direction.UP)) is True
    _pump(turn_game)
    assert (p1.pos.x, p1.pos.y) == (6, 4)

    # Mob steps right into p2's tile
    rat = _add_mob(turn_game, 7, 5)
    rat.ai_state = "hunting"
    turn_game.move_entity(rat.id, -1, 0)
    assert (rat.pos.x, rat.pos.y) == (6, 5), "mob should walk straight onto the AFK player's tile"


def test_turn_based_mobs_never_attack_afk_player(turn_game):
    p1 = _add_hero(turn_game, 1, 1)
    p2 = turn_game.add_player("p2", "Hero2")
    p2.pos = Position(x=5, y=5)
    p2.floor_id = 1
    p2.is_afk = True

    rat = _add_mob(turn_game, 5, 6)
    rat.ai_state = "hunting"
    rat.engaged = True

    floor = turn_game._get_or_create_floor(1)
    assert turn_game._mob_can_strike(rat, floor, 1) is False

    initial_hp = p2.hp
    for _ in range(10):
        turn_game.submit_turn_action(p1.id, msg.Wait(type="WAIT"))
        _pump(turn_game)
        assert p2.hp == initial_hp, "AFK player should not take damage from mobs"


def test_turn_based_ballistica_passes_through_afk_player(turn_game):
    from app.engine.systems.ballistica import ballistica_trace
    p1 = _add_hero(turn_game, 1, 5)
    p2 = turn_game.add_player("p2", "Hero2")
    p2.pos = Position(x=3, y=5)
    p2.floor_id = 1
    p2.is_afk = True

    floor = turn_game._get_or_create_floor(1)
    # Projectile from (1, 5) to (5, 5) should pass through p2 at (3, 5) to reach (5, 5)
    col_x, col_y = ballistica_trace(
        1, 5, 5, 5,
        floor.flags, floor.width, floor.height,
        list(turn_game.players.values()),
        list(floor.mobs.values()),
        p1.id,
    )
    assert (col_x, col_y) == (5, 5), "ballistica should pass through AFK player"


def test_turn_based_reconnect_restores_player_to_turn_scheduler(turn_game):
    p1 = _add_hero(turn_game, 5, 5)
    p2 = turn_game.add_player("p2", "Hero2")
    p2.pos = Position(x=8, y=8)
    p2.floor_id = 1
    _pump(turn_game)

    # p2 disconnects
    p2.is_afk = True
    _pump(turn_game)
    assert len(turn_game._active_players()) == 1

    # p1 takes a turn
    assert turn_game.submit_turn_action(p1.id, msg.Move(type="MOVE", direction=Direction.RIGHT)) is True
    _pump(turn_game)
    assert (p1.pos.x, p1.pos.y) == (6, 5)

    # p2 reconnects
    p2.is_afk = False
    _pump(turn_game)
    assert len(turn_game._active_players()) == 2
    assert turn_game.turn_state_for(p2.id)["is_my_turn"] is True

    # Now both players must act again
    assert turn_game.submit_turn_action(p1.id, msg.Move(type="MOVE", direction=Direction.RIGHT)) is True
    _pump(turn_game)
    # p1's step executed, but turn round does NOT complete yet because p2 has not acted
    assert (p1.pos.x, p1.pos.y) == (7, 5)
    assert turn_game.scheduler.now == pytest.approx(1.0)
    assert turn_game.turn_state_for(p2.id)["is_my_turn"] is True

    assert turn_game.submit_turn_action(p2.id, msg.Move(type="MOVE", direction=Direction.UP)) is True
    _pump(turn_game)
    # Now both acted and round completes; clock advances
    assert (p1.pos.x, p1.pos.y) == (7, 5)
    assert (p2.pos.x, p2.pos.y) == (8, 7)
    assert turn_game.scheduler.now == pytest.approx(2.0)



