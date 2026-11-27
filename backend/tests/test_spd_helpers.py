# Copyright (C) 2026 ArtemNikov
#
import random

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import normal_float, spd_chances
from app.engine.game import spd_act_clock
from app.engine.game.boss_targets import spend_gate
from app.engine.game.constants import TICKS_PER_TURN
from app.engine.systems.spd_ballistica import (
    MAGIC_BOLT, PROJECTILE, STOP_SOLID, WONT_STOP, Ballistica,
)
from tests.conftest import make_open_floor


def test_normal_float_stays_in_range_and_centres():
    random.seed(3)
    rolls = [normal_float(10, 15) for _ in range(5000)]
    assert all(10 <= r < 15 for r in rolls)
    assert abs(sum(rolls) / len(rolls) - 12.5) < 0.1


def test_spd_chances_weights_and_negatives():
    random.seed(4)
    counts = [0, 0, 0]
    for _ in range(6000):
        counts[spd_chances([0, 1, 2])] += 1
    assert counts[0] == 0
    assert abs(counts[2] / 6000 - 2 / 3) < 0.03
    assert spd_chances([0, -1]) == -1


def test_ballistica_straight_line_runs_to_inner_edge():
    floor = make_open_floor(25, 10, 10)
    b = Ballistica((2, 5), (5, 5), WONT_STOP, floor)
    assert b.path[0] == (2, 5)
    assert b.path[-1] == (8, 5)
    assert b.collision_pos == (8, 5)


def test_ballistica_matches_java_dda_on_diagonal_slope():
    floor = make_open_floor(25, 12, 12)
    b = Ballistica((1, 1), (5, 3), WONT_STOP, floor)
    assert b.path[:5] == [(1, 1), (2, 2), (3, 2), (4, 3), (5, 3)]


def test_ballistica_projectile_stops_at_target_and_char():
    floor = make_open_floor(25, 10, 10)
    b = Ballistica((1, 1), (6, 1), PROJECTILE, floor)
    assert b.collision_pos == (6, 1)
    assert b.dist == 5
    blocker = {(4, 1): object()}
    b2 = Ballistica((1, 1), (6, 1), MAGIC_BOLT, floor, lambda x, y: blocker.get((x, y)))
    assert b2.collision_pos == (4, 1)
    assert b2.path[-1] == (8, 1)


def test_ballistica_stop_solid_collides_on_wall():
    floor = make_open_floor(25, 10, 10)
    floor.grid[1][5] = TileType.WALL
    floor.rebuild_flags()
    b = Ballistica((1, 1), (8, 1), STOP_SOLID, floor)
    assert b.collision_pos == (4, 1)
    assert b.sub_path(1, b.dist) == [(2, 1), (3, 1), (4, 1)]


def test_spend_gate_matches_gamemath_gate():
    assert spend_gate(0.4, 1, 3) == 1
    assert spend_gate(1.0, 1, 3) == 1
    assert spend_gate(1.2, 1, 3) == 2
    assert spend_gate(9.0, 1, 3) == 3


class _Clocked:
    def __init__(self):
        self.act_cooldown = 0.0
        self.act_blocking = False
        self.spawn_delay = 0.0
        self.act_spent = None
        self.is_alive = True
        self.speed = 1.0


class _RealtimeGame:
    game_mode = "realtime"
    sim_ticks = 1


def test_act_clock_realtime_acts_once_per_turn():
    mob = _Clocked()
    calls = []
    game = _RealtimeGame()
    for _ in range(TICKS_PER_TURN * 3 - 1):
        spd_act_clock.run(game, mob, lambda: calls.append(1) or 1.0)
    assert len(calls) == 3


def test_act_clock_realtime_spawn_delay_holds_first_act():
    mob = _Clocked()
    spd_act_clock.add_with_delay(mob, 4)
    calls = []
    game = _RealtimeGame()
    for _ in range(TICKS_PER_TURN * 4 - 1):
        assert spd_act_clock.run(game, mob, lambda: calls.append(1) or 1.0)
    assert calls == []
    spd_act_clock.run(game, mob, lambda: calls.append(1) or 1.0)
    assert calls == [1]


def test_act_clock_move_lets_generic_ai_run():
    mob = _Clocked()
    game = _RealtimeGame()
    assert spd_act_clock.run(game, mob, lambda: None) is False
    assert spd_act_clock.run(game, mob, lambda: 1.0) is False


def test_normal_int_range_matches_spd_formula():
    from app.engine.entities.base import normal_int_range
    random.seed(11)
    rolls = [normal_int_range(20, 30) for _ in range(20000)]
    assert min(rolls) == 20 and max(rolls) == 30
    counts = {v: rolls.count(v) for v in range(20, 31)}
    assert counts[25] > counts[22] > counts[20]
    random.seed(12)
    a, b = random.random(), random.random()
    random.seed(12)
    assert normal_int_range(20, 30) == 20 + int((a + b) * 11 / 2)
