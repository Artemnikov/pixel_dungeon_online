from app.engine.dungeon.constants import TileType
from app.engine.entities.items_consumable import Key
from app.engine.entities.mobs import YogDzewa
from app.engine.manager import GameInstance


def test_yog_death_drops_key_matching_locked_exit():
    game = GameInstance("yog-amulet-path-test")
    floor = game.generate_floor(25)
    yog = next(m for m in floor.mobs.values() if isinstance(m, YogDzewa))

    assert len(floor.locked_doors) == 1
    (dx, dy), door_key_id = next(iter(floor.locked_doors.items()))
    assert floor.grid[dy][dx] == TileType.LOCKED_EXIT

    game.handle_mob_death(yog, floor, 25)

    keys = [i for i in floor.items.values() if isinstance(i, Key)]
    assert len(keys) == 1
    assert keys[0].key_id == door_key_id

    # Idempotent: calling it again must not double-drop.
    game.handle_mob_death(yog, floor, 25)
    keys = [i for i in floor.items.values() if isinstance(i, Key)]
    assert len(keys) == 1
