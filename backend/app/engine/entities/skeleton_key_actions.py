# Copyright (C) 2026 ArtemNikov
#
"""SkeletonKey AC_INSERT action — port of SkeletonKey.java:130-386.

Unlocking any lock by targeting a cell: iron doors (1 charge), crystal doors
(5 charge), hero-locked doors (free), normal doors (2 charge, locks them as
HERO_LKD_DR), locked/crystal chests (2/5 charge), and distant walls (2 charge,
summons temporary KeyWall blobs).
"""
import random
import time

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Action, Position
from app.engine.entities.items.artifacts import SkeletonKey
from app.engine.entities.items.union import Chest
from app.engine.entities.wands.base import knockback_char
from app.engine.game.constants import KEY_TIME_TO_UNLOCK
from app.engine.entities.weapons.weapon_enchants import _is_hostile

# Doors whose lock is a boss gating (SPD Dungeon.level.locked) — the key
# refuses these. "goo_door"/"tengu_boss" come from spd_adapter._extract_doors
# and tengu_arena. "goo_door" is actually a LOCKED_EXIT, but guard anyway.
_BOSS_DOOR_LOCKS = frozenset({"goo_door", "tengu_boss"})

# SPD PathFinder.CIRCLE8: N, NE, E, SE, S, SW, W, NW (even index = diagonal).
_CIRCLE8 = (
    (0, -1), (1, -1), (1, 0), (1, 1),
    (0, 1), (-1, 1), (-1, 0), (-1, -1),
)

# SPD KeyWall caps at 10 turns; the port runs 1 turn/sec (GAME_TURN_TICKS=20 @20Hz).
_KEY_WALL_SECONDS = 10.0


def _msg(game, player, text: str) -> None:
    game.add_event("MESSAGE", {"text": text}, floor_id=player.floor_id,
                   player_id=player.id)


def _char_at(floor, x: int, y: int, game):
    for m in floor.mobs.values():
        if m.is_alive and m.pos.x == x and m.pos.y == y:
            return m
    for p in game.players.values():
        if p.is_alive and p.floor_id == floor.floor_id and p.pos.x == x and p.pos.y == y:
            return p
    return None


def _patch_tile(game, player, floor, x: int, y: int, tile: int, sound: str) -> None:
    floor.grid[y][x] = tile
    floor.rebuild_flags()
    game.add_event("MAP_PATCH", {"tiles": [{"x": x, "y": y, "tile": tile}]},
                   floor_id=player.floor_id)
    game.add_event("UNLOCK", {"player": player.id, "x": x, "y": y}, floor_id=player.floor_id)
    game.add_event("PLAY_SOUND", {"sound": sound}, floor_id=player.floor_id)


def action_unlock(game, player, item, tx=None, ty=None) -> None:
    if not isinstance(item, SkeletonKey):
        return
    if not player.belongings.is_equipped(item.id) or item.cursed:
        return
    if tx is None or ty is None:
        return
    floor = game._get_or_create_floor(player.floor_id)
    if not (0 <= tx < floor.width and 0 <= ty < floor.height):
        return
    if (tx, ty) == (player.pos.x, player.pos.y):
        _msg(game, player, "You can't use that on yourself.")
        return

    px, py = player.pos.x, player.pos.y
    adjacent = max(abs(tx - px), abs(ty - py)) <= 1

    if adjacent:
        chest = next(
            (c for c in floor.items.values()
             if isinstance(c, Chest) and c.pos and c.pos.x == tx and c.pos.y == ty
             and c.chest_type in ("LOCKED_CHEST", "CRYSTAL_CHEST")),
            None,
        )
        if chest is not None:
            _skeleton_unlock_chest(game, player, item, floor, tx, ty, chest)
            return

        tile = floor.grid[ty][tx]
        if tile == TileType.LOCKED_EXIT:
            _msg(game, player, "The key refuses to fit into this lock.")
            return
        if tile in (TileType.LOCKED_DOOR, TileType.HERO_LKD_DR,
                    TileType.CRYSTAL_DOOR, TileType.DOOR, TileType.OPEN_DOOR):
            _skeleton_door_action(game, player, item, floor, tx, ty, tile)
            return

    # Any other target (adjacent or distant) summons a temporary KeyWall.
    _skeleton_wall(game, player, item, floor, tx, ty)


def _skeleton_door_action(game, player, item, floor, tx: int, ty: int, tile: int) -> None:
    if tile == TileType.LOCKED_DOOR:
        if floor.locked_doors.get((tx, ty)) in _BOSS_DOOR_LOCKS:
            _msg(game, player, "The key refuses to fit into this lock.")
            return
        if item.charge < 1:
            _msg(game, player, "The key doesn't have enough charge for that.")
            return
        floor.locked_doors.pop((tx, ty), None)
        item.charge -= 1
        _artifact_gain_exp(item, 3)
        _patch_tile(game, player, floor, tx, ty, TileType.DOOR, "UNLOCK")
        return

    if tile == TileType.HERO_LKD_DR:
        # SPD: no charge cost, no artifact on-use.
        _patch_tile(game, player, floor, tx, ty, TileType.DOOR, "UNLOCK")
        return

    if tile == TileType.CRYSTAL_DOOR:
        if item.charge < 5:
            _msg(game, player, "The key doesn't have enough charge for that.")
            return
        floor.locked_doors.pop((tx, ty), None)
        item.charge -= 5
        _artifact_gain_exp(item, 7)
        _patch_tile(game, player, floor, tx, ty, TileType.FLOOR, "UNLOCK")
        return

    # Normal DOOR / OPEN_DOOR — lock it with the hero's own key (HERO_LKD_DR).
    if item.charge < 2:
        _msg(game, player, "The key doesn't have enough charge for that.")
        return

    blocker = _char_at(floor, tx, ty, game)
    if blocker is not None:
        if "IMMOVABLE" in (getattr(blocker, "properties", None) or []):
            _msg(game, player, "There's no space to lock this door.")
            return
        push = _find_door_push_cell(floor, player, tx, ty)
        if push is None:
            _msg(game, player, "There's no space to lock this door.")
            return
        knockback_char(floor, blocker, push[0] - tx, push[1] - ty, 1,
                       damage_on_collision=False, add_event=game.add_event,
                       floor_id=player.floor_id)

    # Scatter any items sitting in the doorway to random passable neighbours.
    items_here = [it for it in floor.items.values()
                  if it.pos and it.pos.x == tx and it.pos.y == ty]
    if items_here:
        candidates = [
            (tx + ox, ty + oy) for ox, oy in _CIRCLE8
            if 0 <= tx + ox < floor.width and 0 <= ty + oy < floor.height
            and floor.flags and floor.flags.passable[ty + oy][tx + ox]
        ]
        for it in items_here:
            if candidates:
                nx, ny = random.choice(candidates)
                it.pos = Position(x=nx, y=ny)

    item.charge -= 2
    _artifact_gain_exp(item, 2)
    _patch_tile(game, player, floor, tx, ty, TileType.HERO_LKD_DR, "UNLOCK")


def _find_door_push_cell(floor, player, tx: int, ty: int):
    """SPD SkeletonKey.java:228-237 — closest open neighbour of the door that
    is farther from the hero than the door itself."""
    px, py = player.pos.x, player.pos.y
    door_dist = abs(tx - px) + abs(ty - py)
    push_cell = None
    push_dist = None
    for ox, oy in _CIRCLE8:
        nx, ny = tx + ox, ty + oy
        if not (0 <= nx < floor.width and 0 <= ny < floor.height):
            continue
        if floor.flags and floor.flags.solid[ny][nx]:
            continue
        if _char_blocking(floor, nx, ny):
            continue
        if abs(nx - px) + abs(ny - py) <= door_dist:
            continue
        d = abs(nx - px) + abs(ny - py)
        if push_cell is None or d < push_dist:
            push_cell = (nx, ny)
            push_dist = d
    return push_cell


def _char_blocking(floor, x: int, y: int) -> bool:
    for m in floor.mobs.values():
        if m.is_alive and m.pos.x == x and m.pos.y == y:
            return True
    for p in floor.players.values() if hasattr(floor, "players") else []:
        if getattr(p, "is_alive", True) and p.pos.x == x and p.pos.y == y:
            return True
    return False


def _skeleton_unlock_chest(game, player, item, floor, tx: int, ty: int, chest) -> None:
    # Mimic disguise — don't waste a charge on a fake locked chest.
    if chest.mimic_hint and game._reveal_mimic_for_chest(player, floor, player.floor_id, chest.id):
        player.action_until = max(player.action_until, time.time() + KEY_TIME_TO_UNLOCK)
        return
    cost = 2 if chest.chest_type == "LOCKED_CHEST" else 5
    if item.charge < cost:
        _msg(game, player, "The key doesn't have enough charge for that.")
        return
    if (tx, ty) in floor.pending_unlocks:
        return
    item.charge -= cost
    _artifact_gain_exp(item, 2 + cost)
    player.action_until = max(player.action_until, time.time() + KEY_TIME_TO_UNLOCK)
    game.add_event("UNLOCK", {"player": player.id, "x": tx, "y": ty}, floor_id=player.floor_id)
    game._register_pending_unlock(floor, tx, ty, "chest", player.id, chest_id=chest.id)


def _skeleton_wall(game, player, item, floor, tx: int, ty: int) -> None:
    if item.charge < 2:
        _msg(game, player, "The key doesn't have enough charge for that.")
        return
    px, py = player.pos.x, player.pos.y

    # Nearest neighbour cell of the hero to the target (SPD trueDistance loop).
    closest_idx = 0
    best = None
    for i, (ox, oy) in enumerate(_CIRCLE8):
        cx, cy = px + ox, py + oy
        if not (0 <= cx < floor.width and 0 <= cy < floor.height):
            continue
        d = abs(tx - cx) + abs(ty - cy)
        if best is None or d < best:
            best = d
            closest_idx = i
    cx, cy = px + _CIRCLE8[closest_idx][0], py + _CIRCLE8[closest_idx][1]
    if floor.flags and floor.flags.solid[cy][cx]:
        _msg(game, player, "You can't use the key here.")
        return

    placed = False
    kd = closest_idx

    def place(ox, oy):
        nonlocal placed
        if not (0 <= ox < floor.width and 0 <= oy < floor.height):
            return
        solid = floor.flags.solid[oy][ox] if floor.flags else True
        has_wall = any(
            (ox, oy) in b.get("cells", set())
            for b in floor.blob_areas.values() if b.get("type") == "key_wall"
        )
        # SPD placeWall: seed unless the cell is solid terrain with no wall yet.
        if solid and not has_wall:
            return
        blob_id = f"key_wall_{ox}_{oy}"
        floor.blob_areas[blob_id] = {
            "type": "key_wall",
            "cells": {(ox, oy)},
            "volume": {(ox, oy): 1},
            "remaining": _KEY_WALL_SECONDS,
        }
        placed = True
        ch = _char_at(floor, ox, oy, game)
        if ch is not None and _is_hostile(player, ch):
            dirx, diry = _CIRCLE8[kd]
            knockback_char(floor, ch, dirx, diry, 1, damage_on_collision=False,
                           add_event=game.add_event, floor_id=player.floor_id)

    place(px + _CIRCLE8[kd][0], py + _CIRCLE8[kd][1])
    place(px + _CIRCLE8[(kd + 7) % 8][0], py + _CIRCLE8[(kd + 7) % 8][1])
    place(px + _CIRCLE8[(kd + 1) % 8][0], py + _CIRCLE8[(kd + 1) % 8][1])
    if kd % 2 == 0:  # diagonal direction gets 2 extra walls
        ax, ay = _CIRCLE8[(kd + 7) % 8]
        bx, by = _CIRCLE8[(kd + 1) % 8]
        place(px + 2 * ax, py + 2 * ay)
        place(px + 2 * bx, py + 2 * by)

    if not placed:
        return

    item.charge -= 2
    _artifact_gain_exp(item, 2)
    floor.rebuild_flags()
    for blob_id, blob in floor.blob_areas.items():
        if blob.get("type") == "key_wall":
            cells = [(c[0], c[1], 1) for c in blob.get("cells", set())]
            game.add_event("BLOB_UPDATE", {"id": blob_id, "type": "key_wall", "cells": cells},
                           floor_id=player.floor_id)
    game.add_event("PLAY_SOUND", {"sound": "TELEPORT"}, floor_id=player.floor_id)


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
