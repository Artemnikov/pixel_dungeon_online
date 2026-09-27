# Copyright (C) 2026 ArtemNikov
#
"""Direct port of the fixed 15x48 layout from levels/CityBossLevel.java
(Dwarf King, depth 20): entrance library, diamond throne arena with 4 summon
pedestals, exit chasm walkway, grand exit staircase, ImpShopRoom, and the
custom ground/wall tilemap overlays from custom_tiles/city_boss.png. Follows
the caves_boss_layout.py / prison_boss_layout.py pattern for fixed layouts.
"""

from __future__ import annotations

from typing import List, Tuple

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.city_painter import CityPainter
from app.engine.dungeon.spd_levelgen.geom import Point, Rect
from app.engine.dungeon.spd_levelgen.level import Feeling, GenLevel
from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import Room
from app.engine.dungeon.spd_levelgen.room_types import ImpShopRoom, _place_shop_items
from app.engine.dungeon.spd_levelgen.run_state import RunState
from app.engine.dungeon.spd_levelgen.shop_items import shop_room_item_list
from app.engine.dungeon.spd_random import SPDRandom

WIDTH = 15
HEIGHT = 48

ENTRY_RECT = Rect(1, 37, 14, 48)
ARENA_RECT = Rect(1, 25, 14, 38)
END_RECT = Rect(0, 0, 15, 22)

BOTTOM_DOOR = Point(7, 37)  # 7 + (ARENA_RECT.bottom - 1) * WIDTH
TOP_DOOR = Point(7, 25)     # 7 + ARENA_RECT.top * WIDTH

THRONE_POS = Point(7, 31)   # arena center: Point(7, 31)
PEDESTAL_POSITIONS = [(4, 28), (10, 28), (10, 34), (4, 34)]

ENTRANCE_POS = Point(7, 44)  # entry center c=(7,42) -> c.x + (c.y+2)*WIDTH
EXIT_POS = Point(7, 8)       # end.left+7 + (end.top+8)*WIDTH


class CityBossEntranceRoom(Room):
    """Marks the entrance library room rect (1, 37, 14, 48)."""

    def is_entrance(self) -> bool:
        return True


class CityBossExitRoom(Room):
    """Marks the exit hallway / grand stairs rect (0, 0, 15, 22)."""

    def is_exit(self) -> bool:
        return True


class DwarfKingBossRoom(Room):
    """Marks the Dwarf King's throne room arena rect (1, 25, 14, 38)."""
    pass


def create_ground_visuals(level: GenLevel) -> list[list[int]]:
    """Port of CityBossLevel.CustomGroundVisuals."""
    tile_w = WIDTH
    tile_h = HEIGHT
    data = [-1] * (tile_w * tile_h)
    m = level.map

    stairs_top = -1

    # upper part of the level, mostly demon halls tiles
    i = tile_w
    while i < tile_w * 22:
        if m[i] == terrain.EXIT and stairs_top == -1:
            stairs_top = i

        # pillars
        if m[i] == terrain.WALL and m[i - tile_w] == terrain.CHASM:
            data[i] = 13 * 8 + 6
            data[i + 1] = 13 * 8 + 7
            i += 1
        elif m[i] == terrain.WALL and m[i - tile_w] == terrain.WALL:
            data[i] = 14 * 8 + 6
            data[i + 1] = 14 * 8 + 7
            i += 1
        elif i > tile_w and m[i] == terrain.CHASM and m[i - tile_w] == terrain.WALL:
            data[i] = 15 * 8 + 6
            data[i + 1] = 15 * 8 + 7
            i += 1
        # imp's pedestal
        elif m[i] == terrain.PEDESTAL:
            data[i] = 12 * 8 + 5
        # skull piles
        elif m[i] == terrain.STATUE:
            data[i] = 15 * 8 + 5
        # ground tiles
        elif m[i] in (terrain.EMPTY, terrain.EMPTY_DECO, terrain.EMBERS,
                      terrain.GRASS, terrain.HIGH_GRASS, terrain.FURROWED_GRASS):
            # final ground stitching with city tiles
            if i // tile_w == 21:
                data[i] = 11 * 8 + 0
                data[i + 1] = 11 * 8 + 1
                data[i + 2] = 11 * 8 + 2
                data[i + 3] = 11 * 8 + 3
                data[i + 4] = 11 * 8 + 4
                data[i + 5] = 11 * 8 + 5
                data[i + 6] = 11 * 8 + 6
                i += 6
            else:
                # regular ground tiles
                if m[i - 1] == terrain.CHASM:
                    data[i] = 12 * 8 + 1
                elif m[i + 1] == terrain.CHASM:
                    data[i] = 12 * 8 + 3
                elif m[i] == terrain.EMPTY_DECO:
                    data[i] = 12 * 8 + 4
                else:
                    data[i] = 12 * 8 + 2
        else:
            data[i] = -1
        i += 1

    # custom for stairs (7 rows x 7 cols)
    if stairs_top != -1:
        st = stairs_top
        for row in range(7):
            for col in range(7):
                data[st + col] = (row + 4) * 8 + col
            st += tile_w

    # lower part: statues, pedestals, and carpets
    i = tile_w * 22
    while i < tile_w * tile_h:
        # pedestal spawners
        if m[i] == terrain.PEDESTAL:
            data[i] = 13 * 8 + 4
        # statues that should face left instead of right
        elif m[i] == terrain.STATUE and (i % tile_w) > 7:
            data[i] = 15 * 8 + 4
        # carpet tiles
        elif m[i] == terrain.EMPTY_SP:
            # top row of DK's throne
            if m[i + 1] == terrain.EMPTY_SP and m[i + tile_w] == terrain.EMPTY_SP:
                data[i] = 13 * 8 + 1
                data[i + 1] = 13 * 8 + 2
                data[i + 2] = 13 * 8 + 3
                i += 2
            # mid row of DK's throne
            elif m[i + 1] == terrain.CUSTOM_DECO:
                data[i] = 14 * 8 + 1
                data[i + 1] = 14 * 8 + 2
                data[i + 2] = 14 * 8 + 3
                i += 2
            # bottom row of DK's throne
            elif m[i + 1] == terrain.EMPTY_SP and m[i - tile_w] == terrain.EMPTY_SP:
                data[i] = 15 * 8 + 1
                data[i + 1] = 15 * 8 + 2
                data[i + 2] = 15 * 8 + 3
                i += 2
            # otherwise entrance carpet
            elif m[i - tile_w] != terrain.EMPTY_SP:
                data[i] = 13 * 8 + 0
            elif m[i + tile_w] != terrain.EMPTY_SP:
                data[i] = 15 * 8 + 0
            else:
                data[i] = 14 * 8 + 0
        else:
            data[i] = -1
        i += 1

    return [data[r * tile_w : (r + 1) * tile_w] for r in range(tile_h)]


def create_wall_visuals(level: GenLevel) -> list[list[int]]:
    """Port of CityBossLevel.CustomWallVisuals."""
    tile_w = WIDTH
    tile_h = HEIGHT
    data = [-1] * (tile_w * tile_h)
    m = level.map

    shadow_top = -1

    # upper part of the level, mostly demon halls tiles
    i = tile_w
    while i < tile_w * 21:
        if m[i] == terrain.EXIT and shadow_top == -1:
            shadow_top = i - tile_w * 4

        # pillars
        if m[i] == terrain.CHASM and m[i + tile_w] == terrain.WALL:
            data[i] = 12 * 8 + 6
            data[i + 1] = 12 * 8 + 7
            i += 1
        elif m[i] == terrain.WALL and m[i - tile_w] == terrain.CHASM:
            data[i] = 13 * 8 + 6
            data[i + 1] = 13 * 8 + 7
            i += 1
        # skull tops
        elif m[i + tile_w] == terrain.STATUE:
            data[i] = 14 * 8 + 5
        else:
            data[i] = -1
        i += 1

    # custom shadow for stairs
    if shadow_top != -1:
        st = shadow_top
        for row in range(8):
            if row < 4:
                data[st] = row * 8 + 0
                for c in range(1, 7):
                    data[st + c] = row * 8 + 1
                data[st + 7] = row * 8 + 2
            else:
                j = row - 4
                data[st] = j * 8 + 3
                for c in range(1, 7):
                    data[st + c] = j * 8 + 4
                data[st + 7] = j * 8 + 5
            st += tile_w

    # lower part: statues and DK's throne
    for i in range(tile_w * 21, tile_w * tile_h):
        if m[i] == terrain.STATUE and (i % tile_w) > 7:
            data[i - tile_w] = 14 * 8 + 4
        elif m[i] == terrain.CUSTOM_DECO:
            data[i - tile_w] = 13 * 8 + 5
        data[i] = -1

    return [data[r * tile_w : (r + 1) * tile_w] for r in range(tile_h)]


def build(rng: SPDRandom, depth: int, run_state: RunState) -> Tuple[GenLevel, List[Room]]:
    """Port of CityBossLevel.build()."""
    level = GenLevel(depth, Feeling.NONE)
    level.run_state = run_state
    level.set_size(WIDTH, HEIGHT)

    Painter.fill(level, 0, 0, WIDTH, HEIGHT, terrain.WALL)

    # 1. Entrance Room (Rect(1, 37, 14, 48))
    Painter.fill(level, ENTRY_RECT, terrain.WALL)
    Painter.fill(level, ENTRY_RECT, 1, terrain.BOOKSHELF)
    Painter.fill(level, ENTRY_RECT, 2, terrain.EMPTY)

    Painter.fill(level, ENTRY_RECT.left + 3, ENTRY_RECT.top + 3, 1, 5, terrain.BOOKSHELF)
    Painter.fill(level, ENTRY_RECT.right - 4, ENTRY_RECT.top + 3, 1, 5, terrain.BOOKSHELF)

    Painter.set(level, ENTRY_RECT.left + 5, ENTRY_RECT.top + 1, terrain.REGION_DECO)
    Painter.set(level, ENTRY_RECT.left + 7, ENTRY_RECT.top + 1, terrain.REGION_DECO)

    c_entry = Point(7, 42)
    Painter.fill(level, c_entry.x - 1, c_entry.y - 2, 3, 1, terrain.STATUE)
    Painter.fill(level, c_entry.x - 1, c_entry.y, 3, 1, terrain.STATUE)
    Painter.fill(level, c_entry.x - 1, c_entry.y + 2, 3, 1, terrain.STATUE)
    Painter.fill(level, c_entry.x, ENTRY_RECT.top + 1, 1, 6, terrain.EMPTY_SP)

    Painter.set(level, BOTTOM_DOOR, terrain.DOOR)
    Painter.set(level, ENTRANCE_POS, terrain.ENTRANCE)

    # 2. Dwarf King's Throne Room (Arena) (Rect(1, 25, 14, 38))
    Painter.fill_diamond(level, ARENA_RECT, 1, terrain.EMPTY)
    Painter.fill(level, ARENA_RECT, 5, terrain.EMPTY_SP)
    Painter.fill(level, ARENA_RECT, 6, terrain.CUSTOM_DECO)

    c_arena = THRONE_POS
    Painter.set(level, c_arena.x - 3, c_arena.y, terrain.STATUE)
    Painter.set(level, c_arena.x - 4, c_arena.y, terrain.STATUE)
    Painter.set(level, c_arena.x + 3, c_arena.y, terrain.STATUE)
    Painter.set(level, c_arena.x + 4, c_arena.y, terrain.STATUE)

    for px, py in PEDESTAL_POSITIONS:
        Painter.set(level, px, py, terrain.PEDESTAL)

    Painter.set(level, TOP_DOOR, terrain.LOCKED_DOOR)

    # 3. Exit Hallway (Rect(0, 0, 15, 22))
    Painter.fill(level, END_RECT, terrain.CHASM)
    Painter.fill(level, END_RECT.left + 4, END_RECT.top + 5, 7, 18, terrain.EMPTY)
    Painter.fill(level, END_RECT.left + 4, END_RECT.top + 5, 7, 4, terrain.EXIT)

    imp_shop = ImpShopRoom()
    imp_shop.set(END_RECT.left + 3, END_RECT.top + 12, END_RECT.left + 11, END_RECT.top + 20)
    Painter.set(level, imp_shop.center(rng), terrain.PEDESTAL)

    Painter.set(level, imp_shop.left + 2, imp_shop.top, terrain.STATUE)
    Painter.set(level, imp_shop.left + 6, imp_shop.top, terrain.STATUE)

    Painter.fill(level, END_RECT.left + 5, END_RECT.bottom + 1, 5, 1, terrain.EMPTY)
    Painter.fill(level, END_RECT.left + 6, END_RECT.bottom + 2, 3, 1, terrain.EMPTY)

    # 4. Decorate using CityPainter
    CityPainter(depth).paint(rng, level, None)

    # 5. Pillars (painted last, no deco on these)
    Painter.fill(level, END_RECT.left + 1, END_RECT.top + 2, 2, 2, terrain.WALL)
    Painter.fill(level, END_RECT.left + 1, END_RECT.top + 7, 2, 2, terrain.WALL)
    Painter.fill(level, END_RECT.left + 1, END_RECT.top + 12, 2, 2, terrain.WALL)
    Painter.fill(level, END_RECT.left + 1, END_RECT.top + 17, 2, 2, terrain.WALL)

    Painter.fill(level, END_RECT.right - 3, END_RECT.top + 2, 2, 2, terrain.WALL)
    Painter.fill(level, END_RECT.right - 3, END_RECT.top + 7, 2, 2, terrain.WALL)
    Painter.fill(level, END_RECT.right - 3, END_RECT.top + 12, 2, 2, terrain.WALL)
    Painter.fill(level, END_RECT.right - 3, END_RECT.top + 17, 2, 2, terrain.WALL)

    # 6. Custom Tilemaps
    level.custom_tiles.append({
        "texture": "city_boss",
        "x": 0,
        "y": 0,
        "w": WIDTH,
        "h": HEIGHT,
        "tiles": create_ground_visuals(level),
    })

    level.custom_walls.append({
        "texture": "city_boss",
        "x": 0,
        "y": 0,
        "w": WIDTH,
        "h": HEIGHT,
        "tiles": create_wall_visuals(level),
    })

    # 7. Rooms
    entrance_room = CityBossEntranceRoom()
    entrance_room.set(ENTRY_RECT.left, ENTRY_RECT.top, ENTRY_RECT.right, ENTRY_RECT.bottom)

    arena_room = DwarfKingBossRoom()
    arena_room.set(ARENA_RECT.left, ARENA_RECT.top, ARENA_RECT.right, ARENA_RECT.bottom)

    exit_room = CityBossExitRoom()
    exit_room.set(END_RECT.left, END_RECT.top, END_RECT.right, END_RECT.bottom)

    rooms: List[Room] = [entrance_room, arena_room, exit_room, imp_shop]

    level.rooms = rooms
    level.room_entrance = entrance_room
    level.room_exit = exit_room
    level.build_flag_maps()

    # 8. Dwarf King Mob & summon spots
    dk_pos = level.point_to_cell(THRONE_POS)
    level.mobs.append(GenMob(cls_name="DwarfKing", pos=dk_pos))
    level.dk_summon_spots = list(PEDESTAL_POSITIONS)

    # 9. Imp Shop Items & Shopkeeper
    items = shop_room_item_list(rng, depth)
    if run_state.imp_quest.completed:
        shop_pos = level.point_to_cell(imp_shop.center(rng))
        level.mobs.append(GenMob(cls_name="Shopkeeper", pos=shop_pos))
        _place_shop_items(level, imp_shop, items)
    else:
        ent = imp_shop.entrance()
        ent_x = ent.x if ent else (imp_shop.left + imp_shop.right) // 2 + 1
        ent_y = ent.y if ent else imp_shop.bottom - 1
        level.imp_shop_room = {
            "left": imp_shop.left,
            "top": imp_shop.top,
            "right": imp_shop.right,
            "bottom": imp_shop.bottom,
            "entrance": (ent_x, ent_y),
            "items": items,
        }

    return level, rooms
