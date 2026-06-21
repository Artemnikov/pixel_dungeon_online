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
"""Direct port of levels/LastLevel.java's build() -- the fixed depth-26 floor
reached after Yog-Dzewa's death, where the Amulet of Yendor sits waiting.

Not procedurally generated (mirrors prison_boss_layout.py's pattern for fixed
layouts). Mob/item spawning is otherwise empty (LastLevel.java's createMob()
returns null and createMobs() is a no-op) -- only the Amulet drops.

CHASM tiles are ported verbatim (matching the original's mostly-pit floor)
even though this engine has no pit-fall mechanic yet -- CHASM currently
renders as an inert solid WALL (spd_adapter._SPD_TO_TILE), so this level
will pick up real chasm behavior automatically once that mechanic lands,
with no changes needed here.

EMPTY_DECO randomization (LastLevel.java line 128, `Random.Int(5)==0`) and
the CustomFloor/CenterPieceVisuals/CenterPieceWalls decorative tilemaps
(lines 139-149) are deliberately not ported -- purely cosmetic on a level
visited once per run, out of proportion to the gameplay-critical layout.
"""

from __future__ import annotations

from typing import List, Tuple

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.level import Feeling, GenLevel
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import Room
from app.engine.dungeon.spd_random import SPDRandom

WIDTH = 16
HEIGHT = 64
ROOM_TOP = 10
MID = WIDTH // 2
AMULET_POS = 12 * WIDTH + MID  # (x=8, y=12)


class LastLevelRoom(Room):
    """Single room covering the entrance/corridor/amulet area -- LastLevel
    has no other rooms, and the same tile (the ENTRANCE strip near the
    bottom) serves as both the arrival point from depth 25 and the
    departure point back to it."""

    def is_entrance(self) -> bool:
        return True

    def is_exit(self) -> bool:
        return True


def build_last_level(rng: SPDRandom, depth: int, run_state) -> Tuple[GenLevel, List[Room]]:
    level = GenLevel(depth, Feeling.NONE)
    level.run_state = run_state
    level.set_size(WIDTH, HEIGHT)

    Painter.fill(level, 0, 0, WIDTH, HEIGHT, terrain.CHASM)
    Painter.fill(level, 0, HEIGHT - 1, WIDTH, 1, terrain.WALL)
    Painter.fill(level, MID - 1, 10, 3, HEIGHT - 11, terrain.EMPTY)
    Painter.fill(level, MID - 2, HEIGHT - 3, 5, 1, terrain.EMPTY)
    Painter.fill(level, MID - 3, HEIGHT - 2, 7, 1, terrain.EMPTY)

    Painter.fill(level, 0, HEIGHT - ROOM_TOP, WIDTH, 2, terrain.WALL)
    Painter.set(level, MID, HEIGHT - ROOM_TOP, terrain.ENTRANCE)
    Painter.set(level, MID, HEIGHT - ROOM_TOP + 1, terrain.ENTRANCE)

    Painter.fill(level, 0, HEIGHT - ROOM_TOP + 2, WIDTH, 8, terrain.EMPTY)
    Painter.fill(level, MID - 1, HEIGHT - ROOM_TOP + 2, 3, 1, terrain.ENTRANCE)

    Painter.fill(level, MID - 2, 9, 5, 7, terrain.EMPTY)
    Painter.fill(level, MID - 3, 10, 7, 5, terrain.EMPTY)

    room = LastLevelRoom()
    room.set(0, HEIGHT - ROOM_TOP, WIDTH, HEIGHT)
    level.rooms = [room]
    level.room_entrance = room
    level.room_exit = room
    level.build_flag_maps()

    level.drop(frozenset({"Amulet"}), AMULET_POS)

    return level, level.rooms
