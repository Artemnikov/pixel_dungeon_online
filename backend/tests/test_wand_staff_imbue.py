"""Tests for the MagesStaff wand-imbuing flow (ItemsMixin.imbue_wand /
Staff.imbue_wand)."""
import pytest

from app.engine.manager import GameInstance
from app.engine.entities.base import Staff, WandOfFireblast, WandOfFrost, CharacterClass


def _make_mage_with_unimbued_staff(game, player_id="mage-1"):
    player = game.add_player(player_id, "T", CharacterClass.MAGE)
    # Mage starts with an already-imbued staff; swap in a fresh, unimbued
    # one so the test exercises the imbue flow from scratch.
    player.belongings.weapon = Staff(id="staff-1")
    return player


def test_imbue_wand_moves_wand_from_backpack_into_staff():
    game = GameInstance("test-game")
    player = _make_mage_with_unimbued_staff(game)
    wand = WandOfFrost(id="wand-1")
    assert player.belongings.backpack.collect(wand)

    game.imbue_wand(player.id, "staff-1", "wand-1")

    staff = player.belongings.weapon
    assert staff.imbued_wand is wand
    assert player.belongings.backpack.find("wand-1") is None


def test_imbue_wand_emits_done_event():
    game = GameInstance("test-game")
    player = _make_mage_with_unimbued_staff(game)
    wand = WandOfFrost(id="wand-1")
    player.belongings.backpack.collect(wand)

    game.imbue_wand(player.id, "staff-1", "wand-1")

    events = game.flush_events()
    assert any(e["type"] == "IMBUE_WAND_DONE" for e in events)


def test_imbue_wand_returns_displaced_wand_when_backpack_has_no_room():
    """Staff.imbue_wand: with Wand Preservation talent, re-imbuing should
    preserve the old wand in the backpack -- but if the backpack has no
    room, the old wand must be handed back to the caller, not discarded."""
    game = GameInstance("test-game")
    player = game.add_player("mage-1", "T", CharacterClass.MAGE)
    staff = player.belongings.weapon
    old_wand = staff.imbued_wand
    player.subclass_info.talent_info.talents["wand_preservation"] = 1
    capacity = player.belongings.backpack.capacity
    player.belongings.backpack.items = [
        WandOfFrost(id=f"filler-{i}") for i in range(capacity)
    ]

    new_wand = WandOfFireblast(id="new-wand")
    displaced = staff.imbue_wand(new_wand, player)

    assert displaced is old_wand
    assert staff.imbued_wand is new_wand


def test_imbue_wand_drops_displaced_wand_on_floor_when_backpack_full():
    """End-to-end: ItemsMixin.imbue_wand must place a displaced wand it
    couldn't preserve onto the floor, not lose it."""
    game = GameInstance("test-game")
    player = game.add_player("mage-1", "T", CharacterClass.MAGE)
    player.subclass_info.talent_info.talents["wand_preservation"] = 1
    staff = player.belongings.weapon
    old_wand = staff.imbued_wand

    capacity = player.belongings.backpack.capacity
    new_wand = WandOfFireblast(id="new-wand")
    player.belongings.backpack.items = [
        WandOfFrost(id=f"filler-{i}") for i in range(capacity)
    ] + [new_wand]

    floor = game._get_or_create_floor(player.floor_id)
    floor.items.clear()

    game.imbue_wand(player.id, staff.id, new_wand.id)

    assert staff.imbued_wand is new_wand
    assert old_wand.id in floor.items
    assert floor.items[old_wand.id] is old_wand
