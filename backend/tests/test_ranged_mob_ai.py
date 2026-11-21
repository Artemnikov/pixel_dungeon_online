# Copyright (C) 2026 ArtemNikov
"""Regression coverage for the ranged-spellcaster mob AI update functions
(DM-100, DM-200, Shaman, Warlock, Spinner, Newborn Fire Elemental) --
locks in the shared targeting/cooldown/accuracy-roll/DR-damage shape that
these ai_*.py modules duplicate, ahead of extracting the common pieces."""
import itertools
import random

import pytest

from app.engine.entities.base import Position
from app.engine.entities.buffs import get_buff
from app.engine.entities.mobs import DM200, RedShaman, Spinner, Warlock
from app.engine.entities.wandmaker_quest import NewbornFireElemental
from app.engine.game.ai_dm100 import _update_dm100
from app.engine.game.ai_dm200 import _update_dm200
from app.engine.game.ai_newborn_elemental import _update_newborn_elemental
from app.engine.game.ai_shaman import _update_shaman
from app.engine.game.ai_spinner import _update_spinner
from app.engine.game.ai_warlock import _update_warlock
from app.engine.entities.mobs import DM100


def _room(open_game_factory, px=10, py=10, size=20):
    g = open_game_factory(width=size, height=size)
    p = g.add_player("p1", "Hero", "warrior")
    p.pos = Position(x=px, y=py)
    p.hp = p.max_hp = 500  # never one-shot in these tests, keeps _find_nearest_player finding p
    floor = g._get_or_create_floor(p.floor_id)
    return g, p, floor


def _hunting(mob):
    mob.ai_state = "hunting"
    return mob


def _force_hit(monkeypatch):
    # acu = r*attack_skill, df = r*defense_skill: a high roll then a low
    # roll guarantees acu >= df regardless of the two mobs' skill values.
    # Trailing 0.0s cover any later proc rolls (e.g. Shaman/Warlock attack_proc).
    vals = itertools.chain([0.99, 0.0], itertools.repeat(0.0))
    monkeypatch.setattr(random, "random", lambda: next(vals))


def _force_miss(monkeypatch):
    vals = itertools.chain([0.0, 0.99], itertools.repeat(0.99))
    monkeypatch.setattr(random, "random", lambda: next(vals))


# --- DM-100 (accuracy-gated, no DR) -----------------------------------------

def test_dm100_out_of_range_is_noop(open_game_factory):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(DM100(id="m", pos=Position(x=1, y=1)))
    floor.mobs[mob.id] = mob
    assert _update_dm100(g, mob, floor, p.floor_id) is False


def test_dm100_melee_range_is_noop(open_game_factory):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(DM100(id="m", pos=Position(x=9, y=10)))
    floor.mobs[mob.id] = mob
    assert _update_dm100(g, mob, floor, p.floor_id) is False


def test_dm100_blocked_los_is_noop(open_game_factory):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(DM100(id="m", pos=Position(x=6, y=10)))
    floor.mobs[mob.id] = mob
    floor.flags.los_blocking[10][8] = True
    assert _update_dm100(g, mob, floor, p.floor_id) is False


def test_dm100_hit_deals_damage_no_dr(open_game_factory, monkeypatch):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(DM100(id="m", pos=Position(x=6, y=10)))
    floor.mobs[mob.id] = mob
    _force_hit(monkeypatch)
    monkeypatch.setattr(random, "randint", lambda lo, hi: hi)

    start_hp = p.hp
    assert _update_dm100(g, mob, floor, p.floor_id) is True
    assert p.hp == start_hp - 10  # _normal_int_range(3, 10) with randint stubbed to hi
    assert mob.last_attack_time > 0


def test_dm100_miss_deals_no_damage(open_game_factory, monkeypatch):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(DM100(id="m", pos=Position(x=6, y=10)))
    floor.mobs[mob.id] = mob
    _force_miss(monkeypatch)

    start_hp = p.hp
    assert _update_dm100(g, mob, floor, p.floor_id) is True  # attack was made, just missed
    assert p.hp == start_hp


def test_dm100_respects_attack_cooldown(open_game_factory, monkeypatch):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(DM100(id="m", pos=Position(x=6, y=10)))
    floor.mobs[mob.id] = mob
    _force_hit(monkeypatch)
    assert _update_dm100(g, mob, floor, p.floor_id) is True
    # Immediately after firing, the cooldown blocks a second attack.
    assert _update_dm100(g, mob, floor, p.floor_id) is False


# --- DM-200 (always-hit, DR, decrementing counter cooldown) ----------------

def test_dm200_hit_applies_dr_damage_and_poison(open_game_factory, monkeypatch):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(DM200(id="m", pos=Position(x=6, y=10)))
    floor.mobs[mob.id] = mob
    monkeypatch.setattr(random, "randint", lambda lo, hi: hi)

    start_hp = p.hp
    assert _update_dm200(g, mob, floor, p.floor_id) is True
    assert p.hp < start_hp
    assert get_buff(p.buffs, "poison") is not None
    assert mob.vent_cooldown == 30


def test_dm200_cooldown_blocks_immediate_refire(open_game_factory, monkeypatch):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(DM200(id="m", pos=Position(x=6, y=10)))
    floor.mobs[mob.id] = mob
    monkeypatch.setattr(random, "randint", lambda lo, hi: hi)

    assert _update_dm200(g, mob, floor, p.floor_id) is True
    assert _update_dm200(g, mob, floor, p.floor_id) is False
    assert mob.vent_cooldown == 29  # decremented even though it didn't fire


# --- Shaman (accuracy-gated, DR, per-colour proc) ---------------------------

def test_shaman_hit_applies_dr_damage_and_proc(open_game_factory, monkeypatch):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(RedShaman(id="m", pos=Position(x=8, y=10)))
    floor.mobs[mob.id] = mob
    _force_hit(monkeypatch)
    monkeypatch.setattr(random, "randint", lambda lo, hi: hi)

    start_hp = p.hp
    assert _update_shaman(g, mob, floor, p.floor_id) is True
    assert p.hp < start_hp
    assert get_buff(p.buffs, "weakness") is not None  # RedShaman proc, forced by randint==hi


def test_shaman_out_of_range_is_noop(open_game_factory):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(RedShaman(id="m", pos=Position(x=1, y=1)))
    floor.mobs[mob.id] = mob
    assert _update_shaman(g, mob, floor, p.floor_id) is False


# --- Warlock (accuracy-gated, DR, no built-in cooldown) ---------------------

def test_warlock_hit_applies_dr_damage(open_game_factory, monkeypatch):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(Warlock(id="m", pos=Position(x=6, y=10)))
    floor.mobs[mob.id] = mob
    _force_hit(monkeypatch)
    monkeypatch.setattr(random, "randint", lambda lo, hi: hi)

    start_hp = p.hp
    assert _update_warlock(g, mob, floor, p.floor_id) is True
    assert p.hp < start_hp


def test_warlock_miss_deals_no_damage(open_game_factory, monkeypatch):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(Warlock(id="m", pos=Position(x=6, y=10)))
    floor.mobs[mob.id] = mob
    _force_miss(monkeypatch)

    start_hp = p.hp
    assert _update_warlock(g, mob, floor, p.floor_id) is True
    assert p.hp == start_hp


def test_warlock_respects_attack_cooldown(open_game_factory, monkeypatch):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(Warlock(id="m", pos=Position(x=6, y=10)))
    floor.mobs[mob.id] = mob
    _force_hit(monkeypatch)
    assert _update_warlock(g, mob, floor, p.floor_id) is True
    assert _update_warlock(g, mob, floor, p.floor_id) is False


def _zap_sounds(g):
    sounds = []
    for e in g.events:
        if e["type"] == "RANGED_ATTACK":
            sounds.append(e["data"].get("sound"))
        elif e["type"] == "PLAY_SOUND":
            sounds.append(e["data"]["sound"])
    return sounds


def test_warlock_zap_plays_zap_once_and_degrade_on_proc(open_game_factory, monkeypatch):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(Warlock(id="m", pos=Position(x=6, y=10)))
    floor.mobs[mob.id] = mob
    _force_hit(monkeypatch)
    g.events.clear()

    assert _update_warlock(g, mob, floor, p.floor_id) is True
    zap = next(e for e in g.events if e["type"] == "RANGED_ATTACK")
    assert zap["data"]["projectile"] == "shadow"
    sounds = _zap_sounds(g)
    assert sounds.count("ZAP") == 1
    assert "DEGRADE" in sounds
    assert p.has_buff("degrade")


def test_warlock_zap_without_degrade_proc_has_no_degrade_sound(open_game_factory, monkeypatch):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(Warlock(id="m", pos=Position(x=6, y=10)))
    floor.mobs[mob.id] = mob
    vals = itertools.chain([0.99, 0.0], itertools.repeat(0.99))
    monkeypatch.setattr(random, "random", lambda: next(vals))
    g.events.clear()

    assert _update_warlock(g, mob, floor, p.floor_id) is True
    sounds = _zap_sounds(g)
    assert sounds.count("ZAP") == 1
    assert "DEGRADE" not in sounds


# --- Spinner (no damage, applies cripple, decrementing counter cooldown) ---

def test_spinner_hit_applies_cripple(open_game_factory):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(Spinner(id="m", pos=Position(x=8, y=10)))
    floor.mobs[mob.id] = mob

    assert _update_spinner(g, mob, floor, p.floor_id) is True
    assert get_buff(p.buffs, "cripple") is not None
    assert mob.web_cooldown == 10


def test_spinner_cooldown_blocks_immediate_refire(open_game_factory):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(Spinner(id="m", pos=Position(x=8, y=10)))
    floor.mobs[mob.id] = mob

    assert _update_spinner(g, mob, floor, p.floor_id) is True
    assert _update_spinner(g, mob, floor, p.floor_id) is False
    assert mob.web_cooldown == 9  # decremented even though it didn't fire


def test_spinner_melee_range_is_noop(open_game_factory):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(Spinner(id="m", pos=Position(x=9, y=10)))
    floor.mobs[mob.id] = mob

    assert _update_spinner(g, mob, floor, p.floor_id) is False


def test_spinner_out_of_range_is_noop(open_game_factory):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(Spinner(id="m", pos=Position(x=1, y=1)))
    floor.mobs[mob.id] = mob

    assert _update_spinner(g, mob, floor, p.floor_id) is False


# --- Newborn Fire Elemental (always-hit, DR, decrementing counter cooldown) -

def test_newborn_elemental_hit_applies_burning(open_game_factory, monkeypatch):
    g, p, floor = _room(open_game_factory, px=10, py=10)
    mob = _hunting(NewbornFireElemental(id="m", pos=Position(x=6, y=10)))
    floor.mobs[mob.id] = mob
    monkeypatch.setattr(random, "randint", lambda lo, hi: hi)

    start_hp = p.hp
    assert _update_newborn_elemental(g, mob, floor, p.floor_id) is True
    assert p.hp < start_hp
    assert get_buff(p.buffs, "burning") is not None
    assert mob.ranged_cooldown == 40
