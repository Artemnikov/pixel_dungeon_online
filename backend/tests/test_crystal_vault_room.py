import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app.engine.dungeon.spd_levelgen.special_rooms import CrystalVaultRoom
from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
from app.engine.dungeon.spd_levelgen.level import GenLevel
from app.engine.dungeon.spd_levelgen.generator import RolledItem, init_generator_state
from app.engine.dungeon.spd_levelgen.room import Door
from app.engine.dungeon.spd_random import SPDRandom


def _make_level(seed=1, depth=16):
    rng = SPDRandom()
    rng.push_generator(seed)
    state = init_generator_state(rng)

    level = GenLevel(depth=depth)
    level.set_size(32, 32)

    class RunState:
        generator_state = state

    level.run_state = RunState()
    return level, rng


def _make_room_with_door(left=2, top=2):
    """CrystalVaultRoom is exactly 7x7 (right=left+6, bottom=top+6).
    Place a door on the top edge centre for entrance()."""
    room = CrystalVaultRoom()
    room.set(left, top, left + 6, top + 6)
    # Attach a fake neighbour so entrance() returns our door.
    door = Door(left + 3, top)   # top-edge midpoint
    from app.engine.dungeon.spd_levelgen.room import Room
    neighbour = Room()
    neighbour.set(left + 2, top - 3, left + 4, top)
    room.connected[neighbour] = door
    return room


def test_crystal_vault_room_chests_have_items():
    """Both heaps must contain a RolledItem, not frozenset()."""
    level, rng = _make_level()
    room = _make_room_with_door()
    room.paint(level, rng)
    chest_heaps = [h for h in level.heaps.values() if getattr(h, 'type', '') == 'CRYSTAL_CHEST']
    # Either 2 chests (no mimic) or 1 chest (mimic took the second slot).
    assert len(chest_heaps) >= 1
    for heap in chest_heaps:
        items = list(heap.items)
        assert len(items) == 1
        assert isinstance(items[0], RolledItem)
        assert items[0].category in ('WAND', 'RING', 'ARTIFACT')


def test_crystal_vault_room_total_chests_or_mimic():
    """Level has either 2 crystal chests, or 1 chest + 1 CrystalMimic mob."""
    level, rng = _make_level(seed=42)
    room = _make_room_with_door()
    room.paint(level, rng)
    chest_heaps = [h for h in level.heaps.values() if getattr(h, 'type', '') == 'CRYSTAL_CHEST']
    crystal_mimics = [m for m in level.mobs if isinstance(m, GenMob) and m.cls_name == 'CrystalMimic']
    assert len(chest_heaps) + len(crystal_mimics) == 2


def test_crystal_vault_no_shatter_on_open():
    """Opening one chest must not remove the other (regression guard)."""
    # Placeholder — implemented in Task 4 movement tests.
    pass
