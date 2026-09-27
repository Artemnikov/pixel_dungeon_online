from app.engine.dungeon.constants import TileType
from app.engine.entities.mobs import YogDzewa
from app.engine.manager import GameInstance


def test_yog_death_unseals_arena_exit_to_last_level():
    game = GameInstance("yog-amulet-path-test")
    floor = game.generate_floor(25)
    yog = next(m for m in floor.mobs.values() if isinstance(m, YogDzewa))

    # Before death: exit at (16, 9) is covered by centerpiece wall/deco
    assert floor.width == 32
    assert floor.height == 32
    assert floor.exit_pos == (16, 9)
    assert floor.grid[9][16] != TileType.STAIRS_DOWN

    # Kill Yog
    game.handle_mob_death(yog, floor, 25)

    # After death: exit at (16, 9) is unsealed as STAIRS_DOWN
    assert floor.grid[9][16] == TileType.STAIRS_DOWN
    assert floor.flags is not None
    assert floor.flags.passable[9][16]
    assert game.boss_scores[4] == 5000

    # Custom tilemaps updated to unsealed
    custom_tiles = next(l for l in floor.custom_tiles if l["texture"] == "halls_special")
    assert custom_tiles["tiles"][0][4] == 19
    assert custom_tiles["tiles"][1][3] == 31
    assert custom_tiles["tiles"][1][5] == 31

    # Descending from 25 goes to floor 26 (LastLevel)
    floor_26 = game.generate_floor(26)
    assert floor_26.width == 16
    assert floor_26.height == 64

