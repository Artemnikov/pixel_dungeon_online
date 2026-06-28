import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.mobs import CrystalMimic
from app.engine.entities.base import Chest, Position


def test_crystal_mimic_has_required_fields():
    m = CrystalMimic(id="cm1", pos=Position(x=1, y=1), faction="dungeon")
    assert m.name == "Crystal Mimic"
    assert m.disguised is True
    assert m.fake_chest_id == ""
    assert m.pending_steal_name == ""
    assert m.pending_teleport is False


def test_chest_has_item_category():
    c = Chest(id="c1", pos=Position(x=1, y=1), chest_type="CRYSTAL_CHEST", item_category="WAND")
    assert c.item_category == "WAND"


def test_chest_item_category_optional():
    c = Chest(id="c2", pos=Position(x=2, y=2))
    assert c.item_category is None
