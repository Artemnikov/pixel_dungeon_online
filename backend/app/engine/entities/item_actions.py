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
from typing import Optional

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import (
    Action, Position, Potion, Seed, Wand, SpiritBow,
    GooBlob, HealthPotion, ElixirOfAquaticRejuvenation, Waterskin,
)
from app.engine.entities.scroll_actions import action_read


def _floor_drop(game, player, item) -> None:
    item.pos = Position(x=player.pos.x, y=player.pos.y)
    floor = game._get_or_create_floor(player.floor_id)
    floor.items[item.id] = item


def action_equip(game, player, item, tx=None, ty=None) -> None:
    player.equip_item(item.id)


def action_unequip(game, player, item, tx=None, ty=None) -> None:
    player.unequip_item(item.id)


def action_drop(game, player, item, tx=None, ty=None) -> None:
    # Drop the whole stack/item, from the backpack or an equip slot.
    detached = player.belongings.backpack.detach_all(item.id)
    if detached is None and player.belongings.is_equipped(item.id):
        if item.cursed and item.cursed_known:
            return  # cursed gear can't be removed
        for slot in ("weapon", "armor", "artifact", "misc", "ring"):
            cur = getattr(player.belongings, slot)
            if cur is not None and cur.id == item.id:
                setattr(player.belongings, slot, None)
                detached = cur
                break
    if detached is None:
        return
    player.quickslot.clear_item(detached.id)
    _floor_drop(game, player, detached)
    game.add_event("DROP", {"player": player.id, "item": detached.id, "item_name": detached.name}, floor_id=player.floor_id)


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


def action_drink(game, player, item, tx=None, ty=None) -> None:
    if isinstance(item, Waterskin):
        action_drink_waterskin(game, player, item, tx, ty)
        return

    # Mirrors PotionOfHealing: heal 0.8*maxHP+14 over time, 25% of the remaining
    # pool per heal-tick. Reviving potions are consumed by reviving a downed ally
    # (see move_entity), not by self-drinking, so they no-op here.
    game.identify_kind(item)  # drinking reveals the potion type to the party
    effect = getattr(item, "effect", "")
    if effect == "regen":
        amount = round(0.8 * player.get_total_max_hp() + 14)
        player.set_heal(amount, 0.25, 0)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        game.add_event("DRINK", {"player": player.id, "type": "regen"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "fury":
        player.has_fury = True
        player.fury_turns_remaining = 10
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        game.add_event("DRINK", {"player": player.id, "type": "fury"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "aqua_rejuv":
        pool = round(player.get_total_max_hp() * 1.5)
        player.aqua_heal_left = max(player.aqua_heal_left, pool)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        game.add_event("DRINK", {"player": player.id, "type": "aqua_rejuv"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "mind_vision":
        # SPD MindVision: 20-turn buff revealing every mob's position through walls.
        player.add_buff("mind_vision", duration=20.0)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        game.add_event("DRINK", {"player": player.id, "type": "mind_vision"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "invisibility":
        # SPD Invisibility: 20-turn buff. Attacking breaks invisibility (see
        # combat._dispel_stealth). Reference-counted on Entity.invisible.
        player.add_buff("invisibility", duration=20.0)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        game.add_event("DRINK", {"player": player.id, "type": "invisibility"}, floor_id=player.floor_id, source_player_id=player.id)
    elif effect == "liquid_flame":
        dmg = max(1, player.hp // 3)
        player.take_damage(dmg)
        player.add_buff("burning", duration=8.0, level=1, stack_mode="extend")
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        game.add_event("DAMAGE", {"target": player.id, "amount": dmg, "burning": True}, floor_id=player.floor_id)
        game.add_event("FLAME_BURST", {"x": player.pos.x, "y": player.pos.y}, floor_id=player.floor_id)
        cx, cy = player.pos.x, player.pos.y
        floor = game._get_or_create_floor(player.floor_id)
        blob_id = f"fire_drink_{player.id}"
        cells = set()
        volume = {}
        strength = 1 + player.floor_id
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    if floor.flags.passable[ny][nx] if floor.flags else False:
                        if floor.grid[ny][nx] != TileType.FLOOR_WATER:
                            cells.add((nx, ny))
                            volume[(nx, ny)] = strength
        if cells:
            for bid in list(floor.blob_areas.keys()):
                b = floor.blob_areas[bid]
                if b.get("type") == "fire" and b.get("cells", set()) & cells:
                    del floor.blob_areas[bid]
            floor.blob_areas[blob_id] = {"type": "fire", "cells": cells, "volume": volume}
            game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)
            game.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=player.floor_id)
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
    }, floor_id=player.floor_id, source_player_id=player.id)


def action_alchemize(game, player, item, tx=None, ty=None) -> None:
    # GooBlob + Health Potion at an Alchemy Pot -> Elixir of Aquatic Rejuvenation
    # (SPD ElixirOfAquaticRejuvenation.Recipe). Requires standing on the pot.
    if not isinstance(item, GooBlob):
        return
    floor = game._get_or_create_floor(player.floor_id)
    if (player.pos.x, player.pos.y) not in floor.alchemy_pots:
        return
    health_potion = next((it for it in player.inventory if isinstance(it, HealthPotion)), None)
    if health_potion is None:
        return

    blob = player.belongings.backpack.detach(item.id)
    if blob is None:
        return
    potion = player.belongings.backpack.detach(health_potion.id)
    if potion is None:
        # roll back the detached blob
        player.belongings.backpack.collect(blob)
        return
    if player.belongings.get_item(item.id) is None:
        player.quickslot.convert_to_placeholder(blob)
    if player.belongings.get_item(health_potion.id) is None:
        player.quickslot.convert_to_placeholder(potion)

    elixir = ElixirOfAquaticRejuvenation()
    player.belongings.backpack.collect(elixir)
    game.add_event("ALCHEMIZE", {"player": player.id, "item": elixir.id},
                   floor_id=player.floor_id, source_player_id=player.id)


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




def action_plant(game, player, item, tx=None, ty=None) -> None:
    if tx is None or ty is None:
        return
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return
    tile = floor.grid[ty][tx]
    valid_terrains = [
        TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.FURROWED_GRASS,
        TileType.FLOOR, TileType.EMPTY_DECO,
    ]
    if tile not in valid_terrains:
        return  # can't plant here
    floor.grid[ty][tx] = TileType.FLOOR_GRASS
    from app.engine.game.terrain_effects import _plant_seed_at
    _plant_seed_at(floor, (tx, ty), item.plant_type)
    removed = player.belongings.backpack.detach(item.id)
    if removed is not None and player.belongings.get_item(item.id) is None:
        player.quickslot.convert_to_placeholder(removed)
    game.add_event("MAP_PATCH", {"tiles": [{"x": tx, "y": ty, "tile": TileType.FLOOR_GRASS}]}, floor_id=player.floor_id)
    # Warden bonus: surrounding cells become FURROWED_GRASS
    subclass_info = getattr(player, "subclass_info", None)
    if subclass_info and subclass_info.subclass == "warden":
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = tx + dx, ty + dy
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    if floor.grid[ny][nx] != TileType.WALL and floor.grid[ny][nx] != TileType.VOID:
                        floor.grid[ny][nx] = TileType.FURROWED_GRASS
        floor.rebuild_flags()
        patches = [{"x": tx + dx, "y": ty + dy, "tile": floor.grid[ty + dy][tx + dx]}
                    for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    if 0 <= tx + dx < floor.width and 0 <= ty + dy < floor.height]
        game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=player.floor_id)
    floor.rebuild_flags()


def action_shoot(game, player, item, tx=None, ty=None) -> None:
    if tx is None or ty is None:
        return
    game.perform_ranged_attack(player.id, item.id, tx, ty)


def action_throw(game, player, item, tx=None, ty=None) -> None:
    if tx is None or ty is None:
        return
    # Seeds are planted, not thrown as items
    if isinstance(item, Seed):
        action_plant(game, player, item, tx, ty)
        return
    # Potion of Liquid Flame: shatter on impact, create fire blob
    if isinstance(item, Potion) and item.effect == "liquid_flame":
        _shatter_liquid_flame(game, player, item, tx, ty)
        return
    game.perform_ranged_attack(player.id, item.id, tx, ty)


def _shatter_liquid_flame(game, player, item, tx, ty) -> None:
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return

    # Remove potion from inventory
    removed = player.belongings.backpack.detach(item.id)
    if removed is not None and player.belongings.get_item(item.id) is None:
        player.quickslot.convert_to_placeholder(removed)

    # Create fire blob in 3x3 area centered on impact, SPD strength 1+depth
    blob_id = f"fire_potion_{player.id}_{tx}_{ty}"
    cells = set()
    volume = {}
    strength = 1 + player.floor_id
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx, ny = tx + dx, ty + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                if floor.flags.passable[ny][nx] if floor.flags else False:
                    if floor.grid[ny][nx] != TileType.FLOOR_WATER:
                        cells.add((nx, ny))
                        volume[(nx, ny)] = strength

    if cells:
        for bid in list(floor.blob_areas.keys()):
            b = floor.blob_areas[bid]
            if b.get("type") == "fire" and b.get("cells", set()) & cells:
                del floor.blob_areas[bid]
        floor.blob_areas[blob_id] = {
            "type": "fire",
            "cells": cells,
            "volume": volume,
        }
        game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=player.floor_id)
        game.add_event("FLAME_BURST", {"x": tx, "y": ty}, floor_id=player.floor_id)
        game.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=player.floor_id)


def action_zap(game, player, item, tx=None, ty=None) -> None:
    if tx is None or ty is None:
        return
    game.perform_ranged_attack(player.id, item.id, tx, ty)


def action_stealth(game, player, item, tx=None, ty=None) -> None:
    # Cloak of Shadows: toggle the Rogue's sustained stealth.
    game.toggle_cloak_stealth(player.id)


def action_summon(game, player, item, tx=None, ty=None) -> None:
    import random
    import uuid
    from app.engine.entities.base import DriedRose
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
    from app.engine.entities.base import DriedRose
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
    from app.engine.entities.base import DriedRose
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
    }, floor_id=player.floor_id, source_player_id=player.id)


def action_eat_handler(game, player, item, tx=None, ty=None) -> None:
    removed = player.belongings.backpack.detach(item.id)
    if removed is not None:
        if player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        game.on_food_eaten(player, item)
    game.add_event("EAT", {"player": player.id, "item": item.id}, floor_id=player.floor_id)


def action_wear(game, player, item, tx=None, ty=None) -> None:
    """Dispatch for WEAR action by item kind: TengusMask (subclass choice)
    or KingsCrown (armor ability choice)."""
    if item.kind == "tengu_mask":
        _wear_tengu_mask(game, player, item)
    elif item.kind == "kings_crown":
        _wear_kings_crown(game, player, item)


def _wear_tengu_mask(game, player, item) -> None:
    """TengusMask: consume the item and open subclass selection (SPD:
    WndChooseSubclass)."""
    from app.engine.entities.subclasses import CLASS_SUBCLASSES
    if player.subclass_info.subclass is not None:
        return  # already chosen
    options = list(CLASS_SUBCLASSES.get(player.class_type, ()))
    if not options:
        return
    removed = player.belongings.backpack.detach(item.id)
    if removed is not None:
        if player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
    game.add_event("SUBCLASS_CHOICE_AVAILABLE", {
        "player": player.id, "options": options,
    }, floor_id=player.floor_id, source_player_id=player.id)


def _wear_kings_crown(game, player, item) -> None:
    """KingsCrown: consume the item and open armor ability selection (SPD:
    WndChooseAbility), but only if armor is equipped."""
    from app.engine.entities.subclasses import CLASS_ARMOR_ABILITIES
    if player.armor_ability:
        return  # already chosen
    if player.belongings.armor is None:
        return  # SPD: "naked" - need armor equipped
    options = list(CLASS_ARMOR_ABILITIES.get(player.class_type, ()))
    if not options:
        return
    removed = player.belongings.backpack.detach(item.id)
    if removed is not None:
        if player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
    game.add_event("ARMOR_ABILITY_CHOICE_AVAILABLE", {
        "player": player.id, "options": options,
    }, floor_id=player.floor_id, source_player_id=player.id)


def action_noop(game, player, item, tx=None, ty=None) -> None:
    # OPEN (bag) are handled client-side or are no-ops.
    return


ITEM_ACTION_DISPATCH = {
    Action.EQUIP: action_equip,
    Action.UNEQUIP: action_unequip,
    Action.DROP: action_drop,
    Action.DRINK: action_drink,
    Action.READ: action_read,
    Action.THROW: action_throw,
    Action.ZAP: action_zap,
    Action.SHOOT: action_shoot,
    Action.AFFIX: action_affix,
    Action.STEALTH: action_stealth,
    Action.SUMMON: action_summon,
    Action.DIRECT: action_direct,
    "GHOST_GEAR": action_ghost_gear,
    Action.EAT: action_eat_handler,
    Action.WEAR: action_wear,
    Action.ALCHEMIZE: action_alchemize,
    Action.IMBUE: action_imbue,
    Action.OPEN: action_noop,
    Action.INFO: action_noop,
}
