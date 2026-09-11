# Copyright (C) 2026 ArtemNikov
#
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
    stop_chars: bool = True,
    stop_solid: bool = True,
    max_dist: int = 0,
) -> Tuple[int, int]:
    """Trace a projectile from (src_x,src_y) toward (target_x,target_y).

    Returns (collision_x, collision_y). With stop_chars/stop_solid flags
    the beam can pierce characters and/or walls (SPD WONT_STOP).
    max_dist > 0 clips the trace to that many cells.
    """
    if not (0 <= target_x < width and 0 <= target_y < height):
        return (src_x, src_y)

    cells = _bresenham(src_x, src_y, target_x, target_y)

    # Position -> blocking entity, built once instead of rescanning every
    # player/mob per traced cell. Players are inserted first so a player
    # takes precedence over a mob sharing the same cell, matching the order
    # entities were checked in before this was a lookup table.
    occupied = {}
    if stop_chars:
        for p in players:
            if p.id != exclude_id and getattr(p, "is_alive", True):
                occupied[(p.pos.x, p.pos.y)] = p
        for m in mobs:
            if getattr(m, "is_alive", True):
                occupied.setdefault((m.pos.x, m.pos.y), m)

    limit = len(cells) if max_dist <= 0 else min(len(cells), max_dist + 1)
    for i in range(1, limit):
        cx, cy = cells[i]
        if not (0 <= cx < width and 0 <= cy < height):
            return (cells[i - 1][0], cells[i - 1][1])

        if stop_solid and flags is not None and flags.solid[cy][cx]:
            if flags.passable[cy][cx]:
                return (cx, cy)
            return (cells[i - 1][0], cells[i - 1][1])

        if (cx, cy) in occupied:
            return (cx, cy)

    return (cells[min(limit - 1, len(cells) - 1)][0], cells[min(limit - 1, len(cells) - 1)][1])


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


def bresenham(x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
    return _bresenham(x0, y0, x1, y1)


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
