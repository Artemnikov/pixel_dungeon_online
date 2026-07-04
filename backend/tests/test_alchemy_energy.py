"""EnergyCrystal: pickup converts to Player.energy, never enters the bag."""
from app.engine.entities.base import Position
from app.engine.entities.items_consumable import EnergyCrystal
from app.engine.game.spd_adapter import _descriptor_to_item
from app.engine.manager import GameInstance


def test_energy_crystal_walk_pickup_converts_to_energy():
    g = GameInstance("t-energy-1")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)
    floor.items["ec1"] = EnergyCrystal(
        id="ec1", quantity=4, pos=Position(x=p.pos.x + 1, y=p.pos.y))

    g.move_entity("p1", 1, 0)

    assert p.energy == 4
    assert "ec1" not in floor.items
    assert all(not isinstance(i, EnergyCrystal) for i in p.inventory)
    assert any(e["type"] == "PICKUP_ENERGY" and e["data"]["amount"] == 4
               for e in g.events)


def test_descriptor_maps_energy_crystal_with_quantity_tag():
    item = _descriptor_to_item(frozenset({"EnergyCrystal", "qty:5"}), 3, 4)
    assert isinstance(item, EnergyCrystal)
    assert item.quantity == 5
    assert (item.pos.x, item.pos.y) == (3, 4)


def test_descriptor_energy_crystal_defaults_to_one():
    item = _descriptor_to_item(frozenset({"EnergyCrystal"}), 0, 0)
    assert isinstance(item, EnergyCrystal)
    assert item.quantity == 1
