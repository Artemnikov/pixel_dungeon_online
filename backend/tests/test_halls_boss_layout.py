# Copyright (C) 2026 ArtemNikov
#
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.dungeon.constants import TileType
from app.engine.dungeon.spd_levelgen import halls_boss_layout as layout
from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.run_state import RunState
from app.engine.dungeon.spd_random import SPDRandom
from app.engine.entities.mobs import YogDzewa
from app.engine.manager import GameInstance


def make_level(seed: int = 123456789):
    rng = SPDRandom()
    rng.push_generator(seed)
    rs = RunState()
    level, rooms = layout.build(rng, 25, rs)
    rng.pop_generator()
    return level, rooms


def test_level_dimensions_and_positions():
    level, rooms = make_level()
    assert level.width() == 32
    assert level.height() == 32

    # Entrance is at (16, bottom-1) where bottom is in [24..28]
    ent_cell = level.entrance()
    ex = ent_cell % 32
    ey = ent_cell // 32
    assert ex == 16
    assert 23 <= ey <= 27
    assert level.map[ent_cell] == terrain.ENTRANCE

    # Exit is at (16, 9)
    exit_cell = level.exit()
    assert exit_cell == 16 + 9 * 32
    assert exit_cell % 32 == 16
    assert exit_cell // 32 == 9

    # Yog pos is at (16, 12)
    assert level.yog_pos == (16, 12)
    yog_mob = next(m for m in level.mobs if m.cls_name == "YogDzewa")
    assert yog_mob.pos == 16 + 12 * 32


def test_custom_tilemaps():
    level, rooms = make_level()
    assert len(level.custom_tiles) == 1
    vis = level.custom_tiles[0]
    assert vis["texture"] == "halls_special"
    assert vis["x"] == 12
    assert vis["y"] == 9
    assert vis["w"] == 9
    assert vis["h"] == 8
    assert vis["tiles"][0][0] == 8
    assert vis["tiles"][0][4] == 11

    assert len(level.custom_walls) == 1
    walls = level.custom_walls[0]
    assert walls["texture"] == "halls_special"
    assert walls["x"] == 12
    assert walls["y"] == 8
    assert walls["w"] == 9
    assert walls["h"] == 8
    assert walls["tiles"][6][0] == 32


def test_floor_state_generation():
    game = GameInstance("test-halls-boss-floor")
    floor = game.generate_floor(25)

    assert floor.width == 32
    assert floor.height == 32
    assert floor.region == "halls"
    assert floor.entrance_pos is not None
    assert floor.entrance_pos[0] == 16
    assert floor.exit_pos == (16, 9)

    yog = next(m for m in floor.mobs.values() if isinstance(m, YogDzewa))
    assert yog.pos.x == 16
    assert yog.pos.y == 12

    assert len(floor.custom_tiles) == 1
    assert floor.custom_tiles[0]["texture"] == "halls_special"
    assert len(floor.custom_walls) == 1
    assert floor.custom_walls[0]["texture"] == "halls_special"


def test_seed_determinism():
    l1, _ = make_level(42)
    l2, _ = make_level(42)
    assert l1.map == l2.map
    assert l1.entrance() == l2.entrance()
    assert l1.exit() == l2.exit()
