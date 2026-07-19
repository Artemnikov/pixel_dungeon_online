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
"""Artifact-specific action handlers.

Each handler follows the standard signature:
    (game, player, item, tx, ty) -> None

Registered into ITEM_ACTION_DISPATCH in item_actions.py.
"""
import random

from app.engine.dungeon.constants import TileType
from app.engine.game.terrain_primitives import _plant_seed_at
from app.engine.entities.base import Action, Position
from app.engine.entities.items_artifacts import AlchemistsToolkit, ChaliceOfBlood, EtherealChains, HolyTome, HornOfPlenty, LloydsBeacon, MasterThievesArmband, SandalsOfNature, SkeletonKey, TalismanOfForesight, TimekeepersHourglass, UnstableSpellbook


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _artifact_gain_exp(item, amount: int) -> None:
    if item.level >= item.level_cap:
        return
    item.exp += amount
    threshold = (item.level + 1) * 50
    if item.exp >= threshold:
        item.exp -= threshold
        item.level += 1
        item.level_known = True
        item.on_upgrade()


# ---------------------------------------------------------------------------
# AlchemistsToolkit
# ---------------------------------------------------------------------------

def action_brew(game, player, item, tx=None, ty=None) -> None:
    # Opens the alchemy overlay anywhere (SPD switches to AlchemyScene).
    if not isinstance(item, AlchemistsToolkit):
        return
    if item.cursed or not player.belongings.is_equipped(item.id):
        return
    game.add_event("TOOLKIT_BREW", {
        "player": player.id, "item_id": item.id, "charges": item.charge,
    }, floor_id=player.floor_id, player_id=player.id)


def action_energize(game, player, item, tx=None, ty=None) -> None:
    # SPD AC_ENERGIZE: spend 6 alchemical energy per toolkit level.
    if not isinstance(item, AlchemistsToolkit):
        return
    if item.cursed or not player.belongings.is_equipped(item.id):
        return
    if item.level >= item.level_cap:
        return
    if player.energy < 6:
        game.add_event("TOAST", {"text": "Not enough alchemical energy."},
                       floor_id=player.floor_id, player_id=player.id)
        return
    max_levels = min(item.level_cap - item.level, player.energy // 6)
    game.add_event("TOOLKIT_ENERGIZE_PROMPT", {
        "player": player.id, "toolkit_id": item.id, "max_levels": max_levels,
    }, floor_id=player.floor_id, player_id=player.id)


# ---------------------------------------------------------------------------
# ChaliceOfBlood
# ---------------------------------------------------------------------------

import math as _math


def _min_prick_dmg(level: int) -> int:
    return _math.ceil(3 + 2.5 * (level * level))


def _max_prick_dmg(level: int) -> int:
    return _math.floor(7 + 3.5 * (level * level))


def _roll_prick_damage(level: int) -> int:
    # SPD Random.NormalIntRange — mean-biased (average of two uniforms).
    lo, hi = _min_prick_dmg(level), _max_prick_dmg(level)
    return round((random.randint(lo, hi) + random.randint(lo, hi)) / 2)


def action_prick(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, ChaliceOfBlood):
        return
    if item.level >= item.level_cap or item.cursed:
        return
    if player.has_buff("time_stasis"):   # SPD: unavailable while invulnerable
        return
    damage = _roll_prick_damage(item.level)
    damage -= random.randint(player.get_dr_min(), player.get_dr_max())  # drRoll
    if damage < 1:
        damage = 1
    player.take_damage(damage)
    game.add_event("CHALICE_PRICK", {
        "player": player.id, "item_id": item.id, "damage": damage,
    }, floor_id=player.floor_id, source_player_id=player.id)
    game.add_event("PLAY_SOUND", {"sound": "CURSED"}, floor_id=player.floor_id)
    if player.is_downed or player.hp <= 0:
        return   # death from friendly magic — no upgrade
    item.level += 1
    item.level_known = True
    item.on_upgrade()
    game.add_event("CHALICE_UPGRADE", {
        "player": player.id, "item_id": item.id, "new_level": item.level,
    }, floor_id=player.floor_id, source_player_id=player.id)


# ---------------------------------------------------------------------------
# EtherealChains
# ---------------------------------------------------------------------------

def _chebyshev(ax, ay, bx, by) -> int:
    return max(abs(ax - bx), abs(ay - by))


def action_cast_chains(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, EtherealChains) or item.cursed:
        return
    if item.charge <= 0 or tx is None or ty is None:
        return
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return

    from app.engine.systems.ballistica import ballistica_path
    path = ballistica_path(player.pos.x, player.pos.y, tx, ty,
                           floor.flags, floor.width, floor.height)
    cx, cy = path[-1]

    def _occupied(x, y):
        if x == player.pos.x and y == player.pos.y:
            return True
        return any(m.is_alive and m.pos.x == x and m.pos.y == y for m in floor.mobs.values())

    enemy = next((m for m in floor.mobs.values()
                  if m.is_alive and m.pos.x == cx and m.pos.y == cy
                  and getattr(m, "faction", "") != "player"), None)

    if enemy is not None:
        # chainEnemy: pull to the earliest open cell along the chain (nearest hero).
        if getattr(enemy, "immovable", False):
            return
        dest = next(((x, y) for (x, y) in path[1:]
                     if not floor.flags.solid[y][x] and not _occupied(x, y)), None)
        if dest is None:
            return
        cost = _chebyshev(enemy.pos.x, enemy.pos.y, dest[0], dest[1])
        if cost > item.charge:
            return
        item.charge -= cost
        _artifact_gain_exp(item, 10)
        from_x, from_y = enemy.pos.x, enemy.pos.y
        enemy.pos = Position(x=dest[0], y=dest[1])
        game.add_event("CHAINS_PULL", {
            "player": player.id, "target": enemy.id,
            "from_x": from_x, "from_y": from_y, "to_x": dest[0], "to_y": dest[1],
        }, floor_id=player.floor_id)
        game.add_event("PLAY_SOUND", {"sound": "CHAINS"}, floor_id=player.floor_id)
        return

    # chainLocation: pull the hero to the collision cell if it's a grabbable
    # surface (passable, has a solid 8-neighbour) and the hero isn't rooted.
    if player.has_buff("rooted"):
        return
    if floor.flags.solid[cy][cx] or not floor.flags.passable[cy][cx]:
        return
    has_solid_neighbour = any(
        0 <= cx + dx < floor.width and 0 <= cy + dy < floor.height
        and floor.flags.solid[cy + dy][cx + dx]
        for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy)
    )
    if not has_solid_neighbour:
        return
    cost = _chebyshev(player.pos.x, player.pos.y, cx, cy)
    if cost <= 0 or cost > item.charge:
        return
    item.charge -= cost
    _artifact_gain_exp(item, 10)
    from_x, from_y = player.pos.x, player.pos.y
    player.pos = Position(x=cx, y=cy)
    game._invalidate_fov_cache()
    game.add_event("TELEPORT", {
        "player": player.id, "from_x": from_x, "from_y": from_y, "x": cx, "y": cy,
    }, floor_id=player.floor_id)
    game.add_event("PLAY_SOUND", {"sound": "CHAINS"}, floor_id=player.floor_id)


# ---------------------------------------------------------------------------
# HolyTome
# ---------------------------------------------------------------------------

def action_bless(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, HolyTome):
        return
    if item.charge < item.charge_cap:
        return
    player.holy_tome_buffed = True
    item.charge = 0
    _artifact_gain_exp(item, 20)
    game.add_event("TOME_BLESS", {
        "player": player.id, "item_id": item.id,
    }, floor_id=player.floor_id, source_player_id=player.id)
    game.add_event("PLAY_SOUND", {"sound": "ITEM"}, floor_id=player.floor_id)


# ---------------------------------------------------------------------------
# HornOfPlenty
# ---------------------------------------------------------------------------

def action_snack(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, HornOfPlenty):
        return
    if item.charge < 1:
        return
    item.charge -= 1
    heal = 3 + item.level
    max_hp = player.get_total_max_hp()
    player.hp = min(max_hp, player.hp + heal)
    _artifact_gain_exp(item, 5)
    game.add_event("HEAL", {
        "target": player.id, "amount": heal,
        "x": player.pos.x, "y": player.pos.y,
    }, floor_id=player.floor_id)
    game.add_event("PLAY_SOUND", {"sound": "EAT"}, floor_id=player.floor_id)


def action_horn_eat(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, HornOfPlenty):
        return
    if item.charge < item.charge_cap:
        return
    turns = item.level + 1
    player.add_buff("satiated", duration=float(turns * 10))
    item.charge = 0
    _artifact_gain_exp(item, 20)
    game.add_event("EAT", {"player": player.id, "item": item.id}, floor_id=player.floor_id)
    game.add_event("PLAY_SOUND", {"sound": "EAT"}, floor_id=player.floor_id)


def action_store_food(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, HornOfPlenty):
        return
    # Find the first food item in the backpack.
    from app.engine.entities.items_consumable import Food as _Food
    food = next(
        (it for it in player.belongings.backpack.items.values()
         if isinstance(it, _Food)),
        None,
    )
    if food is None:
        game.add_event("MESSAGE", {"text": "You have no food to store."},
                       floor_id=player.floor_id, player_id=player.id)
        return
    charges_gained = min(
        item.charge_cap - item.charge,
        max(1, getattr(food, "energy_value", 2)),
    )
    removed = player.belongings.backpack.detach(food.id)
    if removed is None:
        return
    item.charge = min(item.charge_cap, item.charge + charges_gained)
    game.on_food_eaten(player, food)
    game.add_event("HORN_STORE", {
        "player": player.id, "food": food.id, "charges": item.charge,
    }, floor_id=player.floor_id, source_player_id=player.id)


# ---------------------------------------------------------------------------
# LloydsBeacon
# ---------------------------------------------------------------------------

def action_beacon_set(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, LloydsBeacon):
        return
    item.beacon_floor = player.floor_id
    item.beacon_x = player.pos.x
    item.beacon_y = player.pos.y
    game.add_event("BEACON_SET", {
        "player": player.id, "floor": item.beacon_floor,
        "x": item.beacon_x, "y": item.beacon_y,
    }, floor_id=player.floor_id, source_player_id=player.id)
    game.add_event("PLAY_SOUND", {"sound": "ITEM"}, floor_id=player.floor_id)


def action_beacon_return(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, LloydsBeacon):
        return
    if item.charge <= 0 or item.beacon_floor is None:
        return

    from_floor = player.floor_id
    from_x, from_y = player.pos.x, player.pos.y
    dest_floor = item.beacon_floor
    dest_x = item.beacon_x
    dest_y = item.beacon_y

    item.charge -= 1
    _artifact_gain_exp(item, 10)

    if from_floor != dest_floor:
        # Cross-floor warp: move player to destination floor.
        player.floor_id = dest_floor
        player.pos = Position(x=dest_x, y=dest_y)
        game._invalidate_fov_cache()
        game.add_event("FLOOR_CHANGE", {
            "player": player.id,
            "from_floor": from_floor, "to_floor": dest_floor,
            "x": dest_x, "y": dest_y,
        }, floor_id=dest_floor, source_player_id=player.id)
    else:
        player.pos = Position(x=dest_x, y=dest_y)
        game._invalidate_fov_cache()
        game.add_event("TELEPORT", {
            "player": player.id,
            "from_x": from_x, "from_y": from_y,
            "x": dest_x, "y": dest_y,
        }, floor_id=player.floor_id)

    game.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=player.floor_id)


# ---------------------------------------------------------------------------
# MasterThievesArmband
# ---------------------------------------------------------------------------

def action_steal(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, MasterThievesArmband):
        return
    if item.charge <= 0 or tx is None or ty is None:
        return
    floor = game._get_or_create_floor(player.floor_id)
    target_mob = next(
        (m for m in floor.mobs.values()
         if m.is_alive and m.pos.x == tx and m.pos.y == ty),
        None,
    )
    if target_mob is None:
        return

    item.charge -= 1
    steal_chance = (item.level * 10 + 30) / 100.0
    if random.random() < steal_chance:
        # Steal gold from mob.
        gold_amount = random.randint(
            max(1, player.floor_id * 2),
            max(2, player.floor_id * 4),
        )
        player.gold += gold_amount
        _artifact_gain_exp(item, 15)
        game.add_event("STEAL", {
            "player": player.id, "target": target_mob.id,
            "gold": gold_amount, "success": True,
        }, floor_id=player.floor_id, source_player_id=player.id)
        game.add_event("PLAY_SOUND", {"sound": "ITEM"}, floor_id=player.floor_id)
    else:
        # Failed steal — mob becomes aggressive.
        target_mob.ai_state = "hunting"
        target_mob.target_id = player.id
        game.add_event("STEAL", {
            "player": player.id, "target": target_mob.id,
            "gold": 0, "success": False,
        }, floor_id=player.floor_id, source_player_id=player.id)


# ---------------------------------------------------------------------------
# SandalsOfNature
# ---------------------------------------------------------------------------

def action_identify_seed(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, SandalsOfNature):
        return
    if item.charge < 1:
        return
    # Identify the first unidentified seed in backpack.
    seed = next(
        (it for it in player.belongings.backpack.items.values()
         if getattr(it, "kind", "").endswith("_seed") and not it.level_known),
        None,
    )
    if seed is None:
        return
    seed.level_known = True
    seed.cursed_known = True
    item.charge -= 1
    _artifact_gain_exp(item, 10)
    game.add_event("IDENTIFY", {
        "player": player.id, "item": seed.id, "name": seed.name,
    }, floor_id=player.floor_id, player_id=player.id)


def action_plant_seed_from_sandals(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, SandalsOfNature):
        return
    if not item.stored_seeds or tx is None or ty is None:
        return
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return
    valid = (TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.FURROWED_GRASS,
             TileType.FLOOR, TileType.EMPTY_DECO)
    if floor.grid[ty][tx] not in valid:
        return
    seed_kind = item.stored_seeds.pop(0)
    floor.grid[ty][tx] = TileType.FLOOR_GRASS
    _plant_seed_at(floor, (tx, ty), seed_kind.replace("_seed", ""))
    _artifact_gain_exp(item, 10)
    game.add_event("MAP_PATCH", {"tiles": [{"x": tx, "y": ty, "tile": TileType.FLOOR_GRASS}]},
                   floor_id=player.floor_id)
    floor.rebuild_flags()


# ---------------------------------------------------------------------------
# SkeletonKey
# ---------------------------------------------------------------------------

def action_unlock(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, SkeletonKey):
        return
    if item.charge < 1 or tx is None or ty is None:
        return
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return
    tile = floor.grid[ty][tx]
    if tile in (TileType.LOCKED_DOOR, TileType.CRYSTAL_DOOR):
        floor.grid[ty][tx] = TileType.DOOR
        floor.rebuild_flags()
        item.charge -= 1
        _artifact_gain_exp(item, 10)
        game.add_event("MAP_PATCH", {"tiles": [{"x": tx, "y": ty, "tile": TileType.DOOR}]},
                       floor_id=player.floor_id)
        game.add_event("PLAY_SOUND", {"sound": "UNLOCK"}, floor_id=player.floor_id)
    else:
        game.add_event("MESSAGE", {"text": "There is nothing to unlock there."},
                       floor_id=player.floor_id, player_id=player.id)


def action_key_reveal(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, SkeletonKey):
        return
    if item.charge < 2:
        return
    floor = game._get_or_create_floor(player.floor_id)
    radius = 2 + item.level
    px, py = player.pos.x, player.pos.y
    patches = []
    found = False
    for (hx, hy), actual_tile in list(floor.hidden_doors.items()):
        if abs(hx - px) <= radius and abs(hy - py) <= radius:
            floor.hidden_doors.pop((hx, hy))
            floor.grid[hy][hx] = actual_tile
            patches.append({"x": hx, "y": hy, "tile": actual_tile})
            found = True
    for (hx, hy), trap in floor.traps.items():
        if abs(hx - px) <= radius and abs(hy - py) <= radius and trap.hidden:
            trap.hidden = False
            found = True
            if floor.grid[hy][hx] == TileType.SECRET_TRAP:
                floor.grid[hy][hx] = TileType.TRAP
                patches.append({"x": hx, "y": hy, "tile": TileType.TRAP})
    if found:
        item.charge -= 2
        _artifact_gain_exp(item, 10)
        if patches:
            floor.rebuild_flags()
            game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=player.floor_id)
        game.add_event("PLAY_SOUND", {"sound": "SECRET"}, floor_id=player.floor_id)


# ---------------------------------------------------------------------------
# TalismanOfForesight
# ---------------------------------------------------------------------------

def action_scry(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, TalismanOfForesight):
        return
    if item.charge < 20:
        return
    floor = game._get_or_create_floor(player.floor_id)
    radius = 3 + item.level
    px, py = player.pos.x, player.pos.y
    patches = []
    found = False
    for (hx, hy), actual_tile in list(floor.hidden_doors.items()):
        if abs(hx - px) <= radius and abs(hy - py) <= radius:
            floor.hidden_doors.pop((hx, hy))
            floor.grid[hy][hx] = actual_tile
            patches.append({"x": hx, "y": hy, "tile": actual_tile})
            found = True
    for (hx, hy), trap in floor.traps.items():
        if abs(hx - px) <= radius and abs(hy - py) <= radius and trap.hidden:
            trap.hidden = False
            found = True
            if floor.grid[hy][hx] == TileType.SECRET_TRAP:
                floor.grid[hy][hx] = TileType.TRAP
                patches.append({"x": hx, "y": hy, "tile": TileType.TRAP})
    item.charge -= 20
    _artifact_gain_exp(item, 20)
    if patches:
        floor.rebuild_flags()
        game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=player.floor_id)
    game.add_event("SCRY", {
        "player": player.id, "radius": radius, "found": found,
    }, floor_id=player.floor_id, source_player_id=player.id)
    game.add_event("PLAY_SOUND", {"sound": "SECRET"}, floor_id=player.floor_id)


# ---------------------------------------------------------------------------
# TimekeepersHourglass
# ---------------------------------------------------------------------------

# SPD Hourglass spends charge at ~1 per 2 turns of freeze and 5 turns of stasis.
# A "turn" is 20 ticks (_TICKS_PER_TURN); freeze burns per-mob freeze_ticks.
_TICKS_PER_TURN = 20
_FREEZE_TICKS_PER_CHARGE = 2 * _TICKS_PER_TURN   # 2 turns of freeze per charge
_STASIS_SECONDS_PER_CHARGE = 5.0                 # 5 turns of stasis per charge


def action_freeze(game, player, item, tx=None, ty=None) -> None:
    # Freeze: halt hostile mobs on the floor. Other players are unaffected.
    if not isinstance(item, TimekeepersHourglass) or item.cursed:
        return
    if item.charge <= 0:
        return
    used = min(item.charge, 2)
    item.charge -= used
    freeze_ticks = used * _FREEZE_TICKS_PER_CHARGE
    floor = game._get_or_create_floor(player.floor_id)
    for mob in floor.mobs.values():
        if mob.is_alive and getattr(mob, "faction", "") != "player":
            mob.freeze_ticks = freeze_ticks
    game.add_event("TIME_FREEZE", {
        "player": player.id, "ticks": freeze_ticks,
    }, floor_id=player.floor_id, source_player_id=player.id)
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)


def action_stasis(game, player, item, tx=None, ty=None) -> None:
    # Stasis: suspend the user outside time — untargetable + invulnerable, but
    # unable to act — for a fixed duration (SPD grants 5 free turns per charge).
    if not isinstance(item, TimekeepersHourglass) or item.cursed:
        return
    if item.charge <= 0:
        return
    used = min(item.charge, 2)
    item.charge -= used
    duration = used * _STASIS_SECONDS_PER_CHARGE
    player.add_buff("time_stasis", duration=duration)
    # Any mob currently hunting the user loses its lock (they can no longer see it).
    floor = game._get_or_create_floor(player.floor_id)
    for mob in floor.mobs.values():
        if getattr(mob, "target_id", None) == player.id:
            mob.target_id = None
    game.add_event("TIME_STASIS", {
        "player": player.id, "duration": duration,
    }, floor_id=player.floor_id, source_player_id=player.id)
    game.add_event("PLAY_SOUND", {"sound": "TELEPORT"}, floor_id=player.floor_id)


# ---------------------------------------------------------------------------
# UnstableSpellbook
# ---------------------------------------------------------------------------

# SPD ExoticScroll.regToExo (regular scroll kind -> exotic scroll kind).
_REG_TO_EXO = {
    "scroll_of_upgrade": "scroll_of_exotic_enchantment",
    "scroll_of_identify": "scroll_of_divination",
    "scroll_of_remove_curse": "scroll_of_anti_magic",
    "scroll_of_mirror_image": "scroll_of_prismatic_image",
    "scroll_of_recharging": "scroll_of_mystical_energy",
    "scroll_of_teleportation": "scroll_of_passage",
    "scroll_of_lullaby": "scroll_of_sirens_song",
    "scroll_of_magic_mapping": "scroll_of_foresight",
    "scroll_of_rage": "scroll_of_challenge",
    "scroll_of_retribution": "scroll_of_psionic_blast",
    "scroll_of_terror": "scroll_of_dread",
    "scroll_of_transmutation": "scroll_of_metamorphosis",
}

# Scrolls whose roll frequency the book halves (SPD: 50% reroll).
_HALVED_SCROLLS = {"scroll_of_identify", "scroll_of_remove_curse", "scroll_of_magic_mapping"}


def _roll_book_scroll_kind(book) -> str:
    """Mirror UnstableSpellbook.doReadEffect's scroll roll: weighted by the SPD
    SCROLL deck (upgrade weight 0 → excluded), never transmutation, and
    identify/remove_curse/magic_mapping at half frequency."""
    from app.engine.entities.items_artifacts import _SPELLBOOK_SCROLL_KINDS
    from app.engine.dungeon.spd_levelgen.run_state import SCROLL_DEFAULT_PROBS_TOTAL
    pool, weights = [], []
    for i, kind in enumerate(_SPELLBOOK_SCROLL_KINDS):
        w = SCROLL_DEFAULT_PROBS_TOTAL[i]
        if w > 0 and kind != "scroll_of_transmutation":
            pool.append(kind)
            weights.append(w)
    for _ in range(50):
        kind = random.choices(pool, weights=weights, k=1)[0]
        if kind in _HALVED_SCROLLS and random.random() < 0.5:
            continue
        return kind
    return pool[0]


def _construct_scroll(kind: str):
    """Build a scroll instance by kind. Exotic scrolls are not in the loot
    catalog, so fall back to locating the Scroll subclass directly."""
    from app.engine.entities.item_catalog import make_catalog_item
    scroll = make_catalog_item(kind)
    if scroll is not None:
        return scroll
    from app.engine.entities.items_scrolls import Scroll

    def _walk(cls):
        for sub in cls.__subclasses__():
            yield sub
            yield from _walk(sub)

    for cls in _walk(Scroll):
        field = cls.model_fields.get("kind")
        if field is not None and field.default == kind:
            return cls()
    return None


def _apply_book_scroll(game, player, kind: str) -> None:
    """Apply a scroll's read effect for a transient (book-conjured) scroll."""
    from app.engine.entities.scroll_actions import action_read as _read
    scroll = _construct_scroll(kind)
    if scroll is None:
        game.add_event("MESSAGE", {"text": "The spell fizzles!"},
                       floor_id=player.floor_id, player_id=player.id)
        return
    scroll.id = f"book_scroll_{kind}"
    _read(game, player, scroll)
    game.add_event("BOOK_CAST", {
        "player": player.id, "scroll": kind,
    }, floor_id=player.floor_id, source_player_id=player.id)


def action_book_read(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, UnstableSpellbook):
        return
    # Exploit guard (SPD ExploitHandler): a pending empower choice left unresolved
    # is forced to a normal read before a fresh read can begin.
    if getattr(player, "_pending_book_item_id", None) == item.id:
        action_book_read_resolve(game, player, item, 0)
    if item.charge < 1 or item.cursed:
        return
    item.charge -= 1
    kind = _roll_book_scroll_kind(item)
    # Empower prompt: charge left AND the book has "learned" this scroll (removed
    # from its index) AND an exotic form exists.
    if item.charge > 0 and kind not in item.scroll_index and kind in _REG_TO_EXO:
        player._pending_book_item_id = item.id
        player._pending_book_scroll_kind = kind
        game.add_event("BOOK_READ_CHOICE", {
            "player": player.id, "item_id": item.id,
            "normal": kind, "exotic": _REG_TO_EXO[kind],
        }, floor_id=player.floor_id, player_id=player.id)
        return
    _apply_book_scroll(game, player, kind)


def action_book_read_resolve(game, player, item, tx=None, ty=None) -> None:
    """Resolve a pending empower choice. tx == 1 → exotic (spends a 2nd charge),
    anything else → the regular scroll."""
    if not isinstance(item, UnstableSpellbook):
        return
    kind = getattr(player, "_pending_book_scroll_kind", None)
    if kind is None or getattr(player, "_pending_book_item_id", None) != item.id:
        return
    player._pending_book_item_id = None
    player._pending_book_scroll_kind = None
    if tx == 1 and item.charge > 0:
        item.charge -= 1
        _apply_book_scroll(game, player, _REG_TO_EXO.get(kind, kind))
    else:
        _apply_book_scroll(game, player, kind)


def action_book_infuse(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, UnstableSpellbook):
        return
    if item.cursed or item.level >= item.level_cap:
        return
    front = item.scroll_index[:2]
    scroll = next(
        (it for it in player.belongings.all_items()
         if getattr(it, "kind", "") in front and it.level_known),
        None,
    )
    if scroll is None:
        return
    kind = scroll.kind
    player.belongings.backpack.detach(scroll.id)
    if kind in item.scroll_index:
        item.scroll_index.remove(kind)
    item.level += 1
    item.level_known = True
    item.on_upgrade()
    game.add_event("BOOK_INFUSE", {
        "player": player.id, "item_id": item.id,
        "scroll": kind, "new_level": item.level,
    }, floor_id=player.floor_id, source_player_id=player.id)
    game.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=player.floor_id)
