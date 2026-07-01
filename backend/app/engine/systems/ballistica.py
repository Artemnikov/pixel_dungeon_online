# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# Ballistica ray-trace for wand/staff projectiles.
# Mirrors SPD Ballistica.MAGIC_BOLT (STOP_CHARS | STOP_SOLID).

from typing import List, Optional, Tuple

from app.engine.dungeon.terrain_flags import FloorFlagMaps
from app.engine.entities.player import Mob as MobEntity, Player


def ballistica_trace(
    src_x: int, src_y: int,
    target_x: int, target_y: int,
    flags: Optional[FloorFlagMaps],
    width: int, height: int,
    players: List[Player],
    mobs: List[MobEntity],
    exclude_id: str,
) -> Tuple[int, int]:
    """Trace a projectile from (src_x,src_y) toward (target_x,target_y).

    Stops at the first character (STOP_CHARS) or solid wall (STOP_SOLID).
    Returns (collision_x, collision_y).
    """
    if not (0 <= target_x < width and 0 <= target_y < height):
        return (src_x, src_y)

    cells = _bresenham(src_x, src_y, target_x, target_y)

    for i in range(1, len(cells)):
        cx, cy = cells[i]
        if not (0 <= cx < width and 0 <= cy < height):
            return (cells[i - 1][0], cells[i - 1][1])

        if flags is not None and flags.solid[cy][cx]:
            return (cells[i - 1][0], cells[i - 1][1])

        for p in players:
            if p.id != exclude_id and p.pos.x == cx and p.pos.y == cy:
                if getattr(p, "is_alive", True):
                    return (cx, cy)

        for m in mobs:
            if m.pos.x == cx and m.pos.y == cy and getattr(m, "is_alive", True):
                return (cx, cy)

    return (target_x, target_y)


def ballistica_path(
    src_x: int, src_y: int,
    target_x: int, target_y: int,
    flags: Optional[FloorFlagMaps],
    width: int, height: int,
) -> List[Tuple[int, int]]:
    """Chain path from src toward target (SPD Ballistica.STOP_TARGET): stops at
    the target cell, or at the last open cell before a solid wall. Passes through
    characters (they don't stop the chain). Returns the cell list from src to the
    collision cell inclusive; `path[-1]` is the collision position."""
    if not (0 <= target_x < width and 0 <= target_y < height):
        return [(src_x, src_y)]
    cells = _bresenham(src_x, src_y, target_x, target_y)
    path = [cells[0]]
    for i in range(1, len(cells)):
        cx, cy = cells[i]
        if not (0 <= cx < width and 0 <= cy < height):
            break
        if flags is not None and flags.solid[cy][cx]:
            break
        path.append((cx, cy))
        if (cx, cy) == (target_x, target_y):
            break
    return path


def _bresenham(x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
    cells = []
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    cx, cy = x0, y0
    while True:
        cells.append((cx, cy))
        if cx == x1 and cy == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            cx += sx
        if e2 <= dx:
            err += dx
            cy += sy
    return cells
