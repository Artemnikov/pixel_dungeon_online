# Copyright (C) 2026 ArtemNikov
#
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.dungeon.spd_levelgen import city_boss_layout as layout
from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.run_state import RunState
from app.engine.dungeon.spd_random import SPDRandom
from app.engine.entities.mobs import DwarfKing, Shopkeeper
from app.engine.manager import GameInstance


def make_level(seed: int = 123456789, quest_completed: bool = False):
    rng = SPDRandom()
    rng.push_generator(seed)
    rs = RunState()
    rs.imp_quest.completed = quest_completed
    level, rooms = layout.build(rng, 20, rs)
    rng.pop_generator()
    return level, rooms


def test_level_dimensions_and_positions():
    level, rooms = make_level()
    assert level.width() == 15
    assert level.height() == 48

    # Entrance and exit
    entrance_cell = layout.ENTRANCE_POS.x + layout.ENTRANCE_POS.y * layout.WIDTH
    assert level.map[entrance_cell] == terrain.ENTRANCE
    assert layout.ENTRANCE_POS.x == 7
    assert layout.ENTRANCE_POS.y == 44

    exit_cell = layout.EXIT_POS.x + layout.EXIT_POS.y * layout.WIDTH
    assert level.map[exit_cell] == terrain.EXIT
    assert layout.EXIT_POS.x == 7
    assert layout.EXIT_POS.y == 8

    # Throne position
    throne_cell = layout.THRONE_POS.x + layout.THRONE_POS.y * layout.WIDTH
    assert level.map[throne_cell] == terrain.CUSTOM_DECO
    assert layout.THRONE_POS.x == 7
    assert layout.THRONE_POS.y == 31


def test_entrance_hall_layout():
    level, rooms = make_level()
    m = level.map
    w = layout.WIDTH

    # Bookshelves on perimeter
    for y in range(38, 47):
        assert m[2 + y * w] == terrain.BOOKSHELF
        assert m[12 + y * w] == terrain.BOOKSHELF

    # Interior bookshelves
    for y in range(40, 45):
        assert m[4 + y * w] == terrain.BOOKSHELF
        assert m[10 + y * w] == terrain.BOOKSHELF

    # Statues flanking carpet
    for y in (40, 42, 44):
        assert m[6 + y * w] == terrain.STATUE
        assert m[8 + y * w] == terrain.STATUE

    # Central red carpet (EMPTY_SP)
    for y in range(38, 44):
        assert m[7 + y * w] == terrain.EMPTY_SP

    # Connecting door to arena
    assert m[7 + 37 * w] == terrain.DOOR


def test_throne_room_arena_layout():
    level, rooms = make_level()
    m = level.map
    w = layout.WIDTH

    # Throne and 3x3 surrounding carpet
    assert m[7 + 31 * w] == terrain.CUSTOM_DECO
    for y in range(30, 33):
        for x in range(6, 9):
            if (x, y) == (7, 31):
                continue
            assert m[x + y * w] == terrain.EMPTY_SP

    # 4 summon pedestals
    for px, py in layout.PEDESTAL_POSITIONS:
        assert m[px + py * w] == terrain.PEDESTAL

    assert layout.PEDESTAL_POSITIONS == [(4, 28), (10, 28), (10, 34), (4, 34)]

    # Flanking statues
    for x in (3, 4, 10, 11):
        assert m[x + 31 * w] == terrain.STATUE

    # Locked north door to exit chasm
    assert m[7 + 25 * w] == terrain.LOCKED_DOOR


def test_exit_hallway_layout():
    level, rooms = make_level()
    m = level.map
    w = layout.WIDTH

    # Chasm on sides
    assert m[0 + 10 * w] == terrain.CHASM
    assert m[14 + 10 * w] == terrain.CHASM

    # Grand exit staircase
    for y in range(5, 9):
        for x in range(4, 11):
            assert m[x + y * w] == terrain.EXIT

    # Walkway
    for y in range(9, 23):
        for x in range(4, 11):
            assert m[x + y * w] in (terrain.EMPTY, terrain.EMPTY_DECO, terrain.PEDESTAL, terrain.STATUE)

    # Imp shop pedestal and statues
    assert m[7 + 16 * w] == terrain.PEDESTAL
    assert m[5 + 12 * w] == terrain.STATUE
    assert m[9 + 12 * w] == terrain.STATUE

    # Chasm pillars
    for x in (1, 12):
        for y in (2, 7, 12, 17):
            assert m[x + y * w] == terrain.WALL
            assert m[x + 1 + y * w] == terrain.WALL
            assert m[x + (y + 1) * w] == terrain.WALL
            assert m[x + 1 + (y + 1) * w] == terrain.WALL


def test_custom_tilemap_overlays():
    level, rooms = make_level()

    assert len(level.custom_tiles) == 1
    ground = level.custom_tiles[0]
    assert ground["texture"] == "city_boss"
    assert ground["w"] == 15
    assert ground["h"] == 48
    assert len(ground["tiles"]) == 48
    assert all(len(row) == 15 for row in ground["tiles"])

    assert len(level.custom_walls) == 1
    walls = level.custom_walls[0]
    assert walls["texture"] == "city_boss"
    assert walls["w"] == 15
    assert walls["h"] == 48
    assert len(walls["tiles"]) == 48
    assert all(len(row) == 15 for row in walls["tiles"])


def test_dwarf_king_mob_and_summon_spots():
    level, rooms = make_level()

    dk = [mob for mob in level.mobs if mob.cls_name == "DwarfKing"]
    assert len(dk) == 1
    assert dk[0].pos == 7 + 31 * layout.WIDTH
    assert level.dk_summon_spots == layout.PEDESTAL_POSITIONS


def test_imp_shop_pending_vs_completed():
    level_pending, _ = make_level(quest_completed=False)
    assert hasattr(level_pending, "imp_shop_room")
    assert level_pending.imp_shop_room is not None
    assert not any(m.cls_name == "Shopkeeper" for m in level_pending.mobs)

    level_done, _ = make_level(quest_completed=True)
    assert any(m.cls_name == "Shopkeeper" for m in level_done.mobs)


def test_game_instance_floor_20_generation():
    game = GameInstance("test-city-boss-full")
    floor = game._get_or_create_floor(20)

    assert floor.region == "city"
    assert floor.entrance_pos == (7, 44)
    assert len(floor.grid) == 48
    assert len(floor.grid[0]) == 15

    # DwarfKing spawned on floor
    dk = [m for m in floor.mobs.values() if isinstance(m, DwarfKing)]
    assert len(dk) == 1
    assert (dk[0].pos.x, dk[0].pos.y) == (7, 31)

    # Summon spots set
    assert floor.dk_summon_spots == [(4, 28), (10, 28), (10, 34), (4, 34)]

    # Custom tilemaps attached
    assert len(floor.custom_tiles) == 1
    assert floor.custom_tiles[0]["texture"] == "city_boss"
    assert len(floor.custom_walls) == 1
    assert floor.custom_walls[0]["texture"] == "city_boss"
