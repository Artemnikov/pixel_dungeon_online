# Copyright (C) 2026 ArtemNikov
#
"""Yog-Dzewa's six fists (YogFist.java) driven turn by turn."""

import pytest

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.buffs import add_buff, get_buff, is_rooted
from app.engine.entities.mobs import (
    BrightFist, BurningFist, DarkFist, RottingFist, RustedFist, SoiledFist,
)
from app.engine.game import ai_yog_fists
from app.engine.game.ai_yog_fists import fist_act, fist_flush
from app.engine.game.blobs import fire_volume_at
from app.engine.turn.instance import TurnBasedGameInstance

YOG = (10, 3)


@pytest.fixture
def room():
    g = TurnBasedGameInstance("fists")
    g.players = {}
    floor = g._get_or_create_floor(25)
    floor.grid = [[TileType.FLOOR for _ in range(24)] for _ in range(24)]
    for i in range(24):
        floor.grid[0][i] = floor.grid[23][i] = floor.grid[i][0] = floor.grid[i][23] = TileType.WALL
    floor.mobs.clear()
    floor.items.clear()
    floor.traps.clear()
    floor.blob_areas.clear()
    floor.exit_pos = (10, 1)
    floor.rebuild_flags()
    hero = g.add_player("p1", "Hero")
    hero.floor_id = 25
    hero.pos = Position(x=10, y=16)
    hero.hp = hero.max_hp = 1000
    hero.defense_skill = 0
    return g, hero, floor


def _fist(g, floor, cls, x, y):
    f = cls(pos=Position(x=x, y=y))
    f.floor_id = 25
    f.yog_pos = YOG
    floor.mobs[f.id] = f
    return f


@pytest.fixture
def always_hit(monkeypatch):
    monkeypatch.setattr(ai_yog_fists, "spd_hit", lambda a, d: True)


def test_ranged_cooldown_counts_down_once_per_act(room):
    g, hero, floor = room
    f = _fist(g, floor, BurningFist, 10, 10)
    f.ranged_cooldown = 5
    for _ in range(40):
        fist_flush(g, f, floor, 25)
    assert f.ranged_cooldown == 5
    fist_act(g, f, floor, 25)
    assert f.ranged_cooldown == 4


def test_fist_zaps_from_range_then_closes_in(room):
    g, hero, floor = room
    f = _fist(g, floor, BurningFist, 10, 10)
    g.flush_events()
    assert fist_act(g, f, floor, 25) == 1.0
    assert any(e["type"] == "FIST_ZAP" and e["data"]["bolt"] == "fire" for e in g.flush_events())
    assert 8 <= f.ranged_cooldown <= 12
    assert fist_act(g, f, floor, 25) is None


def test_fist_never_melees_from_range(room, monkeypatch):
    g, hero, floor = room
    f = _fist(g, floor, RustedFist, 10, 10)
    f.ranged_cooldown = 5
    bumps = []
    monkeypatch.setattr(g, "move_entity", lambda mid, dx, dy, seq=None: bumps.append((dx, dy)))
    g._mob_take_turn(f, 25)
    assert all(max(abs(dx), abs(dy)) <= 1 for dx, dy in bumps)
    assert hero.hp == hero.max_hp


def test_adjacent_fist_melees_while_zap_cools(room, monkeypatch):
    g, hero, floor = room
    f = _fist(g, floor, BurningFist, 10, 15)
    f.ranged_cooldown = 5
    bumps = []
    monkeypatch.setattr(g, "move_entity", lambda mid, dx, dy, seq=None: bumps.append((dx, dy)))
    fist_act(g, f, floor, 25)
    assert bumps == [(0, 1)]


def test_bright_fist_melees_when_adjacent_instead_of_zapping(room, monkeypatch):
    g, hero, floor = room
    f = _fist(g, floor, BrightFist, 10, 15)
    bumps = []
    monkeypatch.setattr(g, "move_entity", lambda mid, dx, dy, seq=None: bumps.append((dx, dy)))
    g.flush_events()
    fist_act(g, f, floor, 25)
    assert bumps == [(0, 1)]
    assert not any(e["type"] == "FIST_ZAP" for e in g.flush_events())


def test_burning_zap_ignites_and_seeds_fire(room):
    g, hero, floor = room
    f = _fist(g, floor, BurningFist, 10, 10)
    fist_act(g, f, floor, 25)
    assert get_buff(hero.buffs, "burning") is not None
    assert fire_volume_at(floor, (hero.pos.x, hero.pos.y)) == 4
    assert fire_volume_at(floor, (hero.pos.x + 1, hero.pos.y + 1)) == 4


def test_burning_zap_on_water_only_evaporates(room):
    g, hero, floor = room
    floor.grid[hero.pos.y][hero.pos.x] = TileType.FLOOR_WATER
    floor.rebuild_flags()
    f = _fist(g, floor, BurningFist, 10, 10)
    fist_act(g, f, floor, 25)
    assert get_buff(hero.buffs, "burning") is None
    assert floor.grid[hero.pos.y][hero.pos.x] == TileType.FLOOR


def test_soiled_zap_roots_and_grows_grass(room, always_hit):
    g, hero, floor = room
    f = _fist(g, floor, SoiledFist, 10, 10)
    fist_act(g, f, floor, 25)
    assert is_rooted(hero)
    assert floor.grid[hero.pos.y][hero.pos.x] in (TileType.FLOOR_GRASS, TileType.FURROWED_GRASS)


def test_soiled_fist_damage_shrinks_with_tall_grass(room):
    g, hero, floor = room
    f = _fist(g, floor, SoiledFist, 10, 10)
    for dx in (-1, 0, 1):
        floor.grid[10][10 + dx] = TileType.FURROWED_GRASS
    fist_flush(g, f, floor, 25)
    assert f.take_damage(60) == 30
    assert f.take_burning_damage(10) == 0


def test_rotting_fist_turns_damage_into_bleeding(room):
    g, hero, floor = room
    f = _fist(g, floor, RottingFist, 10, 10)
    assert f.take_damage(50) == 0
    assert f.hp == 300
    assert f.bleeding_level == pytest.approx(30.0)


def test_rotting_zap_seeds_toxic_gas_and_heals_in_water(room):
    g, hero, floor = room
    f = _fist(g, floor, RottingFist, 10, 10)
    floor.grid[10][10] = TileType.FLOOR_WATER
    floor.rebuild_flags()
    f.hp = 200
    fist_act(g, f, floor, 25)
    assert f.hp == 206
    gas = next(b for b in floor.blob_areas.values() if b["type"] == "toxic_gas")
    assert gas["volume"][(hero.pos.x, hero.pos.y)] == 100


def test_rusted_fist_defers_damage_and_zap_cripples(room):
    g, hero, floor = room
    f = _fist(g, floor, RustedFist, 10, 10)
    assert f.take_damage(40) == 0 and f.deferred_damage == 40 and f.hp == 300
    fist_act(g, f, floor, 25)
    assert get_buff(hero.buffs, "cripple").remaining == pytest.approx(4.0)


def test_dark_zap_weakens_light(room, always_hit):
    g, hero, floor = room
    add_buff(hero.buffs, "light", duration=100.0)
    f = _fist(g, floor, DarkFist, 10, 10)
    fist_act(g, f, floor, 25)
    assert get_buff(hero.buffs, "light").remaining == pytest.approx(50.0)
    assert hero.hp < hero.max_hp


def test_bright_fist_teleports_out_of_sight_at_half_hp(room):
    g, hero, floor = room
    f = _fist(g, floor, BrightFist, 10, 10)
    f.take_damage(200)
    assert f.hp == 150
    fist_flush(g, f, floor, 25)
    assert f.ai_state == "wandering"
    assert get_buff(hero.buffs, "blindness").remaining == pytest.approx(15.0)
    assert any(e["type"] == "SCREEN_FLASH" for e in g.flush_events())


def test_fist_near_yog_is_invulnerable_and_warns_once(room):
    g, hero, floor = room
    f = _fist(g, floor, BurningFist, YOG[0], YOG[1] + 2)
    g.flush_events()
    assert f.take_damage(50) == 0
    assert f.take_damage(50) == 0
    fist_flush(g, f, floor, 25)
    warns = [e for e in g.flush_events() if e["type"] == "MESSAGE"
             and e["data"].get("key") == "mob.yog_fist.invuln_warn"]
    assert len(warns) == 1


def test_new_fist_waits_four_turns_before_acting(room):
    g, hero, floor = room
    from app.engine.game import spd_act_clock
    f = _fist(g, floor, BurningFist, 10, 10)
    spd_act_clock.add_with_delay(f, 4)
    acted = []
    for _ in range(6):
        before = f.ranged_cooldown
        g._players_acted.add(hero.id)
        g._resolve_dungeon_phase()
        acted.append(f.ranged_cooldown != before)
    assert acted[:4] == [False] * 4
    assert acted[4]
