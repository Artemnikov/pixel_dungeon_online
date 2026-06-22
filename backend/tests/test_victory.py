from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Amulet, Position
from app.engine.manager import GameInstance


def _player_at_surface_entrance(game, floor_id=1):
    floor = game._get_or_create_floor(floor_id)
    floor.mobs = {}
    entrance = next(
        (x, y)
        for y, row in enumerate(floor.grid)
        for x, tile in enumerate(row)
        if tile == TileType.STAIRS_UP
    )
    player = game.add_player("p-victory", "Ascender")
    player.pos = Position(x=entrance[0], y=entrance[1])
    return floor, player, entrance


def test_leaving_depth_1_without_amulet_is_blocked():
    game = GameInstance("victory-test-blocked")
    floor, player, (ex, ey) = _player_at_surface_entrance(game)

    game.flush_events()
    # Step onto the entrance tile itself (dx=dy=0 -- triggers the tile-effect
    # branch without first needing to move there).
    game.move_entity(player.id, 0, 0)

    events = game.flush_events()
    messages = [e for e in events if e["type"] == "MESSAGE"]
    assert any("leave yet" in e["data"]["text"] for e in messages)
    assert player.is_alive


def test_leaving_depth_1_with_amulet_wins():
    game = GameInstance("victory-test-wins")
    floor, player, (ex, ey) = _player_at_surface_entrance(game)
    player.add_to_inventory(Amulet(id="amulet-1"))

    game.flush_events()
    game.move_entity(player.id, 0, 0)

    events = game.flush_events()
    deaths = [e for e in events if e["type"] == "DEATH"]
    assert len(deaths) == 1
    assert deaths[0]["data"]["victory"] is True
    assert deaths[0]["data"]["target"] == player.id
    assert deaths[0]["data"]["can_resurrect"] is False

    assert not player.is_alive
    assert player.death_processed
    # Victory keeps everything -- no drop, no grave.
    assert any(isinstance(it, Amulet) for it in player.belongings.all_items())
    assert not any(getattr(i, "type", "") == "grave" for i in floor.items.values())


def test_has_amulet_reflects_inventory():
    game = GameInstance("victory-test-has-amulet")
    player = game.add_player("p-has-amulet", "Carrier")
    assert not any(isinstance(it, Amulet) for it in player.belongings.all_items())

    player.add_to_inventory(Amulet(id="amulet-2"))
    assert any(isinstance(it, Amulet) for it in player.belongings.all_items())
