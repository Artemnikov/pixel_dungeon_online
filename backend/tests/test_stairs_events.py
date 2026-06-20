from app.engine.dungeon.generator import TileType
from app.engine.manager import GameInstance


WALKABLE_TILES = {
    TileType.FLOOR,
    TileType.DOOR,
    TileType.STAIRS_UP,
    TileType.STAIRS_DOWN,
    TileType.FLOOR_WOOD,
    TileType.FLOOR_WATER,
    TileType.FLOOR_COBBLE,
    TileType.FLOOR_GRASS,
    TileType.EMPTY_DECO,
    TileType.HIGH_GRASS,
}


def _find_tile(floor, tile_type):
    for y in range(floor.height):
        for x in range(floor.width):
            if floor.grid[y][x] == tile_type:
                return x, y
    return None


def _find_adjacent_walkable(floor, x, y):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if not (0 <= ny < len(floor.grid) and 0 <= nx < len(floor.grid[0])):
            continue
        if floor.grid[ny][nx] in WALKABLE_TILES:
            return nx, ny
    return None


def _step_onto(game, player, floor, tx, ty):
    """Place player adjacent to (tx, ty) and move onto it."""
    nx, ny = _find_adjacent_walkable(floor, tx, ty)
    dx, dy = tx - nx, ty - ny
    player.pos.x, player.pos.y = nx, ny
    game.flush_events()
    game.move_entity(player.id, dx, dy)
    return game.flush_events()


def test_first_descent_sets_first_visit_true():
    game = GameInstance("stairs-first-descent")
    floor = game._get_or_create_floor(1)
    player = game.add_player("p1", "Hero")

    assert player.floor_id == 1
    assert player.floors_explored == 1

    down_x, down_y = _find_tile(floor, TileType.STAIRS_DOWN)
    events = _step_onto(game, player, floor, down_x, down_y)

    stairs_down_events = [e for e in events if e["type"] == "STAIRS_DOWN"]
    assert len(stairs_down_events) == 1
    assert stairs_down_events[0]["data"]["first_visit"] is True

    assert player.floor_id == 2
    assert player.floors_explored == 2


def test_redescending_after_returning_sets_first_visit_false():
    game = GameInstance("stairs-redescend")
    floor1 = game._get_or_create_floor(1)
    player = game.add_player("p1", "Hero")

    down_x, down_y = _find_tile(floor1, TileType.STAIRS_DOWN)
    _step_onto(game, player, floor1, down_x, down_y)

    assert player.floor_id == 2
    assert player.floors_explored == 2

    # Go back up to floor 1.
    floor2 = game._get_or_create_floor(2)
    up_x, up_y = _find_tile(floor2, TileType.STAIRS_UP)
    events = _step_onto(game, player, floor2, up_x, up_y)
    stairs_up_events = [e for e in events if e["type"] == "STAIRS_UP"]
    assert len(stairs_up_events) == 1
    # StairsUpData must not carry a first_visit field at all.
    assert "first_visit" not in stairs_up_events[0]["data"]

    assert player.floor_id == 1
    assert player.floors_explored == 2  # deepest floor reached is unaffected by ascending

    # Descend again to floor 2 - already explored, so first_visit must be False.
    floor1 = game._get_or_create_floor(1)
    down_x, down_y = _find_tile(floor1, TileType.STAIRS_DOWN)
    events = _step_onto(game, player, floor1, down_x, down_y)

    stairs_down_events = [e for e in events if e["type"] == "STAIRS_DOWN"]
    assert len(stairs_down_events) == 1
    assert stairs_down_events[0]["data"]["first_visit"] is False

    assert player.floor_id == 2
    assert player.floors_explored == 2
