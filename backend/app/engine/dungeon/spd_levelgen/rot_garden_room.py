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
"""Port of rooms/quest/RotGardenRoom.java -- Wandmaker quest room, Rotberry
variant (Prison depths 7-9, see run_state.WandmakerQuestState). Kept in its
own file (special_rooms.py is already very large) since this one room's
generation algorithm is a self-contained, sizable chunk on its own."""

from __future__ import annotations

from typing import List

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.geom import build_distance_map_limited
from app.engine.dungeon.spd_levelgen.level import _CIRCLE8_OFFSETS
from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import DoorType
from app.engine.dungeon.spd_levelgen.room_types import SpecialRoom
from app.engine.dungeon.spd_levelgen.special_rooms import _IRON_KEY
from app.engine.dungeon.spd_levelgen.standard_rooms import _neighbours4, _neighbours8
from app.engine.dungeon.spd_random import SPDRandom


class RotGardenRoom(SpecialRoom):
    """Generates a high-grass garden with scattered wall clutter, retrying
    the whole layout (do-while, unbounded) until it finds one with >=35
    open cells and at least one candidate cell >=7 tiles from the entrance
    for the RotHeart; then places up to 6 RotLashers one at a time, each
    gated by a fresh heart-to-entrance reachability check so a safe path
    always survives."""

    def min_width(self) -> int:
        return 10

    def min_height(self) -> int:
        return 10

    def paint(self, level, rng: SPDRandom) -> None:
        entrance = self.entrance()
        entrance.set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)

        Painter.fill(level, self, terrain.WALL)
        Painter.set(level, entrance, terrain.LOCKED_DOOR)

        width = level.width()
        height = level.height()
        size = width * height
        entry_pos = level.point_to_cell(entrance)

        candidates: List[int] = []
        passable = [False] * size
        open_cells = 0
        while True:
            Painter.fill(level, self, 1, terrain.HIGH_GRASS)
            for _ in range(12):
                Painter.set(level, self.random(rng, 1), terrain.WALL)
            for _ in range(8):
                Painter.set(level, self.random(rng, 2), terrain.WALL)
            for _ in range(4):
                Painter.set(level, self.random(rng, 3), terrain.WALL)
            Painter.draw_inside(level, self, entrance, 3, terrain.HIGH_GRASS)

            passable = [level.map[i] != terrain.WALL for i in range(size)]
            distance = build_distance_map_limited(entry_pos, passable, width, height, size)

            candidates = []
            open_cells = 0
            for p in self.get_points():
                i = level.point_to_cell(p)
                if distance[i] is not None:
                    open_cells += 1
                    if distance[i] >= 7:
                        candidates.append(i)
                elif level.map[i] == terrain.HIGH_GRASS:
                    level.map[i] = terrain.WALL

            rng.shuffle(candidates)
            closest_pos = 7
            while len(candidates) > 5:
                for i in list(candidates):
                    if len(candidates) > 5 and distance[i] == closest_pos:
                        candidates.remove(i)
                closest_pos += 1

            if candidates and open_cells >= 35:
                break

        heart_pos = candidates[rng.IntMax(len(candidates))]
        _place_plant(level, heart_pos, "RotHeart")

        new_passable = list(passable)
        max_lashers = 6
        for _ in range(1, max_lashers + 1):
            tries = 50
            while True:
                pos = level.point_to_cell(self.random(rng))
                tries -= 1
                if not (tries > 0 and not _valid_rotgarden_plant_pos(
                        passable, new_passable, level, pos, heart_pos, entry_pos)):
                    break
            if tries <= 0:
                break
            _place_plant(level, pos, "RotLasher")

        for i in range(0, len(_CIRCLE8_OFFSETS), 2):
            dx, dy = _CIRCLE8_OFFSETS[i]
            if level.map[heart_pos + dx + dy * width] != terrain.WALL:
                cdx, cdy = _CIRCLE8_OFFSETS[i + 1]
                Painter.set(level, heart_pos + cdx + cdy * width, terrain.HIGH_GRASS)


def _valid_rotgarden_plant_pos(passable: list, new_passable: list, level, pos: int,
                                heart_pos: int, entry_pos: int) -> bool:
    if level.map[pos] != terrain.HIGH_GRASS:
        return False

    width = level.width()
    for off in _neighbours8(width) + (0,):
        if level.find_mob(pos + off) is not None:
            return False

    new_passable[pos] = False
    if level.distance(pos, heart_pos) > 2:
        for off in _neighbours4(width):
            new_passable[pos + off] = False
    else:
        for off in _neighbours8(width):
            new_passable[pos + off] = False

    distance = build_distance_map_limited(heart_pos, new_passable, width, level.height(), len(new_passable))
    if distance[entry_pos] is None:
        new_passable[:] = passable
        return False
    passable[:] = new_passable
    return True


def _place_plant(level, pos: int, cls_name: str) -> None:
    level.mobs.append(GenMob(cls_name=cls_name, pos=pos, depth=level.depth))
    Painter.set(level, pos, terrain.GRASS)
