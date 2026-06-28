"""Runestone action handlers: action_throw_runestone, action_use_stone."""
import random
import uuid

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import (
    Armor, Faction, InventoryStone, ItemBase, KindOfWeapon, Position, Runestone, Wand,
)
from app.engine.entities.armor_glyphs import roll_armor_glyph
from app.engine.entities.weapon_enchants import roll_weapon_enchant


_THROW_SOUNDS = {
    "stone_of_blast": "BLAST",
    "stone_of_blink": "TELEPORT",
    "stone_of_deep_sleep": "LULLABY",
    "stone_of_clairvoyance": "SECRET",
    "stone_of_aggression": "CHALLENGE",
    "stone_of_flock": "SHEEP",
    "stone_of_shock": "LIGHTNING",
    "stone_of_fear": "CURSE",
}


def action_throw_runestone(game, player, item, tx=None, ty=None) -> None:
    if tx is None or ty is None:
        return
    kind = getattr(item, "kind", "")
    if kind not in _THROW_SOUNDS:
        return
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return

    removed = player.belongings.backpack.detach(item.id)
    if removed is not None and player.belongings.get_item(item.id) is None:
        player.quickslot.convert_to_placeholder(removed)

    if kind == "stone_of_blast":
        _blast_effect(game, player, floor, tx, ty)
    elif kind == "stone_of_blink":
        _blink_effect(game, player, floor, tx, ty)
    elif kind == "stone_of_deep_sleep":
        _deep_sleep_effect(game, player, floor, tx, ty)
    elif kind == "stone_of_clairvoyance":
        _clairvoyance_effect(game, player, floor, tx, ty)
    elif kind == "stone_of_aggression":
        _aggression_effect(game, player, floor, tx, ty)
    elif kind == "stone_of_flock":
        _flock_effect(game, player, floor, tx, ty)
    elif kind == "stone_of_shock":
        _shock_effect(game, player, floor, tx, ty)
    elif kind == "stone_of_fear":
        _fear_effect(game, player, floor, tx, ty)

    sound = _THROW_SOUNDS.get(kind, "READ")
    game.add_event("THROW", {"player": player.id, "item": item.id, "sound": sound},
                   floor_id=player.floor_id)


def _blast_effect(game, player, floor, tx, ty) -> None:
    from app.engine.systems.loot import roll_drops
    cells = set()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx, ny = tx + dx, ty + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                cells.add((nx, ny))
    crushed = []
    for eid in list(floor.items.keys()):
        item = floor.items[eid]
        if item.pos and (item.pos.x, item.pos.y) in cells:
            del floor.items[eid]
            crushed.append({"x": item.pos.x, "y": item.pos.y})
    if crushed:
        game.add_event("ITEMS_DESTROYED", {"tiles": crushed}, floor_id=player.floor_id)
    for mob in list(floor.mobs.values()):
        if mob.is_alive and (mob.pos.x, mob.pos.y) in cells:
            dist = abs(mob.pos.x - tx) + abs(mob.pos.y - ty)
            dmg = max(1, 10 - dist * 3 + random.randint(0, 5))
            dealt = mob.take_damage(dmg)
            if dealt > 0:
                game.add_event("DAMAGE", {"target": mob.id, "amount": dealt}, floor_id=player.floor_id)
            if not mob.is_alive:
                mob.die(floor_mobs=floor.mobs, tile_x=mob.pos.x, tile_y=mob.pos.y,
                        players=list(game._players_on_floor(player.floor_id)))
                game.add_event("DEATH", {"target": mob.id}, floor_id=player.floor_id)
                game.handle_mob_death(mob, floor, player.floor_id)
                for drop in roll_drops(mob, game.drop_counters, mob.pos.x, mob.pos.y,
                                        players=list(game._players_on_floor(player.floor_id))):
                    floor.items[drop.id] = drop
    for p in game._players_on_floor(player.floor_id):
        if p.id != player.id and (p.pos.x, p.pos.y) in cells:
            dist = abs(p.pos.x - tx) + abs(p.pos.y - ty)
            dmg = max(1, 10 - dist * 3 + random.randint(0, 5))
            dealt = p.take_damage(dmg)
            if dealt > 0:
                game.add_event("DAMAGE", {"target": p.id, "amount": dealt}, floor_id=player.floor_id)
    blob_id = f"stone_blast_{tx}_{ty}"
    fire_cells = set()
    fire_volume = {}
    for nx, ny in cells:
        if floor.flags and floor.flags.flamable[ny][nx]:
            fire_cells.add((nx, ny))
            fire_volume[(nx, ny)] = 2
    if fire_cells:
        floor.blob_areas[blob_id] = {"type": "fire", "cells": fire_cells, "volume": fire_volume}
    game.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=player.floor_id)
    game.add_event("EXPLOSION", {"x": tx, "y": ty}, floor_id=player.floor_id)


def _blink_effect(game, player, floor, tx, ty) -> None:
    occupied = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
    occupied |= {(p.pos.x, p.pos.y) for p in game.players.values()
                 if p.floor_id == player.floor_id and p.is_alive}
    dest_x, dest_y = tx, ty
    if (dest_x, dest_y) in occupied:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = tx + dx, ty + dy
                if (nx, ny) not in occupied and 0 <= nx < floor.width and 0 <= ny < floor.height:
                    if floor.flags and floor.flags.passable[ny][nx]:
                        dest_x, dest_y = nx, ny
                        break
            if (dest_x, dest_y) != (tx, ty):
                break
        if (dest_x, dest_y) == (tx, ty):
            return
    from_x, from_y = player.pos.x, player.pos.y
    player.pos = Position(x=dest_x, y=dest_y)
    player.remove_buff("rooted")
    game.add_event("TELEPORT", {"player": player.id, "from_x": from_x, "from_y": from_y,
                                 "x": dest_x, "y": dest_y}, floor_id=player.floor_id)


def _deep_sleep_effect(game, player, floor, tx, ty) -> None:
    for mob in floor.mobs.values():
        if mob.is_alive and mob.pos.x == tx and mob.pos.y == ty:
            mob.add_buff("magical_sleep", duration=999.0, level=1)
            game.add_event("PLAY_SOUND", {"sound": "LULLABY"}, floor_id=player.floor_id)
            return


def _clairvoyance_effect(game, player, floor, tx, ty) -> None:
    RADIUS = 20
    mapped = []
    for y in range(max(0, ty - RADIUS), min(floor.height, ty + RADIUS + 1)):
        for x in range(max(0, tx - RADIUS), min(floor.width, tx + RADIUS + 1)):
            if abs(x - tx) + abs(y - ty) <= RADIUS:
                t = floor.grid[y][x]
                if t not in (TileType.VOID, TileType.WALL, TileType.WALL_DECO):
                    if floor.mapped_tiles is None:
                        floor.mapped_tiles = []
                    if (x, y) not in floor.mapped_tiles:
                        floor.mapped_tiles.append((x, y))
                    mapped.append((x, y))
    patches = []
    for (hx, hy), actual_tile in list(floor.hidden_doors.items()):
        if abs(hx - tx) + abs(hy - ty) <= RADIUS:
            floor.hidden_doors.pop((hx, hy))
            floor.grid[hy][hx] = actual_tile
            patches.append({"x": hx, "y": hy, "tile": actual_tile})
    for (trx, try_), trap in floor.traps.items():
        if trap.hidden and abs(trx - tx) + abs(try_ - ty) <= RADIUS:
            trap.hidden = False
            if floor.grid[try_][trx] == TileType.SECRET_TRAP:
                floor.grid[try_][trx] = TileType.TRAP
                patches.append({"x": trx, "y": try_, "tile": TileType.TRAP})
    if patches:
        floor.rebuild_flags()
        game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=player.floor_id)
    if mapped:
        game.add_event("MAP_REVEAL", {"tiles": mapped}, floor_id=player.floor_id)
    if patches:
        game.add_event("PLAY_SOUND", {"sound": "SECRET"}, player_id=player.id)


def _aggression_effect(game, player, floor, tx, ty) -> None:
    for mob in floor.mobs.values():
        if mob.is_alive and mob.pos.x == tx and mob.pos.y == ty:
            duration = 5.0 if getattr(mob, "is_boss", False) else 20.0
            mob.add_buff("aggression", duration=duration, source_id=player.id)
            mob.ai_state = "hunting"
            game.add_event("PLAY_SOUND", {"sound": "CHALLENGE"}, floor_id=player.floor_id)
            return


def _flock_effect(game, player, floor, tx, ty) -> None:
    from app.engine.entities.base import Mob as MobEntity
    RADIUS = 2
    placed = []
    for dy in range(-RADIUS, RADIUS + 1):
        for dx in range(-RADIUS, RADIUS + 1):
            nx, ny = tx + dx, ty + dy
            if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                continue
            if floor.flags and floor.flags.solid[ny][nx]:
                continue
            if floor.flags and floor.flags.pit[ny][nx]:
                continue
            if any(m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values()):
                continue
            if any(p.pos.x == nx and p.pos.y == ny for p in game._players_on_floor(player.floor_id)):
                continue
            sheep_id = str(uuid.uuid4())
            sheep = MobEntity(
                id=sheep_id, name="Sheep", type="npc",
                pos=Position(x=nx, y=ny), hp=0, max_hp=0, speed=0,
                faction=Faction.PLAYER, droptable=[], flying=False,
            )
            sheep.add_buff("sheep_timer", duration=8.0, level=1)
            floor.mobs[sheep_id] = sheep
            placed.append({"id": sheep_id, "x": nx, "y": ny})
            game.add_event("WOOL_BURST", {"x": nx, "y": ny}, floor_id=player.floor_id)
    game.add_event("WOOL_BURST", {"x": tx, "y": ty}, floor_id=player.floor_id)
    if placed:
        game.add_event("FLOCK", {"sheep": placed}, floor_id=player.floor_id)
    game.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=player.floor_id)
    game.add_event("PLAY_SOUND", {"sound": "SHEEP"}, floor_id=player.floor_id)


def _shock_effect(game, player, floor, tx, ty) -> None:
    RADIUS = 2
    for mob in list(floor.mobs.values()):
        if mob.is_alive and abs(mob.pos.x - tx) + abs(mob.pos.y - ty) <= RADIUS:
            mob.add_buff("paralysis", duration=1.0, level=1)
            game.add_event("DAMAGE", {"target": mob.id, "amount": 0, "projectile": "lightning"},
                           floor_id=player.floor_id)
    player.add_buff("recharging", duration=30.0)
    game.add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=player.floor_id)
    game.add_event("SHOCK", {"x": tx, "y": ty, "radius": RADIUS, "source": player.id},
                   floor_id=player.floor_id)


def _fear_effect(game, player, floor, tx, ty) -> None:
    for mob in floor.mobs.values():
        if mob.is_alive and mob.pos.x == tx and mob.pos.y == ty:
            if mob.faction == player.faction:
                return
            mob.add_buff("terror", duration=20.0, source_id=player.id)
            mob.ai_state = "fleeing"
            game.add_event("PLAY_SOUND", {"sound": "CURSE"}, floor_id=player.floor_id)
            return


def action_use_stone(game, player, item, tx=None, ty=None) -> None:
    kind = getattr(item, "kind", "")
    floor = game._get_or_create_floor(player.floor_id)

    if kind == "magical_infusion":
        candidates = [it.id for it in _player_inventory(player)
                      if it.id != item.id and getattr(it, "is_upgradable", lambda: True)()]
        game.add_event("STONE_SELECT_TARGET",
                       {"player": player.id, "stone_id": item.id, "stone_kind": kind,
                        "candidates": candidates},
                       floor_id=player.floor_id, player_id=player.id)
        return

    if kind == "stone_of_detect_magic":
        candidates = [it.id for it in _player_inventory(player)
                      if it.id != item.id and isinstance(it, (KindOfWeapon, Armor, Wand))]
        game.add_event("STONE_SELECT_TARGET",
                       {"player": player.id, "stone_id": item.id, "stone_kind": kind,
                        "candidates": candidates},
                       floor_id=player.floor_id, player_id=player.id)
    elif kind == "stone_of_enchantment":
        candidates = [it.id for it in _player_inventory(player)
                      if it.id != item.id and isinstance(it, (KindOfWeapon, Armor))]
        game.add_event("STONE_SELECT_TARGET",
                       {"player": player.id, "stone_id": item.id, "stone_kind": kind,
                        "candidates": candidates},
                       floor_id=player.floor_id, player_id=player.id)
    elif kind == "stone_of_intuition":
        candidates = [it.id for it in _player_inventory(player)
                      if it.id != item.id and _is_unidentified(it, game)]
        if candidates:
            game.add_event("STONE_INTUITION_PICK_ITEM",
                           {"player": player.id, "stone_id": item.id, "candidates": candidates},
                           floor_id=player.floor_id, player_id=player.id)
        else:
            game.add_event("MESSAGE", {"text": "All items are already identified."},
                           floor_id=player.floor_id, player_id=player.id)
    elif kind == "stone_of_augmentation":
        candidates = [it.id for it in _player_inventory(player)
                      if it.id != item.id and isinstance(it, (KindOfWeapon, Armor))]
        game.add_event("STONE_AUGMENT_PICK_ITEM",
                       {"player": player.id, "stone_id": item.id, "candidates": candidates},
                       floor_id=player.floor_id, player_id=player.id)


def _player_inventory(player):
    items = []
    bag = player.belongings.backpack
    items.extend(bag.items)
    for sub in bag.items:
        if hasattr(sub, "items"):
            items.extend(sub.items)
    eq = ["weapon", "armor", "artifact", "ring", "misc"]
    for slot in eq:
        e = getattr(player.belongings, slot, None)
        if e is not None:
            items.append(e)
    return items


def _is_unidentified(item, game):
    kind = getattr(item, "kind", "")
    return kind.startswith(("potion_", "scroll_", "ring_")) and kind not in game.identified_kinds


def apply_stone_target(game, player, stone_item, target_item) -> None:
    kind = getattr(stone_item, "kind", "")
    if kind == "stone_of_detect_magic":
        _apply_detect_magic(game, player, stone_item, target_item)
    elif kind == "stone_of_enchantment":
        _apply_enchant(game, player, stone_item, target_item)


def _apply_detect_magic(game, player, stone_item, target_item) -> None:
    target_item.cursed_known = True
    lines = []
    if target_item.cursed:
        lines.append(f"The {target_item.name} is cursed!")
    else:
        lines.append(f"The {target_item.name} is not cursed.")
    if hasattr(target_item, "level") and target_item.level != 0:
        lines.append(f"It is level {target_item.level}.")
    if hasattr(target_item, "enchantment"):
        ench = target_item.enchantment
        ench_str = ench if isinstance(ench, str) else getattr(ench, "type", "none")
        if ench_str and ench_str not in ("none", None):
            label = ench_str.replace("_", " ").title()
            lines.append(f"It is enchanted with {label}.")
    _consume_stone(game, player, stone_item)
    for line in lines:
        game.add_event("MESSAGE", {"text": line}, floor_id=player.floor_id, player_id=player.id)
    game.add_event("PLAY_SOUND", {"sound": "IDENTIFY"}, floor_id=player.floor_id)


def _apply_enchant(game, player, stone_item, target_item) -> None:
    if isinstance(target_item, KindOfWeapon):
        ench_name, _ = roll_weapon_enchant(random, enchant_mult=1.0, curse_mult=0.0)
        if ench_name:
            target_item.enchantment = ench_name
    elif isinstance(target_item, Armor):
        glyph_name, _ = roll_armor_glyph(random, glyph_mult=1.0, curse_mult=0.0)
        if glyph_name:
            target_item.enchantment.type = glyph_name
    _consume_stone(game, player, stone_item)
    game.add_event("MESSAGE", {"text": f"Your {target_item.name} glows with magical energy!"},
                   floor_id=player.floor_id, player_id=player.id)
    game.add_event("ENCHANT", {"player": player.id, "item": target_item.id},
                   floor_id=player.floor_id)
    game.add_event("PLAY_SOUND", {"sound": "CURSE"}, floor_id=player.floor_id)


def _consume_stone(game, player, stone_item) -> None:
    removed = player.belongings.backpack.detach(stone_item.id)
    if removed is not None and player.belongings.get_item(stone_item.id) is None:
        player.quickslot.convert_to_placeholder(removed)


def apply_stone_intuition_pick(game, player, stone_id, item_id) -> None:
    stone = player.belongings.get_item(stone_id)
    if stone is None:
        return
    item = player.belongings.get_item(item_id)
    if item is None:
        return
    kind = getattr(item, "kind", "")
    if kind.startswith("potion_"):
        all_kinds = [k for k in _ALL_POTION_KINDS]
        type_label = "Potion"
    elif kind.startswith("scroll_"):
        all_kinds = [k for k in _ALL_SCROLL_KINDS]
        type_label = "Scroll"
    else:
        all_kinds = [k for k in _ALL_RING_KINDS]
        type_label = "Ring"
    candidates = random.sample(all_kinds, min(7, len(all_kinds)))
    if kind not in candidates:
        candidates[0] = kind
    random.shuffle(candidates)
    game.add_event("STONE_INTUITION_GUESS_KIND",
                   {"player": player.id, "stone_id": stone_id, "item_id": item_id,
                    "possible_kinds": candidates}, floor_id=player.floor_id, player_id=player.id)


_ALL_POTION_KINDS = [
    "potion_of_strength", "potion_of_haste", "potion_of_invisibility",
    "potion_of_levitation", "potion_of_mind_vision", "potion_of_frost",
    "potion_of_liquid_flame", "potion_of_toxic_gas", "potion_of_paralytic_gas",
    "potion_of_purity", "potion_of_experience",
    "health_potion", "reviving_potion", "fury_potion",
]

_ALL_SCROLL_KINDS = [
    "scroll_of_upgrade", "scroll_of_identify", "scroll_of_magic_mapping",
    "scroll_of_teleportation", "scroll_of_remove_curse", "scroll_of_recharging",
    "scroll_of_lullaby", "scroll_of_terror", "scroll_of_mirror_image",
    "scroll_of_retribution", "scroll_of_transmutation", "scroll_of_rage",
]

_ALL_RING_KINDS = [
    "ring_accuracy", "ring_evasion", "ring_haste", "ring_furor",
    "ring_might", "ring_tenacity", "ring_energy", "ring_arcana",
    "ring_sharpshooting", "ring_force", "ring_elements", "ring_wealth",
]


def apply_stone_intuition_guess(game, player, stone_id, item_id, guessed_kind) -> bool:
    stone = player.belongings.get_item(stone_id)
    if stone is None:
        return False
    item = player.belongings.get_item(item_id)
    if item is None:
        return False
    first_use = False
    if not player.has_buff("intuition_first_use"):
        first_use = True
        player.add_buff("intuition_first_use", duration=99999.0, level=1)
    if getattr(item, "kind", "") == guessed_kind:
        game.identify_kind(item)
        game.add_event("MESSAGE", {"text": f"You correctly identify the item!"},
                       floor_id=player.floor_id, player_id=player.id)
        game.add_event("PLAY_SOUND", {"sound": "IDENTIFY"}, floor_id=player.floor_id)
        return True
    else:
        game.add_event("MESSAGE", {"text": "Your guess was wrong."},
                       floor_id=player.floor_id, player_id=player.id)
        if not first_use:
            _consume_stone(game, player, stone)
        return False


def apply_stone_augment(game, player, stone_id, item_id, augment_type) -> None:
    stone = player.belongings.get_item(stone_id)
    if stone is None:
        return
    target = player.belongings.get_item(item_id)
    if target is None:
        return
    target.augment = augment_type
    target.level += 1
    _consume_stone(game, player, stone)
    game.add_event("MESSAGE",
                   {"text": f"Your {target.name} is augmented ({augment_type}) and upgraded!"},
                   floor_id=player.floor_id, player_id=player.id)
    game.add_event("PLAY_SOUND", {"sound": "LEVELUP"}, floor_id=player.floor_id)
