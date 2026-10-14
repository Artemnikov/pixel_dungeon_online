import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import uuid
from app.engine.entities.base import Position, Faction
from app.engine.entities.items.union import Chest
from app.engine.entities.mobs import CrystalMimic, Mimic, GoldenMimic, EbonyMimic
from app.engine.dungeon.constants import TileType
from app.engine.game.floor_state import FloorState
from app.engine.manager import GameInstance

from conftest import make_game_with_floors, make_open_floor, partial

_make_floor = partial(make_open_floor, floor_id=16, region="halls")
_make_game = partial(make_game_with_floors, game_id="test-crystal-mimic")


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
    sound_ev = next(e for e in game.events if e["type"] == "PLAY_SOUND")
    assert sound_ev["data"]["sound"] == "MIMIC"
    assert sound_ev["data"]["rate"] == 1.25
    assert sound_ev["data"]["x"] == 4
    assert sound_ev["data"]["y"] == 5


def test_regular_mimic_revealed_plays_sound_and_oop_flow():
    """Regular Mimic stop_hiding sets hunting state and emits sound with rate 1.0."""
    floor = _make_floor()
    game = _make_game(floor)
    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=2, y=2)

    fake_chest = Chest(id="fc_reg", pos=Position(x=3, y=2), chest_type="CHEST", mimic_hint=True)
    floor.items["fc_reg"] = fake_chest

    mimic = Mimic(id="m_reg", pos=Position(x=3, y=2), faction=Faction.DUNGEON, disguised=True, fake_chest_id="fc_reg")
    floor.mobs["m_reg"] = mimic

    game.events = []
    opened = game._try_open_chest(player, floor, floor.floor_id, fake_chest)
    assert opened is True
    assert "fc_reg" not in floor.items
    assert mimic.disguised is False
    assert mimic.ai_state == "hunting"
    assert mimic.target_id == player.id

    sound_ev = next(e for e in game.events if e["type"] == "PLAY_SOUND")
    assert sound_ev["data"]["sound"] == "MIMIC"
    assert sound_ev["data"]["rate"] == 1.0
    assert sound_ev["data"]["x"] == 3
    assert sound_ev["data"]["y"] == 2

    msg_ev = next(e for e in game.events if e["type"] == "MESSAGE")
    assert msg_ev["data"]["text"] == "A chest was a mimic!"


def test_golden_mimic_revealed_plays_sound_with_deep_pitch():
    """Golden Mimic reveal emits sound with rate 0.85 and locked chest message."""
    floor = _make_floor()
    game = _make_game(floor)
    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=1, y=1)

    fake_chest = Chest(id="fc_gold", pos=Position(x=1, y=2), chest_type="LOCKED_CHEST", mimic_hint=True)
    floor.items["fc_gold"] = fake_chest

    mimic = GoldenMimic(id="m_gold", pos=Position(x=1, y=2), faction=Faction.DUNGEON, disguised=True, fake_chest_id="fc_gold")
    floor.mobs["m_gold"] = mimic

    game.events = []
    opened = game._try_open_chest(player, floor, floor.floor_id, fake_chest)
    assert opened is True
    assert "fc_gold" not in floor.items
    assert mimic.disguised is False

    sound_ev = next(e for e in game.events if e["type"] == "PLAY_SOUND")
    assert sound_ev["data"]["sound"] == "MIMIC"
    assert sound_ev["data"]["rate"] == 0.85
    assert sound_ev["data"]["x"] == 1
    assert sound_ev["data"]["y"] == 2

    msg_ev = next(e for e in game.events if e["type"] == "MESSAGE")
    assert msg_ev["data"]["text"] == "A locked chest was a mimic!"


def test_ebony_mimic_revealed_plays_sound_with_deep_pitch():
    """Ebony Mimic reveal emits sound with rate 0.85."""
    floor = _make_floor()
    game = _make_game(floor)
    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=5, y=5)

    fake_chest = Chest(id="fc_ebony", pos=Position(x=5, y=6), chest_type="CHEST", mimic_hint=True)
    floor.items["fc_ebony"] = fake_chest

    mimic = EbonyMimic(id="m_ebony", pos=Position(x=5, y=6), faction=Faction.DUNGEON, disguised=True, fake_chest_id="fc_ebony")
    floor.mobs["m_ebony"] = mimic

    game.events = []
    opened = game._try_open_chest(player, floor, floor.floor_id, fake_chest)
    assert opened is True
    assert "fc_ebony" not in floor.items
    assert mimic.disguised is False

    sound_ev = next(e for e in game.events if e["type"] == "PLAY_SOUND")
    assert sound_ev["data"]["sound"] == "MIMIC"
    assert sound_ev["data"]["rate"] == 0.85
    assert sound_ev["data"]["x"] == 5
    assert sound_ev["data"]["y"] == 6

