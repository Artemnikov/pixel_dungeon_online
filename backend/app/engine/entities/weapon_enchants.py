# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
# `items/weapon/enchantments/` and `items/weapon/curses/`.

from __future__ import annotations

import random
from collections import deque
from typing import TYPE_CHECKING, Callable, Dict, Optional, Tuple

from app.engine.dungeon.constants import TileType

if TYPE_CHECKING:
    from app.engine.entities.base import Entity, KindOfWeapon


# ---------------------------------------------------------------------------
# Registries
# ---------------------------------------------------------------------------

ENCHANT_RARITY: Dict[str, float] = {
    # common (12.5% each)
    "blazing": 12.5,
    "chilling": 12.5,
    "kinetic": 12.5,
    "shocking": 12.5,
    # uncommon (6.67% each)
    "blocking": 100.0 / 15.0,
    "blooming": 100.0 / 15.0,
    "elastic": 100.0 / 15.0,
    "lucky": 100.0 / 15.0,
    "projecting": 100.0 / 15.0,
    "unstable": 100.0 / 15.0,
    # rare (3.33% each)
    "corrupting": 10.0 / 3.0,
    "grim": 10.0 / 3.0,
    "vampiric": 10.0 / 3.0,
}

ENCHANTS: Tuple[str, ...] = tuple(ENCHANT_RARITY)

CURSES: Tuple[str, ...] = (
    "annoying", "displacing", "dazzling", "explosive",
    "friendly", "polarized", "sacrificial", "wayward",
)

_UNSTABLE_POOL: Tuple[str, ...] = tuple(
    n for n in ENCHANT_RARITY if n not in ("kinetic", "grim")
) + CURSES


# ---------------------------------------------------------------------------
# Proc-chance formulas — SPD-faithful
# ---------------------------------------------------------------------------

def missing_hp_pct(entity: "Entity") -> float:
    return 1.0 - entity.hp / max(entity.max_hp, 1)


def _proc_chance_blazing_chilling(lvl: int) -> float:
    return (lvl + 1) / (lvl + 3)


def _proc_chance_blooming(lvl: int) -> float:
    return (lvl + 1) / (lvl + 3)


def _proc_chance_corrupting(lvl: int) -> float:
    return (lvl + 5) / (lvl + 25)


def _proc_chance_lucky(lvl: int) -> float:
    return (lvl + 4) / (lvl + 40)


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
    "dazzling": 0.1,
    "wayward": 0.25,
    "friendly": 0.1,
    "explosive": 0.0,  # handled by durability
}


def striking_wave_multiplier(attacker: "Entity") -> float:
    if attacker.has_buff("striking_wave_tracker"):
        return 1.2
    return 1.0


def trinket_curse_effect_bonus(attacker: "Entity") -> Tuple[float, float]:
    from app.engine.entities.trinkets import WondrousResin as _WR
    from app.engine.entities.trinkets import trinket_level
    lvl = trinket_level(attacker, "wondrous_resin")
    if lvl < 0:
        return (0.0, 0.0)
    return (_WR.positive_curse_effect_chance(lvl),
            _WR.extra_curse_effect_chance(lvl))


def roll_curse_effect_wondrous(attacker: "Entity") -> Optional[str]:
    pos_chance, _ = trinket_curse_effect_bonus(attacker)
    if pos_chance <= 0:
        return None
    if random.random() >= pos_chance:
        return None
    return random.choice(list(ENCHANT_RARITY.keys()))


def roll_extra_curse_effect(attacker: "Entity") -> Optional[str]:
    _, extra_chance = trinket_curse_effect_bonus(attacker)
    if extra_chance <= 0:
        return None
    if random.random() >= extra_chance:
        return None
    return random.choice(list(ENCHANT_RARITY.keys()))


def enraged_catalyst_bonus(attacker: "Entity") -> float:
    info = getattr(attacker, "subclass_info", None)
    if info is None or info.subclass != "berserker" or not getattr(attacker, "berserk_active", False):
        return 0.0
    ec = info.talent_info.level("enraged_catalyst")
    if ec <= 0:
        return 0.0
    return min(1.0, getattr(attacker, "berserk_power", 0.0)) * 0.15 * ec


# ---------------------------------------------------------------------------
# Random generation
# ---------------------------------------------------------------------------

def roll_weapon_level(rng: random.Random = random) -> int:
    r = rng.random()
    if r < 0.75:
        return 0
    if r < 0.95:
        return 1
    return 2


def roll_weapon_enchant(rng: random.Random = random,
                        enchant_mult: float = 1.0,
                        curse_mult: float = 1.0) -> Tuple[Optional[str], bool]:
    r = rng.random()
    curse_threshold = 0.30 * curse_mult
    if r < curse_threshold:
        return rng.choice(CURSES), True
    enchant_threshold = curse_threshold + 0.10 * enchant_mult
    if r < enchant_threshold:
        roll = rng.random() * 100.0
        acc = 0.0
        for name, weight in ENCHANT_RARITY.items():
            acc += weight
            if roll < acc:
                return name, False
        return None, False
    return None, False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_hostile(a: "Entity", b: "Entity") -> bool:
    return a.faction != b.faction


def _power_mult(proc_chance: float) -> float:
    return max(1.0, proc_chance)


def _dmg_mult_round(amount: float) -> int:
    frac = amount - int(amount)
    return int(amount) + (1 if random.random() < frac else 0)


def _arcana_mult(attacker: "Entity") -> float:
    if hasattr(attacker, "belongings"):
        from app.engine.entities.rings import arcana_multiplier
        return arcana_multiplier(attacker)
    return 1.0


def _enrage_bonus(attacker: "Entity") -> float:
    return enraged_catalyst_bonus(attacker)


def _final_chance(base: float, attacker: "Entity", arcana_mult: float) -> float:
    return (base + _enrage_bonus(attacker)) * arcana_mult


def _plants_at(floor, x: int, y: int) -> bool:
    return floor.plants is not None and (x, y) in floor.plants


# ---------------------------------------------------------------------------
# Proc handlers
# ---------------------------------------------------------------------------

def _proc_blazing(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    if not _is_hostile(attacker, defender) or actual_damage <= 0:
        return
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    lvl = weapon.buffed_lvl()
    chance = _final_chance(_proc_chance_blazing_chilling(lvl), attacker, arcana_mult)
    if random.random() >= chance:
        return
    power_multi = _power_mult(chance)
    if not defender.has_buff("burning"):
        defender.add_buff("burning", duration=8.0)
    depth = getattr(floor, "depth", 1)
    burn_dmg = _dmg_mult_round(random.randint(1, 3 + depth // 4) * 0.67 * power_multi)
    if burn_dmg > 0:
        defender.take_damage(burn_dmg)


def _proc_chilling(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    if not _is_hostile(attacker, defender) or actual_damage <= 0:
        return
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    lvl = weapon.buffed_lvl()
    chance = _final_chance((lvl + 1) / (lvl + 4), attacker, arcana_mult)
    if random.random() >= chance:
        return
    power_multi = _power_mult(chance)
    current = 0.0
    existing = defender.get_buff("chill")
    if existing is not None:
        current = existing.duration
    new_duration = 3.0 * power_multi
    cap = 6.0 * power_multi
    defender.add_buff("chill", duration=min(current + new_duration, cap), stack_mode="extend")


def _proc_blooming(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    if not _is_hostile(attacker, defender) or actual_damage <= 0:
        return
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    lvl = weapon.buffed_lvl()
    chance = _final_chance(_proc_chance_blooming(lvl), attacker, arcana_mult)
    if random.random() >= chance:
        return
    power_multi = _power_mult(chance)
    from app.engine.game.terrain_effects import plant_grass
    plants_raw = (1 + 0.1 * lvl) * power_multi
    plants = _dmg_mult_round(plants_raw)
    if plants <= 0:
        return
    cells = [(defender.pos.x, defender.pos.y)]
    adj = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
    for dx, dy in adj:
        cells.append((defender.pos.x + dx, defender.pos.y + dy))
    # attacker's position is lowest priority
    atk_cell = (attacker.pos.x, attacker.pos.y)
    if atk_cell in cells:
        cells.remove(atk_cell)
        cells.append(atk_cell)
    planted = []
    for cx, cy in cells:
        if plants <= 0:
            break
        if floor is None:
            break
        if not (0 <= cx < floor.width and 0 <= cy < floor.height):
            continue
        t = floor.grid[cy][cx]
        if t not in {TileType.FLOOR_GRASS, TileType.EMPTY_DECO, TileType.EMBERS,
                      TileType.HIGH_GRASS, TileType.FURROWED_GRASS}:
            continue
        if _plants_at(floor, cx, cy):
            continue
        plant_grass(floor, cx, cy)
        planted.append((cx, cy))
        plants -= 1
    if planted and kwargs.get("add_event"):
        kwargs["add_event"]("BLOOMING_PROC", {
            "source": attacker.id,
            "defender": defender.id,
            "cells": planted,
        })


def _proc_corrupting(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    if not _is_hostile(attacker, defender):
        return
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    lvl = weapon.buffed_lvl()
    chance = _final_chance(_proc_chance_corrupting(lvl), attacker, arcana_mult)
    if random.random() >= chance:
        return
    if actual_damage < hp_before:
        return
    if not defender.is_alive:
        return
    if hasattr(defender, "is_boss") and defender.is_boss:
        return
    if defender.has_buff("corruption"):
        return
    # immunity check via properties
    if "IMMOVABLE" in getattr(defender, "properties", []):
        return
    defender.faction = attacker.faction
    defender.add_buff("corruption", duration=999.0)
    if chance > 1.1:
        defender.add_buff("adrenaline", duration=round(5 * (chance - 1)))
    if kwargs.get("add_event"):
        kwargs["add_event"]("CORRUPT_PROC", {
            "source": attacker.id,
            "target": defender.id,
        })


def _proc_lucky(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    if not _is_hostile(attacker, defender):
        return
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    lvl = weapon.buffed_lvl()
    chance = _final_chance(_proc_chance_lucky(lvl), attacker, arcana_mult)
    power_multi = _power_mult(chance)
    ring_level = -10 + round(5 * power_multi)
    if random.random() < chance:
        defender.add_buff("luck_proc", duration=2.0, level=max(-10, ring_level))
    else:
        existing = defender.get_buff("luck_proc")
        if existing is not None:
            defender.remove_buff("luck_proc")


def _proc_vampiric(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    if not _is_hostile(attacker, defender):
        return
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    chance = _final_chance(vampiric_chance(missing_hp_pct(attacker)), attacker, arcana_mult)
    if random.random() < chance:
        heal = round(actual_damage * 0.5 * striking_wave_multiplier(attacker))
        if heal > 0:
            attacker.hp = min(attacker.max_hp, attacker.hp + heal)
            if kwargs.get("add_event"):
                kwargs["add_event"]("VAMPIRIC_PROC", {
                    "source": attacker.id,
                    "heal": heal,
                })


def _proc_blocking(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    lvl = weapon.buffed_lvl()
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() < _final_chance(blocking_chance(lvl), attacker, arcana_mult):
        shield = round((2 + lvl) * striking_wave_multiplier(attacker))
        attacker.add_shield("block", shield, priority=0)
        if kwargs.get("add_event"):
            kwargs["add_event"]("BLOCKING_PROC", {
                "source": attacker.id,
                "shield": shield,
            })


def _proc_elastic(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    lvl = weapon.buffed_lvl()
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= _final_chance(elastic_chance(lvl), attacker, arcana_mult):
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
    from_x, from_y = x, y
    for _ in range(2):
        nx, ny = x + step_x, y + step_y
        if not (0 <= nx < floor.width and 0 <= ny < floor.height):
            break
        if floor.flags and (floor.flags.solid[ny][nx] or not floor.flags.passable[ny][nx]):
            break
        x, y = nx, ny
    defender.pos.x, defender.pos.y = x, y
    if kwargs.get("add_event"):
        kwargs["add_event"]("ELASTIC_PROC", {
            "target": defender.id,
            "from_x": from_x,
            "from_y": from_y,
            "to_x": x,
            "to_y": y,
        })


def _proc_shocking(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, add_event=None, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= _final_chance(SHOCKING_CHANCE, attacker, arcana_mult):
        return
    if not _is_hostile(attacker, defender) or actual_damage <= 0:
        return
    chain_targets = []
    affected_ids = {defender.id}

    def _reachable(from_x, from_y, max_dist):
        visited = {(from_x, from_y)}
        q = deque([(from_x, from_y, 0)])
        while q:
            cx, cy, d = q.popleft()
            if d >= max_dist:
                continue
            for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
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
            dmg = round(actual_damage * 0.5)
            if dmg < 1:
                dmg = 1
            m.take_damage(dmg)
            chain_targets.append({"id": m.id, "x": m.pos.x, "y": m.pos.y})
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
    if random.random() >= _final_chance(CURSE_PROC_CHANCE["sacrificial"], attacker, arcana_mult):
        return
    cost = round(missing_hp_pct(attacker) ** 2 * attacker.max_hp / 8 * random.random())
    if cost > 0:
        attacker.take_damage(cost)


def _proc_displacing(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= _final_chance(CURSE_PROC_CHANCE["displacing"], attacker, arcana_mult):
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
        from_x, from_y = defender.pos.x, defender.pos.y
        defender.pos.x, defender.pos.y = random.choice(candidates)
        if kwargs.get("add_event"):
            kwargs["add_event"]("TELEPORT", {
                "player": defender.id,
                "from_x": from_x,
                "from_y": from_y,
                "x": defender.pos.x,
                "y": defender.pos.y,
            })


def _proc_annoying(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= _final_chance(CURSE_PROC_CHANCE["annoying"], attacker, arcana_mult):
        return
    for mob in (floor_mobs or {}).values():
        if not mob.is_alive:
            continue
        mob.target_id = attacker.id
        mob.ai_state = "hunting"


def _proc_dazzling(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= _final_chance(CURSE_PROC_CHANCE["dazzling"], attacker, arcana_mult):
        return
    attacker.add_buff("blindness", duration=10.0)
    for mob in (floor_mobs or {}).values():
        if mob.is_alive and mob.id != attacker.id and mob.id != defender.id:
            mob.add_buff("blindness", duration=5.0)


def _proc_wayward(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= _final_chance(CURSE_PROC_CHANCE["wayward"], attacker, arcana_mult):
        return
    existing = attacker.get_buff("wayward_buff")
    if existing is not None:
        attacker.remove_buff("wayward_buff")
    else:
        attacker.add_buff("wayward_buff", duration=10.0)


def _proc_friendly(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    if random.random() >= _final_chance(CURSE_PROC_CHANCE["friendly"], attacker, arcana_mult):
        return
    existing_charm = attacker.get_buff("charm")
    if existing_charm is not None and getattr(existing_charm, "source_id", None) == defender.id:
        return
    attacker.add_buff("charm", duration=10.0, source_id=defender.id)
    defender.add_buff("charm", duration=5.0, source_id=attacker.id)
    if kwargs.get("add_event"):
        kwargs["add_event"]("CHARM_PROC", {
            "source": attacker.id,
            "target": defender.id,
        })


_EXPLOSIVE_DURABILITY_MAX = 100
_EXPLOSIVE_DURABILITY_WARM = 50
_EXPLOSIVE_DURABILITY_HOT = 10


def _proc_explosive(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    arcana_mult = kwargs.get("arcana_mult", 1.0)
    durability = getattr(weapon, "_explosive_durability", _EXPLOSIVE_DURABILITY_MAX)
    durability -= round(random.randint(0, 10) * arcana_mult)
    weapon._explosive_durability = durability
    if durability <= 0:
        weapon._explosive_durability = _EXPLOSIVE_DURABILITY_MAX
        if floor is None:
            return
        best = None
        best_dist = 999
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            nx, ny = defender.pos.x + dx, defender.pos.y + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                if floor.flags and floor.flags.passable[ny][nx] and not floor.flags.solid[ny][nx]:
                    d = abs(nx - defender.pos.x) + abs(ny - defender.pos.y)
                    if d < best_dist:
                        best_dist = d
                        best = (nx, ny)
        if best is not None:
            bx, by = best
            for mob in (floor_mobs or {}).values():
                if mob.is_alive and abs(mob.pos.x - bx) + abs(mob.pos.y - by) <= 2:
                    dmg = max(1, 20 - (abs(mob.pos.x - bx) + abs(mob.pos.y - by)) * 5)
                    mob.take_damage(dmg)
            if kwargs.get("add_event"):
                kwargs["add_event"]("EXPLOSIVE_PROC", {
                    "x": bx,
                    "y": by,
                    "radius": 2,
                })


def _proc_unstable(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs):
    name = random.choice(_UNSTABLE_POOL)
    _PROC_HANDLERS[name](attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, **kwargs)


_PROC_HANDLERS: Dict[str, Callable] = {
    "blazing": _proc_blazing,
    "chilling": _proc_chilling,
    "blooming": _proc_blooming,
    "corrupting": _proc_corrupting,
    "lucky": _proc_lucky,
    "vampiric": _proc_vampiric,
    "blocking": _proc_blocking,
    "elastic": _proc_elastic,
    "shocking": _proc_shocking,
    "sacrificial": _proc_sacrificial,
    "displacing": _proc_displacing,
    "annoying": _proc_annoying,
    "dazzling": _proc_dazzling,
    "wayward": _proc_wayward,
    "friendly": _proc_friendly,
    "explosive": _proc_explosive,
    "unstable": _proc_unstable,
}


def _resolve_wondrous_resin(
    name: str, attacker: "Entity", **kwargs,
) -> str:
    if name in CURSES:
        replacement = roll_curse_effect_wondrous(attacker)
        if replacement is not None:
            return replacement
    return name


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
    name = _resolve_wondrous_resin(name, attacker)
    handler = _PROC_HANDLERS.get(name)
    if handler is not None:
        arcana_mult = _arcana_mult(attacker)
        handler(attacker, defender, weapon, raw_damage, actual_damage, hp_before, result, floor_mobs, tile_x, tile_y, floor, add_event=add_event, arcana_mult=arcana_mult)


def polarized_roll() -> float:
    return 1.5 if random.random() < 0.5 else 0.0
