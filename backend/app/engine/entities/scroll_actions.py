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
"""Scroll action handlers: action_read and apply_scroll_target.

Extracted from item_actions.py so that file stays under the 400-line limit.
"""
import random

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.item_union import Bag
from app.engine.entities.items_equip import Armor, ArmorEnchantment, KindOfWeapon
from app.engine.entities.items_wands import Wand
from app.engine.entities.player import Mob
from app.engine.entities.item_catalog import TRANSMUTE_GROUPS, make_catalog_item
from app.engine.entities.scroll_predicates import PREDICATE, player_inventory_items, transmute_group
from app.engine.entities.weapon_enchants import CURSES

_SCROLL_SOUNDS: dict[str, str] = {
    "scroll_of_rage": "CHALLENGE",
    "scroll_of_retribution": "BLAST",
    "scroll_of_recharging": "CHARGEUP",
    "scroll_of_lullaby": "LULLABY",
    # Teleportation intentionally absent: READ event plays the paper "READ" sound;
    # the TELEPORT event plays "TELEPORT" when the hero actually moves.
}

_SCROLL_VISUALS: dict[str, str] = {
    "scroll_of_identify": "IDENTIFY",
    "scroll_of_upgrade": "UP",
    "scroll_of_remove_curse": "CURSE",
    "scroll_of_transmutation": "CHANGE",
    "scroll_of_metamorphosis": "CHANGE",
    "scroll_of_rage": "SCREAM",
    "scroll_of_retribution": "FLASH",
    "scroll_of_recharging": "ENERGY",
    "scroll_of_lullaby": "NOTE",
    "scroll_of_terror": "TERROR",
    "scroll_of_magic_mapping": "MAP",
}


def _maybe_proc_inscribed_stealth(game, player) -> None:
    """Inscribed Stealth talent: reading any scroll grants brief invisibility."""
    inscribed_stealth = player.subclass_info.talent_info.level("inscribed_stealth")
    if inscribed_stealth > 0:
        player.add_buff("invisibility", duration=1.0 * (1 + 2 * inscribed_stealth), level=1)
        game.add_event("PLAY_SOUND", {"sound": "MELD"}, floor_id=player.floor_id, source_player_id=player.id)


def _teleport_player(game, player) -> None:
    """SPD ScrollOfTeleportation: move the player to a random passable,
    unoccupied cell on their current floor.

    Prefers unlocked SpecialRoom interiors (teleportPreferringUnseen).
    Falls back to any passable cell, preferring out-of-FOV.
    Auto-discovers secret doors adjacent to destination when using special room path.
    Breaks "rooted" on success."""
    from app.engine.dungeon.constants import RoomKind

    floor = game._get_or_create_floor(player.floor_id)

    occupied = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
    occupied |= {
        (p.pos.x, p.pos.y)
        for p in game.players.values()
        if p.floor_id == player.floor_id and p.is_alive
    }

    visible = set(game.get_visible_tiles(
        player.pos, radius=game._view_distance(player), floor_id=player.floor_id,
        viewer_id=player.id))

    used_special_path = False
    pool: list = []

    # Step 1: prefer unlocked SpecialRoom interiors (SPD teleportPreferringUnseen)
    special_cells = []
    for room in floor.rooms:
        if room.kind != RoomKind.SPECIAL:
            continue
        locked = False
        for ry in range(max(0, room.y - 1), min(floor.height, room.y + room.height + 1)):
            for rx in range(max(0, room.x - 1), min(floor.width, room.x + room.width + 1)):
                t = floor.grid[ry][rx]
                if t in (TileType.LOCKED_DOOR, TileType.CRYSTAL_DOOR, TileType.BARRICADE):
                    locked = True
                    break
            if locked:
                break
        if locked:
            continue
        for ry in range(room.y, room.y + room.height):
            for rx in range(room.x, room.x + room.width):
                if (rx, ry) not in occupied and floor.flags and floor.flags.passable[ry][rx]:
                    special_cells.append((rx, ry))

    if special_cells:
        used_special_path = True
        out_of_fov = [c for c in special_cells if c not in visible]
        pool = out_of_fov if out_of_fov else special_cells

    # Step 2: fallback — any passable unoccupied cell, prefer out-of-FOV
    if not pool:
        for y in range(floor.height):
            for x in range(floor.width):
                if floor.flags and floor.flags.passable[y][x] and (x, y) not in occupied:
                    pool.append((x, y))
        if pool:
            out_of_fov = [c for c in pool if c not in visible]
            pool = out_of_fov if out_of_fov else pool

    if not pool:
        return

    from_x, from_y = player.pos.x, player.pos.y
    tx, ty = random.choice(pool)
    player.pos = Position(x=tx, y=ty)
    player.remove_buff("rooted")

    # Secret door auto-discovery (SPD: check neighbor cells for secret doors
    # when teleporting into a special room)
    secret_positions = []
    if used_special_path:
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
            nx, ny = tx + dx, ty + dy
            if (nx, ny) in floor.hidden_doors:
                actual_tile = floor.hidden_doors.pop((nx, ny))
                floor.grid[ny][nx] = actual_tile
                secret_positions.append({"x": nx, "y": ny})
        if secret_positions:
            floor.rebuild_flags()
            game.add_event("MAP_PATCH", {"tiles": secret_positions}, floor_id=player.floor_id)
            game.add_event("PLAY_SOUND", {"sound": "SECRET"}, player_id=player.id)

    game.add_event("TELEPORT", {
        "player": player.id, "from_x": from_x, "from_y": from_y, "x": tx, "y": ty,
    }, floor_id=player.floor_id)


def action_read(game, player, item, tx=None, ty=None) -> None:
    effect = getattr(item, "kind", "")
    _extra_event_data: dict = {}

    # SPD reading blocks: blindness, magic immunity, cursed book (scroll base).
    if player.has_buff("blindness"):
        game.add_event("READ", {"player": player.id, "item": item.id, "blocked": "blinded"}, floor_id=player.floor_id)
        return
    if player.has_buff("magic_immune"):
        game.add_event("READ", {"player": player.id, "item": item.id, "blocked": "no_magic"}, floor_id=player.floor_id)
        return

    if effect in PREDICATE:
        candidates = [it.id for it in player_inventory_items(player) if it.id != item.id and PREDICATE[effect](it, game)]
        was_unidentified = item.kind not in game.identified_kinds
        game.identify_kind(item)
        _maybe_proc_inscribed_stealth(game, player)
        if was_unidentified:
            # SPD: reading an unidentified scroll consumes it immediately,
            # before the target-selection dialog even opens.
            removed = player.belongings.backpack.detach(item.id)
            if removed is not None and player.belongings.get_item(item.id) is None:
                player.quickslot.convert_to_placeholder(removed)
        # Store the scroll kind so select_scroll_target can still apply the
        # effect even when the scroll was already consumed (unidentified path).
        player._pending_scroll_kind = effect
        player._pending_scroll_id = item.id
        game.add_event(
            "SCROLL_SELECT_TARGET",
            {"player": player.id, "scroll_id": item.id, "scroll_kind": effect, "candidates": candidates},
            floor_id=player.floor_id, player_id=player.id,
        )
        return

    # All non-PREDICATE scrolls are consumed immediately, so identify on read.
    game.identify_kind(item)

    if effect == "scroll_of_rage":
        floor = game._get_or_create_floor(player.floor_id)
        # beckon: wake ALL alive mobs on the floor toward the player (SPD: mob.beckon(curUser.pos))
        beckoned_ids = []
        for mob in floor.mobs.values():
            if mob.is_alive:
                mob.ai_state = "hunting"
                beckoned_ids.append(mob.id)
        # amok: FOV mobs only, excludes allies (matches SPD ScrollOfRage).
        for mob in game._mobs_in_fov(player, floor, player.floor_id):
            mob.add_buff("amok", duration=5, source_id=player.id)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        # SPD's beckon() always calls notice()→showAlert() unconditionally, even for
        # already-hunting mobs. Send IDs so the frontend can force-show the ! icon.
        _extra_event_data["beckoned_ids"] = beckoned_ids
    elif effect == "scroll_of_retribution":
        from app.engine.systems.loot import roll_drops

        max_hp = max(1, player.max_hp)
        power = min(4.0, 4.45 * (max_hp - player.hp) / max_hp)

        floor = game._get_or_create_floor(player.floor_id)
        for mob in game._mobs_in_fov(player, floor, player.floor_id):
            dmg = round(mob.max_hp / 10 + mob.hp * power * 0.225)
            dealt = mob.take_damage(dmg)
            if dealt > 0:
                game.add_event("DAMAGE", {"target": mob.id, "amount": dealt}, floor_id=player.floor_id)
            if not mob.is_alive:
                mob.die(
                    floor_mobs=floor.mobs,
                    tile_x=mob.pos.x,
                    tile_y=mob.pos.y,
                    players=list(game._players_on_floor(player.floor_id)),
                )
                game.add_event("DEATH", {"target": mob.id}, floor_id=player.floor_id)
                game.handle_mob_death(mob, floor, player.floor_id)
                for drop in roll_drops(mob, game.drop_counters, mob.pos.x, mob.pos.y, players=list(game._players_on_floor(player.floor_id))):
                    floor.items[drop.id] = drop
            else:
                mob.add_buff("blindness", duration=10)

        player.add_buff("weakness", duration=20)
        player.add_buff("blindness", duration=10)

        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
    elif effect == "scroll_of_teleportation":
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        _teleport_player(game, player)
    elif effect == "scroll_of_recharging":
        player.add_buff("recharging", duration=30.0)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
    elif effect == "scroll_of_lullaby":
        floor = game._get_or_create_floor(player.floor_id)
        affected_mobs = []
        for mob in game._mobs_in_fov(player, floor, player.floor_id):
            mob.add_buff("drowsy", duration=5)
            affected_mobs.append({"x": mob.pos.x, "y": mob.pos.y})
        player.add_buff("drowsy", duration=5)  # SPD also drowses curUser
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        _extra_event_data["affected_mobs"] = affected_mobs
    elif effect == "scroll_of_terror":
        floor = game._get_or_create_floor(player.floor_id)
        for mob in game._mobs_in_fov(player, floor, player.floor_id):
            if "terror" in getattr(mob, "immunities", []):
                continue
            mob.add_buff("terror", duration=20, source_id=player.id)
            mob.ai_state = "fleeing"
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
    elif effect == "scroll_of_magic_mapping":
        floor = game._get_or_create_floor(player.floor_id)
        # SPD: only mark discoverable cells (non-wall/void/deco) as mapped.
        floor.mapped = True
        NON_DISCOVERABLE = {TileType.VOID, TileType.WALL, TileType.WALL_DECO}
        floor.mapped_tiles = [
            (x, y) for y in range(floor.height) for x in range(floor.width)
            if floor.grid[y][x] not in NON_DISCOVERABLE
        ]
        patches = []
        fov_discover_positions = []
        found_secret = False
        visible = set(game.get_visible_tiles(
            player.pos, radius=game._view_distance(player), floor_id=player.floor_id,
            viewer_id=player.id))
        for (tx, ty), actual_tile in list(floor.hidden_doors.items()):
            floor.hidden_doors.pop((tx, ty))
            floor.grid[ty][tx] = actual_tile
            patches.append({"x": tx, "y": ty, "tile": actual_tile})
            if (tx, ty) in visible:
                fov_discover_positions.append({"x": tx, "y": ty})
            found_secret = True
        for (tx, ty), trap in floor.traps.items():
            if trap.hidden:
                trap.hidden = False
                found_secret = True
                if floor.grid[ty][tx] == TileType.SECRET_TRAP:
                    floor.grid[ty][tx] = TileType.TRAP
                    patches.append({"x": tx, "y": ty, "tile": TileType.TRAP})
                if (tx, ty) in visible:
                    fov_discover_positions.append({"x": tx, "y": ty})
        if patches:
            floor.rebuild_flags()
            game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=player.floor_id)
        if found_secret:
            game.add_event("PLAY_SOUND", {"sound": "SECRET"}, player_id=player.id)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        if fov_discover_positions:
            _extra_event_data["discover_positions"] = fov_discover_positions
    elif effect == "scroll_of_mirror_image":
        floor = game._get_or_create_floor(player.floor_id)
        clone_ids = game._spawn_mirror_images(player, floor, player.floor_id)
        clone_data = [
            {"id": cid, "x": floor.mobs[cid].pos.x, "y": floor.mobs[cid].pos.y}
            for cid in clone_ids if cid in floor.mobs
        ]
        game.add_event("MIRROR_IMAGE", {"player": player.id, "clones": clone_data}, floor_id=player.floor_id)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
    elif effect == "scroll_of_metamorphosis":
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        _maybe_proc_inscribed_stealth(game, player)
        sound = _SCROLL_SOUNDS.get(effect, "READ")
        visual = _SCROLL_VISUALS.get(effect)
        read_data: dict = {"player": player.id, "item": item.id, "sound": sound}
        if visual:
            read_data["visual"] = visual
        game.add_event("READ", read_data, floor_id=player.floor_id)
        game.add_event("METAMORPH_OPEN", {"player": player.id}, floor_id=player.floor_id)
        return
    elif effect == "scroll_of_anti_magic":
        player.add_buff("magic_immune", duration=20.0)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
    elif effect == "scroll_of_challenge":
        floor = game._get_or_create_floor(player.floor_id)
        beckoned_ids = []
        for mob in floor.mobs.values():
            if mob.is_alive and mob.faction != "player":
                mob.ai_state = "hunting"
                mob.target_id = player.id
                beckoned_ids.append(mob.id)
        player.add_buff("challenge_arena", duration=100.0)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        _extra_event_data["beckoned_ids"] = beckoned_ids
    elif effect == "scroll_of_divination":
        unid = [it for it in player.belongings.all_items()
                if getattr(it, "kind", "") not in game.identified_kinds
                and hasattr(it, "kind") and getattr(it, "category", None) in ("potion", "scroll", "wand", "ring")]
        random.shuffle(unid)
        identified = []
        for it in unid[:4]:
            game.identify_kind(it)
            identified.append(it.id)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        _extra_event_data["identified"] = identified
    elif effect == "scroll_of_dread":
        floor = game._get_or_create_floor(player.floor_id)
        for mob in game._mobs_in_fov(player, floor, player.floor_id):
            if "terror" in getattr(mob, "immunities", []):
                continue
            mob.add_buff("terror", duration=20, source_id=player.id)
            mob.add_buff("dread", duration=999999, source_id=player.id)
            mob.ai_state = "fleeing"
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
    elif effect == "scroll_of_foresight":
        player.add_buff("foresight", duration=400.0)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
    elif effect == "scroll_of_mystical_energy":
        player.add_buff("artifact_recharge", duration=30.0)
        for it in player.belongings.all_items():
            from app.engine.entities.items_wands import Wand
            if isinstance(it, Wand) and it.charges < it.max_charges:
                it.charges = it.max_charges
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        _extra_event_data["artifact_recharge"] = True
    elif effect == "scroll_of_passage":
        prev_floor = player.floor_id - 1
        if prev_floor >= 1:
            old_floor_id = player.floor_id
            player.floor_id = prev_floor
            game._invalidate_fov_cache()
            floor_prev = game._get_or_create_floor(prev_floor)
            if floor_prev.entrance_pos:
                player.pos = Position(x=floor_prev.entrance_pos[0], y=floor_prev.entrance_pos[1])
            game.add_event("FLOOR_CHANGE", {
                "player": player.id, "from_floor": old_floor_id, "to_floor": prev_floor,
                "x": player.pos.x, "y": player.pos.y,
            }, floor_id=prev_floor, source_player_id=player.id, player_id=player.id)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
    elif effect == "scroll_of_prismatic_image":
        floor = game._get_or_create_floor(player.floor_id)
        import uuid as _uuid_mod
        existing_image = next(
            (m for m in floor.mobs.values()
             if getattr(m, "mob_type", None) == "prismatic_image" and getattr(m, "owner_id", None) == player.id),
            None)
        if existing_image:
            heal = round(player.get_total_max_hp() * 0.5)
            existing_image.hp = min(existing_image.max_hp, existing_image.hp + heal)
            _extra_event_data["healed_image"] = existing_image.id
        else:
            spawn = None
            for dx, dy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)):
                nx, ny = player.pos.x+dx, player.pos.y+dy
                if 0<=nx<floor.width and 0<=ny<floor.height and floor.flags and floor.flags.passable[ny][nx]:
                    if not any(m.is_alive and m.pos.x==nx and m.pos.y==ny for m in floor.mobs.values()):
                        spawn = (nx, ny)
                        break
            if spawn:
                img_id = f"prismatic_{_uuid_mod.uuid4().hex[:8]}"
                img_hp = player.get_total_max_hp()
                img = Mob(
                    id=img_id, type="mob", mob_type="prismatic_image",
                    name="Prismatic Image",
                    pos=Position(x=spawn[0], y=spawn[1]),
                    hp=img_hp, max_hp=img_hp,
                    attack=player.attack, defense=player.defense,
                    damage_min=getattr(player, "damage_min", 1),
                    damage_max=getattr(player, "damage_max", 4),
                    faction="player", owner_id=player.id,
                )
                floor.mobs[img.id] = img
                _extra_event_data["prismatic_image"] = {"id": img.id, "x": spawn[0], "y": spawn[1]}
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
    elif effect == "scroll_of_psionic_blast":
        from app.engine.systems.loot import roll_drops
        floor = game._get_or_create_floor(player.floor_id)
        for mob in game._mobs_in_fov(player, floor, player.floor_id):
            dmg = max(1, round(mob.max_hp * 0.4))
            dealt = mob.take_damage(dmg)
            if dealt > 0:
                game.add_event("DAMAGE", {"target": mob.id, "amount": dealt, "psionic": True}, floor_id=player.floor_id)
            if not mob.is_alive:
                mob.die(floor_mobs=floor.mobs, tile_x=mob.pos.x, tile_y=mob.pos.y,
                        players=list(game._players_on_floor(player.floor_id)))
                game.add_event("DEATH", {"target": mob.id}, floor_id=player.floor_id)
                game.handle_mob_death(mob, floor, player.floor_id)
                for drop in roll_drops(mob, game.drop_counters, mob.pos.x, mob.pos.y,
                                       players=list(game._players_on_floor(player.floor_id))):
                    floor.items[drop.id] = drop
        self_dmg = max(1, round(player.get_total_max_hp() * 0.15))
        player.take_damage(self_dmg)
        player.add_buff("blindness", duration=10.0)
        player.add_buff("weakness", duration=50.0)
        game.add_event("DAMAGE", {"target": player.id, "amount": self_dmg, "psionic": True}, floor_id=player.floor_id)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
    elif effect == "scroll_of_sirens_song":
        floor = game._get_or_create_floor(player.floor_id)
        visible_mobs = list(game._mobs_in_fov(player, floor, player.floor_id))
        enthralled = None
        for mob in visible_mobs:
            if "charm" in getattr(mob, "immunities", []):
                continue
            mob.add_buff("charm", duration=999999, source_id=player.id)
            mob.faction = "player"
            mob.ai_state = "hunting"
            if enthralled is None:
                enthralled = mob
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        if enthralled:
            _extra_event_data["enthralled"] = enthralled.id

    _maybe_proc_inscribed_stealth(game, player)

    sound = _SCROLL_SOUNDS.get(effect, "READ")
    visual = _SCROLL_VISUALS.get(effect)
    event_data: dict = {"player": player.id, "item": item.id, "sound": sound}
    if visual:
        event_data["visual"] = visual
    event_data.update(_extra_event_data)
    game.add_event("READ", event_data, floor_id=player.floor_id)


def _apply_upgrade_target(game, player, target_item) -> None:
    from app.engine.entities.items_equip import Staff, KindOfWeapon, Armor as ArmorCls, Ring as RingCls
    # Pre-upgrade state tracking (SPD: curse enchant vs plain curse distinction)
    had_cursed_enchant = False
    if isinstance(target_item, KindOfWeapon) and target_item.enchantment:
        had_cursed_enchant = target_item.enchantment in CURSES
    if isinstance(target_item, ArmorCls):
        had_cursed_enchant = target_item.enchantment.type in CURSES

    if isinstance(target_item, Staff):
        target_item.upgrade()
    elif isinstance(target_item, RingCls):
        target_item.upgrade()
    else:
        target_item.level += 1
    target_item.level_known = True
    target_item.cursed = False
    target_item.cursed_known = True

    # SPD: Degrade.detach(curUser, Degrade.class)
    player.remove_buff("degrade")


def _apply_identify(game, player, target_item) -> None:
    game.identify_kind(target_item)


def _replace_in_bag(bag, old_id, new_item) -> bool:
    """Recursively replaces the item with id `old_id` inside `bag` (or one of
    its sub-bags) with `new_item`, in place. Returns True if found/replaced.

    Replacing in place preserves the item's slot/position in the bag, unlike
    detach+collect which would move it to the end or merge it into an
    existing stack of the same kind."""
    for idx, it in enumerate(bag.items):
        if it.id == old_id:
            bag.items[idx] = new_item
            return True
        if isinstance(it, Bag) and _replace_in_bag(it, old_id, new_item):
            return True
    return False


def _carry_over_enchantment(target_item, new_item) -> None:
    """Preserves enchantment/charge state across a transmutation so a cursed
    or enchanted item doesn't silently lose that state on its new kind."""
    if isinstance(target_item, KindOfWeapon) and isinstance(new_item, KindOfWeapon):
        new_item.enchantment = target_item.enchantment
    if isinstance(target_item, Armor) and isinstance(new_item, Armor):
        new_item.enchantment = target_item.enchantment.model_copy(deep=True)
    if isinstance(target_item, Wand) and isinstance(new_item, Wand):
        new_item.charges = target_item.charges
        new_item.max_charges = target_item.max_charges


def _apply_transmutation(game, player, target_item):
    group = transmute_group(target_item)
    candidate_kinds = [k for k in TRANSMUTE_GROUPS[group] if k != target_item.kind]
    if not candidate_kinds:
        # Deliberate fallback for single-member groups (armor/wand/ring each
        # have only one catalog kind currently): the scroll is still consumed,
        # but the "transmutation" is a no-op re-roll of the same kind. This is
        # a known catalog-size limitation, not a bug.
        candidate_kinds = TRANSMUTE_GROUPS[group]

    new_kind = random.choice(candidate_kinds)
    new_item = make_catalog_item(new_kind)

    if target_item.quantity > 1:
        source = target_item.split(1)
        new_item.level, new_item.level_known = source.level, source.level_known
        new_item.cursed, new_item.cursed_known = source.cursed, source.cursed_known
        _carry_over_enchantment(source, new_item)
        new_item.id = source.id
        new_item.quantity = 1
        player.belongings.backpack.collect(new_item)
        return new_item

    new_item.level, new_item.level_known = target_item.level, target_item.level_known
    new_item.cursed, new_item.cursed_known = target_item.cursed, target_item.cursed_known
    _carry_over_enchantment(target_item, new_item)
    new_item.id = target_item.id

    if player.belongings.is_equipped(target_item.id):
        slot_name = player.belongings.slot_name_for(new_item)
        if slot_name is not None:
            setattr(player.belongings, slot_name, new_item)
    else:
        _replace_in_bag(player.belongings.backpack, target_item.id, new_item)
    return new_item


def _apply_remove_curse(game, player, target_item) -> bool:
    """Returns True if any curse was actually removed (SPD: `procced`)."""
    procced = False
    if target_item.cursed:
        procced = True
    target_item.cursed = False
    target_item.cursed_known = True
    enchantment = getattr(target_item, "enchantment", None)
    if isinstance(enchantment, str) and enchantment in CURSES:
        target_item.enchantment = None
        procced = True
    elif hasattr(enchantment, "type") and enchantment.type in CURSES:
        target_item.enchantment = ArmorEnchantment()
        procced = True
    if isinstance(target_item, Wand):
        target_item.level_known = True
    # SPD: Degrade.detach(curUser, Degrade.class) + updateHT(false) for Ring of Might
    player.remove_buff("degrade")
    return procced


def _apply_enchant_random(game, player, target_item) -> None:
    """ScrollOfEnchantment (regular): apply a random enchant/glyph."""
    if isinstance(target_item, KindOfWeapon):
        from app.engine.entities.weapon_enchants import roll_weapon_enchant
        import random as _r
        ench_name, _ = roll_weapon_enchant(_r, enchant_mult=1.0, curse_mult=0.0)
        if ench_name:
            target_item.enchantment = ench_name
    elif isinstance(target_item, Armor):
        from app.engine.entities.armor_glyphs import roll_armor_glyph
        import random as _r
        glyph_name, _ = roll_armor_glyph(_r, glyph_mult=1.0, curse_mult=0.0)
        if glyph_name:
            target_item.enchantment.type = glyph_name


def _generate_enchant_options(game, player, target_item) -> dict:
    """Generate 3 enchant/glyph choices for the exotic scroll."""
    from app.engine.entities.weapon_enchants import roll_weapon_enchant
    from app.engine.entities.armor_glyphs import roll_armor_glyph
    import random as _r

    if isinstance(target_item, KindOfWeapon):
        existing = target_item.enchantment if isinstance(target_item.enchantment, str) else None
        opts = []
        used = set()
        if existing:
            used.add(existing)
        for _ in range(3):
            name, _ = roll_weapon_enchant(_r, enchant_mult=1.0, curse_mult=0.0)
            if name and name not in used:
                opts.append(name)
                used.add(name)
        if len(opts) < 3:
            for _ in range(10):
                name, _ = roll_weapon_enchant(_r, enchant_mult=1.0, curse_mult=0.0)
                if name and name not in used:
                    opts.append(name)
                    used.add(name)
                if len(opts) >= 3:
                    break
        if not opts:
            opts = ["blazing", "chilling", "shocking"]
        return {"is_weapon": True, "options": opts[:3]}
    elif isinstance(target_item, Armor):
        existing = target_item.enchantment.type if hasattr(target_item.enchantment, "type") else "none"
        opts = []
        used = set()
        if existing not in ("none", None):
            used.add(existing)
        for _ in range(3):
            name, _ = roll_armor_glyph(_r, glyph_mult=1.0, curse_mult=0.0)
            if name and name not in used:
                opts.append(name)
                used.add(name)
        if len(opts) < 3:
            for _ in range(10):
                name, _ = roll_armor_glyph(_r, glyph_mult=1.0, curse_mult=0.0)
                if name and name not in used:
                    opts.append(name)
                    used.add(name)
                if len(opts) >= 3:
                    break
        if not opts:
            opts = ["thorns", "affection", "entanglement"]
        return {"is_weapon": False, "options": opts[:3]}
    return {"options": []}


# scroll `kind` -> apply function, called once a target has been chosen.
_APPLY_SCROLL_TARGET = {
    "scroll_of_upgrade": _apply_upgrade_target,
    "scroll_of_identify": _apply_identify,
    "scroll_of_remove_curse": _apply_remove_curse,
    "scroll_of_transmutation": _apply_transmutation,
    "scroll_of_enchantment": _apply_enchant_random,
}


def apply_scroll_target(game, player, scroll_item, target_item) -> None:
    """Finishes a selector-based scroll read once the player has chosen a
    target item (via SELECT_SCROLL_TARGET / ItemsMixin.select_scroll_target)."""

    # Exotic scroll: generate 3 choices and wait for player pick (don't consume yet)
    if scroll_item.kind == "scroll_of_exotic_enchantment":
        opts = _generate_enchant_options(game, player, target_item)
        if not opts.get("options"):
            return
        player._pending_exotic_scroll_id = scroll_item.id
        player._pending_exotic_target_id = target_item.id
        player._pending_exotic_is_weapon = opts.get("is_weapon", True)
        game.add_event("ENCHANT_CHOICE_AVAILABLE", {
            "player": player.id,
            "scroll_id": scroll_item.id,
            "target_id": target_item.id,
            "is_weapon": opts["is_weapon"],
            "options": opts["options"],
        }, floor_id=player.floor_id, source_player_id=player.id)
        return

    apply_fn = _APPLY_SCROLL_TARGET.get(scroll_item.kind)
    if apply_fn is None:
        return
    # Identify the scroll here — it's consumed on this path (apply_fn + detach below).
    game.identify_kind(scroll_item)
    old_kind = target_item.kind
    # Capture curse state before apply_fn clears it (for shadow particle VFX).
    was_cursed = bool(getattr(target_item, "cursed", False))
    new_item_result = apply_fn(game, player, target_item)

    removed = player.belongings.backpack.detach(scroll_item.id)
    if removed is not None and player.belongings.get_item(scroll_item.id) is None:
        player.quickslot.convert_to_placeholder(removed)

    sound = _SCROLL_SOUNDS.get(scroll_item.kind, "READ")
    visual = _SCROLL_VISUALS.get(scroll_item.kind)
    read_data: dict = {"player": player.id, "item": scroll_item.id, "sound": sound}
    if visual:
        read_data["visual"] = visual
    if scroll_item.kind == "scroll_of_transmutation" and new_item_result is not None:
        read_data["old_kind"] = old_kind
        read_data["new_kind"] = new_item_result.kind
    if scroll_item.kind == "scroll_of_upgrade" and was_cursed:
        read_data["shadow_particles"] = True
    if scroll_item.kind == "scroll_of_remove_curse":
        read_data["cleansed"] = bool(new_item_result)
    game.add_event("READ", read_data, floor_id=player.floor_id)


def choose_enchant_apply(game, player, choice_index: int) -> None:
    """Apply the chosen enchant from an exotic scroll selection."""
    scroll_id = getattr(player, "_pending_exotic_scroll_id", None)
    target_id = getattr(player, "_pending_exotic_target_id", None)
    is_weapon = getattr(player, "_pending_exotic_is_weapon", True)
    if not scroll_id or not target_id:
        return
    scroll_item = player.belongings.get_item(scroll_id)
    target_item = player.belongings.get_item(target_id)
    if scroll_item is None or target_item is None:
        return
    # Re-generate options to validate choice
    opts = _generate_enchant_options(game, player, target_item)
    options = opts.get("options", [])
    if choice_index < 0 or choice_index >= len(options):
        return
    chosen = options[choice_index]
    if is_weapon:
        target_item.enchantment = chosen
    else:
        target_item.enchantment.type = chosen
    # Consume the scroll
    removed = player.belongings.backpack.detach(scroll_item.id)
    if removed is not None and player.belongings.get_item(scroll_item.id) is None:
        player.quickslot.convert_to_placeholder(removed)
    game.add_event("MESSAGE", {"text": f"Your {target_item.name} glows with {chosen.replace('_', ' ')}!"},
                   floor_id=player.floor_id, player_id=player.id)
    game.add_event("ENCHANT", {"player": player.id, "item": target_item.id},
                   floor_id=player.floor_id)
    game.add_event("PLAY_SOUND", {"sound": "READ"}, floor_id=player.floor_id)
    # Clean up pending state
    player._pending_exotic_scroll_id = None
    player._pending_exotic_target_id = None
