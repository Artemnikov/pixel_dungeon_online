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
"""Port of EntranceRoom/ExitRoom + sewers-eligible StandardRoom subclasses
(rooms/standard/{entrance,exit}/*.java, rooms/standard/*.java).

sizing/sizeCatProbs overrides gate the `set_size`/`init_size_cat` RNG draws.
`paint()` is fully ported (terrain/loot/mob placement, RNG-exact draw order)
for every StandardRoom class with nonzero `chances[depth]` weight on depths
1-5 (the sewers-exclusive quintet -- SewerPipeRoom/RingRoom/WaterBridgeRoom/
RegionDecoPatchRoom/CircleBasinRoom -- plus the "universal" filler rooms:
PlantsRoom, AquariumRoom, PlatformRoom, BurnedRoom, FissureRoom,
GrassyGraveRoom, StripedRoom, StudyRoom, SuspiciousChestRoom, MinefieldRoom).

The prison/caves/city/halls-region-only StandardRoom variants below (CaveRoom,
RitualRoom, StatuesRoom, etc.) are unreachable on sewers floors (weight 0
there) and are out of this port's current scope -- `paint = _stub_paint`
placeholders (generic wall+floor box) preserve their registration-order
indices so `Random.chances` still resolves correctly for other regions."""

from __future__ import annotations

import math
from typing import List, Optional, Type

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.geom import Point, Rect, gate, _to_f32
from app.engine.dungeon.spd_levelgen import patch as patch_mod
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import DoorType, Room
from app.engine.dungeon.spd_levelgen.room_types import SizeCategory, StandardRoom
from app.engine.dungeon.spd_random import SPDRandom


def _stub_paint(self, level, rng) -> None:
    Painter.fill(level, self, terrain.WALL)
    Painter.fill(level, self, 1, terrain.EMPTY)
    entrance = getattr(self, 'entrance', None)
    if entrance is not None:
        d = entrance()
        if d is not None:
            d.set(DoorType.REGULAR)
    if self.is_entrance():
        cell = level.point_to_cell(self.random(rng, 2))
        for nb in _neighbours8(level.width()):
            Painter.set(level, cell + nb, terrain.EMPTY)
        Painter.set(level, cell, terrain.ENTRANCE)
    elif self.is_exit():
        cell = level.point_to_cell(self.random(rng, 2))
        for nb in _neighbours8(level.width()):
            Painter.set(level, cell + nb, terrain.EMPTY)
        Painter.set(level, cell, terrain.EXIT)


def _neighbours8(width: int) -> tuple:
    """PathFinder.NEIGHBOURS8 with the level's actual map width substituted."""
    return (-width - 1, -width, -width + 1, -1, 1, width - 1, width, width + 1)


def _neighbours4(width: int) -> tuple:
    """PathFinder.NEIGHBOURS4 with the level's actual map width substituted."""
    return (-width, -1, 1, width)


def _space_between(a: int, b: int) -> int:
    return abs(a - b) - 1


def _patch_distance_map(to_idx: int, passable: List[bool], width: int, height: int) -> List[Optional[int]]:
    """Port of PathFinder.buildDistanceMap(to, passable) (no `from`/`limit`) --
    a plain multi-step BFS over an 8-connected grid. Zero-RNG/deterministic;
    only used here to test patch-cell reachability (`distance[i] == MAX_VALUE`),
    so traversal order doesn't matter -- shortest-path distances (and thus
    reachability) are order-independent. `None` stands in for Integer.MAX_VALUE."""
    from collections import deque

    distance: List[Optional[int]] = [None] * (width * height)
    distance[to_idx] = 0
    queue: deque = deque([to_idx])
    while queue:
        step = queue.popleft()
        x, y = step % width, step // width
        next_distance = distance[step] + 1
        for dx, dy in ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                n = nx + ny * width
                if passable[n] and (distance[n] is None or distance[n] > next_distance):
                    distance[n] = next_distance
                    queue.append(n)
    return distance


class EmptyRoom(StandardRoom):
    """Port of rooms.standard.EmptyRoom -- used by CrystalPathRoom purely as
    a Rect-like geometry container (setPos/resize/center), never connected
    or painted on its own, so paint() is left unported (would never run)."""
    pass


# -- EntranceRoom / ExitRoom base classes ----------------------------------

class EntranceRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 5)

    def min_height(self) -> int:
        return max(super().min_height(), 5)

    def is_entrance(self) -> bool:
        return True

    paint = _stub_paint


class ExitRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 5)

    def min_height(self) -> int:
        return max(super().min_height(), 5)

    def is_exit(self) -> bool:
        return True

    paint = _stub_paint


# -- StandardRoom abstract bases used by sewers-eligible subclasses --------

class StandardBridgeRoom(StandardRoom):
    def __init__(self) -> None:
        super().__init__()
        self.space_rect: Optional[Rect] = None
        self.bridge_rect: Optional[Rect] = None

    def min_width(self) -> int:
        return max(5, super().min_width())

    def min_height(self) -> int:
        return max(5, super().min_height())

    def _max_bridge_width(self, room_dimension: int) -> int:
        raise NotImplementedError

    def _space_tile(self) -> int:
        raise NotImplementedError

    def _bridge_tile(self) -> int:
        return terrain.EMPTY_SP

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        # prefer to place the bridge space to segment the most doors, or the
        # most space in the room
        doors_xy = 0
        for door in self.connected.values():
            door.set(DoorType.REGULAR)
            if door.x == self.left or door.x == self.right:
                doors_xy += 1
            else:
                doors_xy -= 1
        doors_xy += (self.width() - self.height()) // 2

        if doors_xy > 0 or (doors_xy == 0 and rng.IntMax(2) == 0):
            space_points: List[Point] = [
                door for door in self.connected.values() if door.y == self.top or door.y == self.bottom
            ]
            # fake doors for very left/right
            space_points.append(Point(self.left + 1, 0))
            space_points.append(Point(self.right - 1, 0))
            space_points.sort(key=lambda p: p.x)

            space_start = -1
            space_end = -1
            for i in range(len(space_points) - 1):
                if space_end - space_start < space_points[i + 1].x - space_points[i].x:
                    space_start = space_points[i].x
                    space_end = space_points[i + 1].x

            while space_end - space_start > self._max_bridge_width(self.width()) + 1:
                if rng.IntMax(2) == 0:
                    space_start += 1
                else:
                    space_end -= 1

            self.space_rect = Rect(space_start + 1, self.top + 1, space_end, self.bottom)

            bridge_y = rng.NormalIntRange(self.space_rect.top + 1, self.space_rect.bottom - 2)
            self.bridge_rect = Rect(self.space_rect.left, bridge_y, self.space_rect.right, bridge_y + 1)

        else:
            space_points = [
                door for door in self.connected.values() if door.x == self.left or door.x == self.right
            ]
            # fake doors for very top/bottom
            space_points.append(Point(0, self.top + 1))
            space_points.append(Point(0, self.bottom - 1))
            space_points.sort(key=lambda p: p.y)

            space_start = -1
            space_end = -1
            for i in range(len(space_points) - 1):
                if space_end - space_start < space_points[i + 1].y - space_points[i].y:
                    space_start = space_points[i].y
                    space_end = space_points[i + 1].y

            while space_end - space_start > self._max_bridge_width(self.height()) + 1:
                if rng.IntMax(2) == 0:
                    space_start += 1
                else:
                    space_end -= 1

            self.space_rect = Rect(self.left + 1, space_start + 1, self.right, space_end)

            bridge_x = rng.NormalIntRange(self.space_rect.left + 1, self.space_rect.right - 2)
            self.bridge_rect = Rect(bridge_x, self.space_rect.top, bridge_x + 1, self.space_rect.bottom)

        Painter.fill(level, self.space_rect, self._space_tile())
        Painter.fill(level, self.bridge_rect, self._bridge_tile())


class PatchRoom(StandardRoom):
    def __init__(self) -> None:
        super().__init__()
        self.patch: Optional[List[bool]] = None

    def _fill(self) -> float:
        raise NotImplementedError

    def _clustering(self) -> int:
        raise NotImplementedError

    def _ensure_path(self) -> bool:
        raise NotImplementedError

    def _clean_edges(self) -> bool:
        raise NotImplementedError

    def _xy_to_patch_coords(self, x: int, y: int) -> int:
        return (x - self.left - 1) + (y - self.top - 1) * (self.width() - 2)

    def _setup_patch(self, level, rng: SPDRandom) -> None:
        pw, ph = self.width() - 2, self.height() - 2

        if self._ensure_path():
            fill = self._fill()
            attempts = 0
            while True:
                self.patch = patch_mod.generate(rng, pw, ph, fill, self._clustering(), True)

                start_point = level.point_to_cell(self.center(rng))
                for door in self.connected.values():
                    if door.x == self.left:
                        start_point = self._xy_to_patch_coords(door.x + 1, door.y)
                        self.patch[self._xy_to_patch_coords(door.x + 1, door.y)] = False
                        self.patch[self._xy_to_patch_coords(door.x + 2, door.y)] = False
                    elif door.x == self.right:
                        start_point = self._xy_to_patch_coords(door.x - 1, door.y)
                        self.patch[self._xy_to_patch_coords(door.x - 1, door.y)] = False
                        self.patch[self._xy_to_patch_coords(door.x - 2, door.y)] = False
                    elif door.y == self.top:
                        start_point = self._xy_to_patch_coords(door.x, door.y + 1)
                        self.patch[self._xy_to_patch_coords(door.x, door.y + 1)] = False
                        self.patch[self._xy_to_patch_coords(door.x, door.y + 2)] = False
                    elif door.y == self.bottom:
                        start_point = self._xy_to_patch_coords(door.x, door.y - 1)
                        self.patch[self._xy_to_patch_coords(door.x, door.y - 1)] = False
                        self.patch[self._xy_to_patch_coords(door.x, door.y - 2)] = False

                not_patch = [not p for p in self.patch]
                distance = _patch_distance_map(start_point, not_patch, pw, ph)

                valid = True
                for i in range(len(self.patch)):
                    if not self.patch[i] and distance[i] is None:
                        valid = False
                        break

                attempts += 1
                if attempts > 100:
                    fill -= 0.01
                    attempts = 0

                if valid:
                    break
        else:
            self.patch = patch_mod.generate(rng, pw, ph, self._fill(), self._clustering(), True)

        if self._clean_edges():
            self._clean_diagonal_edges()

    def _fill_patch(self, level, terrain_id: int) -> None:
        for i in range(self.top + 1, self.bottom):
            for j in range(self.left + 1, self.right):
                if self.patch[self._xy_to_patch_coords(j, i)]:
                    cell = i * level.width() + j
                    level.map[cell] = terrain_id

    def _clean_diagonal_edges(self) -> None:
        if self.patch is None:
            return

        p_width = self.width() - 2

        for i in range(len(self.patch) - p_width):
            if not self.patch[i]:
                continue

            if i % p_width != 0:
                if self.patch[i - 1 + p_width] and not (self.patch[i - 1] or self.patch[i + p_width]):
                    self.patch[i - 1 + p_width] = False

            if (i + 1) % p_width != 0:
                if self.patch[i + 1 + p_width] and not (self.patch[i + 1] or self.patch[i + p_width]):
                    self.patch[i + 1 + p_width] = False


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


# -- "filler" StandardRoom subclasses (registration-table indices 25-34) ---

def _random_plant_seed(rng: SPDRandom):
    """Port of PlantsRoom.randomSeed(): Generator.randomUsingDefaults(SEED) in
    a do-while excluding Firebloom.Seed. Firebloom already carries weight 0 in
    the SEED chances table (generator._SEED[0] == 0.0), so Random.chances can
    never select it and the do-while always terminates after one draw."""
    from app.engine.dungeon.spd_levelgen.generator import _random_using_defaults_seed
    return _random_using_defaults_seed(rng)


class PlantsRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 5)

    def min_height(self) -> int:
        return max(super().min_height(), 5)

    def size_cat_probs(self):
        return [3.0, 1.0, 0.0]

    def merge(self, level, other, merge_rect, merge_terrain):
        if merge_terrain == terrain.EMPTY and isinstance(other, (PlantsRoom, GrassyGraveRoom)):
            super().merge(level, other, merge_rect, terrain.GRASS)
        else:
            super().merge(level, other, merge_rect, merge_terrain)

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.GRASS)
        Painter.fill(level, self, 2, terrain.HIGH_GRASS)

        if min(self.width(), self.height()) >= 7:
            Painter.fill(level, self, 3, terrain.GRASS)

        center = self.center(rng)

        if max(self.width(), self.height()) >= 9:
            if min(self.width(), self.height()) >= 11:
                Painter.draw_line(level, Point(self.left + 2, center.y), Point(self.right - 2, center.y), terrain.HIGH_GRASS)
                Painter.draw_line(level, Point(center.x, self.top + 2), Point(center.x, self.bottom - 2), terrain.HIGH_GRASS)
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x - 1, center.y - 1)))
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x + 1, center.y - 1)))
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x - 1, center.y + 1)))
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x + 1, center.y + 1)))
            elif self.width() > self.height() or (self.width() == self.height() and rng.IntMax(2) == 0):
                Painter.draw_line(level, Point(center.x, self.top + 2), Point(center.x, self.bottom - 2), terrain.HIGH_GRASS)
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x - 1, center.y)))
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x + 1, center.y)))
            else:
                Painter.draw_line(level, Point(self.left + 2, center.y), Point(self.right - 2, center.y), terrain.HIGH_GRASS)
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x, center.y - 1)))
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x, center.y + 1)))
        else:
            level.plant(_random_plant_seed(rng), level.point_to_cell(center))

        for door in self.connected.values():
            door.set(DoorType.REGULAR)


class AquariumRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 7)

    def min_height(self) -> int:
        return max(super().min_height(), 7)

    def size_cat_probs(self):
        return [3.0, 1.0, 0.0]

    def can_place_item(self, p, level) -> bool:
        return super().can_place_item(p, level) and level.map[level.point_to_cell(p)] != terrain.WATER

    def can_place_character(self, p, level) -> bool:
        return super().can_place_character(p, level) and level.map[level.point_to_cell(p)] != terrain.WATER

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)
        Painter.fill(level, self, 2, terrain.EMPTY_SP)
        Painter.fill(level, self, 3, terrain.WATER)

        min_dim = min(self.width(), self.height())
        num_fish = (min_dim - 4) // 3

        for _ in range(num_fish):
            cls_name = "PhantomPiranha" if rng.Float() < 0.02 else "Piranha"
            while True:
                pos = level.point_to_cell(self.random(rng, 3))
                if level.map[pos] == terrain.WATER and level.find_mob(pos) is None:
                    break
            level.mobs.append(GenMob(cls_name=cls_name, pos=pos, depth=level.depth))

        for door in self.connected.values():
            door.set(DoorType.REGULAR)


class PlatformRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 6)

    def min_height(self) -> int:
        return max(super().min_height(), 6)

    def size_cat_probs(self):
        return [6.0, 3.0, 1.0]

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.CHASM)

        platforms: List[Rect] = []
        self._split_platforms(rng, Rect(self.left + 2, self.top + 2, self.right - 2, self.bottom - 2), platforms)

        for platform in platforms:
            Painter.fill(level, platform.left, platform.top,
                         platform.width() + 1, platform.height() + 1, terrain.EMPTY_SP)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)
            Painter.draw_inside(level, self, door, 2, terrain.EMPTY_SP)

    def _split_platforms(self, rng: SPDRandom, cur: Rect, all_platforms: List[Rect]) -> None:
        cur_area = (cur.width() + 1) * (cur.height() + 1)

        # chance to split scales between 0% and 100% between areas of 25 and 36
        if rng.Float() < (cur_area - 25) / 11.0:
            if cur.width() > cur.height() or (cur.width() == cur.height() and rng.IntMax(2) == 0):

                split_x = rng.IntRange(cur.left + 2, cur.right - 2)
                self._split_platforms(rng, Rect(cur.left, cur.top, split_x - 1, cur.bottom), all_platforms)
                self._split_platforms(rng, Rect(split_x + 1, cur.top, cur.right, cur.bottom), all_platforms)

                bridge_y = rng.NormalIntRange(cur.top, cur.bottom)
                all_platforms.append(Rect(split_x - 1, bridge_y, split_x + 1, bridge_y))

            else:
                split_y = rng.IntRange(cur.top + 2, cur.bottom - 2)
                self._split_platforms(rng, Rect(cur.left, cur.top, cur.right, split_y - 1), all_platforms)
                self._split_platforms(rng, Rect(cur.left, split_y + 1, cur.right, cur.bottom), all_platforms)

                bridge_x = rng.NormalIntRange(cur.left, cur.right)
                all_platforms.append(Rect(bridge_x, split_y - 1, bridge_x, split_y + 1))
        else:
            all_platforms.append(cur)


class BurnedRoom(PatchRoom):
    def size_cat_probs(self):
        return [4.0, 1.0, 0.0]

    def _fill(self) -> float:
        return min(1.0, 1.48 - (self.width() + self.height()) * 0.03)

    def _clustering(self) -> int:
        return 2

    def _ensure_path(self) -> bool:
        return False

    def _clean_edges(self) -> bool:
        return False

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        self._setup_patch(level, rng)

        # TrapMechanism.revealHiddenTrapChance() baseline (fresh game, no
        # trinket -> trinketLevel == -1) is always 0, so revealInc never
        # crosses 1 and the `case 3` branch always lands on SECRET_TRAP.
        for i in range(self.top + 1, self.bottom):
            for j in range(self.left + 1, self.right):
                if not self.patch[self._xy_to_patch_coords(j, i)]:
                    continue
                cell = i * level.width() + j
                roll = rng.IntMax(5)
                if roll == 0:
                    t = terrain.EMPTY
                elif roll == 1:
                    t = terrain.EMBERS
                elif roll == 2:
                    t = terrain.TRAP
                    # level.setTrap(BurningTrap().reveal(), cell) -- zero-RNG, omitted
                elif roll == 3:
                    t = terrain.SECRET_TRAP
                    # level.setTrap(BurningTrap().hide(), cell) -- zero-RNG, omitted
                else:
                    t = terrain.INACTIVE_TRAP
                    # level.setTrap(trap, cell) -- zero-RNG, omitted
                level.map[cell] = t


class FissureRoom(StandardRoom):
    def min_height(self) -> int:
        return max(5, super().min_height())

    def min_width(self) -> int:
        return max(5, super().min_width())

    def size_cat_probs(self):
        return [6.0, 3.0, 1.0]

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.geom import _f32_div

        Painter.fill(level, self, terrain.WALL)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)
        Painter.fill(level, self, 1, terrain.EMPTY)

        if self.square() <= 25:
            p = self.center(rng)
            Painter.set(level, p.x, p.y, terrain.CHASM)
        else:
            smallest_dim = min(self.width(), self.height())
            floor_w = int(math.sqrt(smallest_dim))
            edge_floor_chance = _to_f32(math.fmod(_to_f32(math.sqrt(smallest_dim)), 1.0))
            edge_floor_chance = _to_f32(_f32_div(
                _to_f32(edge_floor_chance + _to_f32((floor_w - 1) * 0.5)),
                _to_f32(floor_w),
            ))

            for i in range(self.top + 2, self.bottom - 1):
                for j in range(self.left + 2, self.right - 1):
                    v = min(i - self.top, self.bottom - i)
                    h = min(j - self.left, self.right - j)
                    if min(v, h) > floor_w or (min(v, h) == floor_w and rng.Float() > edge_floor_chance):
                        Painter.set(level, j, i, terrain.CHASM)

        # CavesFissureEntranceRoom/CavesFissureExitRoom inherit this paint()
        # without their own override (see the "entrance variants" section
        # below for the pattern other real-paint rooms use) -- carve/stamp
        # the transition tile here, same as _stub_paint's tail, so those
        # subclasses' floors always have their ENTRANCE/EXIT terrain even
        # though the anchor point may land on a just-painted CHASM cell.
        if self.is_entrance() or self.is_exit():
            cell = level.point_to_cell(self.random(rng, 2))
            for nb in _neighbours8(level.width()):
                Painter.set(level, cell + nb, terrain.EMPTY)
            Painter.set(level, cell, terrain.ENTRANCE if self.is_entrance() else terrain.EXIT)


class GrassyGraveRoom(StandardRoom):
    def merge(self, level, other, merge_rect, merge_terrain):
        if merge_terrain == terrain.EMPTY and isinstance(other, (GrassyGraveRoom, PlantsRoom)):
            super().merge(level, other, merge_rect, terrain.GRASS)
        else:
            super().merge(level, other, merge_rect, merge_terrain)

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)
        Painter.fill(level, self, 1, terrain.GRASS)

        w = self.width() - 2
        h = self.height() - 2
        n_graves = max(w, h) // 2

        index = rng.IntMax(n_graves)
        shift = rng.IntMax(2)
        for i in range(n_graves):
            if w > h:
                pos = self.left + 1 + shift + i * 2 + (self.top + 2 + rng.IntMax(h - 2)) * level.width()
            else:
                pos = (self.left + 2 + rng.IntMax(w - 2)) + (self.top + 1 + shift + i * 2) * level.width()
            if i == index:
                item = gen.generator_random(level.run_state.generator_state, rng, level.depth)
            else:
                gen._roll_gold_item(rng, level.depth)
                item = frozenset({"Gold"})
            level.drop(item, pos).type = "TOMB"


class StripedRoom(StandardRoom):
    def size_cat_probs(self):
        return [2.0, 1.0, 0.0]

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        if self.size_cat == SizeCategory.NORMAL:
            Painter.fill(level, self, 1, terrain.EMPTY_SP)
            if self.width() > self.height() or (self.width() == self.height() and rng.IntMax(2) == 0):
                i = self.left + 2
                while i < self.right:
                    Painter.fill(level, i, self.top + 1, 1, self.height() - 2, terrain.HIGH_GRASS)
                    i += 2
            else:
                i = self.top + 2
                while i < self.bottom:
                    Painter.fill(level, self.left + 1, i, self.width() - 2, 1, terrain.HIGH_GRASS)
                    i += 2

        elif self.size_cat == SizeCategory.LARGE:
            layers = (min(self.width(), self.height()) - 1) // 2
            for i in range(1, layers + 1):
                Painter.fill(level, self, i, terrain.EMPTY_SP if i % 2 == 1 else terrain.HIGH_GRASS)


class StudyRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 7)

    def min_height(self) -> int:
        return max(super().min_height(), 7)

    def size_cat_probs(self):
        return [2.0, 1.0, 0.0]

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.BOOKSHELF)
        Painter.fill(level, self, 2, terrain.EMPTY_SP)

        for door in self.connected.values():
            Painter.draw_inside(level, self, door, 2, terrain.EMPTY_SP)
            door.set(DoorType.REGULAR)

        if self.size_cat == SizeCategory.LARGE:
            pillar_w = (self.width() - 7) // 2
            pillar_h = (self.height() - 7) // 2

            Painter.fill(level, self.left + 3, self.top + 3, pillar_w, 1, terrain.BOOKSHELF)
            Painter.fill(level, self.left + 3, self.top + 3, 1, pillar_h, terrain.BOOKSHELF)

            Painter.fill(level, self.left + 3, self.bottom - 2 - 1, pillar_w, 1, terrain.BOOKSHELF)
            Painter.fill(level, self.left + 3, self.bottom - 2 - pillar_h, 1, pillar_h, terrain.BOOKSHELF)

            Painter.fill(level, self.right - 2 - pillar_w, self.top + 3, pillar_w, 1, terrain.BOOKSHELF)
            Painter.fill(level, self.right - 2 - 1, self.top + 3, 1, pillar_h, terrain.BOOKSHELF)

            Painter.fill(level, self.right - 2 - pillar_w, self.bottom - 2 - 1, pillar_w, 1, terrain.BOOKSHELF)
            Painter.fill(level, self.right - 2 - 1, self.bottom - 2 - pillar_h, 1, pillar_h, terrain.BOOKSHELF)

        center = self.center(rng)
        Painter.set(level, center, terrain.PEDESTAL)

        prize = level.find_prize_item(rng) if rng.IntMax(2) == 0 else None

        pos = level.point_to_cell(center)
        if prize is not None:
            level.drop(prize, pos)
        else:
            cat = "POTION" if rng.IntMax(2) == 0 else "SCROLL"
            item = gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, cat)
            level.drop(item, pos)


class SuspiciousChestRoom(StandardRoom):
    def min_width(self) -> int:
        return max(5, super().min_width())

    def min_height(self) -> int:
        return max(5, super().min_height())

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        item = level.find_prize_item(rng)
        if item is None:
            gen._roll_gold_item(rng, level.depth)  # new Gold().random()
            item = frozenset({"Gold"})

        center = level.point_to_cell(self.center(rng))
        Painter.set(level, center, terrain.PEDESTAL)

        mimic_chance = (1.0 / 3.0) * gen.MIMIC_CHANCE_MULTIPLIER
        if rng.Float() < mimic_chance:
            level.mobs.append(gen.spawn_mimic(rng, level, center, item, level.depth))
        else:
            heap = level.drop(item, center)
            heap.type = "CHEST"


class MinefieldRoom(StandardRoom):
    def size_cat_probs(self):
        return [4.0, 1.0, 0.0]

    def can_merge(self, level, other, p, merge_terrain) -> bool:
        cell = level.point_to_cell(self.point_inside(p, 1))
        return level.map[cell] == terrain.EMPTY

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.traps import ExplosiveTrap, reveal_hidden_trap_chance

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        # Math.round(double): floor(x + 0.5), double precision (no float32
        # truncation -- Math.sqrt/Math.round(double) here, unlike the float32
        # helpers elsewhere in this module).
        mines = math.floor(math.sqrt(self.square()) + 0.5)
        if self.size_cat == SizeCategory.NORMAL:
            mines -= 3
        elif self.size_cat == SizeCategory.LARGE:
            mines += 3
        elif self.size_cat == SizeCategory.GIANT:
            mines += 9

        revealed_chance = reveal_hidden_trap_chance()
        reveal_inc = 0.0
        nbrs = _neighbours8(level.width())
        for _ in range(mines):
            while True:
                pos = level.point_to_cell(self.random(rng, 1))
                if pos not in level.traps:
                    break

            for _ in range(8):
                c = nbrs[rng.IntMax(8)]
                if pos + c not in level.traps and level.map[pos + c] == terrain.EMPTY:
                    Painter.set(level, pos + c, terrain.EMBERS)

            reveal_inc += revealed_chance
            if reveal_inc >= 1:
                Painter.set(level, pos, terrain.TRAP)
                level.set_trap(ExplosiveTrap().reveal(), pos)
                reveal_inc -= 1
            else:
                Painter.set(level, pos, terrain.SECRET_TRAP)
                level.set_trap(ExplosiveTrap().hide(), pos)


# -- Prison standard rooms (region-table indices 5-9) ----------------------

class RegionDecoLineRoom(StandardRoom):
    paint = _stub_paint


class SegmentedRoom(StandardRoom):
    paint = _stub_paint


class PillarsRoom(StandardRoom):
    paint = _stub_paint


class ChasmBridgeRoom(StandardBridgeRoom):
    paint = _stub_paint


class CellBlockRoom(StandardRoom):
    paint = _stub_paint


# -- Caves standard rooms (region-table indices 10-14) ---------------------

class CaveRoom(StandardRoom):
    paint = _stub_paint


class RegionDecoBridgeRoom(StandardBridgeRoom):
    paint = _stub_paint


class CavesFissureRoom(FissureRoom):
    pass  # inherits FissureRoom's paint


class CirclePitRoom(StandardRoom):
    paint = _stub_paint


class CircleWallRoom(StandardRoom):
    paint = _stub_paint


# -- City standard rooms (region-table indices 15-19) ----------------------

class HallwayRoom(StandardRoom):
    paint = _stub_paint


class LibraryHallRoom(StandardRoom):
    paint = _stub_paint


class LibraryRingRoom(StandardRoom):
    paint = _stub_paint


class StatuesRoom(StandardRoom):
    paint = _stub_paint


class SegmentedLibraryRoom(StandardRoom):
    paint = _stub_paint


# -- Halls standard rooms (region-table indices 20-24) ---------------------

class RuinsRoom(StandardRoom):
    paint = _stub_paint


# index 21 reuses RegionDecoPatchRoom (Java does rooms.add(RegionDecoPatchRoom.class) again)

class ChasmRoom(StandardRoom):
    paint = _stub_paint


class SkullsRoom(StandardRoom):
    paint = _stub_paint


class RitualRoom(StandardRoom):
    paint = _stub_paint


# -- Prison entrance/exit variants (entrance indices 4-7, exit indices 4-7) -

class RegionDecoLineEntranceRoom(RegionDecoLineRoom):
    def is_entrance(self) -> bool:
        return True


class RegionDecoLineExitRoom(RegionDecoLineRoom):
    def is_exit(self) -> bool:
        return True


class ChasmBridgeEntranceRoom(ChasmBridgeRoom):
    def is_entrance(self) -> bool:
        return True


class ChasmBridgeExitRoom(ChasmBridgeRoom):
    def is_exit(self) -> bool:
        return True


class PillarsEntranceRoom(PillarsRoom):
    def is_entrance(self) -> bool:
        return True


class PillarsExitRoom(PillarsRoom):
    def is_exit(self) -> bool:
        return True


class CellBlockEntranceRoom(CellBlockRoom):
    def is_entrance(self) -> bool:
        return True


class CellBlockExitRoom(CellBlockRoom):
    def is_exit(self) -> bool:
        return True


# -- Caves entrance/exit variants (entrance indices 8-11, exit indices 8-11) -

class CaveEntranceRoom(CaveRoom):
    def is_entrance(self) -> bool:
        return True


class CaveExitRoom(CaveRoom):
    def is_exit(self) -> bool:
        return True


class RegionDecoBridgeEntranceRoom(RegionDecoBridgeRoom):
    def is_entrance(self) -> bool:
        return True


class RegionDecoBridgeExitRoom(RegionDecoBridgeRoom):
    def is_exit(self) -> bool:
        return True


class CavesFissureEntranceRoom(CavesFissureRoom):
    def is_entrance(self) -> bool:
        return True


class CavesFissureExitRoom(CavesFissureRoom):
    def is_exit(self) -> bool:
        return True


class CircleWallEntranceRoom(CircleWallRoom):
    def is_entrance(self) -> bool:
        return True


class CircleWallExitRoom(CircleWallRoom):
    def is_exit(self) -> bool:
        return True


# -- City entrance/exit variants (entrance indices 12-15, exit indices 12-15) -

class HallwayEntranceRoom(HallwayRoom):
    def is_entrance(self) -> bool:
        return True


class HallwayExitRoom(HallwayRoom):
    def is_exit(self) -> bool:
        return True


class StatuesEntranceRoom(StatuesRoom):
    def is_entrance(self) -> bool:
        return True


class StatuesExitRoom(StatuesRoom):
    def is_exit(self) -> bool:
        return True


class LibraryHallEntranceRoom(LibraryHallRoom):
    def is_entrance(self) -> bool:
        return True


class LibraryHallExitRoom(LibraryHallRoom):
    def is_exit(self) -> bool:
        return True


class LibraryRingEntranceRoom(LibraryRingRoom):
    def is_entrance(self) -> bool:
        return True


class LibraryRingExitRoom(LibraryRingRoom):
    def is_exit(self) -> bool:
        return True


# -- Halls entrance/exit variants (entrance indices 16-19, exit indices 16-19) -

# index 16 reuses RegionDecoPatchEntranceRoom/RegionDecoPatchExitRoom (already defined)

class RuinsEntranceRoom(RuinsRoom):
    def is_entrance(self) -> bool:
        return True


class RuinsExitRoom(RuinsRoom):
    def is_exit(self) -> bool:
        return True


class ChasmEntranceRoom(ChasmRoom):
    def is_entrance(self) -> bool:
        return True


class ChasmExitRoom(ChasmRoom):
    def is_exit(self) -> bool:
        return True


class RitualEntranceRoom(RitualRoom):
    def is_entrance(self) -> bool:
        return True


class RitualExitRoom(RitualRoom):
    def is_exit(self) -> bool:
        return True


# -- registration-order tables + factories (EntranceRoom/ExitRoom/StandardRoom.java) --

# EntranceRoom.rooms / ExitRoom.rooms: only the first 4 entries have nonzero
# `chances[depth]` weight for depths 1-5 (the rest are prison/caves/city/halls
# variants) -- ported in full per the original 20-entry static list, with
# unreachable-on-sewers-floors slots as `None` placeholders preserving index.
_ENTRANCE_ROOM_TYPES: tuple = (
    # Sewers [0-3]
    WaterBridgeEntranceRoom, RegionDecoPatchEntranceRoom, RingEntranceRoom, CircleBasinEntranceRoom,
    # Prison [4-7]
    RegionDecoLineEntranceRoom, ChasmBridgeEntranceRoom, PillarsEntranceRoom, CellBlockEntranceRoom,
    # Caves [8-11]
    CaveEntranceRoom, RegionDecoBridgeEntranceRoom, CavesFissureEntranceRoom, CircleWallEntranceRoom,
    # City [12-15]
    HallwayEntranceRoom, StatuesEntranceRoom, LibraryHallEntranceRoom, LibraryRingEntranceRoom,
    # Halls [16-19] — index 16 reuses RegionDecoPatchEntranceRoom (Java reuses it)
    RegionDecoPatchEntranceRoom, RuinsEntranceRoom, ChasmEntranceRoom, RitualEntranceRoom,
)

_EXIT_ROOM_TYPES: tuple = (
    # Sewers [0-3]
    WaterBridgeExitRoom, RegionDecoPatchExitRoom, RingExitRoom, CircleBasinExitRoom,
    # Prison [4-7]
    RegionDecoLineExitRoom, ChasmBridgeExitRoom, PillarsExitRoom, CellBlockExitRoom,
    # Caves [8-11]
    CaveExitRoom, RegionDecoBridgeExitRoom, CavesFissureExitRoom, CircleWallExitRoom,
    # City [12-15]
    HallwayExitRoom, StatuesExitRoom, LibraryHallExitRoom, LibraryRingExitRoom,
    # Halls [16-19] — index 16 reuses RegionDecoPatchExitRoom (Java reuses it)
    RegionDecoPatchExitRoom, RuinsExitRoom, ChasmExitRoom, RitualExitRoom,
)

# EntranceRoom.chances[depth]
_ENTRANCE_CHANCES = {
    1:  (4.0, 3.0, 0.0, 0.0) + (0.0,) * 16,
    2:  (4.0, 3.0, 0.0, 0.0) + (0.0,) * 16,
    3:  (4.0, 3.0, 2.0, 1.0) + (0.0,) * 16,
    4:  (4.0, 3.0, 2.0, 1.0) + (0.0,) * 16,
    5:  (4.0, 3.0, 2.0, 1.0) + (0.0,) * 16,
    # Prison
    6:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    7:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    8:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    9:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    10: (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    # Caves
    11: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    12: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    13: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    14: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    15: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    # City
    16: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    17: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    18: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    19: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    20: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    # Halls
    21: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    22: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    23: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    24: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    25: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    26: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
}

# ExitRoom.chances[depth]
_EXIT_CHANCES = {
    1:  (4.0, 3.0, 0.0, 0.0) + (0.0,) * 16,
    2:  (4.0, 3.0, 2.0, 1.0) + (0.0,) * 16,
    3:  (4.0, 3.0, 2.0, 1.0) + (0.0,) * 16,
    4:  (4.0, 3.0, 2.0, 1.0) + (0.0,) * 16,
    5:  (4.0, 3.0, 2.0, 1.0) + (0.0,) * 16,
    # Prison
    6:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    7:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    8:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    9:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    10: (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    # Caves
    11: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    12: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    13: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    14: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    15: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    # City
    16: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    17: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    18: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    19: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    20: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    # Halls
    21: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    22: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    23: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    24: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    25: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    26: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
}

# StandardRoom.rooms registration order (35 entries: 5 region-table groups of
# 5 + 10 filler rooms).
_STANDARD_ROOM_TYPES: tuple = (
    # Sewers [0-4]
    SewerPipeRoom, RingRoom, WaterBridgeRoom, RegionDecoPatchRoom, CircleBasinRoom,
    # Prison [5-9]
    RegionDecoLineRoom, SegmentedRoom, PillarsRoom, ChasmBridgeRoom, CellBlockRoom,
    # Caves [10-14]
    CaveRoom, RegionDecoBridgeRoom, CavesFissureRoom, CirclePitRoom, CircleWallRoom,
    # City [15-19]
    HallwayRoom, LibraryHallRoom, LibraryRingRoom, StatuesRoom, SegmentedLibraryRoom,
    # Halls [20-24] — index 21 is RegionDecoPatchRoom again (Java reuses it)
    RuinsRoom, RegionDecoPatchRoom, ChasmRoom, SkullsRoom, RitualRoom,
    # Filler [25-34]
    PlantsRoom, AquariumRoom, PlatformRoom, BurnedRoom, FissureRoom,
    GrassyGraveRoom, StripedRoom, StudyRoom, SuspiciousChestRoom, MinefieldRoom,
)

# StandardRoom.chances[depth]
_STANDARD_CHANCES = {
    1:  (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 20 + (1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0),
    2:  (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 20 + (1.0,) * 10,
    3:  (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 20 + (1.0,) * 10,
    4:  (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 20 + (1.0,) * 10,
    5:  (16.0, 8.0, 8.0, 4.0, 0.0) + (0.0,) * 30,
    # Prison
    6:  (0.0,) * 5 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 15 + (1.0,) * 10,
    7:  (0.0,) * 5 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 15 + (1.0,) * 10,
    8:  (0.0,) * 5 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 15 + (1.0,) * 10,
    9:  (0.0,) * 5 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 15 + (1.0,) * 10,
    10: (0.0,) * 5 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 15 + (1.0,) * 10,
    # Caves
    11: (0.0,) * 10 + (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 10 + (1.0,) * 10,
    12: (0.0,) * 10 + (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 10 + (1.0,) * 10,
    13: (0.0,) * 10 + (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 10 + (1.0,) * 10,
    14: (0.0,) * 10 + (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 10 + (1.0,) * 10,
    15: (0.0,) * 10 + (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 10 + (1.0,) * 10,
    # City
    16: (0.0,) * 15 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 5 + (1.0,) * 10,
    17: (0.0,) * 15 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 5 + (1.0,) * 10,
    18: (0.0,) * 15 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 5 + (1.0,) * 10,
    19: (0.0,) * 15 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 5 + (1.0,) * 10,
    20: (0.0,) * 15 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 5 + (1.0,) * 10,
    # Halls
    21: (0.0,) * 20 + (10.0, 10.0, 10.0, 5.0, 5.0) + (1.0,) * 10,
    22: (0.0,) * 20 + (10.0, 10.0, 10.0, 5.0, 5.0) + (1.0,) * 10,
    23: (0.0,) * 20 + (10.0, 10.0, 10.0, 5.0, 5.0) + (1.0,) * 10,
    24: (0.0,) * 20 + (10.0, 10.0, 10.0, 5.0, 5.0) + (1.0,) * 10,
    25: (0.0,) * 20 + (10.0, 10.0, 10.0, 5.0, 5.0) + (1.0,) * 10,
    26: (0.0,) * 20 + (10.0, 10.0, 10.0, 5.0, 5.0) + (1.0,) * 10,
}


def _create_from_table(rng: SPDRandom, types: tuple, chances: tuple) -> Room:
    idx = rng.chances(chances)
    room_type: Optional[Type[StandardRoom]] = types[idx]
    room = room_type()
    room.init_size_cat(rng)
    return room


def create_entrance(rng: SPDRandom, depth: int) -> Room:
    """Port of EntranceRoom.createEntrance()."""
    return _create_from_table(rng, _ENTRANCE_ROOM_TYPES, _ENTRANCE_CHANCES[depth])


def create_exit(rng: SPDRandom, depth: int) -> Room:
    """Port of ExitRoom.createExit()."""
    return _create_from_table(rng, _EXIT_ROOM_TYPES, _EXIT_CHANCES[depth])


def create_standard_room(rng: SPDRandom, depth: int) -> Room:
    """Port of StandardRoom.createRoom()."""
    return _create_from_table(rng, _STANDARD_ROOM_TYPES, _STANDARD_CHANCES[depth])
