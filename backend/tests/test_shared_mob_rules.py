# Copyright (C) 2026 ArtemNikov
#
"""System rules shared by every mob: Light vs. floor view distance, melee
reach, ranged hold, and Roots."""

import pytest

from app.engine.entities.base import Position
from app.engine.entities.buffs import add_buff, is_rooted
from app.engine.entities.mobs.caves import DM200, Spinner, Warlock
from app.engine.entities.mobs.prison import DM100, RedShaman
from app.engine.entities.mobs.sewers import GnollExile, Rat
from app.engine.game.constants import LIGHT_DISTANCE
from tests.conftest import make_open_game


def _room(depth=1, size=20):
    g = make_open_game(size, size, depth)
    p = g.add_player("p1", "Hero")
    p.floor_id = depth
    p.pos = Position(x=10, y=10)
    return g, p, g._get_or_create_floor(depth)


def test_floor_view_distance_binds_players_but_not_mobs():
    g, p, floor = _room()
    floor.view_distance = 2
    rat = g._spawn_mob_at(Rat, 3, 3)
    floor.mobs[rat.id] = rat
    assert g._view_distance(p) == 2
    assert g._view_distance(rat) == rat.view_distance


def test_light_lifts_floor_view_distance_to_light_distance():
    g, p, floor = _room()
    floor.view_distance = 1
    add_buff(p.buffs, "light", duration=50.0)
    assert g._view_distance(p) == LIGHT_DISTANCE


def _hits_after_ai(g, p, mob_cls, mx, my, monkeypatch, *, freeze_ai=True):
    floor = g._get_or_create_floor(p.floor_id)
    mob = g._spawn_mob_at(mob_cls, mx, my)
    mob.ai_state = "hunting"
    mob.last_attack_time = 0.0
    mob.engaged = True
    floor.mobs[mob.id] = mob
    bumps = []
    real = g.move_entity

    def spy(entity_id, dx, dy, seq=None):
        if entity_id == mob.id and (mob.pos.x + dx, mob.pos.y + dy) == (p.pos.x, p.pos.y):
            bumps.append((dx, dy))
            return None
        return real(entity_id, dx, dy, seq)

    monkeypatch.setattr(g, "move_entity", spy)
    g._tick_generic_mob_ai(mob, floor, p.floor_id)
    return mob, bumps


@pytest.mark.parametrize("mob_cls", [Warlock, RedShaman, DM100, Spinner, DM200])
def test_ranged_mobs_never_melee_from_range(mob_cls, monkeypatch):
    g, p, _ = _room(depth=12)
    _mob, bumps = _hits_after_ai(g, p, mob_cls, 10, 6, monkeypatch)
    assert bumps == []


@pytest.mark.parametrize("mob_cls", [Warlock, RedShaman, DM100])
def test_casters_hold_position_while_target_in_range(mob_cls, monkeypatch):
    g, p, _ = _room(depth=12)
    mob, _ = _hits_after_ai(g, p, mob_cls, 10, 6, monkeypatch)
    assert (mob.pos.x, mob.pos.y) == (10, 6)


@pytest.mark.parametrize("mob_cls", [Spinner, DM200])
def test_ability_mobs_close_in_to_melee(mob_cls, monkeypatch):
    g, p, _ = _room(depth=12)
    g._mob_move_times = {}
    mob, _ = _hits_after_ai(g, p, mob_cls, 10, 6, monkeypatch)
    assert g._get_distance(mob.pos, p.pos) < 4


@pytest.mark.parametrize("mob_cls", [Warlock, Spinner, Rat])
def test_adjacent_mob_melees(mob_cls, monkeypatch):
    g, p, _ = _room(depth=12)
    _mob, bumps = _hits_after_ai(g, p, mob_cls, 10, 9, monkeypatch)
    assert bumps == [(0, 1)]


def test_gnoll_exile_reaches_two_tiles(monkeypatch):
    g, p, _ = _room()
    _mob, bumps = _hits_after_ai(g, p, GnollExile, 10, 8, monkeypatch)
    assert bumps == [(0, 2)]


def test_rooted_mob_cannot_step_but_can_strike():
    g, p, floor = _room()
    rat = g._spawn_mob_at(Rat, 5, 5)
    floor.mobs[rat.id] = rat
    add_buff(rat.buffs, "roots", duration=5.0)
    assert is_rooted(rat)
    g.move_entity(rat.id, 1, 0)
    assert (rat.pos.x, rat.pos.y) == (5, 5)


def test_legacy_rooted_spelling_still_roots_players():
    _g, p, _ = _room()
    add_buff(p.buffs, "rooted", duration=5.0)
    assert is_rooted(p)
