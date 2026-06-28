import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import uuid
from app.engine.entities.base import Position, Faction, Chest
from app.engine.entities.mobs import CrystalMimic
from app.engine.dungeon.generator import TileType
from app.engine.game.floor_state import FloorState
from app.engine.manager import GameInstance


def _make_floor(floor_id=16, w=10, h=10):
    grid = [[TileType.FLOOR for _ in range(w)] for _ in range(h)]
    floor = FloorState(floor_id=floor_id, grid=grid, rooms=[], mobs={}, items={}, region="halls")
    floor.rebuild_flags()
    return floor


def _make_game(floor):
    game = GameInstance("test-crystal-mimic")
    game.players = {}
    game.floors[floor.floor_id] = floor
    game.depth = floor.floor_id
    return game


def test_crystal_chest_open_does_not_remove_other_chest():
    """Opening one crystal chest must NOT remove the other (regression: _shatter_other_crystal_chests removed)."""
    floor = _make_floor()
    game = _make_game(floor)
    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=3, y=3)

    # Give player a crystal key for floor 16
    player.add_key("crystal", 16, name="Crystal Key")

    chest1 = Chest(id="ch1", pos=Position(x=3, y=3), chest_type="CRYSTAL_CHEST")
    chest2 = Chest(id="ch2", pos=Position(x=5, y=5), chest_type="CRYSTAL_CHEST")
    floor.items["ch1"] = chest1
    floor.items["ch2"] = chest2

    # Trigger open by bumping into the chest cell (player is already on it)
    game._try_open_chest(player, floor, floor.floor_id, chest1)

    assert "ch2" in floor.items, "Second crystal chest must remain after opening first"


def test_disguised_mimic_not_in_serialized_mobs():
    """Disguised CrystalMimic must not appear in client mob list."""
    floor = _make_floor()
    game = _make_game(floor)
    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=5, y=5)

    mimic = CrystalMimic(id="cm1", pos=Position(x=9, y=9), faction=Faction.DUNGEON)
    mimic.disguised = True
    floor.mobs["cm1"] = mimic

    state = game.get_state(player.id)
    mob_ids = [m["id"] for m in state["mobs"]]
    assert "cm1" not in mob_ids


def test_crystal_mimic_revealed_on_open():
    """Trying to open a disguised CrystalMimic's fake chest must reveal it (SPAWN_MOB, MESSAGE, fake chest removed)."""
    floor = _make_floor()
    game = _make_game(floor)
    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=4, y=5)
    player.add_key("crystal", floor.floor_id, name="Crystal Key")

    fake_chest = Chest(id="fc1", pos=Position(x=4, y=5), chest_type="CRYSTAL_CHEST")
    floor.items["fc1"] = fake_chest

    mimic = CrystalMimic(id="cm1", pos=Position(x=4, y=5), faction=Faction.DUNGEON)
    mimic.disguised = True
    mimic.fake_chest_id = "fc1"
    floor.mobs["cm1"] = mimic

    game.events = []
    game._reveal_crystal_mimic_for_chest(player, floor, floor.floor_id, "fc1")

    assert "fc1" not in floor.items
    assert mimic.disguised is False
    event_types = [e["type"] for e in game.events]
    assert "SPAWN_MOB" in event_types
    assert "MESSAGE" in event_types
