# Copyright (C) 2026 ArtemNikov
#
"""Direct port of the fixed 33x42 layout from levels/CavesBossLevel.java
(DM-300, depth 15): the gate row, ellipse arena, water/wires patch, the
semi-randomized mirrored entrance/corner stamps, the exit area, and the
pylon-reachability validation retry. Follows the prison_boss_layout.py
pattern for fixed layouts.

Deliberate deviations from the Java original (layout-only port):
- DM300 + Pylons are spawned at generation time (Java spawns DM300 in
  seal() at runtime); the DM300 position roll reproduces seal()'s
  Random.element(mainArena.getPoints()) re-roll loop.
- seal()/unseal(), the PylonEnergy blob, and the custom tilemap visuals
  (CityEntrance/EntranceOverhang/ArenaVisuals from caves_boss.png) are not
  ported.
"""

from __future__ import annotations

from app.engine.dungeon.spd_levelgen import patch, terrain
from app.engine.dungeon.spd_levelgen.caves_painter import CavesPainter
from app.engine.dungeon.spd_levelgen.geom import Rect, build_distance_map_limited
from app.engine.dungeon.spd_levelgen.level import Feeling, GenLevel
from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_random import SPDRandom

WIDTH = 33
HEIGHT = 42

DIGGABLE_AREA = Rect(2, 11, 31, 40)
MAIN_ARENA = Rect(5, 14, 28, 37)
GATE = Rect(14, 13, 19, 14)
PYLON_POSITIONS = [4 + 13 * WIDTH, 28 + 13 * WIDTH, 4 + 37 * WIDTH, 28 + 37 * WIDTH]

ENTRANCE_POS = 16 + 25 * WIDTH
EXIT_POS = 16 + 2 * WIDTH

_n = -1  # used when a tile shouldn't be changed
_W = terrain.WALL
_e = terrain.EMPTY
_s = terrain.EMPTY_SP

_entrance1 = [
    _n, _n, _n, _n, _n, _n, _n, _n,
    _n, _n, _n, _n, _n, _n, _n, _n,
    _n, _n, _n, _n, _W, _e, _W, _W,
    _n, _n, _n, _W, _W, _e, _W, _W,
    _n, _n, _W, _W, _e, _e, _e, _e,
    _n, _n, _e, _e, _e, _W, _W, _e,
    _n, _n, _W, _W, _e, _W, _e, _e,
    _n, _n, _W, _W, _e, _e, _e, _e,
]

_entrance2 = [
    _n, _n, _n, _n, _n, _n, _n, _n,
    _n, _n, _n, _n, _n, _n, _n, _n,
    _n, _n, _n, _n, _n, _e, _e, _e,
    _n, _n, _n, _W, _e, _W, _W, _e,
    _n, _n, _n, _e, _e, _e, _e, _e,
    _n, _n, _e, _W, _e, _W, _W, _e,
    _n, _n, _e, _W, _e, _W, _e, _e,
    _n, _n, _e, _e, _e, _e, _e, _e,
]

_entrance3 = [
    _n, _n, _n, _n, _n, _n, _n, _n,
    _n, _n, _n, _n, _n, _n, _n, _n,
    _n, _n, _n, _n, _n, _n, _n, _n,
    _n, _n, _n, _W, _W, _e, _W, _W,
    _n, _n, _n, _W, _W, _e, _W, _W,
    _n, _n, _n, _e, _e, _e, _e, _e,
    _n, _n, _n, _W, _W, _e, _W, _e,
    _n, _n, _n, _W, _W, _e, _e, _e,
]

_entrance4 = [
    _n, _n, _n, _n, _n, _n, _n, _n,
    _n, _n, _n, _n, _n, _n, _n, _e,
    _n, _n, _n, _n, _n, _n, _W, _e,
    _n, _n, _n, _n, _n, _W, _W, _e,
    _n, _n, _n, _n, _W, _W, _W, _e,
    _n, _n, _n, _W, _W, _W, _W, _e,
    _n, _n, _W, _W, _W, _W, _e, _e,
    _n, _e, _e, _e, _e, _e, _e, _e,
]

ENTRANCE_VARIANTS = [_entrance1, _entrance2, _entrance3, _entrance4]

_corner1 = [
    _W, _W, _W, _W, _W, _W, _W, _W, _W, _W,
    _W, _s, _s, _s, _e, _e, _e, _W, _W, _W,
    _W, _s, _s, _s, _W, _W, _e, _e, _W, _W,
    _W, _s, _s, _s, _W, _W, _W, _e, _e, _W,
    _W, _e, _W, _W, _W, _W, _W, _W, _e, _n,
    _W, _e, _W, _W, _W, _W, _W, _n, _n, _n,
    _W, _e, _e, _W, _W, _W, _n, _n, _n, _n,
    _W, _W, _e, _e, _W, _n, _n, _n, _n, _n,
    _W, _W, _W, _e, _e, _n, _n, _n, _n, _n,
    _W, _W, _W, _W, _n, _n, _n, _n, _n, _n,
]

_corner2 = [
    _W, _W, _W, _W, _W, _W, _W, _W, _W, _W,
    _W, _s, _s, _s, _W, _W, _W, _W, _W, _W,
    _W, _s, _s, _s, _e, _e, _e, _e, _e, _W,
    _W, _s, _s, _s, _W, _W, _W, _W, _e, _e,
    _W, _W, _e, _W, _W, _W, _W, _W, _W, _e,
    _W, _W, _e, _W, _W, _W, _W, _n, _n, _n,
    _W, _W, _e, _W, _W, _W, _n, _n, _n, _n,
    _W, _W, _e, _W, _W, _n, _n, _n, _n, _n,
    _W, _W, _e, _e, _W, _n, _n, _n, _n, _n,
    _W, _W, _W, _e, _e, _n, _n, _n, _n, _n,
]

_corner3 = [
    _W, _W, _W, _W, _W, _W, _W, _W, _W, _W,
    _W, _s, _s, _s, _W, _W, _W, _W, _W, _W,
    _W, _s, _s, _s, _e, _e, _e, _e, _W, _W,
    _W, _s, _s, _s, _W, _W, _W, _e, _W, _W,
    _W, _W, _e, _W, _W, _W, _W, _e, _W, _n,
    _W, _W, _e, _W, _W, _W, _W, _e, _e, _n,
    _W, _W, _e, _W, _W, _W, _n, _n, _n, _n,
    _W, _W, _e, _e, _e, _e, _n, _n, _n, _n,
    _W, _W, _W, _W, _W, _e, _n, _n, _n, _n,
    _W, _W, _W, _W, _n, _n, _n, _n, _n, _n,
]

_corner4 = [
    _W, _W, _W, _W, _W, _W, _W, _W, _W, _W,
    _W, _s, _s, _s, _W, _W, _W, _W, _W, _W,
    _W, _s, _s, _s, _e, _e, _e, _W, _W, _W,
    _W, _s, _s, _s, _W, _W, _e, _W, _W, _W,
    _W, _W, _e, _W, _W, _W, _e, _W, _W, _n,
    _W, _W, _e, _W, _W, _W, _e, _e, _n, _n,
    _W, _W, _e, _e, _e, _e, _e, _n, _n, _n,
    _W, _W, _W, _W, _W, _e, _n, _n, _n, _n,
    _W, _W, _W, _W, _W, _n, _n, _n, _n, _n,
    _W, _W, _W, _W, _n, _n, _n, _n, _n, _n,
]

CORNER_VARIANTS = [_corner1, _corner2, _corner3, _corner4]


_OVERHANG_ENTRY_WAY = [
    0, 7, 7, 7, 4,
    0, 15, 15, 15, 4,
    -1, 23, 23, 23, -1,
    -1, -1, -1, -1, -1,
    -1, 6, -1, 14, -1,
    -1, -1, -1, -1, -1,
    -1, 6, -1, 14, -1,
    -1, -1, -1, -1, -1,
    -1, 6, -1, 14, -1,
    -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1,
]

_ENTRY_WAY = [
    -1, 7, 7, 7, -1,
    -1, 1, 2, 3, -1,
    8, 1, 2, 3, 12,
    16, 9, 10, 11, 20,
    16, 16, 18, 20, 20,
    16, 17, 18, 19, 20,
    16, 16, 18, 20, 20,
    16, 17, 18, 19, 20,
    16, 16, 18, 20, 20,
    16, 17, 18, 19, 20,
    24, 25, 26, 27, 28,
]


def create_city_entrance_visuals() -> list[list[int]]:
    """Port of CavesBossLevel.CityEntrance: decorative city entrance floor at rows 0-10."""
    tiles = []
    entry_pos = 0
    for row in range(11):
        tile_row = []
        for col in range(WIDTH):
            if 14 <= col <= 18:
                tile_row.append(_ENTRY_WAY[entry_pos])
                entry_pos += 1
            elif row == 2:
                tile_row.append(13)
            elif row == 3:
                if col in (9, 23):
                    tile_row.append(-1)
                else:
                    tile_row.append(21)
            else:
                tile_row.append(-1)
        tiles.append(tile_row)
    return tiles


def create_entrance_overhang_visuals() -> list[list[int]]:
    """Port of CavesBossLevel.EntranceOverhang: decorative city entrance overhang walls at rows 0-10."""
    tiles = []
    entry_pos = 0
    for row in range(11):
        tile_row = []
        for col in range(WIDTH):
            if 14 <= col <= 18:
                tile_row.append(_OVERHANG_ENTRY_WAY[entry_pos])
                entry_pos += 1
            else:
                tile_row.append(-1)
        tiles.append(tile_row)
    return tiles


def create_arena_visuals(level: GenLevel) -> list[list[int]]:
    """Port of CavesBossLevel.ArenaVisuals: wires (electrical rods), pylon mounts, and gate at rows 12-38."""
    tiles = []
    w = WIDTH
    for row in range(27):
        y = 12 + row
        tile_row = []
        for col in range(WIDTH):
            j = col + y * WIDTH
            t = level.map[j]
            idx = -1
            if t == terrain.EMPTY_SP:
                for k in PYLON_POSITIONS:
                    kx = k % w
                    ky = k // w
                    if max(abs(col - kx), abs(y - ky)) == 1:
                        # 3x3 surrounding conductive metal plate
                        idx = 54 + (col + 8 * y) - (kx + 8 * ky)
                        break
            elif t == terrain.INACTIVE_TRAP:
                idx = 37  # Electrical rod / wire sprite
            elif y == GATE.top and GATE.left <= col < GATE.right:
                idx = 40 + (col - GATE.left)  # Closed gate row
            tile_row.append(idx)
        tiles.append(tile_row)
    return tiles


def _build_entrance(rng: SPDRandom, level: GenLevel) -> None:
    """Port of CavesBossLevel.buildEntrance() -- a random 8x8 variant stamped
    4-way mirrored around the fixed entrance cell."""
    w = level.width()
    entrance = 16 + 25 * w

    NW = entrance - 7 - 7 * w
    NE = entrance + 7 - 7 * w
    SE = entrance + 7 + 7 * w
    SW = entrance - 7 + 7 * w

    entrance_tiles = rng.element(ENTRANCE_VARIANTS)
    for i in range(len(entrance_tiles)):
        if i % 8 == 0 and i != 0:
            NW += w - 8
            NE += w + 8
            SE -= w - 8
            SW -= w + 8

        if entrance_tiles[i] != _n:
            level.map[NW] = level.map[NE] = level.map[SE] = level.map[SW] = entrance_tiles[i]
        NW += 1
        NE -= 1
        SW += 1
        SE -= 1

    Painter.set(level, entrance, terrain.ENTRANCE)


def _build_corners(rng: SPDRandom, level: GenLevel) -> None:
    """Port of CavesBossLevel.buildCorners() -- a random 10x10 variant stamped
    4-way mirrored into the arena corners (the EMPTY_SP 3x3 blocks land on
    the pylon positions)."""
    w = level.width()

    NW = 2 + 11 * w
    NE = 30 + 11 * w
    SE = 30 + 39 * w
    SW = 2 + 39 * w

    corner_tiles = rng.element(CORNER_VARIANTS)
    for i in range(len(corner_tiles)):
        if i % 10 == 0 and i != 0:
            NW += w - 10
            NE += w + 10
            SE -= w - 10
            SW -= w + 10

        if corner_tiles[i] != _n:
            level.map[NW] = level.map[NE] = level.map[SE] = level.map[SW] = corner_tiles[i]
        NW += 1
        NE -= 1
        SW += 1
        SE -= 1


def _build(rng: SPDRandom, depth: int, challenged: bool) -> GenLevel:
    """Port of CavesBossLevel.build(). Returns None-equivalent by raising --
    callers use build() which wraps this in the Level.create() retry loop."""
    level = GenLevel(depth, Feeling.NONE)
    level.set_size(WIDTH, HEIGHT)

    Painter.fill(level, GATE, terrain.CUSTOM_DECO)

    # set up main boss arena
    Painter.fill_ellipse(level, MAIN_ARENA, terrain.EMPTY)

    water_patch = patch.generate(rng, WIDTH, HEIGHT - 14, 0.15, 2, True)
    for i in range(14 * WIDTH, level.length()):
        if level.map[i] == terrain.EMPTY:
            if water_patch[i - 14 * WIDTH]:
                level.map[i] = terrain.WATER
            elif rng.IntMax(4 if challenged else 8) == 0:
                level.map[i] = terrain.INACTIVE_TRAP

    _build_entrance(rng, level)
    _build_corners(rng, level)

    CavesPainter().paint(rng, level, None)

    # setup exit area above main boss arena
    Painter.fill(level, 0, 3, WIDTH, 4, terrain.CHASM)
    Painter.fill(level, 6, 7, 21, 1, terrain.CHASM)
    Painter.fill(level, 9, 3, 1, 6, terrain.REGION_DECO_ALT)
    Painter.fill(level, 23, 3, 1, 6, terrain.REGION_DECO_ALT)
    Painter.fill(level, 10, 8, 13, 1, terrain.CHASM)
    Painter.fill(level, 12, 9, 9, 1, terrain.CHASM)
    Painter.fill(level, 13, 10, 7, 1, terrain.CHASM)
    Painter.fill(level, 14, 3, 5, 10, terrain.EMPTY)

    # fill in special floor, statues, and exits
    Painter.fill(level, 15, 2, 3, 3, terrain.EMPTY_SP)
    Painter.fill(level, 15, 5, 3, 1, terrain.STATUE)
    Painter.fill(level, 15, 7, 3, 1, terrain.STATUE)
    Painter.fill(level, 15, 9, 3, 1, terrain.STATUE)
    Painter.fill(level, 16, 5, 1, 6, terrain.EMPTY_SP)
    Painter.fill(level, 15, 0, 3, 3, terrain.EXIT)

    # Custom Tilemaps (CityEntrance, EntranceOverhang, ArenaVisuals / wires)
    level.custom_tiles.append({
        "texture": "caves_boss",
        "x": 0,
        "y": 0,
        "w": WIDTH,
        "h": 11,
        "tiles": create_city_entrance_visuals(),
    })

    level.custom_walls.append({
        "texture": "caves_boss",
        "x": 0,
        "y": 0,
        "w": WIDTH,
        "h": 11,
        "tiles": create_entrance_overhang_visuals(),
    })

    level.custom_tiles.append({
        "texture": "caves_boss",
        "x": 0,
        "y": 12,
        "w": WIDTH,
        "h": 27,
        "tiles": create_arena_visuals(level),
    })

    # ensures that all pylons can be reached without stepping over water or wires
    passable = [
        tile in (terrain.EMPTY, terrain.EMPTY_SP, terrain.EMPTY_DECO)
        for tile in level.map
    ]
    distance = build_distance_map_limited(16 + 25 * WIDTH, passable, WIDTH, HEIGHT, WIDTH * HEIGHT)
    for pos in PYLON_POSITIONS:
        if distance[pos] is None:
            raise _BuildFailed

    return level


class _BuildFailed(Exception):
    """CavesBossLevel.build() returning false -- Level.create() re-rolls."""


def _spawn_mobs(rng: SPDRandom, level: GenLevel) -> None:
    """Port of CavesBossLevel.createMobs() (4 fixed pylons) plus the DM300
    position roll from seal() (Random.element(mainArena.getPoints()),
    re-rolled while not open space / EMPTY_SP / occupied). Requires
    build_flag_maps() to have run (open_space)."""
    for pos in PYLON_POSITIONS:
        level.mobs.append(GenMob(cls_name="Pylon", pos=pos))

    arena_points = MAIN_ARENA.get_points()
    while True:
        pos = level.point_to_cell(rng.element(arena_points))
        if (level.open_space[pos]
                and level.map[pos] != terrain.EMPTY_SP
                and level.find_mob(pos) is None):
            break
    level.mobs.append(GenMob(cls_name="DM300", pos=pos))


def build(rng: SPDRandom, depth: int, challenged: bool = False) -> GenLevel:
    """Port of CavesBossLevel's Level.create() sequence: do { build() } while
    the pylon-reachability validation fails, then flag maps + mobs."""
    while True:
        try:
            level = _build(rng, depth, challenged)
            break
        except _BuildFailed:
            continue

    level.build_flag_maps()
    _spawn_mobs(rng, level)
    return level
