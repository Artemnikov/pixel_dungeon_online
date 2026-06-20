"""Keys are picked up like Gold/Dewdrop: they bypass the bag entirely and go
straight into the player's depth-keyed key counter."""
from app.engine.entities.base import Key, Position
from app.engine.manager import GameInstance


def test_key_pickup_adds_to_counter_and_skips_inventory():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")

    floor = g._get_or_create_floor(p.floor_id)
    floor.items["key1"] = Key(id="key1", name="Iron Key", key_id="iron", pos=Position(x=p.pos.x + 1, y=p.pos.y))

    g.move_entity("p1", 1, 0)

    assert p.key_count("iron", depth=p.floor_id) == 1
    assert "key1" not in floor.items
    assert all(not isinstance(i, Key) for i in p.inventory)


def test_key_pickup_emits_pickup_key_event():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")

    floor = g._get_or_create_floor(p.floor_id)
    floor.items["key1"] = Key(id="key1", name="Iron Key", key_id="iron", pos=Position(x=p.pos.x + 1, y=p.pos.y))

    g.move_entity("p1", 1, 0)

    pickup_events = [e for e in g.events if e["type"] == "PICKUP_KEY"]
    assert len(pickup_events) == 1
    assert pickup_events[0]["data"] == {"player": "p1", "key_id": "iron", "name": "Iron Key"}
