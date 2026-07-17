# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
# `items/armor/glyphs/`.

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Callable, Dict, Optional, Tuple

if TYPE_CHECKING:
    from app.engine.entities.base import Entity
    from app.engine.entities.items_equip import Armor


# ---------------------------------------------------------------------------
# Registries
# ---------------------------------------------------------------------------

GLYPH_RARITY: Dict[str, float] = {
    # common (12.5% each)
    "obfuscation": 12.5,
    "swiftness": 12.5,
    "viscosity": 12.5,
    "potential": 12.5,
    # uncommon (6.67% each)
    "brimstone": 100.0 / 15.0,
    "stone": 100.0 / 15.0,
    "entanglement": 100.0 / 15.0,
    "repulsion": 100.0 / 15.0,
    "camouflage": 100.0 / 15.0,
    "flow": 100.0 / 15.0,
    # rare (3.33% each)
    "affection": 10.0 / 3.0,
    "anti_magic": 10.0 / 3.0,
    "thorns": 10.0 / 3.0,
}

GLYPHS: Tuple[str, ...] = tuple(GLYPH_RARITY)

GLYPH_DESC: Dict[str, str] = {
    "obfuscation": "Increases stealth while worn, making you harder for enemies to detect.",
    "swiftness":   "Increases movement speed when no enemies are nearby.",
    "viscosity":   "Spreads damage taken over time instead of absorbing it all at once.",
    "potential":   "On hit, charges your wands and staff slightly.",
    "brimstone":   "Provides immunity to fire damage.",
    "stone":       "Reduces damage taken based on how likely the attack was to hit.",
    "entanglement":"On hit, has a chance to root you in magical earthen armor that absorbs damage.",
    "repulsion":   "On hit, has a chance to knock your attacker away.",
    "camouflage":  "Grants invisibility briefly when you walk over grass.",
    "flow":        "Greatly increases movement speed while standing in water.",
    "affection":   "On hit, has a chance to charm your attacker, causing them to fight for you.",
    "anti_magic":  "Reduces magical damage and debuff durations.",
    "thorns":      "Reflects a portion of melee damage back at your attacker.",
    # curses
    "anti_entropy":  "Cursed: spreads chill and fire to nearby tiles on hit.",
    "corrosion":     "Cursed: slowly corrodes and weakens the armor over time.",
    "displacement":  "Cursed: randomly teleports you when hit.",
    "metabolism":    "Cursed: rapidly drains your hunger when hit.",
    "multiplicity":  "Cursed: spawns hostile clones of yourself on hit.",
    "stench":        "Cursed: releases a cloud of toxic gas when hit.",
    "overgrowth":    "Cursed: causes wild plants to sprout around you on hit.",
    "bulk":          "Cursed: slows your movement while passing through doorways.",
}

CURSE_GLYPHS: Tuple[str, ...] = (
    "anti_entropy", "corrosion", "displacement", "metabolism",
    "multiplicity", "stench", "overgrowth", "bulk",
)


# ---------------------------------------------------------------------------
# Proc-chance formulas
# ---------------------------------------------------------------------------

def _proc_chance_entanglement(lvl: int) -> float:
    return 0.25


def _proc_chance_repulsion(lvl: int) -> float:
    return (lvl + 1) / (lvl + 5)


def _proc_chance_affection(lvl: int) -> float:
    return (lvl + 3) / (lvl + 20)


def _proc_chance_thorns(lvl: int) -> float:
    return (lvl + 2) / (lvl + 12)


def _proc_chance_stone(lvl: int) -> float:
    return 1.0  # always active


def _proc_chance_viscosity(lvl: int) -> float:
    return (lvl + 1) / (lvl + 6)


def _proc_chance_potential(lvl: int) -> float:
    return (lvl + 1) / (lvl + 6)


CURSE_GLYPH_CHANCE: Dict[str, float] = {
    "anti_entropy": 1.0 / 8.0,
    "corrosion": 1.0 / 10.0,
    "displacement": 1.0 / 20.0,
    "metabolism": 1.0 / 6.0,
    "multiplicity": 1.0 / 20.0,
    "stench": 1.0 / 8.0,
    "overgrowth": 1.0 / 20.0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _arcana_mult(entity: "Entity") -> float:
    if hasattr(entity, "belongings"):
        from app.engine.entities.rings import arcana_multiplier
        return arcana_multiplier(entity)
    return 1.0


def _power_mult(proc_chance: float) -> float:
    return max(1.0, proc_chance)


def _dmg_mult_round(amount: float) -> int:
    frac = amount - int(amount)
    return int(amount) + (1 if random.random() < frac else 0)


# ---------------------------------------------------------------------------
# Random generation
# ---------------------------------------------------------------------------

def roll_armor_glyph(rng: random.Random = random,
                     glyph_mult: float = 1.0,
                     curse_mult: float = 1.0) -> Tuple[Optional[str], bool]:
    """Returns (glyph_or_curse_name, is_cursed). 30% cursed, else 10% glyphed,
    else (None, False)."""
    r = rng.random()
    curse_threshold = 0.30 * curse_mult
    if r < curse_threshold:
        return rng.choice(CURSE_GLYPHS), True
    glyph_threshold = curse_threshold + 0.10 * glyph_mult
    if r < glyph_threshold:
        roll = rng.random() * 100.0
        acc = 0.0
        for name, weight in GLYPH_RARITY.items():
            acc += weight
            if roll < acc:
                return name, False
        return None, False
    return None, False


# ---------------------------------------------------------------------------
# Proc handlers — all called as `proc(name, defender, attacker, damage, ...)`
# and return the (possibly modified) damage value.
# ---------------------------------------------------------------------------

def _proc_obfuscation(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    return raw_damage  # passive stealth boost, handled elsewhere


def _proc_swiftness(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    return raw_damage  # passive speed boost, handled elsewhere


def _proc_viscosity(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    lvl = armor.buffed_lvl()
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    chance = _proc_chance_viscosity(lvl) * arcana_mult
    percent = min(1.0, chance)
    if percent <= 0:
        return raw_damage
    deferred = math.ceil(raw_damage * percent)
    actual = raw_damage - deferred
    if deferred > 0:
        existing = defender.get_buff("deferred_damage")
        total = deferred + (existing.level if existing else 0)
        defender.add_buff("deferred_damage", duration=999.0, level=total)
    if kwargs.get("add_event"):
        kwargs["add_event"]("VISCOSITY_PROC", {
            "defender": defender.id,
            "deferred": deferred,
        })
    return max(0, actual)


def _proc_potential(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    lvl = armor.buffed_lvl()
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    chance = _proc_chance_potential(lvl) * arcana_mult
    if random.random() >= chance:
        return raw_damage
    power_multi = _power_mult(chance)
    if hasattr(defender, "belongings"):
        defender.belongings.charge(power_multi)
    if kwargs.get("add_event"):
        kwargs["add_event"]("POTENTIAL_PROC", {
            "defender": defender.id,
        })
    return raw_damage


def _proc_brimstone(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    return raw_damage  # passive fire immunity, handled in damage pipeline


def _proc_stone(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    lvl = armor.buffed_lvl()
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    # stone glyph: DR formula based on hit chance (always active)
    atk_acc = attacker.attack_skill
    if attacker.has_buff("hex"):
        atk_acc = int(atk_acc * 0.75)
    if attacker.has_buff("daze"):
        atk_acc = int(atk_acc * 0.5)
    def_ev = defender.get_effective_defense_skill()
    if defender.has_buff("hex"):
        def_ev = int(def_ev * 0.75)
    hit_chance = (random.random() * atk_acc) / (random.random() * def_ev) if def_ev > 0 else 1.0
    hit_chance = max(0.25, min(1.0, (1.0 + 3.0 * hit_chance) / 4.0))
    return math.ceil(raw_damage * hit_chance)


def _proc_entanglement(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    lvl = armor.buffed_lvl()
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    chance = _proc_chance_entanglement(lvl) * arcana_mult
    if random.random() >= chance:
        return raw_damage
    power_multi = _power_mult(chance)
    absorb = round((5 + 2 * lvl) * power_multi)
    defender.add_buff("earthroot_armor", duration=20.0, level=absorb)
    if kwargs.get("add_event"):
        kwargs["add_event"]("ENTANGLEMENT_PROC", {
            "defender": defender.id,
            "absorb": absorb,
        })
    return raw_damage


def _proc_repulsion(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    lvl = armor.buffed_lvl()
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    chance = _proc_chance_repulsion(lvl) * arcana_mult
    if random.random() >= chance:
        return raw_damage
    if "IMMOVABLE" in getattr(attacker, "properties", []):
        return raw_damage
    power_multi = _power_mult(chance)
    dx = attacker.pos.x - defender.pos.x
    dy = attacker.pos.y - defender.pos.y
    step_x = (dx > 0) - (dx < 0)
    step_y = (dy > 0) - (dy < 0)
    if step_x == 0 and step_y == 0:
        return raw_damage
    if floor is None:
        return raw_damage
    x, y = attacker.pos.x, attacker.pos.y
    from_x, from_y = x, y
    tiles = round(2 * power_multi)
    for _ in range(tiles):
        nx, ny = x + step_x, y + step_y
        if not (0 <= nx < floor.width and 0 <= ny < floor.height):
            break
        if floor.flags and (floor.flags.solid[ny][nx] or not floor.flags.passable[ny][nx]):
            break
        x, y = nx, ny
    attacker.pos.x, attacker.pos.y = x, y
    if kwargs.get("add_event"):
        kwargs["add_event"]("REPULSION_PROC", {
            "target": attacker.id,
            "from_x": from_x,
            "from_y": from_y,
            "to_x": x,
            "to_y": y,
        })
    return raw_damage


def _proc_camouflage(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    return raw_damage  # triggered on grass trample, handled in terrain_effects.py


def _proc_flow(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    return raw_damage  # passive speed boost in water, handled elsewhere


def _proc_affection(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    lvl = armor.buffed_lvl()
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    chance = _proc_chance_affection(lvl) * arcana_mult
    if random.random() >= chance:
        return raw_damage
    power_multi = _power_mult(chance)
    if defender.faction == attacker.faction:
        return raw_damage
    duration = 10.0 * power_multi
    attacker.add_buff("charm", duration=duration, source_id=defender.id)
    if kwargs.get("add_event"):
        kwargs["add_event"]("CHARM_PROC", {
            "source": attacker.id,
            "target": defender.id,
        })
    return raw_damage


def _proc_anti_magic(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    return raw_damage  # passive magic resistance, handled in damage pipeline


def _proc_thorns(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    lvl = armor.buffed_lvl()
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    chance = _proc_chance_thorns(lvl) * arcana_mult
    if random.random() >= chance:
        return raw_damage
    if defender.faction == attacker.faction:
        return raw_damage
    power_multi = _power_mult(chance)
    bleed = round((4 + lvl) * power_multi)
    if bleed > 0:
        attacker.add_buff("bleeding", duration=bleed / 2.0, level=bleed)
    if kwargs.get("add_event"):
        kwargs["add_event"]("THORNS_PROC", {
            "defender": defender.id,
            "attacker": attacker.id,
            "bleed": bleed,
        })
    return raw_damage


# Curse glyphs
def _proc_anti_entropy(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= CURSE_GLYPH_CHANCE["anti_entropy"] * arcana_mult:
        return raw_damage
    if floor is None:
        return raw_damage
    for dx, dy in [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]:
        nx, ny = defender.pos.x + dx, defender.pos.y + dy
        if 0 <= nx < floor.width and 0 <= ny < floor.height:
            pass  # freeze effect — terrain modification in SPD
    defender.add_buff("burning", duration=4.0)
    if kwargs.get("add_event"):
        kwargs["add_event"]("ANTI_ENTROPY_PROC", {
            "defender": defender.id,
            "x": defender.pos.x,
            "y": defender.pos.y,
        })
    return raw_damage


def _proc_corrosion(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= CURSE_GLYPH_CHANCE["corrosion"] * arcana_mult:
        return raw_damage
    for mob in (floor_mobs or {}).values():
        if mob.is_alive and abs(mob.pos.x - defender.pos.x) + abs(mob.pos.y - defender.pos.y) <= 1:
            mob.add_buff("ooze", duration=5.0)
    if kwargs.get("add_event"):
        kwargs["add_event"]("CORROSION_PROC", {
            "defender": defender.id,
            "x": defender.pos.x,
            "y": defender.pos.y,
        })
    return raw_damage


def _proc_displacement(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= CURSE_GLYPH_CHANCE["displacement"] * arcana_mult:
        return raw_damage
    if kwargs.get("add_event"):
        kwargs["add_event"]("DISPLACEMENT_PROC", {
            "defender": defender.id,
            "attacker": attacker.id,
        })
    return 0  # attack misses (SPD returns 0 damage)


def _proc_metabolism(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= CURSE_GLYPH_CHANCE["metabolism"] * arcana_mult:
        return raw_damage
    if not hasattr(defender, "hunger"):
        return raw_damage
    healing = min(defender.hunger // 100, defender.max_hp - defender.hp)
    if healing > 0:
        defender.hp += healing
        defender.hunger -= healing * 10
    if kwargs.get("add_event"):
        kwargs["add_event"]("METABOLISM_PROC", {
            "defender": defender.id,
            "heal": healing,
        })
    return raw_damage


def _proc_multiplicity(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= CURSE_GLYPH_CHANCE["multiplicity"] * arcana_mult:
        return raw_damage

    game = kwargs.get("game")
    if game is None or floor is None:
        return raw_damage

    from app.engine.entities.base import Position
    from app.engine.entities.mobs import MirrorImage

    # SPD Multiplicity: 50% chance to spawn a MirrorImage of the defender
    # (hero), 50% chance to duplicate the attacker. If the attacker can't
    # be duplicated (boss/miniboss/NPC/etc.), spawn a random floor mob.
    spawn_mirror = random.random() < 0.5

    if spawn_mirror and hasattr(defender, "belongings"):
        clone_ids = game._spawn_mirror_images(defender, floor, defender.floor_id)
        if clone_ids:
            for cid in clone_ids:
                if add_event:
                    add_event("MULTIPLICITY_SPAWN", {
                        "defender": defender.id,
                        "clone": cid,
                    }, floor_id=defender.floor_id)
        return raw_damage

    # Duplicate the attacker (or spawn random mob if can't clone).
    from app.engine.entities.mobs import MobEntity
    is_boss = getattr(attacker, "is_boss", False)
    is_miniboss = getattr(attacker, "is_miniboss", False)
    is_npc = "NPC" in getattr(attacker, "properties", [])
    can_clone = isinstance(attacker, MobEntity) and not is_boss and not is_miniboss and not is_npc

    if can_clone:
        clone = attacker.model_copy(deep=True)
        clone.id = f"mult_{attacker.id}_{random.randint(0, 99999)}"
        clone.hp = clone.max_hp
    else:
        # Spawn a random enemy mob for the floor
        clone = _spawn_random_enemy(floor, defender.floor_id)
        if clone is None:
            return raw_damage

    # Find a valid spawn point adjacent to the defender
    from app.engine.dungeon.spd_levelgen.level import _CIRCLE8_OFFSETS
    occupied = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
    spawn_points = []
    for ddx, ddy in _CIRCLE8_OFFSETS:
        cx, cy = defender.pos.x + ddx, defender.pos.y + ddy
        if 0 <= cx < floor.width and 0 <= cy < floor.height:
            if floor.flags and (floor.flags.passable[cy][cx] or floor.flags.avoid[cy][cx]):
                if (cx, cy) not in occupied:
                    spawn_points.append((cx, cy))

    if spawn_points:
        sx, sy = random.choice(spawn_points)
        clone.pos = Position(x=sx, y=sy)
        clone.faction = "enemy"
        clone.ai_state = "hunting"
        floor.mobs[clone.id] = clone
        if add_event:
            add_event("MULTIPLICITY_SPAWN", {
                "defender": defender.id,
                "clone": clone.id,
                "x": sx, "y": sy,
            }, floor_id=defender.floor_id)

    return raw_damage


def _spawn_random_enemy(floor, floor_id: int):
    """Spawn a random enemy mob appropriate for the current floor.

    Simplified from SPD Level.createMob(): picks from a pool of basic
    enemies weighted by floor depth.
    """
    import uuid as _uuid
    from app.engine.entities.base import Position
    from app.engine.entities.mobs import (
        Rat, Gnoll, Crab, Skeleton, Thief, Shaman, Guard,
        DM200, Spinner, Warlock, Monk, Succubus, Eye, Scorpio,
        Bat, Brute, FireElemental, Golem, DM100,
    )

    # Basic enemy pool by dungeon region (mirrors SPD mobClass distribution).
    if floor_id <= 4:
        pool = [Rat, Gnoll, Crab]
    elif floor_id <= 9:
        pool = [Skeleton, Thief, Shaman, Guard]
    elif floor_id <= 14:
        pool = [DM200, Spinner, Warlock, Monk, Bat, Brute]
    else:
        pool = [Succubus, Eye, Scorpio, FireElemental, Golem, DM100]

    mob_cls = random.choice(pool)
    mob = mob_cls(id=f"mult_random_{_uuid.uuid4().hex[:8]}")

    # Find a valid passable tile near the floor center.
    for _ in range(20):
        cx = random.randint(1, max(1, floor.width - 2))
        cy = random.randint(1, max(1, floor.height - 2))
        if floor.flags and floor.flags.passable[cy][cx]:
            occupied = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
            if (cx, cy) not in occupied:
                mob.pos = Position(x=cx, y=cy)
                return mob
    return None


def _proc_stench(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= CURSE_GLYPH_CHANCE["stench"] * arcana_mult:
        return raw_damage
    if floor is not None:
        blob_id = f"stench_{defender.pos.x}_{defender.pos.y}"
        floor.blob_areas[blob_id] = {
            "type": "toxic_gas",
            "cells": {(defender.pos.x, defender.pos.y)},
            "volume": {(defender.pos.x, defender.pos.y): 250},
        }
    if kwargs.get("add_event"):
        kwargs["add_event"]("STENCH_PROC", {
            "defender": defender.id,
            "x": defender.pos.x,
            "y": defender.pos.y,
        })
    return raw_damage


def _proc_overgrowth(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= CURSE_GLYPH_CHANCE["overgrowth"] * arcana_mult:
        return raw_damage
    return raw_damage  # seed planting — deferred


def _proc_bulk(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, **kwargs):
    return raw_damage  # passive speed penalty on doors, handled elsewhere


_GLYPH_PROC_HANDLERS: Dict[str, Callable] = {
    "obfuscation": _proc_obfuscation,
    "swiftness": _proc_swiftness,
    "viscosity": _proc_viscosity,
    "potential": _proc_potential,
    "brimstone": _proc_brimstone,
    "stone": _proc_stone,
    "entanglement": _proc_entanglement,
    "repulsion": _proc_repulsion,
    "camouflage": _proc_camouflage,
    "flow": _proc_flow,
    "affection": _proc_affection,
    "anti_magic": _proc_anti_magic,
    "thorns": _proc_thorns,
    "anti_entropy": _proc_anti_entropy,
    "corrosion": _proc_corrosion,
    "displacement": _proc_displacement,
    "metabolism": _proc_metabolism,
    "multiplicity": _proc_multiplicity,
    "stench": _proc_stench,
    "overgrowth": _proc_overgrowth,
    "bulk": _proc_bulk,
}


# ---------------------------------------------------------------------------
# Passive stat helpers (speed, stealth, magic resist)
# ---------------------------------------------------------------------------

def stealth_boost(entity: "Entity", armor: "Armor") -> float:
    g = armor.enchantment.type if hasattr(armor.enchantment, "type") else armor.enchantment
    if g != "obfuscation" or armor.buffed_lvl() == -1:
        return 0.0
    lvl = armor.buffed_lvl()
    return (1 + lvl / 3) * _arcana_mult(entity)


def speed_boost(entity: "Entity", armor: "Armor", enemies_nearby: bool = False) -> float:
    """Swiftness (speed when no enemies within 3 tiles), Flow (speed in water),
    Bulk (slow on doors). Returns a speed multiplier (1.0 = normal)."""
    g = armor.enchantment.type if hasattr(armor.enchantment, "type") else armor.enchantment
    mult = 1.0
    if g == "swiftness" and not enemies_nearby:
        lvl = armor.buffed_lvl()
        mult *= (1.2 + 0.04 * lvl) * _arcana_mult(entity)
    elif g == "flow" and hasattr(entity, "pos"):
        if floor_at(entity, "water"):
            lvl = armor.buffed_lvl()
            mult *= (2.0 + 0.5 * lvl) * _arcana_mult(entity)
    elif g == "bulk":
        if floor_at(entity, "door"):
            mult *= 1.0 / 3.0 * _arcana_mult(entity)
    return mult


def floor_at(entity: "Entity", terrain: str) -> bool:
    pos = getattr(entity, "pos", None)
    if pos is None:
        return False
    from app.engine.dungeon.constants import TileType as _TT
    t = 0
    # Try to get floor tile
    floor = getattr(entity, "_floor_ref", None)
    if floor is None:
        return False
    if 0 <= pos.y < len(floor.grid) and 0 <= pos.x < len(floor.grid[0]):
        t = floor.grid[pos.y][pos.x]
    if terrain == "water":
        return t == _TT.FLOOR_WATER
    if terrain == "door":
        return t in (_TT.DOOR, _TT.OPEN_DOOR, _TT.LOCKED_DOOR, _TT.SECRET_DOOR, _TT.CRYSTAL_DOOR)
    return False


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def apply_glyph_proc(
    name: str,
    defender: "Entity",
    attacker: "Entity",
    armor: "Armor",
    raw_damage: int,
    floor_mobs: dict,
    tile_x: int,
    tile_y: int,
    floor=None,
    add_event=None,
    game=None,
) -> int:
    """Dispatch an on-hit armor glyph/curse proc. Returns modified damage."""
    handler = _GLYPH_PROC_HANDLERS.get(name)
    if handler is None:
        return raw_damage
    a_mult = _arcana_mult(defender)
    return handler(defender, attacker, armor, raw_damage, floor_mobs, tile_x, tile_y, floor, add_event=add_event, arcana_mult=a_mult, game=game)
