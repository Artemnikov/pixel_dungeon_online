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
from app.engine.entities.base import (
    Armor, ArmorEnchantment, Bag, KindOfWeapon, Position, Wand,
)
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
    unoccupied cell on their current floor, preferring cells outside their
    current FOV. Breaks "rooted" on success."""
    floor = game._get_or_create_floor(player.floor_id)

    occupied = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
    occupied |= {
        (p.pos.x, p.pos.y)
        for p in game.players.values()
        if p.floor_id == player.floor_id and p.is_alive
    }

    candidates = []
    for y in range(floor.height):
        for x in range(floor.width):
            if floor.flags and floor.flags.passable[y][x] and (x, y) not in occupied:
                candidates.append((x, y))

    if not candidates:
        return

    visible = set(game.get_visible_tiles(
        player.pos, radius=game._view_distance(player), floor_id=player.floor_id,
        viewer_id=player.id))
    out_of_fov = [c for c in candidates if c not in visible]
    pool = out_of_fov if out_of_fov else candidates

    from_x, from_y = player.pos.x, player.pos.y
    tx, ty = random.choice(pool)
    player.pos = Position(x=tx, y=ty)
    player.remove_buff("rooted")

    game.add_event("TELEPORT", {"player": player.id, "from_x": from_x, "from_y": from_y, "x": tx, "y": ty}, floor_id=player.floor_id)


def action_read(game, player, item, tx=None, ty=None) -> None:
    effect = getattr(item, "kind", "")
    _extra_event_data: dict = {}

    if effect in PREDICATE:
        # Identify and proc stealth only if there are valid targets — no free
        # identification or stealth buff when the scroll fizzles (no candidates).
        candidates = [it.id for it in player_inventory_items(player) if it.id != item.id and PREDICATE[effect](it, game)]
        if not candidates:
            game.add_event("READ", {"player": player.id, "item": item.id}, floor_id=player.floor_id)
            return
        game.identify_kind(item)
        _maybe_proc_inscribed_stealth(game, player)
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
        # amok: only FOV mobs. include_allies=True is intentional for multiplayer
        # (SPD spares Char.Alignment.ALLY, but clones/images amok-ing is the desired chaos here).
        for mob in game._mobs_in_fov(player, floor, player.floor_id, include_allies=True):
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
        for wand in player_inventory_items(player):
            if isinstance(wand, Wand):
                wand.charges = wand.max_charges
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
        floor.mapped = True
        floor.mapped_tiles = [(x, y) for y in range(floor.height) for x in range(floor.width)]
        patches = []
        discover_positions = []
        found_secret = False
        for (tx, ty), actual_tile in list(floor.hidden_doors.items()):
            floor.hidden_doors.pop((tx, ty))
            floor.grid[ty][tx] = actual_tile
            patches.append({"x": tx, "y": ty, "tile": actual_tile})
            discover_positions.append({"x": tx, "y": ty})
            found_secret = True
        for (tx, ty), trap in floor.traps.items():
            if trap.hidden:
                trap.hidden = False
                found_secret = True
                if floor.grid[ty][tx] == TileType.SECRET_TRAP:
                    floor.grid[ty][tx] = TileType.TRAP
                    patches.append({"x": tx, "y": ty, "tile": TileType.TRAP})
                discover_positions.append({"x": tx, "y": ty})
        if patches:
            floor.rebuild_flags()
            game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=player.floor_id)
        if found_secret:
            game.add_event("PLAY_SOUND", {"sound": "SECRET"}, player_id=player.id)
        removed = player.belongings.backpack.detach(item.id)
        if removed is not None and player.belongings.get_item(item.id) is None:
            player.quickslot.convert_to_placeholder(removed)
        if discover_positions:
            _extra_event_data["discover_positions"] = discover_positions
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

    _maybe_proc_inscribed_stealth(game, player)

    sound = _SCROLL_SOUNDS.get(effect, "READ")
    visual = _SCROLL_VISUALS.get(effect)
    event_data: dict = {"player": player.id, "item": item.id, "sound": sound}
    if visual:
        event_data["visual"] = visual
    event_data.update(_extra_event_data)
    game.add_event("READ", event_data, floor_id=player.floor_id)


def _apply_upgrade_target(game, player, target_item) -> None:
    from app.engine.entities.base import Staff
    if isinstance(target_item, Staff):
        target_item.upgrade()
    else:
        target_item.level += 1
    target_item.level_known = True
    target_item.cursed = False
    target_item.cursed_known = True


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


def _apply_remove_curse(game, player, target_item) -> None:
    target_item.cursed = False
    target_item.cursed_known = True
    enchantment = getattr(target_item, "enchantment", None)
    if isinstance(enchantment, str) and enchantment in CURSES:
        target_item.enchantment = None
    elif hasattr(enchantment, "type") and enchantment.type in CURSES:
        target_item.enchantment = ArmorEnchantment()
    if isinstance(target_item, Wand):
        target_item.level_known = True


# scroll `kind` -> apply function, called once a target has been chosen.
_APPLY_SCROLL_TARGET = {
    "scroll_of_upgrade": _apply_upgrade_target,
    "scroll_of_identify": _apply_identify,
    "scroll_of_remove_curse": _apply_remove_curse,
    "scroll_of_transmutation": _apply_transmutation,
}


def apply_scroll_target(game, player, scroll_item, target_item) -> None:
    """Finishes a selector-based scroll read once the player has chosen a
    target item (via SELECT_SCROLL_TARGET / ItemsMixin.select_scroll_target)."""
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
        # SPD emits ShadowParticle.UP when an upgrade removes a curse from an item.
        read_data["shadow_particles"] = True
    game.add_event("READ", read_data, floor_id=player.floor_id)
