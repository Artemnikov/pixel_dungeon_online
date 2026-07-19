import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.mobs import CrystalMimic
from app.engine.entities.item_union import Chest
from app.engine.dungeon.constants import TileType
from app.engine.game.floor_state import FloorState
from app.engine.game.spd_adapter import gen_level_to_floor_state
import pytest


def _build_floor_with_crystal_vault(seed=99, depth=16):
    from app.engine.dungeon.spd_levelgen.generator import SPDRandom, GeneratorState, generate_level
    rng = SPDRandom(seed)
    gen_level = generate_level(depth=depth, rng=rng)
    return gen_level_to_floor_state(gen_level, depth)


def test_crystal_chest_has_contents(monkeypatch):
    """Crystal chest heaps must produce Chest entities with real item contents."""
    from app.engine.dungeon.spd_levelgen.generator import RolledItem
    from app.engine.game.spd_adapter import _spawn_chest

    class FakeHeap:
        type = "CRYSTAL_CHEST"
        items = [RolledItem(category="WAND", is_artifact=False, is_upgradable=True, level=0, item_index=0)]

    chest = _spawn_chest(FakeHeap(), 5, 5)
    assert chest is not None
    assert chest.chest_type == "CRYSTAL_CHEST"
    assert chest.item_category == "WAND"
    assert len(chest.contents) == 1


def test_crystal_mimic_spawned_as_mob(monkeypatch):
    """GenMob with cls_name=CrystalMimic must produce a CrystalMimic mob + fake Chest item."""
    from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
    from app.engine.dungeon.spd_levelgen.generator import RolledItem
    from app.engine.game.spd_adapter import _adapt_gen_mobs_and_items

    ri = RolledItem(category="RING", is_artifact=False, is_upgradable=False, level=0)
    gen_mob = GenMob(cls_name="CrystalMimic", pos=5 + 5 * 32, items=[ri])
    mobs, items = _adapt_gen_mobs_and_items([gen_mob], width=32)

    crystal_mimics = [m for m in mobs.values() if isinstance(m, CrystalMimic)]
    fake_chests = [i for i in items.values() if isinstance(i, Chest) and i.chest_type == "CRYSTAL_CHEST"]
    assert len(crystal_mimics) == 1
    assert len(fake_chests) == 1
    m = crystal_mimics[0]
    fc = fake_chests[0]
    assert m.fake_chest_id == fc.id
    assert fc.item_category == "RING"
    assert m.pos.x == 5 and m.pos.y == 5
    assert fc.pos.x == 5 and fc.pos.y == 5
