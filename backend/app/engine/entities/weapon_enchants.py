# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
"""Weapon enchantments and curses, ported from `items/weapon/enchantments/` and
`items/weapon/curses/` per docs/spd_items/01-weapons-bombs.md §6-7.

Phase 1 implements only the enchants/curses that don't depend on a brand-new
status-effect system (Burning, Chill, Blindness, Charm/Corruption):

    ENCHANTS = vampiric, blocking, projecting, kinetic, grim, shocking,
               elastic, unstable
    CURSES   = polarized, sacrificial, displacing, annoying

The remaining SPD enchants/curses (Blazing, Chilling, Blooming, Corrupting,
Lucky, Dazzling, Wayward, Friendly, Explosive) are left for later phases.

`Enchantment.random()`'s `typeChances = [50, 40, 10]` table assigns 12.5% to
each of 4 "common" enchants, 6.67% to each of 6 "uncommon", 3.33% to each of 3
"rare". Only some of each tier is implemented here:
  - common (implemented 2/4): kinetic, shocking -> 12.5% each
  - uncommon (implemented 4/6): blocking, elastic, projecting, unstable -> 6.67% each
  - rare (implemented 2/3): grim, vampiric -> 3.33% each
These sum to ~58.3% of the 10% "item is enchanted" roll; the remaining ~41.7%
(which would have picked one of the not-yet-implemented enchants) falls back to
no enchant. Same idea for curses: 4/8 SPD curses implemented, each keeping an
equal 1/8 share of the 30% "item is cursed" roll; rolling one of the other 4
curses falls back to "not cursed".
"""

from __future__ import annotations

import random
from collections import deque
from typing import TYPE_CHECKING, Callable, Dict, Optional, Tuple

from app.engine.dungeon.generator import TileType

if TYPE_CHECKING:
    from app.engine.entities.base import Entity, KindOfWeapon


# ---------------------------------------------------------------------------
# Registries
# ---------------------------------------------------------------------------

# All SPD weapon curses, for documentation/rarity-table purposes; only the
# names in CURSES below are implemented.
ALL_SPD_CURSES: Tuple[str, ...] = (
    "annoying", "displacing", "dazzling", "explosive",
    "sacrificial", "wayward", "polarized", "friendly",
)

CURSES: Tuple[str, ...] = ("polarized", "sacrificial", "displacing", "annoying")

# (enchant name -> share of the 10% "enchanted" roll, in percentage points)
ENCHANT_RARITY: Dict[str, float] = {
    # common (12.5% each)
    "kinetic": 12.5,
    "shocking": 12.5,
    # uncommon (6.67% each)
    "blocking": 100.0 / 15.0,
    "elastic": 100.0 / 15.0,
    "projecting": 100.0 / 15.0,
    "unstable": 100.0 / 15.0,
    # rare (3.33% each)
    "grim": 10.0 / 3.0,
    "vampiric": 10.0 / 3.0,
}

ENCHANTS: Tuple[str, ...] = tuple(ENCHANT_RARITY)

# Enchants Unstable can re-roll into (excludes itself, and excludes
# kinetic/grim which hook into combat.py's existing Entity-field-based helpers
# rather than the generic proc dispatch below).
_UNSTABLE_POOL: Tuple[str, ...] = (
    "vampiric", "blocking", "elastic", "shocking",
    "sacrificial", "displacing", "annoying",
)


# ---------------------------------------------------------------------------
# Proc-chance formulas (docs/spd_items/01-weapons-bombs.md §6-7)
# ---------------------------------------------------------------------------

def missing_hp_pct(entity: "Entity") -> float:
    return 1.0 - entity.hp / max(entity.max_hp, 1)


def vampiric_chance(missing_pct: float) -> float:
    return 0.05 + 0.25 * missing_pct


def blocking_chance(lvl: int) -> float:
    return (lvl + 4) / (lvl + 40)


def elastic_chance(lvl: int) -> float:
    return (lvl + 1) / (lvl + 5)


SHOCKING_CHANCE = 1.0 / 3.0


def grim_chance(lvl: int) -> float:
    return min(1.0, 0.5 + 0.05 * lvl)


CURSE_PROC_CHANCE: Dict[str, float] = {
    "polarized": 0.5,
    "sacrificial": 0.1,
    "displacing": 1.0 / 12.0,
    "annoying": 0.05,
}


def striking_wave_multiplier(attacker: "Entity") -> float:
    """Striking Wave +4 (warrior T4 shockwave): for a few turns after the
    shockwave procs, weapon enchant effect magnitudes get +20% power."""
    if attacker.has_buff("striking_wave_tracker"):
        return 1.2
    return 1.0


def enraged_catalyst_bonus(attacker: "Entity") -> float:
    """Enraged Catalyst (warrior T3 berserker): while raging, weapon
    enchant/curse proc chances go up by up to 15% per point, scaled by
    current Berserk power (capped at 100%)."""
    info = getattr(attacker, "subclass_info", None)
    if info is None or info.subclass != "berserker" or not getattr(attacker, "berserk_active", False):
        return 0.0
    ec = info.talent_info.level("enraged_catalyst")
    if ec <= 0:
        return 0.0
    return min(1.0, getattr(attacker, "berserk_power", 0.0)) * 0.15 * ec


# ---------------------------------------------------------------------------
# Random generation (Item.random() / Enchantment.random())
# ---------------------------------------------------------------------------

def roll_weapon_level(rng: random.Random = random) -> int:
    """75% +0, 20% +1, 5% +2."""
    r = rng.random()
    if r < 0.75:
        return 0
    if r < 0.95:
        return 1
    return 2


def roll_weapon_enchant(rng: random.Random = random) -> Tuple[Optional[str], bool]:
    """Returns (enchant_or_curse_name, is_cursed). 30% cursed, else 10%
    enchanted, else (None, False). See module docstring for the rarity-table
    renormalization used for the not-yet-implemented enchants/curses."""
    r = rng.random()
    if r < 0.30:
        curse = rng.choice(ALL_SPD_CURSES)
        if curse in CURSES:
            return curse, True
        return None, False
    if r < 0.40:
        roll = rng.random() * 100.0
        acc = 0.0
        for name, weight in ENCHANT_RARITY.items():
            acc += weight
            if roll < acc:
                return name, False
        return None, False
    return None, False


# ---------------------------------------------------------------------------
# Proc handlers
# ---------------------------------------------------------------------------

def _is_hostile(a: "Entity", b: "Entity") -> bool:
    return a.faction != b.faction


def _proc_vampiric(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    if not _is_hostile(attacker, defender):
        return
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    chance = (vampiric_chance(missing_hp_pct(attacker)) + enraged_catalyst_bonus(attacker)) * arcana_mult
    if random.random() < chance:
        heal = round(actual_damage * 0.5 * striking_wave_multiplier(attacker))
        if heal > 0:
            attacker.hp = min(attacker.max_hp, attacker.hp + heal)


def _proc_blocking(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    lvl = weapon.buffed_lvl()
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() < (blocking_chance(lvl) + enraged_catalyst_bonus(attacker)) * arcana_mult:
        attacker.add_shield("block", round((2 + lvl) * striking_wave_multiplier(attacker)), priority=0)


def _proc_elastic(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    lvl = weapon.buffed_lvl()
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= (elastic_chance(lvl) + enraged_catalyst_bonus(attacker)) * arcana_mult:
        return
    if "IMMOVABLE" in getattr(defender, "properties", []):
        return
    dx = defender.pos.x - attacker.pos.x
    dy = defender.pos.y - attacker.pos.y
    step_x = (dx > 0) - (dx < 0)
    step_y = (dy > 0) - (dy < 0)
    if step_x == 0 and step_y == 0:
        return
    if floor is None:
        return
    x, y = defender.pos.x, defender.pos.y
    for _ in range(2):  # round(2 * powerMulti), powerMulti=1
        nx, ny = x + step_x, y + step_y
        if not (0 <= nx < floor.width and 0 <= ny < floor.height):
            break
        if not floor.flags or not floor.flags.passable[ny][nx] or floor.flags.solid[ny][nx]:
            break
        x, y = nx, ny
    defender.pos.x, defender.pos.y = x, y


def _proc_shocking(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, add_event=None, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= (SHOCKING_CHANCE + enraged_catalyst_bonus(attacker)) * arcana_mult:
        return
    if not _is_hostile(attacker, defender) or actual_damage <= 0:
        return
    chain_targets = []
    affected_ids = {defender.id}

    def _reachable(from_x, from_y, max_dist):
        visited = {(from_x, from_y)}
        q = deque([(from_x, from_y, 0)])
        while q:
            x, y, d = q.popleft()
            if d >= max_dist:
                continue
            for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    if (nx, ny) not in visited and not floor.flags.solid[ny][nx]:
                        visited.add((nx, ny))
                        q.append((nx, ny, d + 1))
        return visited

    def _shock_arc(from_x, from_y, recurse_dist):
        nonlocal chain_targets
        reachable = _reachable(from_x, from_y, recurse_dist)
        for m in (floor_mobs or {}).values():
            if not m.is_alive or m.id in affected_ids:
                continue
            if not _is_hostile(attacker, m):
                continue
            if (m.pos.x, m.pos.y) not in reachable:
                continue
            affected_ids.add(m.id)
            dmg = round(actual_damage * 0.5 * striking_wave_multiplier(attacker))
            if dmg < 1:
                dmg = 1
            m.take_damage(dmg)
            chain_targets.append({"id": m.id, "x": m.pos.x, "y": m.pos.y})
            # Recurse with reduced range (1 tile, or 2 if target in water and not flying)
            next_dist = 2 if (floor and hasattr(floor, 'grid')
                             and floor.grid[m.pos.y][m.pos.x] == TileType.FLOOR_WATER
                             and "FLYING" not in getattr(m, "properties", [])) else 1
            _shock_arc(m.pos.x, m.pos.y, next_dist)

    _shock_arc(defender.pos.x, defender.pos.y, 2)
    if chain_targets and add_event:
        add_event("SHOCKING_PROC", {
            "source": attacker.id,
            "defender": defender.id,
            "defender_x": defender.pos.x,
            "defender_y": defender.pos.y,
            "chain_targets": chain_targets,
        })


def _proc_sacrificial(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= (CURSE_PROC_CHANCE["sacrificial"] + enraged_catalyst_bonus(attacker)) * arcana_mult:
        return
    cost = round(missing_hp_pct(attacker) ** 2 * attacker.max_hp / 8 * random.random())
    if cost > 0:
        attacker.take_damage(cost)


def _proc_displacing(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= (CURSE_PROC_CHANCE["displacing"] + enraged_catalyst_bonus(attacker)) * arcana_mult:
        return
    if "IMMOVABLE" in getattr(defender, "properties", []):
        return
    if floor is None or not floor.flags:
        return
    candidates = [
        (x, y)
        for y in range(floor.height)
        for x in range(floor.width)
        if floor.flags.passable[y][x] and not floor.flags.solid[y][x]
    ]
    if candidates:
        defender.pos.x, defender.pos.y = random.choice(candidates)


def _proc_annoying(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= (CURSE_PROC_CHANCE["annoying"] + enraged_catalyst_bonus(attacker)) * arcana_mult:
        return
    for mob in floor_mobs.values():
        if not mob.is_alive:
            continue
        mob.target_id = attacker.id
        mob.ai_state = "hunting"


def _proc_unstable(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    name = random.choice(_UNSTABLE_POOL)
    _PROC_HANDLERS[name](attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs)


_PROC_HANDLERS: Dict[str, Callable] = {
    "vampiric": _proc_vampiric,
    "blocking": _proc_blocking,
    "elastic": _proc_elastic,
    "shocking": _proc_shocking,
    "sacrificial": _proc_sacrificial,
    "displacing": _proc_displacing,
    "annoying": _proc_annoying,
    "unstable": _proc_unstable,
}


def apply_enchant_proc(
    name: str,
    attacker: "Entity",
    defender: "Entity",
    weapon: "KindOfWeapon",
    raw_damage: int,
    actual_damage: int,
    hp_before: int,
    result: dict,
    floor_mobs: dict,
    tile_x: int,
    tile_y: int,
    floor=None,
    add_event=None,
) -> None:
    """Dispatch an on-hit weapon enchant/curse proc. Grim, Kinetic, Polarized
    and Projecting are handled separately in combat.py (see plan §3)."""
    handler = _PROC_HANDLERS.get(name)
    if handler is not None:
        arcana_mult = 1.0
        if hasattr(attacker, "belongings"):
            from app.engine.entities.rings import arcana_multiplier
            arcana_mult = arcana_multiplier(attacker)
        handler(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, add_event=add_event, arcana_mult=arcana_mult)


def polarized_roll() -> float:
    """50% chance 1.5x damage, 50% chance 0x."""
    return 1.5 if random.random() < 0.5 else 0.0
