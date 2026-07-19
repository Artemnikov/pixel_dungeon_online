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
"""Sewers-region StandardRoom subclasses (region-table indices 0-4) + their
entrance/exit variants (registration-table indices 0-3): SewerPipeRoom,
RingRoom, WaterBridgeRoom, RegionDecoPatchRoom, CircleBasinRoom.

Split out of standard_rooms.py, which used to hold all ~85 StandardRoom
subclasses across every region in one file.
"""

import math
from typing import List, Optional

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.geom import Point, Rect, gate, _to_f32
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import DoorType
from app.engine.dungeon.spd_levelgen.room_types import SizeCategory, StandardRoom
from app.engine.dungeon.spd_random import SPDRandom
from app.engine.dungeon.spd_levelgen.standard_rooms_base import (
    PatchRoom, StandardBridgeRoom, _neighbours4, _neighbours8, _space_between,
)

# -- concrete StandardRoom subclasses (region-table indices 0-4) -----------

class SewerPipeRoom(StandardRoom):
    def __init__(self) -> None:
        super().__init__()
        self._corners: Optional[List[Point]] = None

    def min_width(self) -> int:
        return max(7, super().min_width())

    def min_height(self) -> int:
        return max(7, super().min_height())

    def size_cat_probs(self):
        return [3.0, 2.0, 1.0]

    def can_connect_point(self, p) -> bool:
        return super().can_connect_point(p) and (
            (p.x > self.left + 1 and p.x < self.right - 1) or
            (p.y > self.top + 1 and p.y < self.bottom - 1)
        )

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)

        c = self._connection_space(rng)

        if len(self.connected) == 1 or (len(self.connected) == 2 and self.size_cat == SizeCategory.NORMAL):
            for door in self.connected.values():
                start = Point(door.x, door.y)
                if start.x == self.left:
                    start.x += 2
                elif start.y == self.top:
                    start.y += 2
                elif start.x == self.right:
                    start.x -= 2
                elif start.y == self.bottom:
                    start.y -= 2

                if start.x < c.left:
                    right_shift = c.left - start.x
                elif start.x > c.right:
                    right_shift = c.right - start.x
                else:
                    right_shift = 0

                if start.y < c.top:
                    down_shift = c.top - start.y
                elif start.y > c.bottom:
                    down_shift = c.bottom - start.y
                else:
                    down_shift = 0

                # always goes inward first
                if door.x == self.left or door.x == self.right:
                    mid = Point(start.x + right_shift, start.y)
                    end = Point(mid.x, mid.y + down_shift)
                else:
                    mid = Point(start.x, start.y + down_shift)
                    end = Point(mid.x + right_shift, mid.y)

                Painter.draw_line(level, start, mid, terrain.WATER)
                Painter.draw_line(level, mid, end, terrain.WATER)
        else:
            door_points: List[Point] = list(self.connected.values())

            # if we only have two doors, add a phantom 3rd door along an empty
            # wall -- guarantees a minimum open space for larger pipe rooms
            if len(door_points) == 2:
                p = Point(0, 0)
                while True:
                    valid = True
                    if rng.IntMax(2) == 0:
                        p.x = self.left if rng.IntMax(2) == 0 else self.right
                        p.y = rng.IntRange(self.top + 2, self.bottom - 2)
                    else:
                        p.x = rng.IntRange(self.left + 2, self.right - 2)
                        p.y = self.top if rng.IntMax(2) == 0 else self.bottom

                    for door in self.connected.values():
                        if door.x == p.x or door.y == p.y:
                            valid = False
                    if valid:
                        break
                door_points.append(p)

            points_to_fill: List[Point] = []
            for door in door_points:
                p = Point(door.x, door.y)
                if p.y == self.top:
                    p.y += 2
                elif p.y == self.bottom:
                    p.y -= 2
                elif p.x == self.left:
                    p.x += 2
                else:
                    p.x -= 2
                points_to_fill.append(p)

            points_filled = [points_to_fill.pop(0)]

            while points_to_fill:
                shortest_distance = None
                from_p = to_p = None
                for f in points_filled:
                    for t in points_to_fill:
                        dist = self._distance_between_points(f, t)
                        if shortest_distance is None or dist < shortest_distance:
                            from_p = f
                            to_p = t
                            shortest_distance = dist
                self._fill_between_points(level, from_p, to_p, terrain.WATER)
                points_filled.append(to_p)
                points_to_fill.remove(to_p)

        for p in self.get_points():
            cell = level.point_to_cell(p)
            if level.map[cell] == terrain.WATER:
                for i in _neighbours8(level.width()):
                    if level.map[cell + i] == terrain.WALL:
                        Painter.set(level, cell + i, terrain.EMPTY)

        for r, door in list(self.connected.items()):
            if isinstance(r, SewerPipeRoom):
                Painter.fill(level, door.x - 1, door.y - 1, 3, 3, terrain.EMPTY)
                if door.x == self.left or door.x == self.right:
                    Painter.fill(level, door.x - 1, door.y, 3, 1, terrain.WATER)
                else:
                    Painter.fill(level, door.x, door.y - 1, 1, 3, terrain.WATER)
                door.set(DoorType.WATER)
            else:
                door.set(DoorType.REGULAR)

    def _connection_space(self, rng: SPDRandom) -> Rect:
        c = self.center(rng) if len(self.connected) <= 1 else self._door_center(rng)
        return Rect(c.x, c.y, c.x, c.y)

    def can_place_water(self, p: Point) -> bool:
        return False

    def _door_center(self, rng: SPDRandom) -> Point:
        door_center_x = 0.0
        door_center_y = 0.0
        for door in self.connected.values():
            door_center_x = _to_f32(door_center_x + door.x)
            door_center_y = _to_f32(door_center_y + door.y)

        n = len(self.connected)
        c = Point(int(door_center_x) // n, int(door_center_y) // n)
        if rng.Float() < math.fmod(door_center_x, 1.0):
            c.x += 1
        if rng.Float() < math.fmod(door_center_y, 1.0):
            c.y += 1
        c.x = int(gate(self.left + 2, c.x, self.right - 2))
        c.y = int(gate(self.top + 2, c.y, self.bottom - 2))
        return c

    def _distance_between_points(self, a: Point, b: Point) -> int:
        if (((a.x == self.left + 2 or a.x == self.right - 2) and a.y == b.y)
                or ((a.y == self.top + 2 or a.y == self.bottom - 2) and a.x == b.x)):
            return max(_space_between(a.x, b.x), _space_between(a.y, b.y))

        return (min(_space_between(self.left, a.x) + _space_between(self.left, b.x),
                    _space_between(self.right, a.x) + _space_between(self.right, b.x))
                + min(_space_between(self.top, a.y) + _space_between(self.top, b.y),
                      _space_between(self.bottom, a.y) + _space_between(self.bottom, b.y))
                - 1)

    def _fill_between_points(self, level, from_: Point, to: Point, floor: int) -> None:
        if (((from_.x == self.left + 2 or from_.x == self.right - 2) and from_.x == to.x)
                or ((from_.y == self.top + 2 or from_.y == self.bottom - 2) and from_.y == to.y)):
            Painter.fill(level,
                         min(from_.x, to.x), min(from_.y, to.y),
                         _space_between(from_.x, to.x) + 2, _space_between(from_.y, to.y) + 2,
                         floor)
            return

        if self._corners is None:
            self._corners = [
                Point(self.left + 2, self.top + 2),
                Point(self.right - 2, self.top + 2),
                Point(self.right - 2, self.bottom - 2),
                Point(self.left + 2, self.bottom - 2),
            ]

        for c in self._corners:
            if (c.x == from_.x or c.y == from_.y) and (c.x == to.x or c.y == to.y):
                Painter.draw_line(level, from_, c, floor)
                Painter.draw_line(level, c, to, floor)
                return

        if from_.y == self.top + 2 or from_.y == self.bottom - 2:
            if (_space_between(self.left, from_.x) + _space_between(self.left, to.x)
                    <= _space_between(self.right, from_.x) + _space_between(self.right, to.x)):
                side = Point(self.left + 2, self.top + self.height() // 2)
            else:
                side = Point(self.right - 2, self.top + self.height() // 2)
        else:
            if (_space_between(self.top, from_.y) + _space_between(self.top, to.y)
                    <= _space_between(self.bottom, from_.y) + _space_between(self.bottom, to.y)):
                side = Point(self.left + self.width() // 2, self.top + 2)
            else:
                side = Point(self.left + self.width() // 2, self.bottom - 2)

        self._fill_between_points(level, from_, side, floor)
        self._fill_between_points(level, side, to, floor)


class RingRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 7)

    def min_height(self) -> int:
        return max(super().min_height(), 7)

    def size_cat_probs(self):
        return [9.0, 3.0, 1.0]

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        min_dim = min(self.width(), self.height())
        passage_width = int(math.floor(_to_f32(0.2 * (min_dim + 3))))
        Painter.fill(level, self, passage_width + 1, terrain.WALL)

        if min_dim >= 10:
            Painter.fill(level, self, passage_width + 2, self._center_deco_tiles())
            center = self.center(rng)
            x_dir = 0
            y_dir = 0

            # prefer to make the door further away if possible
            if rng.IntMax(2) == 0:
                if center.x < (self.left + self.right) / 2.0:
                    x_dir = 1
                elif center.x > (self.left + self.right) / 2.0:
                    x_dir = -1
                else:
                    x_dir = 1 if rng.IntMax(2) == 0 else -1
            else:
                if center.y < (self.top + self.bottom) / 2.0:
                    y_dir = 1
                elif center.y > (self.top + self.bottom) / 2.0:
                    y_dir = -1
                else:
                    y_dir = 1 if rng.IntMax(2) == 0 else -1

            Painter.set(level, center, terrain.EMPTY_SP)
            self._place_center_detail(level, rng, level.point_to_cell(center))

            center.x += x_dir
            center.y += y_dir
            while level.map[level.point_to_cell(center)] != terrain.WALL:
                Painter.set(level, center, terrain.EMPTY_SP)
                center.x += x_dir
                center.y += y_dir
            Painter.set(level, center, terrain.DOOR)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)

    def _center_deco_tiles(self) -> int:
        return terrain.REGION_DECO_ALT

    def _place_center_detail(self, level, rng: SPDRandom, pos: int) -> None:
        prize = level.find_prize_item(rng)
        if prize is not None:
            level.drop(prize, pos)


class WaterBridgeRoom(StandardBridgeRoom):
    def _max_bridge_width(self, room_dimension: int) -> int:
        return 3 if room_dimension >= 8 else 2

    def _space_tile(self) -> int:
        return terrain.WATER

    def can_place_water(self, p) -> bool:
        return False


class RegionDecoPatchRoom(PatchRoom):
    def min_height(self) -> int:
        return max(5, super().min_height())

    def min_width(self) -> int:
        return max(5, super().min_width())

    def _fill(self) -> float:
        scale = min(self.width() * self.height(), 10 * 10)
        return _to_f32(0.20 + scale / 1024.0)

    def _clustering(self) -> int:
        return 1

    def _ensure_path(self) -> bool:
        return len(self.connected) > 0

    def _clean_edges(self) -> bool:
        return True

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        self._setup_patch(level, rng)
        self._fill_patch(level, terrain.REGION_DECO)


class CircleBasinRoom(PatchRoom):
    def min_width(self) -> int:
        return self.size_cat.min_dim + 1

    def min_height(self) -> int:
        return self.size_cat.min_dim + 1

    def size_cat_probs(self):
        return [0.0, 3.0, 1.0]

    def resize(self, w: int, h: int) -> "Rect":
        super().resize(w, h)
        if self.width() % 2 == 0:
            self.right -= 1
        if self.height() % 2 == 0:
            self.bottom -= 1
        return self

    def _fill(self) -> float:
        return 0.5

    def _clustering(self) -> int:
        return 5

    def _ensure_path(self) -> bool:
        return False

    def _clean_edges(self) -> bool:
        return False

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)

        Painter.fill_ellipse(level, self, 1, terrain.EMPTY)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)
            if door.x == self.left or door.x == self.right:
                Painter.draw_inside(level, self, door, self.width() // 2, terrain.EMPTY)
            else:
                Painter.draw_inside(level, self, door, self.height() // 2, terrain.EMPTY)

        Painter.fill_ellipse(level, self, 3, terrain.CHASM)

        start = Point(self.left + self.width() // 2, self.top + 3)
        end = Point(self.left + self.width() // 2, self.bottom - 3)
        Painter.draw_line(level, start, end, terrain.EMPTY_SP)

        start = Point(self.left + 3, self.top + self.height() // 2)
        end = Point(self.right - 3, self.top + self.height() // 2)
        Painter.draw_line(level, start, end, terrain.EMPTY_SP)

        if self.width() > 11 or self.height() > 11:
            center = self.center(rng)
            Painter.fill(level, center.x - 1, center.y - 1, 3, 3, terrain.EMPTY_SP)
            Painter.set(level, center, terrain.WALL)

        self._setup_patch(level, rng)
        for i in range(self.top + 1, self.bottom):
            for j in range(self.left + 1, self.right):
                cell = i * level.width() + j
                if level.map[cell] == terrain.EMPTY and self.patch[self._xy_to_patch_coords(j, i)]:
                    level.map[cell] = terrain.WATER
                    if level.map[cell - level.width()] == terrain.WALL:
                        level.map[cell - level.width()] = terrain.WALL_DECO


# -- entrance variants (registration-table indices 0-3) --------------------

class WaterBridgeEntranceRoom(WaterBridgeRoom):
    def min_width(self) -> int:
        return max(7, super().min_width())

    def min_height(self) -> int:
        return max(7, super().min_height())

    def is_entrance(self) -> bool:
        return True

    def paint(self, level, rng: SPDRandom) -> None:
        super().paint(level, rng)

        while True:
            entrance = level.point_to_cell(self.random(rng, 2))
            if not (self.space_rect.inside(level.cell_to_point(entrance)) or level.find_mob(entrance) is not None):
                break

        for i in _neighbours8(level.width()):
            Painter.set(level, entrance + i, terrain.EMPTY)

        Painter.set(level, entrance, terrain.ENTRANCE)
        # LevelTransition registration + placeEarlyGuidePages -- zero-RNG /
        # unseeded-generator side effects, out of layout-parity scope.


class RegionDecoPatchEntranceRoom(RegionDecoPatchRoom):
    def min_height(self) -> int:
        return max(7, super().min_height())

    def min_width(self) -> int:
        return max(7, super().min_width())

    def is_entrance(self) -> bool:
        return True

    def paint(self, level, rng: SPDRandom) -> None:
        super().paint(level, rng)

        tries = 30
        while True:
            entrance = level.point_to_cell(self.random(rng, 2))

            if tries > 0:
                tries -= 1
                valid = level.map[entrance] != terrain.REGION_DECO and level.find_mob(entrance) is None
            else:
                valid = False
                for i in _neighbours4(level.width()):
                    if level.map[entrance + i] != terrain.REGION_DECO:
                        valid = True
                valid = valid and level.find_mob(entrance) is None

            if valid:
                break

        Painter.set(level, entrance, terrain.ENTRANCE)

        for i in _neighbours8(level.width()):
            Painter.set(level, entrance + i, terrain.EMPTY)

        # LevelTransition registration -- zero-RNG, out of layout-parity scope.


class RingEntranceRoom(RingRoom):
    def size_cat_probs(self):
        return [0.0, 1.0, 0.0]

    def is_entrance(self) -> bool:
        return True

    def _center_deco_tiles(self) -> int:
        return terrain.EMPTY_SP

    def _place_center_detail(self, level, rng: SPDRandom, pos: int) -> None:
        # Painter.set + LevelTransition registration -- zero RNG, out of
        # layout-parity scope (mirrors CrystalPathRoom's drop/transition omissions).
        Painter.set(level, pos, terrain.ENTRANCE_SP)


class CircleBasinEntranceRoom(CircleBasinRoom):
    def size_cat_probs(self):
        return [0.0, 1.0, 0.0]

    def is_entrance(self) -> bool:
        return True

    def paint(self, level, rng: SPDRandom) -> None:
        super().paint(level, rng)

        entrance = level.point_to_cell(self.center(rng))
        Painter.set(level, entrance, terrain.ENTRANCE_SP)
        # LevelTransition registration -- zero-RNG, out of layout-parity scope.


# -- exit variants (registration-table indices 0-3) ------------------------

class WaterBridgeExitRoom(WaterBridgeRoom):
    def min_width(self) -> int:
        return max(7, super().min_width())

    def min_height(self) -> int:
        return max(7, super().min_height())

    def is_exit(self) -> bool:
        return True

    def paint(self, level, rng: SPDRandom) -> None:
        super().paint(level, rng)

        while True:
            exit_ = level.point_to_cell(self.random(rng, 2))
            if not (self.space_rect.inside(level.cell_to_point(exit_)) or level.find_mob(exit_) is not None):
                break

        for i in _neighbours8(level.width()):
            Painter.set(level, exit_ + i, terrain.EMPTY)

        Painter.set(level, exit_, terrain.EXIT)
        # LevelTransition registration -- zero-RNG, out of layout-parity scope.


class RegionDecoPatchExitRoom(RegionDecoPatchRoom):
    def min_height(self) -> int:
        return max(7, super().min_height())

    def min_width(self) -> int:
        return max(7, super().min_width())

    def is_exit(self) -> bool:
        return True

    def paint(self, level, rng: SPDRandom) -> None:
        super().paint(level, rng)

        tries = 30
        while True:
            exit_ = level.point_to_cell(self.random(rng, 2))

            if tries > 0:
                tries -= 1
                valid = level.map[exit_] != terrain.REGION_DECO and level.find_mob(exit_) is None
            else:
                valid = False
                for i in _neighbours4(level.width()):
                    if level.map[exit_ + i] != terrain.REGION_DECO:
                        valid = True
                valid = valid and level.find_mob(exit_) is None

            if valid:
                break

        Painter.set(level, exit_, terrain.EXIT)

        for i in _neighbours8(level.width()):
            Painter.set(level, exit_ + i, terrain.EMPTY)

        # LevelTransition registration -- zero-RNG, out of layout-parity scope.


class RingExitRoom(RingRoom):
    def size_cat_probs(self):
        return [0.0, 1.0, 0.0]

    def is_exit(self) -> bool:
        return True

    def _center_deco_tiles(self) -> int:
        return terrain.EMPTY_SP

    def _place_center_detail(self, level, rng: SPDRandom, pos: int) -> None:
        # Painter.set + LevelTransition registration -- zero RNG, out of
        # layout-parity scope.
        Painter.set(level, pos, terrain.EXIT)


class CircleBasinExitRoom(CircleBasinRoom):
    def size_cat_probs(self):
        return [0.0, 1.0, 0.0]

    def is_exit(self) -> bool:
        return True

    def paint(self, level, rng: SPDRandom) -> None:
        super().paint(level, rng)

        exit_ = level.point_to_cell(self.center(rng))
        Painter.set(level, exit_, terrain.EXIT)
        # LevelTransition registration -- zero-RNG, out of layout-parity scope.
