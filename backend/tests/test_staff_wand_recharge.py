"""Tests for staff-imbued wand visibility (Belongings.all_items) and the
passive recharge tick (_tick_passive_wand_recharge / recharge_scale)."""
import pytest

from app.engine.entities.items_equip import Staff
from app.engine.entities.items_potions import PotionOfLiquidFlame
from app.engine.entities.items_scrolls import ScrollOfIdentify, ScrollOfUpgrade
from app.engine.entities.items_wands import Wand
from app.engine.entities.player import CharacterClass
from app.engine.manager import GameInstance


def test_all_items_includes_the_imbued_wand():
    """A staff-imbued wand is detached from the backpack, so it must be
    surfaced by all_items() directly off the equipped Staff -- otherwise
    Scroll of Recharging / wand-charge talents never see it."""
    game = GameInstance("test-game")
    player = game.add_player("mage-1", "T", CharacterClass.MAGE)
    staff = player.belongings.weapon
    wand = staff.imbued_wand
    assert wand is not None

    assert wand in list(player.belongings.all_items())


def test_passive_recharge_does_not_double_charge_imbued_wand():
    """Once all_items() surfaces the imbued wand, the generic per-wand
    recharge loop in _tick_passive_wand_recharge must not ALSO accumulate
    partial_charge for it -- that's the dedicated staff-recharge block's
    job (a few lines down in the same method)."""
    game = GameInstance("test-game")
    player = game.add_player("mage-1", "T", CharacterClass.MAGE)
    staff = player.belongings.weapon
    wand = staff.imbued_wand
    wand.charges = wand.max_charges - 1

    game._tick_passive_wand_recharge(player, dt=1.0)

    # Only the dedicated staff-recharge block's contribution
    # (dt / (2.0 * recharge_scale)) should be present -- not also the
    # generic per-wand formula's contribution on top of it.
    expected = 1.0 / (2.0 * wand.recharge_scale)
    assert wand.partial_charge == pytest.approx(expected)


def test_staff_recharge_respects_recharge_scale():
    """Staff.imbue_wand sets imbued_wand.recharge_scale = 0.75 (MagesStaff
    recharges its wand faster than the wand alone). The dedicated
    staff-recharge block must actually use that field, not a flat 2.0s."""
    game = GameInstance("test-game")
    player = game.add_player("mage-1", "T", CharacterClass.MAGE)
    staff = player.belongings.weapon
    wand = staff.imbued_wand
    wand.charges = wand.max_charges - 1
    assert wand.recharge_scale == 0.75

    game._tick_passive_wand_recharge(player, dt=1.5)

    assert wand.charges == wand.max_charges


# --- Mage starting state ----------------------------------------------------

def test_mage_starts_with_scroll_of_upgrade():
    game = GameInstance("test-game")
    player = game.add_player("mage-1", "T", CharacterClass.MAGE)
    items = list(player.belongings.all_items())
    assert any(it.kind == "scroll_of_upgrade" for it in items)


def test_mage_starts_with_potion_of_liquid_flame():
    game = GameInstance("test-game")
    player = game.add_player("mage-1", "T", CharacterClass.MAGE)
    items = list(player.belongings.all_items())
    assert any(it.kind == "potion_of_liquid_flame" for it in items)


def test_mage_starter_scroll_and_potion_are_identified():
    game = GameInstance("test-game")
    player = game.add_player("mage-1", "T", CharacterClass.MAGE)
    assert "scroll_of_upgrade" in game.identified_kinds
    assert "potion_of_liquid_flame" in game.identified_kinds


def test_mage_staff_melee_range_is_1():
    game = GameInstance("test-game")
    player = game.add_player("mage-1", "T", CharacterClass.MAGE)
    staff = player.belongings.weapon
    assert isinstance(staff, Staff)
    # KindOfWeapon.range default = 1; zap range comes from imbued wand.
    assert staff.range == 1


def test_mage_staff_zap_range_comes_from_wand():
    game = GameInstance("test-game")
    player = game.add_player("mage-1", "T", CharacterClass.MAGE)
    staff = player.belongings.weapon
    assert isinstance(staff, Staff)
    assert staff.imbued_wand is not None
    wand_reach = staff.imbued_wand.get_reach()
    assert wand_reach == 8


def test_all_classes_start_with_scroll_of_identify():
    for cls in (CharacterClass.WARRIOR, CharacterClass.MAGE, CharacterClass.ROGUE, CharacterClass.HUNTRESS):
        game = GameInstance("test-game")
        player = game.add_player("p", "T", cls)
        items = list(player.belongings.all_items())
        assert any(it.kind == "scroll_of_identify" for it in items), f"{cls} missing ScrollOfIdentify"
        assert "scroll_of_identify" in game.identified_kinds, f"{cls} ScrollOfIdentify not identified"
