# Copyright (C) 2026 ArtemNikov
#
"""SPD act() ports of Eye, Scorpio and Ripper Demon, driven turn by turn."""

import pytest

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.buffs import get_buff
from app.engine.entities.mobs import Eye, RipperDemon, Scorpio
from app.engine.turn.instance import TurnBasedGameInstance


@pytest.fixture
def room():
    g = TurnBasedGameInstance("minions")
    g.players = {}
    floor = g._get_or_create_floor(17)
    floor.grid = [[TileType.FLOOR for _ in range(20)] for _ in range(20)]
    floor.mobs.clear()
    floor.items.clear()
    floor.traps.clear()
    floor.rebuild_flags()
    hero = g.add_player("p1", "Hero")
    hero.floor_id = 17
    hero.pos = Position(x=10, y=10)
    hero.hp = hero.max_hp = 1000
    return g, hero, floor


def _mob(g, floor, cls, x, y):
    mob = g._spawn_mob_at(cls, x, y, 17)
    mob.pos = Position(x=x, y=y)
    mob.ai_state = "hunting"
    floor.mobs[mob.id] = mob
    return mob


def test_eye_charges_then_fires_at_aimed_cell(room, monkeypatch):
    g, hero, floor = room
    eye = _mob(g, floor, Eye, 10, 4)
    monkeypatch.setattr("app.engine.game.ai_eye.spd_hit", lambda a, d: True)
    cost = g._mob_take_turn(eye, 17)
    assert eye.beam_charged
    assert cost == pytest.approx(2.0)
    assert (eye.beam_target_x, eye.beam_target_y) == (10, 10)
    hp = hero.hp
    g._mob_take_turn(eye, 17)
    assert not eye.beam_charged
    assert hero.hp < hp
    assert 4 <= eye.beam_cooldown <= 6


def test_eye_fires_at_old_cell_even_if_target_steps_aside(room, monkeypatch):
    g, hero, floor = room
    eye = _mob(g, floor, Eye, 10, 4)
    g._mob_take_turn(eye, 17)
    hero.pos = Position(x=15, y=15)
    hp = hero.hp
    g.flush_events()
    g._mob_take_turn(eye, 17)
    assert not eye.beam_charged
    assert hero.hp == hp
    assert any(e["type"] == "EYE_DEATH_RAY" for e in g.flush_events())


def test_eye_takes_quarter_damage_while_charged(room):
    g, _hero, floor = room
    eye = _mob(g, floor, Eye, 10, 4)
    eye.beam_charged = True
    eye.take_damage(40)
    assert eye.hp == eye.max_hp - 10


def test_eye_melees_only_adjacent_while_beam_cools(room, monkeypatch):
    g, _hero, floor = room
    eye = _mob(g, floor, Eye, 10, 4)
    eye.beam_cooldown = 3
    bumps = []
    monkeypatch.setattr(g, "move_entity", lambda *a, **k: bumps.append(a))
    g._mob_take_turn(eye, 17)
    assert bumps == [] or all(max(abs(dx), abs(dy)) == 1 for _id, dx, dy in bumps)
    assert not eye.beam_charged


def test_scorpio_attacks_only_from_range(room, monkeypatch):
    g, _hero, floor = room
    sc = _mob(g, floor, Scorpio, 10, 6)
    bumps = []
    monkeypatch.setattr(g, "move_entity", lambda mid, dx, dy, seq=None: bumps.append((dx, dy)))
    g._mob_take_turn(sc, 17)
    assert bumps == [(0, 4)]


def test_scorpio_backs_off_when_adjacent(room):
    g, hero, floor = room
    sc = _mob(g, floor, Scorpio, 10, 9)
    g._mob_take_turn(sc, 17)
    assert g._get_distance(sc.pos, hero.pos) == 2
    assert hero.hp == hero.max_hp


def test_scorpio_hit_can_cripple(room, monkeypatch):
    _g, hero, floor = room
    monkeypatch.setattr("app.engine.entities.mobs.city.random.random", lambda: 0.0)
    Scorpio().attack_proc(hero)
    assert get_buff(hero.buffs, "cripple") is not None


def test_ripper_telegraphs_then_leaps_and_bleeds(room, monkeypatch):
    g, hero, floor = room
    rip = _mob(g, floor, RipperDemon, 10, 4)
    rip.last_enemy_pos = (10, 10)
    g.flush_events()
    cost = g._mob_take_turn(rip, 17)
    assert rip.leap_pos == (10, 10)
    assert 0.5 <= cost <= 1.5
    assert any(e["type"] == "RIPPER_LEAP_PREP" for e in g.flush_events())
    monkeypatch.setattr("app.engine.game.ai_ripper.normal_int_range", lambda lo, hi: lo if lo == 2 else 20)
    g._mob_take_turn(rip, 17)
    assert rip.leap_pos is None
    assert g._get_distance(rip.pos, hero.pos) == 1
    assert get_buff(hero.buffs, "bleeding") is not None
    assert hero.bleeding_level == pytest.approx(15.0)


def test_ripper_leap_cancelled_when_rooted(room):
    g, _hero, floor = room
    rip = _mob(g, floor, RipperDemon, 10, 4)
    rip.leap_pos = (10, 10)
    from app.engine.entities.buffs import add_buff
    add_buff(rip.buffs, "roots", duration=5.0)
    g._mob_take_turn(rip, 17)
    assert rip.leap_pos is None
    assert (rip.pos.x, rip.pos.y) == (10, 4)


def test_eye_realtime_charges_then_fires_after_two_seconds():
    from app.engine.game.constants import TICKS_PER_TURN
    from tests.conftest import make_open_game
    g = make_open_game(20, 20, 17)
    hero = g.add_player("p1", "Hero")
    hero.floor_id = 17
    hero.pos = Position(x=10, y=10)
    hero.hp = hero.max_hp = 1000
    floor = g._get_or_create_floor(17)
    eye = g._spawn_mob_at(Eye, 10, 4, 17)
    eye.ai_state = "hunting"
    floor.mobs[eye.id] = eye
    g._tick_mob(eye, floor, 17)
    assert eye.beam_charged
    for _ in range(2 * TICKS_PER_TURN - 2):
        g._tick_mob(eye, floor, 17)
    assert eye.beam_charged
    g.flush_events()
    for _ in range(2):
        g._tick_mob(eye, floor, 17)
    assert not eye.beam_charged
    assert any(e["type"] == "EYE_DEATH_RAY" for e in g.flush_events())
