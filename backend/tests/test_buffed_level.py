import uuid

from app.engine.entities.items_equip import Dagger, Staff
from app.engine.entities.items_wands import WandOfMagicMissile


def _id():
    return str(uuid.uuid4())


def test_plain_weapon_buffed_equals_true_level():
    w = Dagger(id=_id(), level=2, level_known=True)
    assert w.visibly_upgraded() == 2
    assert w.buffed_visibly_upgraded() == 2


def test_unknown_level_reads_as_zero():
    w = Dagger(id=_id(), level=2, level_known=False)
    assert w.visibly_upgraded() == 0
    assert w.buffed_visibly_upgraded() == 0


def test_staff_with_imbued_wand_buffed_exceeds_true():
    wand = WandOfMagicMissile(id=_id(), charges=4, max_charges=4, level=3, level_known=True)
    staff = Staff(id=_id(), imbued_wand=wand, level=0, level_known=True)
    assert staff.visibly_upgraded() == 0
    assert staff.buffed_visibly_upgraded() == 3
