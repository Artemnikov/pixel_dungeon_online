from app.engine.game.constants import HERO_PRIO, MOB_PRIO, TIME_TO_WAIT
from app.engine.turn.actors import ActorRef, MobActor, PlayerActor
from app.engine.turn.scheduler import TurnScheduler


class _StubActor(ActorRef):
    def __init__(self, entity_id, act_priority=MOB_PRIO):
        super().__init__(entity_id, act_priority)


def _drain(scheduler, actor, cost, pops):
    scheduler.reschedule(actor, cost)
    pops.append(actor.entity_id)


def test_pop_orders_by_scheduled_time():
    scheduler = TurnScheduler()
    slow = _StubActor("slow")
    fast = _StubActor("fast")
    scheduler.schedule(slow, 2.0)
    scheduler.schedule(fast, 1.0)

    assert scheduler.pop() is fast
    assert scheduler.now == 1.0
    assert scheduler.pop() is slow
    assert scheduler.now == 2.0


def test_speed_interleave_half_cost_acts_twice():
    scheduler = TurnScheduler()
    fast = _StubActor("fast")
    slow = _StubActor("slow")
    scheduler.schedule(fast, 0.0)
    scheduler.schedule(slow, 0.0)

    pops = []
    for _ in range(6):
        actor = scheduler.pop()
        _drain(scheduler, actor, 0.5 if actor is fast else 1.0, pops)

    assert pops == ["fast", "slow", "fast", "slow", "fast", "fast"]


def test_hero_pops_before_mob_on_time_tie():
    scheduler = TurnScheduler()
    mob = _StubActor("mob", MOB_PRIO)
    hero = _StubActor("hero", HERO_PRIO)
    scheduler.schedule(mob, 1.0)
    scheduler.schedule(hero, 1.0)

    assert scheduler.pop() is hero
    assert scheduler.pop() is mob


def test_schedule_snaps_near_integer_times():
    scheduler = TurnScheduler()
    actor = _StubActor("a")
    scheduler.schedule(actor, 1.0 - 5e-4)
    assert actor.scheduled_time == 1.0

    other = _StubActor("b")
    scheduler.schedule(other, 0.5)
    assert other.scheduled_time == 0.5


def test_seq_gives_stable_order_within_same_time_and_priority():
    scheduler = TurnScheduler()
    actors = [_StubActor(f"a{i}") for i in range(3)]
    for actor in actors:
        scheduler.schedule(actor, 1.0)

    assert [scheduler.pop() for _ in range(3)] == actors


def test_push_back_reinserts_without_changing_time():
    scheduler = TurnScheduler()
    actor = _StubActor("a")
    scheduler.schedule(actor, 3.0)
    scheduler.pop()
    scheduler.push_back(actor)

    assert actor.scheduled_time == 3.0
    assert scheduler.pop() is actor
    assert scheduler.now == 3.0


class _FakeAction:
    def __init__(self, cost):
        self.cost = cost
        self.calls = []

    def execute(self, game, player):
        self.calls.append(player.id)
        return self.cost


def test_player_actor_requires_input(game):
    player = game.add_player("p1", "Tester")
    actor = PlayerActor(player)

    assert actor.requires_input() is True

    actor.pending_action = _FakeAction(1.0)
    assert actor.requires_input() is False

    actor.pending_action = None
    player.is_downed = True
    assert actor.requires_input() is False

    player.is_downed = False
    player.is_alive = False
    assert actor.requires_input() is False


def test_player_actor_take_turn_executes_and_clears_pending(game):
    player = game.add_player("p1", "Tester")
    actor = PlayerActor(player)
    action = _FakeAction(0.75)
    actor.pending_action = action

    assert actor.take_turn(game) == 0.75
    assert actor.pending_action is None
    assert action.calls == [player.id]


def test_player_actor_take_turn_without_action_waits(game):
    player = game.add_player("p1", "Tester")
    actor = PlayerActor(player)

    assert actor.take_turn(game) == TIME_TO_WAIT


def test_mob_actor_take_turn_dispatches_to_its_brain(game):
    mob = type("Mob", (), {"id": "m1"})()
    actor = MobActor(mob, 3)
    seen = []

    def _take_turn(game):
        seen.append(game)
        return 0.5

    actor.brain.take_turn = _take_turn

    assert actor.take_turn(game) == 0.5
    assert seen == [game]
    assert actor.requires_input() is False


def test_mob_actor_retarget_moves_the_brain_to_the_new_floor(game):
    mob_a = type("Mob", (), {"id": "m1"})()
    mob_b = type("Mob", (), {"id": "m2"})()
    actor = MobActor(mob_a, 3)

    actor.retarget(mob_b, 7)

    assert actor.mob is mob_b
    assert actor.floor_id == 7
    assert actor.brain.mob is mob_b
    assert actor.brain.floor_id == 7
    # The scheduler keys off the id the actor was registered under.
    assert actor.entity_id == "m1"
