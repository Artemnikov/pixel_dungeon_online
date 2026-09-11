# Copyright (C) 2026 ArtemNikov
#
"""Generic item-action dispatch — the Python analogue of SPD's
Item.execute(hero, action).

Kept in its own module (not on the model classes) so item models stay free of a
GameInstance import cycle. Each handler has the signature
    (game, player, item, tx, ty) -> None
where `game` is the GameInstance, `tx/ty` are the optional target cell for
targeted actions (THROW/ZAP). Server validates `action in item.actions(player)`
before dispatch, so handlers can assume the action is legal for the item.

Scroll-specific handlers live in scroll_actions.py.
"""
import math
import random
import time
from typing import Callable, Dict, Optional

from app.engine.dungeon.constants import TileType
from app.engine.game.terrain_primitives import _create_fire_blob, _create_gas, _plant_seed_at
from app.engine.game.terrain_effects import press_cell, _trigger_plant_effect, _freeze_area
from app.engine.systems.ballistica import ballistica_trace
from app.engine.entities.base import Action, Position, consume_backpack_item as _consume_item
from app.engine.entities.player import Player
from app.engine.entities.runestones import Runestone
from app.engine.entities.items.consumables import Seed, Waterskin
from app.engine.entities.wands.wandmaker_quest_items import CeremonialCandle
from app.engine.entities.items.potions import Potion
from app.engine.entities.wands import Wand
from app.engine.entities.runestone_actions import action_throw_runestone, action_use_stone
from app.engine.entities.scroll_actions import action_read
from app.engine.entities.armors.armor_glyphs import CURSE_GLYPHS as _CURSE_GLYPHS_TUPLE
from app.engine.entities.artifact_actions import (
    action_brew, action_energize,
    action_prick,
    action_cast_chains,
    action_bless,
    action_snack, action_horn_eat, action_store_food,
    action_beacon_set, action_beacon_return,
    action_steal,
    action_identify_seed, action_plant_seed_from_sandals,
    action_unlock, action_key_reveal,
    action_scry,
    action_freeze, action_stasis,
    action_book_read, action_book_read_resolve, action_book_infuse,
)


def _floor_drop(game, player, item, x: Optional[int] = None, y: Optional[int] = None) -> None:
    drop_x = player.pos.x if x is None else x
    drop_y = player.pos.y if y is None else y
    item.pos = Position(x=drop_x, y=drop_y)
    floor = game._get_or_create_floor(player.floor_id)
    floor.items[item.id] = item


def action_equip(game, player, item, tx=None, ty=None) -> None:
    player.equip_item(item.id)
    if item.cursed and item.cursed_known:
        game.add_event("EQUIP_CURSED", {
            "player_id": player.id,
            "x": player.pos.x,
            "y": player.pos.y,
        }, floor_id=player.floor_id, player_id=player.id)


def action_unequip(game, player, item, tx=None, ty=None) -> None:
    player.unequip_item(item.id)


def action_drop(game, player, item, tx=None, ty=None) -> None:
    # Drop the whole stack/item, from the backpack or an equip slot.
    detached = player.belongings.backpack.detach_all(item.id)
    if detached is None and player.belongings.is_equipped(item.id):
        if item.cursed and item.cursed_known:
            return  # cursed gear can't be removed
        slot = player.belongings.find_equipped_slot(item.id)
        if slot is not None:
            detached = getattr(player.belongings, slot)
            setattr(player.belongings, slot, None)
    if detached is None:
        return
    player.quickslot.clear_item(detached.id)
    _floor_drop(game, player, detached)
    game.add_event("DROP", {"player": player.id, "item": detached.id, "item_name": detached.name, "item_kind": detached.kind, "item_type": detached.type}, floor_id=player.floor_id)
    if isinstance(detached, CeremonialCandle):
        game._check_ritual_candles(player.floor_id)


def action_drink_waterskin(game, player, item, tx=None, ty=None) -> None:
    # Mirrors SPD's Waterskin.execute(AC_DRINK): each drop is worth 5% of max HP,
    # drunk instantly (not a gradual heal like potions). Shielding Dew (Warden T2)
    # also tops up a "dew" shield, consuming extra drops to do so.
    max_hp = player.get_total_max_hp()
    missing_pct = 1.0 - (player.hp / max_hp if max_hp else 1.0)
    drops_needed = missing_pct / 0.05

    shielding_dew = player.talent_info.level("shielding_dew")
    shield_drops = 0.0
    if shielding_dew > 0:
        max_shield = round(max_hp * 0.2 * shielding_dew)
        cur_shield = player.get_shield("dew").amount if player.get_shield("dew") else 0
        if max_shield > 0:
            missing_shield_pct = (1 - cur_shield / max_shield) * 0.2 * shielding_dew
            if missing_shield_pct > 0:
                shield_drops = missing_shield_pct / 0.05

    drops_to_consume = math.ceil(drops_needed + shield_drops - 0.01)
    drops_to_consume = max(1, min(drops_to_consume, item.volume))

    heal_drops = drops_to_consume
    shield_amount = 0
    if shielding_dew > 0 and drops_needed < drops_to_consume:
        # excess drops (beyond what's needed to fill HP) go to shielding
        heal_drops = max(0, math.ceil(drops_needed - 0.01))
        shield_amount = round((drops_to_consume - heal_drops) * 0.05 * max_hp)

    heal = round(heal_drops * 0.05 * max_hp)
    if heal > 0:
        player.hp = min(max_hp, player.hp + heal)
        game.add_event("HEAL", {"target": player.id, "amount": heal, "x": player.pos.x, "y": player.pos.y}, floor_id=player.floor_id)
    if shield_amount > 0:
        player.add_shield("dew", shield_amount, priority=0)

    item.volume -= drops_to_consume
    game.add_event("DRINK", {"player": player.id, "type": "waterskin"}, floor_id=player.floor_id, source_player_id=player.id)


# PotionOfPurity's debuff list; Cleansing/HoneyedHealing cure that same set
# plus the five debuffs Purity leaves untouched (SPD PotionOfCleansing).
_PURITY_DEBUFFS = ("poison", "blindness", "bleeding", "weakness", "slow", "burning", "cripple")
_FULL_DEBUFF_CLEANSE = _PURITY_DEBUFFS + ("paralysis", "terror", "drowsy", "frost", "ooze")
_HEALING_POTION_CLEANSE = ("poison", "bleeding", "cripple", "ooze")


def action_drink(game, player, item, tx=None, ty=None) -> None:
    if isinstance(item, Waterskin):
        action_drink_waterskin(game, player, item, tx, ty)
        return

    # Mirrors PotionOfHealing: heal 0.8*maxHP+14 over time, 25% of the remaining
    # pool per heal-tick. Reviving potions are consumed by reviving a downed ally
    # (see move_entity), not by self-drinking, so they no-op here.
    game.identify_kind(item, player)  # drinking reveals the potion type
    effect = getattr(item, "effect", "")
    if effect == "regen":
        player.cleanse(_HEALING_POTION_CLEANSE)
        amount = round(0.8 * player.get_total_max_hp() + 14)
        player.set_heal(amount, 0.25, 0)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "regen"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "fury":
        player.has_fury = True
        player.fury_turns_remaining = 10
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "fury"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "aqua_rejuv":
        pool = round(player.get_total_max_hp() * 1.5)
        player.aqua_heal_left = max(player.aqua_heal_left, pool)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "aqua_rejuv"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "mind_vision":
        # SPD MindVision: 20-turn buff revealing every mob's position through walls.
        player.add_buff("mind_vision", duration=20.0)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "mind_vision"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "invisibility":
        # SPD Invisibility: 20-turn buff. Attacking breaks invisibility (see
        # combat._dispel_stealth). Reference-counted on Entity.invisible.
        player.add_buff("invisibility", duration=20.0)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "invisibility"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "liquid_flame":
        dmg = max(1, player.hp // 3)
        player.take_damage(dmg)
        player.add_buff("burning", duration=8.0, level=1, stack_mode="extend")
        _consume_item(player, item)
        game.add_event("DAMAGE", {"target": player.id, "amount": dmg, "burning": True}, floor_id=player.floor_id)
        game.add_event("FLAME_BURST", {"x": player.pos.x, "y": player.pos.y}, floor_id=player.floor_id)
        cx, cy = player.pos.x, player.pos.y
        floor = game._get_or_create_floor(player.floor_id)
        if _create_fire_blob(floor, (cx, cy), 1 + player.floor_id, f"fire_drink_{player.id}"):
            game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)
            game.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=player.floor_id)
    elif effect == "toxic_gas":
        dmg = max(1, player.hp // 4)
        player.take_damage(dmg)
        player.add_buff("poison", duration=10.0, level=1, stack_mode="extend")
        _consume_item(player, item)
        game.add_event("DAMAGE", {"target": player.id, "amount": dmg}, floor_id=player.floor_id)
        cx, cy = player.pos.x, player.pos.y
        floor = game._get_or_create_floor(player.floor_id)
        _create_gas(floor, (cx, cy), 4 + player.floor_id // 2, "toxic_gas")
        game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)
    elif effect == "paralytic_gas":
        player.add_buff("paralysis", duration=5.0, level=1, stack_mode="extend")
        _consume_item(player, item)
        cx, cy = player.pos.x, player.pos.y
        floor = game._get_or_create_floor(player.floor_id)
        _create_gas(floor, (cx, cy), 4 + player.floor_id // 2, "paralytic_gas")
        game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)
    elif effect == "levitation":
        player.add_buff("levitation", duration=20.0)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "levitation"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "haste":
        player.add_buff("haste", duration=20.0)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "haste"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "frost":
        dmg = max(1, round(player.get_total_max_hp() * 0.1))
        player.take_damage(dmg)
        player.add_buff("frost", duration=10.0, level=1)
        _consume_item(player, item)
        game.add_event("DAMAGE", {"target": player.id, "amount": dmg}, floor_id=player.floor_id)
        game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)
        game.add_event("DRINK", {"player": player.id, "type": "frost"}, floor_id=player.floor_id)
    elif effect == "purity":
        player.cleanse(_PURITY_DEBUFFS)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "purity"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "experience":
        amount = max(1, round((player.get_total_max_hp() - player.hp) * 2))
        leveled = player.earn_exp(amount)
        if leveled:
            game.add_event("LEVEL_UP", {"player": player.id, "level": player.level}, floor_id=player.floor_id)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "experience"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "strength":
        player.strength = min(player.strength + 1, 30)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "strength"}, floor_id=player.floor_id, source_player_id=player.id)
    # ── Exotic Potions ──────────────────────────────────────────────────────
    elif effect == "cleansing":
        player.cleanse(_FULL_DEBUFF_CLEANSE)
        floor = game._get_or_create_floor(player.floor_id)
        cx, cy = player.pos.x, player.pos.y
        to_remove = [bid for bid, b in floor.blob_areas.items()
                     if any(abs(x-cx)<=2 and abs(y-cy)<=2 for x, y in b.get("cells", set()))]
        for bid in to_remove:
            del floor.blob_areas[bid]
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "cleansing"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "corrosive_gas":
        # Drink: release at player's feet (like throwing at self)
        cx, cy = player.pos.x, player.pos.y
        floor = game._get_or_create_floor(player.floor_id)
        _create_gas(floor, (cx, cy), 5 + player.floor_id // 2, "corrosive_gas")
        dmg = max(1, player.hp // 4)
        player.take_damage(dmg)
        player.add_buff("ooze", duration=10.0, level=1, stack_mode="extend")
        _consume_item(player, item)
        game.add_event("DAMAGE", {"target": player.id, "amount": dmg}, floor_id=player.floor_id)
        game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)
    elif effect == "dragons_breath":
        # Breathe fire in 3 tiles in a line toward tx/ty (or random direction)
        floor = game._get_or_create_floor(player.floor_id)
        if tx is not None and ty is not None and (tx != player.pos.x or ty != player.pos.y):
            dx = tx - player.pos.x
            dy = ty - player.pos.y
            mag = max(1, math.hypot(dx, dy))
            sx, sy = dx/mag, dy/mag
        else:
            sx, sy = 1.0, 0.0
        fire_cells = set()
        fire_vol = {}
        strength = 3 + player.floor_id
        for step in range(1, 4):
            nx, ny = round(player.pos.x + sx*step), round(player.pos.y + sy*step)
            if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                break
            if not (floor.flags and floor.flags.passable[ny][nx]):
                break
            fire_cells.add((nx, ny))
            fire_vol[(nx, ny)] = strength
            for mob in floor.mobs.values():
                if mob.is_alive and mob.pos.x == nx and mob.pos.y == ny:
                    mob.add_buff("burning", duration=8.0, level=1, stack_mode="extend")
        if fire_cells:
            blob_id = f"fire_breath_{player.id}"
            floor.blob_areas[blob_id] = {"type": "fire", "cells": fire_cells, "volume": fire_vol}
            game.add_event("FLAME_BURST", {"x": player.pos.x, "y": player.pos.y}, floor_id=player.floor_id)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "dragons_breath"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "earthen_armor":
        armor_level = 2 + player.level // 3
        player.add_buff("barkskin", duration=50.0, level=armor_level)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "earthen_armor"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "magical_sight":
        player.add_buff("magical_sight", duration=50.0, level=12)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "magical_sight"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "mastery":
        # Stub: open item selection dialog for strength reduction
        _consume_item(player, item)
        game.add_event("MASTERY_SELECT", {"player": player.id}, floor_id=player.floor_id, player_id=player.id)
    elif effect == "shielding":
        shield_amount = round(0.6 * player.get_total_max_hp() + 10)
        player.shield_hp = getattr(player, "shield_hp", 0) + shield_amount
        player.add_buff("shielded", duration=999.0, level=shield_amount)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "shielding"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "shrouding_fog":
        cx, cy = player.pos.x, player.pos.y
        floor = game._get_or_create_floor(player.floor_id)
        _create_gas(floor, (cx, cy), 8 + player.floor_id // 2, "smoke_screen")
        _consume_item(player, item)
        game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)
    elif effect == "snap_freeze":
        cx, cy = player.pos.x, player.pos.y
        floor = game._get_or_create_floor(player.floor_id)
        for mob in floor.mobs.values():
            if not mob.is_alive or mob.faction == "player":
                continue
            if abs(mob.pos.x - cx) <= 3 and abs(mob.pos.y - cy) <= 3:
                mob.add_buff("frost", duration=10.0, level=1)
                mob.add_buff("roots", duration=10.0)
        player.add_buff("frost", duration=5.0, level=1)
        _consume_item(player, item)
        game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)
        game.add_event("DRINK", {"player": player.id, "type": "snap_freeze"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "stamina":
        player.add_buff("stamina", duration=100.0)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "stamina"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "storm_clouds":
        cx, cy = player.pos.x, player.pos.y
        floor = game._get_or_create_floor(player.floor_id)
        _create_gas(floor, (cx, cy), 6 + player.floor_id // 2, "storm_cloud")
        _consume_item(player, item)
        game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)
    elif effect == "divine_inspiration":
        # Stub: grant 1 talent point to all tiers
        game.add_event("DIVINE_INSPIRATION", {"player": player.id}, floor_id=player.floor_id, player_id=player.id)
        _consume_item(player, item)
    # ── Elixirs ─────────────────────────────────────────────────────────────
    elif effect == "arcane_armor":
        armor_level = 5 + player.level // 2
        player.add_buff("arcane_armor", duration=60.0, level=armor_level)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "arcane_armor"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "dragons_blood":
        player.add_buff("fire_imbue", duration=30.0)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "dragons_blood"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "feather_fall":
        player.add_buff("feather_fall", duration=50.0)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "feather_fall"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "honeyed_healing":
        max_hp = player.get_total_max_hp()
        player.hp = max_hp
        player.cleanse(_FULL_DEBUFF_CLEANSE)
        _consume_item(player, item)
        game.add_event("HEAL", {"target": player.id, "amount": max_hp}, floor_id=player.floor_id)
        game.add_event("DRINK", {"player": player.id, "type": "honeyed_healing"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "icy_touch":
        player.add_buff("frost_imbue", duration=30.0)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "icy_touch"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "might":
        player.strength = min(player.strength + 1, 30)
        old_max = player.max_hp
        player.max_hp += 5
        player.hp = min(player.hp + 5, player.max_hp)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "might", "str_gained": 1, "hp_gained": 5}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "toxic_essence":
        player.add_buff("toxic_imbue", duration=30.0)
        _consume_item(player, item)
        game.add_event("DRINK", {"player": player.id, "type": "toxic_essence"}, floor_id=player.floor_id, source_player_id=player.id)
    game.on_potion_drunk(player, item)


def action_imbue(game, player, item, tx=None, ty=None) -> None:
    """Open wand selection dialog (SPD MagesStaff AC_IMBUE)."""
    wands = [i for i in player.belongings.all_items() if isinstance(i, Wand) and i is not item.imbued_wand]
    if not wands:
        return
    game.add_event("IMBUE_WAND_CHOICE_AVAILABLE", {
        "player": player.id,
        "staff_id": item.id,
        "candidates": [w.id for w in wands],
    }, floor_id=player.floor_id, player_id=player.id)


def action_affix(game, player, item, tx=None, ty=None) -> None:
    armor = player.belongings.armor
    if armor is None:
        return
    if item.cursed and item.cursed_known:
        return
    armor.level += max(1, item.level + 1)
    armor.level_known = True
    player.belongings.artifact = None
    player.quickslot.clear_item(item.id)
    player.seal_affixed = True
    game.add_event("AFFIX_SEAL", {"player": player.id, "armor": armor.id}, floor_id=player.floor_id, source_player_id=player.id)




def _drop_item_down_chasm(game, player, item, x: int, y: int) -> None:
    game.add_event("DROP", {
        "player": player.id,
        "item": item.id,
        "item_name": item.name,
        "item_kind": item.kind,
        "item_type": item.type,
    }, floor_id=player.floor_id)
    next_floor_id = player.floor_id + 1
    if next_floor_id <= 25:
        next_floor = game._get_or_create_floor(next_floor_id)
        item.pos = Position(x=x, y=y)
        next_floor.items[item.id] = item


def _resolve_seed_placement(game, player, seed: Seed, x: int, y: int, play_sound: bool = True) -> None:
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= x < floor.width and 0 <= y < floor.height):
        return

    tile = floor.grid[y][x]

    if tile == TileType.CHASM:
        _drop_item_down_chasm(game, player, seed, x, y)
        return

    if tile == TileType.ALCHEMY:
        _floor_drop(game, player, seed, x, y)
        game.add_event("DROP", {"player": player.id, "item": seed.id, "item_name": seed.name, "item_kind": seed.kind, "item_type": seed.type}, floor_id=player.floor_id)
        return

    if (x, y) in floor.traps:
        _floor_drop(game, player, seed, x, y)
        game.add_event("DROP", {"player": player.id, "item": seed.id, "item_name": seed.name, "item_kind": seed.kind, "item_type": seed.type}, floor_id=player.floor_id)
        game.trigger_trap_at(floor, x, y, player.floor_id)
        return

    plantable_terrains = {
        TileType.FLOOR, TileType.FLOOR_GRASS, TileType.HIGH_GRASS,
        TileType.FURROWED_GRASS, TileType.EMPTY_DECO, TileType.EMBERS,
        TileType.FLOOR_WOOD, TileType.FLOOR_COBBLE, TileType.REGION_DECO,
        TileType.REGION_DECO_ALT, TileType.FLOOR_WATER,
        TileType.DOOR, TileType.OPEN_DOOR,
    }

    if tile in plantable_terrains:
        floor.plants.pop((x, y), None)

        if tile not in (TileType.FLOOR_WATER, TileType.FLOOR_GRASS, TileType.DOOR, TileType.OPEN_DOOR):
            floor.grid[y][x] = TileType.FLOOR_GRASS
            game.add_event("MAP_PATCH", {"tiles": [{"x": x, "y": y, "tile": TileType.FLOOR_GRASS}]}, floor_id=player.floor_id)

        _plant_seed_at(floor, (x, y), seed.plant_type)
        if play_sound:
            game.add_event("PLAY_SOUND", {"sound": "PLANT", "x": x, "y": y}, floor_id=player.floor_id)

        subclass_info = getattr(player, "subclass_info", None)
        if subclass_info and subclass_info.subclass == "warden":
            patches = []
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < floor.width and 0 <= ny < floor.height:
                        ntile = floor.grid[ny][nx]
                        if ntile in (TileType.FLOOR, TileType.FLOOR_GRASS, TileType.EMPTY_DECO, TileType.EMBERS):
                            floor.grid[ny][nx] = TileType.FURROWED_GRASS
                            patches.append({"x": nx, "y": ny, "tile": TileType.FURROWED_GRASS})
            if patches:
                game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=player.floor_id)

        floor.rebuild_flags()

        in_lotus_range = False
        for mob in getattr(floor, "mobs", {}).values():
            if getattr(mob, "mob_type", "") == "lotus" and getattr(mob, "is_alive", True):
                dist = max(abs(x - mob.pos.x), abs(y - mob.pos.y))
                range_val = getattr(mob, "view_distance", 2)
                if dist <= range_val:
                    in_lotus_range = True
                    break

        if in_lotus_range:
            target_entity = game._entity_at(floor, player.floor_id, x, y, exclude_id="")

            if target_entity is not None and (x, y) in floor.plants:
                plant_obj = floor.plants[(x, y)]
                _trigger_plant_effect(floor, (x, y), plant_obj, target_entity)
                floor.plants.pop((x, y), None)
                game.add_event("PLAY_SOUND", {"sound": "PLANT_TRIGGER", "x": x, "y": y}, floor_id=player.floor_id)
                if isinstance(target_entity, Player) and getattr(target_entity, "pending_ascend", False):
                    target_entity.pending_ascend = False
                    game._apply_fadeleaf_ascend(target_entity, target_entity.id, target_entity.floor_id)

        return

    _floor_drop(game, player, seed, x, y)
    game.add_event("DROP", {"player": player.id, "item": seed.id, "item_name": seed.name, "item_kind": seed.kind, "item_type": seed.type}, floor_id=player.floor_id)


def action_plant_seed(game, player, item, tx=None, ty=None) -> None:
    single_seed = _consume_item(player, item)
    if single_seed is None:
        return
    _resolve_seed_placement(game, player, single_seed, player.pos.x, player.pos.y)
    player.action_until = time.time() + 1.0


def _detach_item_for_throw(player, item):
    if player.belongings.is_equipped(item.id):
        if item.cursed and item.cursed_known:
            return None
        slot = player.belongings.find_equipped_slot(item.id)
        if slot is not None:
            cur = getattr(player.belongings, slot)
            if hasattr(cur, "on_unequip"):
                cur.on_unequip(player)
            setattr(player.belongings, slot, None)
            player.quickslot.clear_item(cur.id)
            return cur
    return _consume_item(player, item)


def _proc_improvised_projectiles(game, player, target_entity, floor_id: int) -> None:
    if target_entity is None or not getattr(target_entity, "is_alive", True):
        return
    if getattr(player, "faction", None) == getattr(target_entity, "faction", None):
        return
    talent_info = getattr(player, "talent_info", None)
    if talent_info is None:
        subclass_info = getattr(player, "subclass_info", None)
        talent_info = getattr(subclass_info, "talent_info", None)
    if talent_info is None:
        return
    ip = talent_info.level("improvised_projectiles") if hasattr(talent_info, "level") else talent_info.talents.get("improvised_projectiles", 0)
    if ip > 0 and not player.has_buff("improvised_projectile_cooldown"):
        target_entity.add_buff("blindness", duration=1.0 + ip, level=1)
        player.add_buff("improvised_projectile_cooldown", duration=50.0, level=1)
        game.add_event("PLAY_SOUND", {"sound": "HIT"}, floor_id=floor_id)


def _trace_throw(game, player, floor, tx: int, ty: int) -> tuple[int, int]:
    return ballistica_trace(
        player.pos.x, player.pos.y, tx, ty,
        floor.flags, floor.width, floor.height,
        list(game._players_on_floor(player.floor_id)),
        list(floor.mobs.values()),
        player.id,
        stop_chars=True,
        stop_solid=True,
    )


def _action_throw_seed(game, player, item, tx: int, ty: int) -> None:
    floor = game._get_or_create_floor(player.floor_id)
    single_seed = _detach_item_for_throw(player, item)
    if single_seed is None:
        return

    lx, ly = _trace_throw(game, player, floor, tx, ty)

    serialized_item = game._serialize_floor_item(single_seed)
    game.add_event("RANGED_ATTACK", {
        "source": player.id,
        "x": player.pos.x,
        "y": player.pos.y,
        "target_x": lx,
        "target_y": ly,
        "projectile": "seed",
        "item": serialized_item,
        "sound": "THROW",
        "is_wand": False,
        "is_bow": False,
        "next_attack_in_ms": 1000,
    }, floor_id=player.floor_id)

    target_entity = game._entity_at(floor, player.floor_id, lx, ly, exclude_id=player.id)
    _proc_improvised_projectiles(game, player, target_entity, player.floor_id)
    _resolve_seed_placement(game, player, single_seed, lx, ly, play_sound=False)
    player.last_attack_time = time.time()
    player.action_until = time.time() + 1.0


def _action_throw_potion(game, player, item, tx: int, ty: int) -> None:
    floor = game._get_or_create_floor(player.floor_id)
    single_potion = _detach_item_for_throw(player, item)
    if single_potion is None:
        return

    lx, ly = _trace_throw(game, player, floor, tx, ty)

    serialized_item = game._serialize_floor_item(single_potion)
    game.add_event("RANGED_ATTACK", {
        "source": player.id,
        "x": player.pos.x,
        "y": player.pos.y,
        "target_x": lx,
        "target_y": ly,
        "projectile": "potion",
        "item": serialized_item,
        "sound": "THROW",
        "is_wand": False,
        "is_bow": False,
        "next_attack_in_ms": 1000,
    }, floor_id=player.floor_id)

    tile = floor.grid[ly][lx] if (0 <= lx < floor.width and 0 <= ly < floor.height) else TileType.FLOOR
    if tile == TileType.CHASM:
        _drop_item_down_chasm(game, player, single_potion, lx, ly)
        player.last_attack_time = time.time()
        player.action_until = time.time() + 1.0
        return

    if tile == TileType.WELL:
        _floor_drop(game, player, single_potion, lx, ly)
        game.add_event("DROP", {"player": player.id, "item": single_potion.id, "item_name": single_potion.name, "item_kind": single_potion.kind, "item_type": single_potion.type}, floor_id=player.floor_id)
        player.last_attack_time = time.time()
        player.action_until = time.time() + 1.0
        return

    game.on_potion_drunk(player, single_potion)
    game.identify_kind(single_potion, player)
    game.trigger_trap_at(floor, lx, ly, player.floor_id)

    handler = _SHATTER_HANDLERS.get(getattr(single_potion, "effect", ""))
    if handler is not None:
        handler(game, player, single_potion, lx, ly)
    else:
        _shatter_splash(game, player, single_potion, lx, ly)

    player.last_attack_time = time.time()
    player.action_until = time.time() + 1.0


def _action_throw_regular_item(game, player, item, tx: int, ty: int) -> None:
    floor = game._get_or_create_floor(player.floor_id)
    single_item = _detach_item_for_throw(player, item)
    if single_item is None:
        return

    lx, ly = _trace_throw(game, player, floor, tx, ty)

    serialized_item = game._serialize_floor_item(single_item)
    game.add_event("RANGED_ATTACK", {
        "source": player.id,
        "x": player.pos.x,
        "y": player.pos.y,
        "target_x": lx,
        "target_y": ly,
        "projectile": getattr(single_item, "kind", "item"),
        "item": serialized_item,
        "sound": "THROW",
        "is_wand": False,
        "is_bow": False,
        "next_attack_in_ms": 1000,
    }, floor_id=player.floor_id)

    target_entity = game._entity_at(floor, player.floor_id, lx, ly, exclude_id=player.id)
    _proc_improvised_projectiles(game, player, target_entity, player.floor_id)

    tile = floor.grid[ly][lx] if (0 <= lx < floor.width and 0 <= ly < floor.height) else TileType.FLOOR
    if tile == TileType.CHASM:
        _drop_item_down_chasm(game, player, single_item, lx, ly)
    else:
        if tile == TileType.DOOR:
            floor.grid[ly][lx] = TileType.OPEN_DOOR
            floor.rebuild_flags()
            game.add_event("PLAY_SOUND", {"sound": "DOOR_OPEN", "x": lx, "y": ly}, floor_id=player.floor_id)
            game.add_event("MAP_PATCH", {"tiles": [{"x": lx, "y": ly, "tile": TileType.OPEN_DOOR}]}, floor_id=player.floor_id)

        press_cell(floor, (lx, ly), target_entity)
        game.trigger_trap_at(floor, lx, ly, player.floor_id)
        _floor_drop(game, player, single_item, lx, ly)
        game.add_event("DROP", {"player": player.id, "item": single_item.id, "item_name": single_item.name, "item_kind": single_item.kind, "item_type": single_item.type}, floor_id=player.floor_id)
        if isinstance(single_item, CeremonialCandle):
            game._check_ritual_candles(player.floor_id)

    player.last_attack_time = time.time()
    player.action_until = time.time() + 1.0


def action_shoot(game, player, item, tx=None, ty=None) -> None:
    if tx is None or ty is None:
        return
    game.perform_ranged_attack(player.id, item.id, tx, ty)


def _action_throw_missile(game, player, item, tx: int, ty: int) -> None:
    game.perform_ranged_attack(player.id, item.id, tx, ty)


def _action_throw_bomb(game, player, item, tx: int, ty: int) -> None:
    floor = game._get_or_create_floor(player.floor_id)
    lx, ly = _trace_throw(game, player, floor, tx, ty)
    removed = _detach_item_for_throw(player, item)
    if removed is None:
        return
    game.add_event("THROW", {"player": player.id, "item": removed.id, "sound": "THROW"},
                   floor_id=player.floor_id)
    game.light_bomb(player, floor, player.floor_id, removed, lx, ly)
    player.last_attack_time = time.time()
    player.action_until = time.time() + 1.0


_THROW_DISPATCH: Dict[str, Callable] = {
    "missile": _action_throw_missile,
    "seed": _action_throw_seed,
    "potion": _action_throw_potion,
    "bomb": _action_throw_bomb,
    "runestone": action_throw_runestone,
    "regular": _action_throw_regular_item,
}


def action_throw(game, player, item, tx=None, ty=None) -> None:
    if tx is None or ty is None:
        return
    behavior = getattr(item, "throw_behavior", "regular")
    handler = _THROW_DISPATCH.get(behavior, _action_throw_regular_item)
    handler(game, player, item, tx, ty)


def _shatter_liquid_flame(game, player, item, tx, ty) -> None:
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return

    blob_id = f"fire_potion_{player.id}_{tx}_{ty}"
    if _create_fire_blob(floor, (tx, ty), 1 + player.floor_id, blob_id):
        game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)
        game.add_event("FLAME_BURST", {"x": tx, "y": ty}, floor_id=player.floor_id)
        game.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=player.floor_id)


def _shatter_gas(game, player, item, tx, ty) -> None:
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return

    gas_type = getattr(item, "effect", "")
    if gas_type == "levitation":
        gas_type = "confusion_gas"
    strength = 4 + player.floor_id // 2
    _create_gas(floor, (tx, ty), strength, gas_type)

    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)


def _shatter_frost(game, player, item, tx, ty) -> None:
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return
    _freeze_area(floor, (tx, ty))
    _create_gas(floor, (tx, ty), 4, "frost_gas")
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)


def _shatter_snap_freeze(game, player, item, tx, ty) -> None:
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return
    for mob in floor.mobs.values():
        if not mob.is_alive or mob.faction == "player":
            continue
        if abs(mob.pos.x - tx) <= 3 and abs(mob.pos.y - ty) <= 3:
            mob.add_buff("frost", duration=10.0, level=1)
            mob.add_buff("roots", duration=10.0)
    _create_gas(floor, (tx, ty), 4, "frost_gas")
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)


def _shatter_aqua(game, player, item, tx, ty) -> None:
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return
    for mob in floor.mobs.values():
        if not mob.is_alive or mob.faction == "player":
            continue
        if abs(mob.pos.x - tx) <= 2 and abs(mob.pos.y - ty) <= 2:
            dmg = max(1, round(mob.max_hp * 0.25))
            mob.take_damage(dmg)
            game.add_event("DAMAGE", {"target": mob.id, "amount": dmg, "water": True}, floor_id=player.floor_id)
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)
    game.add_event("SPLASH", {"x": tx, "y": ty}, floor_id=player.floor_id)


def _shatter_caustic(game, player, item, tx, ty) -> None:
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return
    for mob in floor.mobs.values():
        if not mob.is_alive or mob.faction == "player":
            continue
        if abs(mob.pos.x - tx) <= 3 and abs(mob.pos.y - ty) <= 3:
            mob.add_buff("ooze", duration=10.0, level=1, stack_mode="extend")
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)


def _shatter_unstable(game, player, item, tx, ty) -> None:
    effects = ["liquid_flame", "toxic_gas", "paralytic_gas", "corrosive_gas", "frost_gas"]
    chosen = random.choice(effects)
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return
    if chosen == "liquid_flame":
        blob_id = f"fire_unstable_{player.id}_{tx}_{ty}"
        _create_fire_blob(floor, (tx, ty), 1 + player.floor_id, blob_id)
    else:
        _create_gas(floor, (tx, ty), 4 + player.floor_id // 2, chosen)
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)


def _shatter_purity(game, player, item, tx, ty) -> None:
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return
    for bid in list(floor.blob_areas.keys()):
        b = floor.blob_areas[bid]
        cells = b.get("cells", [])
        new_cells = [c for c in cells if max(abs(c[0] - tx), abs(c[1] - ty)) > 3]
        if not new_cells:
            del floor.blob_areas[bid]
        else:
            b["cells"] = new_cells
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)
    game.add_event("DISCOVER", {"x": tx, "y": ty}, floor_id=player.floor_id)


def _shatter_splash(game, player, item, tx, ty) -> None:
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)
    game.add_event("SPLASH", {"x": tx, "y": ty}, floor_id=player.floor_id)


# Potion-effect -> shatter handler, dispatched by action_throw. Mirrors the
# _PROC_HANDLERS pattern in weapon_enchants.py/armor_glyphs.py.
_SHATTER_HANDLERS: Dict[str, Callable] = {
    **{effect: _shatter_liquid_flame for effect in ("liquid_flame", "infernal_brew")},
    **{effect: _shatter_gas for effect in (
        "toxic_gas", "paralytic_gas", "corrosive_gas", "shrouding_fog",
        "storm_clouds", "blizzard_brew", "shocking_brew", "levitation",
    )},
    "frost": _shatter_frost,
    "snap_freeze": _shatter_snap_freeze,
    "aqua_brew": _shatter_aqua,
    "caustic_brew": _shatter_caustic,
    "unstable_brew": _shatter_unstable,
    "purity": _shatter_purity,
    "cleansing": _shatter_purity,
}


def action_zap(game, player, item, tx=None, ty=None) -> None:
    if tx is None or ty is None:
        return
    game.perform_ranged_attack(player.id, item.id, tx, ty)


def action_stealth(game, player, item, tx=None, ty=None) -> None:
    # Cloak of Shadows: toggle the Rogue's sustained stealth.
    game.toggle_cloak_stealth(player.id)


def action_summon(game, player, item, tx=None, ty=None) -> None:
    import uuid
    from app.engine.entities.items.artifacts import DriedRose
    from app.engine.entities.mobs import GhostHeroMob

    if not isinstance(item, DriedRose):
        return
    floor = game._get_or_create_floor(player.floor_id)
    neighbors = [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]
    random.shuffle(neighbors)
    spawn_pos = None
    for dx, dy in neighbors:
        nx, ny = player.pos.x + dx, player.pos.y + dy
        if not (0 <= nx < floor.width and 0 <= ny < floor.height):
            continue
        if not floor.flags.passable[ny][nx]:
            continue
        occupied = any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values())
        if not occupied:
            spawn_pos = (nx, ny)
            break
    if spawn_pos is None:
        return

    ghost = GhostHeroMob(
        id=f"ghost_hero_{uuid.uuid4().hex[:8]}",
        pos=Position(x=spawn_pos[0], y=spawn_pos[1]),
        owner_id=player.id,
    )
    floor.mobs[ghost.id] = ghost
    item.ghost_id = ghost.id
    item.charge = 0
    game.add_event("GHOST_SUMMON", {
        "player": player.id, "ghost_id": ghost.id,
        "x": ghost.pos.x, "y": ghost.pos.y,
    }, floor_id=player.floor_id, source_player_id=player.id)


def action_direct(game, player, item, tx=None, ty=None) -> None:
    from app.engine.entities.items.artifacts import DriedRose
    from app.engine.entities.mobs import GhostHeroMob
    if not isinstance(item, DriedRose) or tx is None or ty is None:
        return
    floor = game._get_or_create_floor(player.floor_id)
    ghost = floor.mobs.get(item.ghost_id)
    if ghost is None or not ghost.is_alive:
        return
    if isinstance(ghost, GhostHeroMob):
        ghost.direct_x = tx
        ghost.direct_y = ty
        ghost.target_id = ""
        game.add_event("GHOST_DIRECT", {
            "player": player.id, "ghost_id": ghost.id,
            "x": tx, "y": ty,
        }, floor_id=player.floor_id, source_player_id=player.id)


def _ghost_weapon_info(w) -> dict:
    if w is None:
        return None
    return {
        "id": w.id, "name": w.name, "kind": w.kind, "tier": getattr(w, "tier", 0),
        "damage_min": w.damage_min, "damage_max": w.damage_max,
    }


def _ghost_armor_info(a) -> dict:
    if a is None:
        return None
    return {
        "id": a.id, "name": a.name, "kind": a.kind, "tier": getattr(a, "tier", 0),
        "dr_min": a.dr_min, "dr_max": a.dr_max,
    }


def action_ghost_gear(game, player, item, tx=None, ty=None) -> None:
    from app.engine.entities.items.artifacts import DriedRose
    if not isinstance(item, DriedRose):
        return
    floor = game._get_or_create_floor(player.floor_id)
    ghost = floor.mobs.get(item.ghost_id)
    if ghost is None or not ghost.is_alive:
        return
    game.add_event("GHOST_GEAR_OPEN", {
        "player": player.id,
        "rose_id": item.id,
        "ghost_id": ghost.id,
        "ghost_hp": ghost.hp,
        "ghost_max_hp": ghost.max_hp,
        "weapon": _ghost_weapon_info(item.weapon),
        "armor": _ghost_armor_info(item.armor),
    }, floor_id=player.floor_id, player_id=player.id)


def action_eat_handler(game, player, item, tx=None, ty=None) -> None:
    """Dispatch for EAT by item kind: HornOfPlenty (artifact, spends charge),
    Blandfruit (raw warning or cooked effect), or regular food."""
    if item.kind == "horn_of_plenty":
        action_horn_eat(game, player, item, tx, ty)
        return
    if item.kind == "blandfruit":
        potion_type = getattr(item, "potion_type", None)
        if potion_type is None:
            game.add_event("MESSAGE", {"text": "This fruit is far too bitter and tough to eat raw. Cook it at an alchemy pot with a seed first."},
                           floor_id=player.floor_id, player_id=player.id)
            return
        # Cooked blandfruit gives food energy AND potion effect
        removed = _consume_item(player, item)
        if removed is not None:
            game.on_food_eaten(player, item)

        # Apply imbued potion effect
        if potion_type == "strength":
            player.strength = min(player.strength + 1, 30)
            game.add_event("MESSAGE", {"text": "You feel a surge of strength!"}, floor_id=player.floor_id, player_id=player.id)
        elif potion_type == "health":
            player.cleanse(_HEALING_POTION_CLEANSE)
            amount = round(0.8 * player.get_total_max_hp() + 14)
            player.set_heal(amount, 0.25, 0)
        elif potion_type == "mind_vision":
            player.add_buff("mind_vision", duration=20.0)
        elif potion_type == "invisibility":
            player.add_buff("invisibility", duration=20.0)
        elif potion_type == "levitation":
            player.add_buff("levitation", duration=20.0)
        elif potion_type == "haste":
            player.add_buff("haste", duration=20.0)
        elif potion_type == "purity":
            player.cleanse(_PURITY_DEBUFFS)
        elif potion_type == "experience":
            amount = max(1, round((player.get_total_max_hp() - player.hp) * 2))
            if player.earn_exp(amount):
                game.add_event("LEVEL_UP", {"player": player.id, "level": player.level}, floor_id=player.floor_id)

        game.add_event("EAT", {"player": player.id, "item": item.id}, floor_id=player.floor_id)
        game.add_event("MESSAGE", {"text": f"You eat the {item.dynamic_name() if hasattr(item, 'dynamic_name') else item.name}."},
                       floor_id=player.floor_id, player_id=player.id)
        game.add_event("PLAY_SOUND", {"sound": "EAT"}, floor_id=player.floor_id)
        return

    removed = _consume_item(player, item)
    if removed is not None:
        game.on_food_eaten(player, item)
    game.add_event("EAT", {"player": player.id, "item": item.id}, floor_id=player.floor_id)
    game.add_event("MESSAGE", {"text": f"You eat the {item.name}."},
                    floor_id=player.floor_id, player_id=player.id)
    game.add_event("PLAY_SOUND", {"sound": "EAT"}, floor_id=player.floor_id)


def action_wear(game, player, item, tx=None, ty=None) -> None:
    """Dispatch for WEAR action by item kind: TengusMask (subclass choice)
    or KingsCrown (armor ability choice)."""
    if item.kind == "tengu_mask":
        _wear_tengu_mask(game, player, item)
    elif item.kind == "kings_crown":
        _wear_kings_crown(game, player, item)


def _wear_tengu_mask(game, player, item) -> None:
    """TengusMask: open subclass selection (SPD: WndChooseSubclass). The item
    is only consumed once a subclass is actually picked (SPD TengusMask.choose);
    dismissing the window keeps it so the choice can be re-opened by re-wearing."""
    from app.engine.entities.subclasses import CLASS_SUBCLASSES
    if player.subclass_info.subclass is not None:
        return  # already chosen
    options = list(CLASS_SUBCLASSES.get(player.class_type, ()))
    if not options:
        return
    player._tengu_mask_worn = True
    game.add_event("SUBCLASS_CHOICE_AVAILABLE", {
        "player": player.id, "options": options,
    }, floor_id=player.floor_id, player_id=player.id)


def _wear_kings_crown(game, player, item) -> None:
    """KingsCrown: open armor ability selection (SPD: WndChooseAbility), but
    only if armor is equipped. The item is only consumed once an ability is
    actually picked (SPD KingsCrown.upgradeArmor); dismissing the window keeps
    it so the choice can be re-opened by re-wearing."""
    from app.engine.entities.subclasses import CLASS_ARMOR_ABILITIES
    if player.armor_ability:
        return  # already chosen
    if player.belongings.armor is None:
        game.add_event("MESSAGE", {"text": "You need to be wearing armor to use the King's Crown."},
                       floor_id=player.floor_id, player_id=player.id)
        return  # SPD: "naked" - need armor equipped
    options = list(CLASS_ARMOR_ABILITIES.get(player.class_type, ()))
    if not options:
        return
    player._kings_crown_worn = True
    game.add_event("ARMOR_ABILITY_CHOICE_AVAILABLE", {
        "player": player.id, "options": options,
    }, floor_id=player.floor_id, player_id=player.id)


def action_inscribe(game, player, item, tx=None, ty=None) -> None:
    """ArcaneStylus: open armor picker, then apply glyph via apply_stylus_target."""
    from app.engine.entities.items.equip import Armor as _Armor
    candidates = [
        it.id for it in player.belongings.all_items()
        if it.id != item.id and isinstance(it, _Armor)
        and not (it.cursed_known and it.cursed)
        and not (hasattr(it.enchantment, "type") and it.enchantment.type in _CURSE_GLYPH_SET)
    ]
    if not candidates:
        game.add_event("MESSAGE", {"text": "You have no armor suitable for inscription."},
                       floor_id=player.floor_id, player_id=player.id)
        return
    game.add_event(
        "STONE_SELECT_TARGET",
        {"player": player.id, "stone_id": item.id, "stone_kind": "arcane_stylus",
         "candidates": candidates},
        floor_id=player.floor_id, player_id=player.id,
    )


def apply_stylus_target(game, player, stylus, armor) -> None:
    """Apply a random glyph to the chosen armor; consume the stylus."""
    from app.engine.entities.items.equip import Armor as _Armor
    if not isinstance(armor, _Armor):
        return
    if armor.cursed_known and armor.cursed:
        game.add_event("MESSAGE", {"text": "The armor is cursed and rejects the stylus!"},
                       floor_id=player.floor_id, player_id=player.id)
        return
    if hasattr(armor.enchantment, "type") and armor.enchantment.type in _CURSE_GLYPH_SET:
        game.add_event("MESSAGE", {"text": "The cursed glyph cannot be overwritten!"},
                       floor_id=player.floor_id, player_id=player.id)
        return
    detached = _consume_item(player, stylus)
    if detached is None:
        return
    from app.engine.entities.armors.armor_glyphs import GLYPH_RARITY
    glyph_name = random.choices(list(GLYPH_RARITY.keys()), weights=list(GLYPH_RARITY.values()), k=1)[0]
    armor.enchantment.type = glyph_name
    glyph_label = glyph_name.replace("_", " ").title()
    game.add_event("MESSAGE", {"text": f"Your {armor.name} is inscribed with the {glyph_label} glyph!"},
                   floor_id=player.floor_id, player_id=player.id)
    game.add_event("ENCHANT", {"player": player.id, "item": armor.id},
                   floor_id=player.floor_id)
    game.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=player.floor_id)
    player.action_until = time.time() + 2.0


_CURSE_GLYPH_SET = frozenset(_CURSE_GLYPHS_TUPLE)


def action_noop(game, player, item, tx=None, ty=None) -> None:
    # OPEN (bag) are handled client-side or are no-op.
    return


ITEM_ACTION_DISPATCH = {
    Action.EQUIP: action_equip,
    Action.UNEQUIP: action_unequip,
    Action.DROP: action_drop,
    Action.DRINK: action_drink,
    Action.READ: action_read,
    Action.THROW: action_throw,
    Action.PLANT: action_plant_seed,
    Action.USE: action_use_stone,
    Action.ZAP: action_zap,
    Action.SHOOT: action_shoot,
    Action.AFFIX: action_affix,
    Action.STEALTH: action_stealth,
    Action.SUMMON: action_summon,
    Action.DIRECT: action_direct,
    "GHOST_GEAR": action_ghost_gear,
    Action.EAT: action_eat_handler,
    Action.WEAR: action_wear,
    Action.IMBUE: action_imbue,
    Action.INSCRIBE: action_inscribe,
    Action.OPEN: action_noop,
    Action.INFO: action_noop,
    # Artifact actions
    Action.BREW: action_brew,
    Action.ENERGIZE: action_energize,
    Action.PRICK: action_prick,
    Action.CAST: action_cast_chains,
    Action.BLESS: action_bless,
    Action.SNACK: action_snack,
    Action.STORE: action_store_food,
    Action.BEACON_SET: action_beacon_set,
    Action.BEACON_RETURN: action_beacon_return,
    Action.STEAL: action_steal,
    Action.PLANT_SEED: action_plant_seed_from_sandals,
    Action.IDENTIFY_SEED: action_identify_seed,
    Action.UNLOCK: action_unlock,
    Action.KEY_REVEAL: action_key_reveal,
    Action.SCRY: action_scry,
    Action.FREEZE: action_freeze,
    Action.STASIS: action_stasis,
    Action.BOOK_READ: action_book_read,
    Action.BOOK_READ_RESOLVE: action_book_read_resolve,
    Action.BOOK_INFUSE: action_book_infuse,
}
