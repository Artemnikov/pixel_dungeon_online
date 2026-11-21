# Copyright (C) 2026 ArtemNikov
#
"""Turn rooms charge every mob the SPD time its turn spent (Actor.spend)."""

import pytest

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.mobs.sewers import Rat
from app.engine.turn.instance import TurnBasedGameInstance


@pytest.fixture
def room():
    g = TurnBasedGameInstance("turn-time")
    g.players = {}
    floor = g._get_or_create_floor(1)
    floor.grid = [[TileType.FLOOR for _ in range(20)] for _ in range(20)]
    floor.mobs.clear()
    floor.rebuild_flags()
    hero = g.add_player("p1", "Hero")
    hero.pos = Position(x=2, y=2)
    hero.floor_id = 1
    return g


def _timed_mob(game, cost, spawn_delay=0.0):
    floor = game._get_or_create_floor(1)
    mob = game._spawn_mob_at(Rat, 15, 15)
    mob.floor_id = 1
    mob.spawn_delay = spawn_delay
    floor.mobs[mob.id] = mob
    calls = []
    actor = game._ensure_mob_actor(mob, 1)

    def fake_turn(_g, a=actor):
        calls.append(a.scheduled_time)
        return cost

    actor.brain.take_turn = fake_turn
    return mob, calls


def _rounds(game, n):
    for _ in range(n):
        game._resolve_dungeon_phase()


def test_speed_two_mob_acts_twice_per_round(room):
    _, calls = _timed_mob(room, 0.5)
    _rounds(room, 3)
    assert calls == [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]


def test_two_turn_spend_skips_a_round(room):
    _, calls = _timed_mob(room, 2.0)
    _rounds(room, 4)
    assert calls == [0.0, 2.0]


def test_one_and_a_half_turn_spend_acts_twice_in_three_rounds(room):
    _, calls = _timed_mob(room, 1.5)
    _rounds(room, 3)
    assert calls == [0.0, 1.5]


def test_spawn_delay_holds_first_act(room):
    _, calls = _timed_mob(room, 1.0, spawn_delay=4.0)
    _rounds(room, 6)
    assert calls == [4.0, 5.0]


def test_idle_time_is_not_banked(room):
    mob, calls = _timed_mob(room, 1.0)
    actor = room._mob_actors[mob.id]
    room.scheduler.now = 10.0
    actor.scheduled_time = 0.0
    _rounds(room, 1)
    assert calls == [10.0]
