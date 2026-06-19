"""Tests for staff-imbued wand visibility (Belongings.all_items) and the
passive recharge tick (_tick_passive_wand_recharge / recharge_scale)."""
import pytest

from app.engine.manager import GameInstance
from app.engine.entities.base import CharacterClass


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
