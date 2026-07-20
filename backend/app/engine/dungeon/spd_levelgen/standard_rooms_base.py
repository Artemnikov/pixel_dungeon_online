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

from typing import List, Optional

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.geom import Point, Rect
from app.engine.dungeon.spd_levelgen import patch as patch_mod
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import DoorType
from app.engine.dungeon.spd_levelgen.room_types import StandardRoom
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
