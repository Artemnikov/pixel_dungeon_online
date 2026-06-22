from app.engine.entities.base import Amulet
from app.engine.entities.item_catalog import make_catalog_item
from app.engine.game.spd_adapter import _DESCRIPTOR_ITEM_MAP


def test_amulet_is_unique_and_not_stackable():
    amulet = Amulet(id="a1", name="Amulet of Yendor")
    assert amulet.unique is True
    assert amulet.stackable is False
    assert amulet.kind == "amulet"


def test_amulet_in_descriptor_item_map():
    assert "Amulet" in _DESCRIPTOR_ITEM_MAP
    item = _DESCRIPTOR_ITEM_MAP["Amulet"]("a2", None)
    assert isinstance(item, Amulet)


def test_amulet_in_admin_catalog():
    item = make_catalog_item("amulet")
    assert isinstance(item, Amulet)
