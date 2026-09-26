import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.dungeon.constants import TileType
from app.engine.dungeon.spd_levelgen import caves_boss_layout as layout
from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.geom import build_distance_map_limited
from app.engine.dungeon.spd_random import SPDRandom
from app.engine.entities.mobs import DM300, Pylon
from app.engine.manager import GameInstance


def make_level(seed: int = 123456789, challenged: bool = False):
    rng = SPDRandom()
    rng.push_generator(seed)
    level = layout.build(rng, 15, challenged)
    rng.pop_generator()
    return level


def make_game():
    game = GameInstance("test-caves-boss")
    game.players = {}
    floor = game.generate_floor(15)
    return game, floor


def test_level_dimensions_and_feeling():
    level = make_level()
    assert level.width() == 33
    assert level.height() == 42


def test_entrance_and_exit_cells():
    level = make_level()
    assert level.map[layout.ENTRANCE_POS] == terrain.ENTRANCE
    assert level.entrance() == layout.ENTRANCE_POS
    # 3x3 EXIT block at (15..17, 0..2); exit() scans the first cell
    for y in range(3):
        for x in range(15, 18):
            assert level.map[x + y * layout.WIDTH] == terrain.EXIT
    assert level.exit() == 15


def test_gate_row_is_closed_custom_deco():
    level = make_level()
    for x in range(14, 19):
        assert level.map[x + 13 * layout.WIDTH] == terrain.CUSTOM_DECO


def test_exit_area_terrain():
    level = make_level()
    m = level.map
    w = layout.WIDTH
    # full-width chasm band rows 3-6 outside the shaft/pillars
    assert m[0 + 3 * w] == terrain.CHASM
    assert m[32 + 6 * w] == terrain.CHASM
    # metal pillar columns
    for y in range(3, 9):
        assert m[9 + y * w] == terrain.REGION_DECO_ALT
        assert m[23 + y * w] == terrain.REGION_DECO_ALT
    # stepped chasm funnel
    assert m[10 + 8 * w] == terrain.CHASM
    assert m[22 + 8 * w] == terrain.CHASM
    assert m[12 + 9 * w] == terrain.CHASM
    assert m[13 + 10 * w] == terrain.CHASM
    # statue-lined corridor
    for x in (15, 17):
        for y in (5, 7, 9):
            assert m[x + y * w] == terrain.STATUE
    assert m[16 + 5 * w] == terrain.EMPTY_SP
    assert m[16 + 10 * w] == terrain.EMPTY_SP
    # vertical shaft connecting exit area to the gate row
    for y in range(3, 13):
        for x in range(14, 19):
            if x == 16:
                continue  # EMPTY_SP corridor column
            assert m[x + y * w] in (terrain.EMPTY, terrain.EMPTY_SP, terrain.STATUE)


def test_arena_ellipse_and_patch():
    level = make_level()
    m = level.map
    w = layout.WIDTH
    # center of the ellipse arena is open
    assert m[16 + 25 * w] == terrain.ENTRANCE
    # outside the arena ellipse (mid-left of the map edge) stays solid
    assert m[0 + 25 * w] == terrain.WALL
    # the water/wires patch produces some water and some wires in the arena
    arena_tiles = [m[x + y * w] for y in range(14, 42) for x in range(33)]
    assert terrain.WATER in arena_tiles
    assert terrain.INACTIVE_TRAP in arena_tiles


def test_pylon_positions_have_empty_sp():
    level = make_level()
    for pos in layout.PYLON_POSITIONS:
        assert level.map[pos] == terrain.EMPTY_SP
    pylons = [mob for mob in level.mobs if mob.cls_name == "Pylon"]
    assert sorted(mob.pos for mob in pylons) == sorted(layout.PYLON_POSITIONS)


def test_dm300_spawned_in_open_arena_cell():
    for seed in (1, 42, 123456789, 987654321):
        level = make_level(seed)
        dm300 = [mob for mob in level.mobs if mob.cls_name == "DM300"]
        assert len(dm300) == 1
        pos = dm300[0].pos
        x, y = pos % layout.WIDTH, pos // layout.WIDTH
        assert 5 <= x <= 28 and 14 <= y <= 37
        assert level.open_space[pos]
        assert level.map[pos] != terrain.EMPTY_SP


def test_pylons_reachable_from_entrance():
    for seed in (1, 7, 42, 123456789, 987654321):
        level = make_level(seed)
        passable = [
            tile in (terrain.EMPTY, terrain.EMPTY_SP, terrain.EMPTY_DECO)
            for tile in level.map
        ]
        distance = build_distance_map_limited(
            layout.ENTRANCE_POS, passable, layout.WIDTH, layout.HEIGHT,
            layout.WIDTH * layout.HEIGHT)
        for pos in layout.PYLON_POSITIONS:
            assert distance[pos] is not None


def test_generation_is_deterministic_per_seed():
    a = make_level(2026)
    b = make_level(2026)
    assert a.map == b.map
    assert [(m.cls_name, m.pos) for m in a.mobs] == [(m.cls_name, m.pos) for m in b.mobs]


def test_challenged_build_also_valid():
    level = make_level(42, challenged=True)
    assert level.width() == 33
    assert level.map[layout.ENTRANCE_POS] == terrain.ENTRANCE


def test_floor_state_adaptation():
    game, floor = make_game()
    assert floor.region == "caves"
    assert floor.entrance_pos == (16, 25)
    assert floor.exit_pos == (15, 0)
    # CUSTOM_DECO gate -> solid WALL_DECO in runtime tiles
    for x in range(14, 19):
        assert floor.grid[13][x] == TileType.WALL_DECO
    dm300 = [m for m in floor.mobs.values() if isinstance(m, DM300)]
    pylons = [m for m in floor.mobs.values() if isinstance(m, Pylon)]
    assert len(dm300) == 1
    assert len(pylons) == 4
    assert sorted((p.pos.x, p.pos.y) for p in pylons) == [(4, 13), (4, 37), (28, 13), (28, 37)]
