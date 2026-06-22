from app.engine.dungeon.constants import TileType
from app.engine.manager import GameInstance


def test_last_level_generates_with_amulet_and_entrance():
    game = GameInstance("last-level-test")
    floor = game.generate_floor(26)

    assert floor.width == 16
    assert floor.height == 64

    amulets = [i for i in floor.items.values() if getattr(i, "kind", "") == "amulet"]
    assert len(amulets) == 1
    assert amulets[0].pos.x == 8 and amulets[0].pos.y == 12

    entrance_tiles = [
        (x, y)
        for y, row in enumerate(floor.grid)
        for x, tile in enumerate(row)
        if tile == TileType.STAIRS_UP
    ]
    assert (8, 54) in entrance_tiles
    assert (8, 55) in entrance_tiles

    # The corridor connecting the entrance room to the amulet room must be walkable.
    assert floor.flags.passable[12][8]
    assert floor.flags.passable[54][8]
