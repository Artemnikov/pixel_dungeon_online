# Copyright (C) 2026 ArtemNikov
#
"""Port of SPD `mechanics/Ballistica.java`.

`path` is the full trace to the map's inner edge, including cells after the
collision; `collision_pos` is the first cell the projectile stopped at, and
`dist` its index in `path`. Cells are (x, y) tuples.
"""

from typing import Callable, List, Optional, Tuple

Cell = Tuple[int, int]

STOP_TARGET = 1
STOP_CHARS = 2
STOP_SOLID = 4
IGNORE_SOFT_SOLID = 8

PROJECTILE = STOP_TARGET | STOP_CHARS | STOP_SOLID
MAGIC_BOLT = STOP_CHARS | STOP_SOLID
WONT_STOP = 0


class Ballistica:
    def __init__(
        self,
        src: Cell,
        dst: Cell,
        params: int,
        floor,
        char_at: Optional[Callable[[int, int], object]] = None,
    ) -> None:
        self.source_pos: Cell = (int(src[0]), int(src[1]))
        self.collision_properties = params
        self.path: List[Cell] = []
        self.collision_pos: Optional[Cell] = None
        self.dist: int = 0
        self._floor = floor
        self._char_at = char_at or (lambda _x, _y: None)

        self._build(
            self.source_pos,
            (int(dst[0]), int(dst[1])),
            bool(params & STOP_TARGET),
            bool(params & STOP_CHARS),
            bool(params & STOP_SOLID),
            bool(params & IGNORE_SOFT_SOLID),
        )

        if self.collision_pos is not None:
            self.dist = self.path.index(self.collision_pos)
        elif self.path:
            self.dist = len(self.path) - 1
            self.collision_pos = self.path[self.dist]
        else:
            self.path.append(self.source_pos)
            self.collision_pos = self.source_pos
            self.dist = 0

    def _inside_map(self, x: int, y: int) -> bool:
        w, h = self._floor.width, self._floor.height
        return 1 <= x < w - 1 and 1 <= y < h - 1

    def _flag(self, name: str, x: int, y: int) -> bool:
        flags = self._floor.flags
        if flags is None:
            self._floor.rebuild_flags()
            flags = self._floor.flags
        return bool(getattr(flags, name)[y][x])

    def _collide(self, cell: Cell) -> None:
        if self.collision_pos is None:
            self.collision_pos = cell

    def _build(self, src: Cell, dst: Cell, stop_target: bool, stop_chars: bool,
               stop_terrain: bool, ignore_soft_solid: bool) -> None:
        x0, y0 = src
        x1, y1 = dst
        dx = x1 - x0
        dy = y1 - y0
        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1
        dx = abs(dx)
        dy = abs(dy)

        if dx > dy:
            a_is_x = True
            d_a, d_b = dx, dy
        else:
            a_is_x = False
            d_a, d_b = dy, dx

        cx, cy = x0, y0
        err = d_a // 2
        while self._inside_map(cx, cy):
            cell = (cx, cy)
            is_source = cell == self.source_pos
            has_char = self._char_at(cx, cy) is not None

            if (self.collision_pos is None and stop_terrain and not is_source
                    and not self._flag("passable", cx, cy)
                    and not self._flag("avoid", cx, cy)
                    and not has_char):
                self._collide(self.path[-1])

            self.path.append(cell)

            if self.collision_pos is None and stop_terrain and not is_source and self._flag("solid", cx, cy):
                if not (ignore_soft_solid and (self._flag("passable", cx, cy) or self._flag("avoid", cx, cy))):
                    self._collide(cell)
            if self.collision_pos is None and not is_source and stop_chars and has_char:
                self._collide(cell)
            if self.collision_pos is None and cell == dst and stop_target:
                self._collide(cell)

            if a_is_x:
                cx += step_x
            else:
                cy += step_y
            err += d_b
            if err >= d_a:
                err -= d_a
                if a_is_x:
                    cy += step_y
                else:
                    cx += step_x

    def sub_path(self, start: int, end: int) -> List[Cell]:
        end = min(end, len(self.path) - 1)
        if start < 0 or start > end + 1:
            return []
        return self.path[start:end + 1]


def char_lookup(game, floor, floor_id: int) -> Callable[[int, int], object]:
    """`Actor.findChar` over a floor's live mobs and active players."""
    occupied = {}
    for m in floor.mobs.values():
        if m.is_alive:
            occupied[(m.pos.x, m.pos.y)] = m
    for p in game._players_on_floor(floor_id):
        if p.is_alive and not getattr(p, "is_downed", False):
            occupied[(p.pos.x, p.pos.y)] = p
    return lambda x, y: occupied.get((x, y))
