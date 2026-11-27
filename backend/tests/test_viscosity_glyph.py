# Copyright (C) 2026 ArtemNikov
#
"""Viscosity glyph: deferred damage is actually dealt later (DeferedDamage)."""

from app.engine.entities.base import Position
from app.engine.entities.buffs import get_buff, remove_buff
from app.engine.entities.armors.armor_glyphs import _proc_viscosity
from app.engine.entities.player import Player
from app.engine.game.constants import TICKS_PER_TURN
from app.engine.game.deferred_damage import tick_deferred_damage


class _Armor:
    def buffed_lvl(self):
        return 2


class _Clock:
    sim_ticks = TICKS_PER_TURN

    def __init__(self):
        self.events = []

    def add_event(self, kind, data, floor_id=None):
        self.events.append(kind)


def _hero():
    return Player(id="p", name="H", pos=Position(x=1, y=1), hp=100, max_hp=100)


def test_viscosity_defers_then_releases_ten_percent_a_turn():
    hero = _hero()
    taken = _proc_viscosity(hero, None, _Armor(), 40, {}, 0, 0, None)
    deferred = 40 - taken
    assert deferred > 0
    assert hero.deferred_damage == deferred
    assert get_buff(hero.buffs, "deferred_damage").level == deferred
    clock = _Clock()
    tick_deferred_damage(clock, hero, 1)
    assert hero.hp == 100 - max(1, int(deferred * 0.1))
    for _ in range(60):
        tick_deferred_damage(clock, hero, 1)
    assert hero.hp == 100 - deferred
    assert get_buff(hero.buffs, "deferred_damage") is None


def test_cleansing_the_indicator_clears_the_pool():
    hero = _hero()
    _proc_viscosity(hero, None, _Armor(), 40, {}, 0, 0, None)
    remove_buff(hero.buffs, "deferred_damage")
    tick_deferred_damage(_Clock(), hero, 1)
    assert hero.deferred_damage == 0 and hero.hp == 100
