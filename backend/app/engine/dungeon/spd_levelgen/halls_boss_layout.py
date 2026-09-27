# Copyright (C) 2026 ArtemNikov
#
"""Direct port of levels/HallsBossLevel.java (Yog-Dzewa, depth 25): the 32x32
arena layout with 5 randomized vertical strips, cavernous water/statue/deco
patches, central altar platform, CenterPieceVisuals/CenterPieceWalls tilemaps
from custom_tiles/halls_special.png, entrance at the south and exit altar at
the north.
"""

from __future__ import annotations

from typing import List, Tuple

from app.engine.dungeon.spd_levelgen import patch
from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.geom import build_distance_map_limited
from app.engine.dungeon.spd_levelgen.level import Feeling, GenLevel
from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import Room
from app.engine.dungeon.spd_levelgen.run_state import RunState
from app.engine.dungeon.spd_random import SPDRandom

WIDTH = 32
HEIGHT = 32

ROOM_LEFT = WIDTH // 2 - 4   # 12
ROOM_RIGHT = WIDTH // 2 + 4  # 20
ROOM_TOP = 8
ROOM_BOTTOM = ROOM_TOP + 8   # 16

CENTER_PIECE_VISUALS = [
    [ 8,  9, 10, 11, 11, 11, 12, 13, 14],
    [16, 17, 18, 27, 19, 27, 20, 21, 22],
    [24, 25, 26, 19, 19, 19, 28, 29, 30],
    [24, 25, 26, 19, 19, 19, 28, 29, 30],
    [24, 25, 26, 19, 19, 19, 28, 29, 30],
    [24, 25, 34, 35, 35, 35, 34, 29, 30],
    [40, 41, 36, 36, 36, 36, 36, 40, 41],
    [48, 49, 36, 36, 36, 36, 36, 48, 49],
]

CENTER_PIECE_WALLS = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1],
    [32, 33, -1, -1, -1, -1, -1, 32, 33],
    [40, 41, -1, -1, -1, -1, -1, 40, 41],
]


def get_center_piece_visuals(unsealed: bool = False) -> list[list[int]]:
    """Port of HallsBossLevel.CenterPieceVisuals."""
    grid = [list(row) for row in CENTER_PIECE_VISUALS]
    if unsealed:
        grid[0][4] = 19
        grid[1][3] = 31
        grid[1][5] = 31
    return grid


def get_center_piece_walls(unsealed: bool = False) -> list[list[int]]:
    """Port of HallsBossLevel.CenterPieceWalls."""
    grid = [list(row) for row in CENTER_PIECE_WALLS]
    if unsealed:
        grid[0][3] = 1
        grid[0][4] = 0
        grid[0][5] = 2
        grid[1][4] = 23
    return grid


class HallsBossEntranceRoom(Room):
    """Marks the entrance room area at the southern end of the arena."""

    def is_entrance(self) -> bool:
        return True


class HallsBossExitRoom(Room):
    """Marks the exit room area surrounding the centerpiece altar at the north."""

    def is_exit(self) -> bool:
        return True


class YogDzewaBossRoom(Room):
    """Marks the main Yog-Dzewa arena area."""
    pass


def build(rng: SPDRandom, depth: int, run_state: RunState) -> Tuple[GenLevel, List[Room]]:
    """Port of HallsBossLevel.build(). Loops until a valid passable path
    between entrance and exit is verified by PathFinder."""
    while True:
        level = GenLevel(depth, Feeling.NONE)
        level.run_state = run_state
        level.set_size(WIDTH, HEIGHT)

        entrance_cell = -1
        for i in range(5):
            if i == 0 or i == 4:
                top = rng.IntRange(ROOM_TOP - 1, ROOM_TOP + 3)
                bottom = rng.IntRange(ROOM_BOTTOM + 2, ROOM_BOTTOM + 6)
            elif i == 1 or i == 3:
                top = rng.IntRange(ROOM_TOP - 5, ROOM_TOP - 1)
                bottom = rng.IntRange(ROOM_BOTTOM + 6, ROOM_BOTTOM + 10)
            else:
                top = rng.IntRange(ROOM_TOP - 6, ROOM_TOP - 3)
                bottom = rng.IntRange(ROOM_BOTTOM + 8, ROOM_BOTTOM + 12)

            Painter.fill(level, 4 + i * 5, top, 5, bottom - top + 1, terrain.EMPTY)

            if i == 2:
                entrance_cell = (6 + i * 5) + (bottom - 1) * WIDTH

        exit_cell = WIDTH // 2 + (ROOM_TOP + 1) * WIDTH
        boss_pos = exit_cell + WIDTH * 3

        # Patch 1: 0.20 fill, 0 clustering -> REGION_DECO or STATUE
        patch1 = patch.generate(rng, WIDTH, HEIGHT, 0.20, 0, True)
        for idx in range(level.length()):
            if level.map[idx] == terrain.EMPTY and patch1[idx]:
                dist = level.distance(idx, boss_pos)
                level.map[idx] = (terrain.REGION_DECO
                                  if dist + rng.IntMax(5) >= 10
                                  else terrain.STATUE)

        level.map[entrance_cell] = terrain.ENTRANCE

        Painter.fill(level, ROOM_LEFT - 1, ROOM_TOP - 1, 11, 11, terrain.EMPTY)

        # Patch 2: 0.30 fill, 3 clustering -> WATER
        patch2 = patch.generate(rng, WIDTH, HEIGHT, 0.30, 3, True)
        for idx in range(level.length()):
            if ((level.map[idx] in (terrain.EMPTY, terrain.STATUE, terrain.REGION_DECO))
                    and patch2[idx]):
                level.map[idx] = terrain.WATER

        # EMPTY_DECO pass (1 in 4)
        for idx in range(level.length()):
            if level.map[idx] == terrain.EMPTY and rng.IntMax(4) == 0:
                level.map[idx] = terrain.EMPTY_DECO

        # Centerpiece painting
        Painter.fill(level, ROOM_LEFT, ROOM_TOP, 9, 9, terrain.EMPTY_SP)
        Painter.fill(level, ROOM_LEFT, ROOM_TOP, 9, 2, terrain.WALL_DECO)
        Painter.fill(level, ROOM_LEFT, ROOM_BOTTOM - 1, 2, 2, terrain.WALL_DECO)
        Painter.fill(level, ROOM_RIGHT - 1, ROOM_BOTTOM - 1, 2, 2, terrain.WALL_DECO)
        Painter.fill(level, ROOM_LEFT + 3, ROOM_TOP + 2, 3, 4, terrain.EMPTY)

        # Custom visual overlays
        level.custom_tiles.append({
            "texture": "halls_special",
            "x": ROOM_LEFT,
            "y": ROOM_TOP + 1,
            "w": 9,
            "h": 8,
            "tiles": get_center_piece_visuals(unsealed=False),
        })

        level.custom_walls.append({
            "texture": "halls_special",
            "x": ROOM_LEFT,
            "y": ROOM_TOP,
            "w": 9,
            "h": 8,
            "tiles": get_center_piece_walls(unsealed=False),
        })

        # REGION_DECO_ALT pass (1 in 2)
        for idx in range(level.length()):
            if level.map[idx] == terrain.REGION_DECO and rng.IntMax(2) == 0:
                level.map[idx] = terrain.REGION_DECO_ALT

        level.exit_cell = exit_cell
        level.entrance_cell = entrance_cell

        # Check path existence from entrance to exit
        passable = [level.map[idx] in terrain.PASSABLE for idx in range(level.length())]
        dist_map = build_distance_map_limited(exit_cell, passable, WIDTH, HEIGHT, WIDTH * HEIGHT)
        if dist_map[entrance_cell] is not None:
            break

    # Setup rooms
    entrance_room = HallsBossEntranceRoom()
    entrance_room.set(ROOM_LEFT, entrance_cell // WIDTH - 2, ROOM_RIGHT + 1, entrance_cell // WIDTH + 1)

    exit_room = HallsBossExitRoom()
    exit_room.set(ROOM_LEFT, ROOM_TOP, ROOM_RIGHT + 1, ROOM_BOTTOM + 1)

    arena_room = YogDzewaBossRoom()
    arena_room.set(4, 2, 29, 29)

    rooms: List[Room] = [entrance_room, exit_room, arena_room]
    level.rooms = rooms
    level.room_entrance = entrance_room
    level.room_exit = exit_room
    level.build_flag_maps()

    # Pre-spawn YogDzewa mob at boss_pos
    level.mobs.append(GenMob(cls_name="YogDzewa", pos=boss_pos))
    level.yog_pos = (boss_pos % WIDTH, boss_pos // WIDTH)

    return level, rooms
