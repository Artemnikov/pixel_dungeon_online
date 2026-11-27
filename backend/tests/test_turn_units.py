# Copyright (C) 2026 ArtemNikov
#
"""Per-turn world systems advance one SPD turn per turn in both room modes."""

import random

import pytest

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.buffs import add_buff, get_buff
from app.engine.entities.mobs.sewers import Rat
from app.engine.game.bleeding import apply_bleeding, tick_bleeding
from app.engine.game.blobs import tick_blob_areas
from app.engine.game.constants import TICKS_PER_TURN, TICK_DURATION
from app.engine.game.deferred_damage import extend_deferred, tick_deferred_damage
from tests.conftest import make_open_floor


class _Clock:
    """Minimal game stand-in for the per-turn helpers."""

    def __init__(self, turn_room: bool):
        self.sim_ticks = TICKS_PER_TURN if turn_room else 1
        self.sim_unit = 1.0 if turn_room else TICK_DURATION
        self.events = []

    def add_event(self, kind, data, floor_id=None):
        self.events.append((kind, data))


def _calls_per_turn(turn_room: bool) -> int:
    return 1 if turn_room else TICKS_PER_TURN


@pytest.mark.parametrize("turn_room", [False, True])
def test_fire_of_volume_four_burns_four_turns(turn_room):
    clock = _Clock(turn_room)
    floor = make_open_floor(1, 6, 6)
    floor.blob_areas["f"] = {"type": "fire", "cells": {(2, 2)}, "volume": {(2, 2): 4}}
    alive_turns = 0
    for _ in range(8):
        for _ in range(_calls_per_turn(turn_room)):
            tick_blob_areas({1: floor}, {}, clock.sim_unit, clock.sim_ticks)
        if "f" in floor.blob_areas:
            alive_turns += 1
    assert alive_turns == 3


@pytest.mark.parametrize("turn_room", [False, True])
def test_toxic_gas_evolves_once_per_turn(turn_room):
    clock = _Clock(turn_room)
    floor = make_open_floor(1, 12, 12)
    floor.blob_areas["g"] = {"type": "toxic_gas", "cells": {(5, 5)}, "volume": {(5, 5): 100}}
    for _ in range(_calls_per_turn(turn_room)):
        tick_blob_areas({1: floor}, {}, clock.sim_unit, clock.sim_ticks)
    vol = floor.blob_areas["g"]["volume"]
    assert vol[(5, 5)] == 100 // 5 - 1
    assert vol[(6, 5)] == 100 // 4 - 1 or vol[(6, 5)] == 100 // 5 - 1


@pytest.mark.parametrize("turn_room", [False, True])
def test_bleeding_decays_and_hits_once_per_turn(turn_room, monkeypatch):
    clock = _Clock(turn_room)
    rat = Rat(id="r", pos=Position(x=1, y=1), hp=100, max_hp=100)
    monkeypatch.setattr("app.engine.game.bleeding.normal_float", lambda lo, hi: hi * 0.75)
    apply_bleeding(rat, 8)
    for _ in range(_calls_per_turn(turn_room)):
        tick_bleeding(clock, rat, 1)
    assert rat.hp == 100 - 6
    for _ in range(_calls_per_turn(turn_room)):
        tick_bleeding(clock, rat, 1)
    assert rat.hp == 100 - 6 - round(4.5)


def test_bleeding_set_only_raises_level():
    rat = Rat(id="r", pos=Position(x=1, y=1))
    apply_bleeding(rat, 8)
    apply_bleeding(rat, 3)
    assert rat.bleeding_level == 8
    assert get_buff(rat.buffs, "bleeding").level == 8


def test_bleeding_detaches_at_zero():
    clock = _Clock(True)
    rat = Rat(id="r", pos=Position(x=1, y=1), hp=100, max_hp=100)
    random.seed(1)
    apply_bleeding(rat, 0.4)
    tick_bleeding(clock, rat, 1)
    assert get_buff(rat.buffs, "bleeding") is None


@pytest.mark.parametrize("turn_room", [False, True])
def test_deferred_damage_waits_a_turn_then_releases_ten_percent(turn_room):
    clock = _Clock(turn_room)
    rat = Rat(id="r", pos=Position(x=1, y=1), hp=300, max_hp=300)
    extend_deferred(rat, 50)
    for _ in range(_calls_per_turn(turn_room) - 1):
        tick_deferred_damage(clock, rat, 1)
    assert rat.hp == 300
    tick_deferred_damage(clock, rat, 1)
    assert rat.hp == 295 and rat.deferred_damage == 45
    for _ in range(_calls_per_turn(turn_room)):
        tick_deferred_damage(clock, rat, 1)
    assert rat.hp == 291 and rat.deferred_damage == 41


def test_burning_ticks_once_per_turn_in_turn_room():
    from app.engine.turn.instance import TurnBasedGameInstance
    g = TurnBasedGameInstance("burn")
    g.players = {}
    floor = g._get_or_create_floor(1)
    floor.grid = [[TileType.FLOOR for _ in range(8)] for _ in range(8)]
    floor.mobs.clear()
    floor.rebuild_flags()
    rat = g._spawn_mob_at(Rat, 3, 3)
    rat.hp = rat.max_hp = 100
    floor.mobs[rat.id] = rat
    add_buff(rat.buffs, "burning", duration=8.0, level=1)
    g._process_burning(1, [])
    assert rat.hp < 100
