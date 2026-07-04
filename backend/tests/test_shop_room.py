"""Tests for the depth-tiered ShopRoom (floors 6/11/16)."""
import pytest

from app.engine.entities.mobs import Shopkeeper
from app.engine.manager import GameInstance

# ShopRoom.ChooseBag(), simplified to a fixed depth->bag mapping (see
# shop_items.py). Each of these depths grants exactly one free bag.
_EXPECTED_BAG_KIND = {6: "scroll_holder", 11: "potion_bandolier", 16: "magical_holster"}


@pytest.mark.parametrize("depth", [6, 11, 16])
def test_shop_floor_has_shopkeeper_and_stock(depth):
    g = GameInstance("shoptest")
    floor = g._get_or_create_floor(depth)

    shopkeepers = [m for m in floor.mobs.values() if isinstance(m, Shopkeeper)]
    assert len(shopkeepers) == 1

    for_sale = [i for i in floor.items.values() if i.for_sale]
    assert len(for_sale) == 18

    # Artifacts are intentionally priceless (value()==0, matches SPD); every
    # other shop item should have a positive sell-back value.
    for item in for_sale:
        if item.kind != "artifact":
            assert item.value() > 0


@pytest.mark.parametrize("depth", [6, 11, 16])
def test_shop_floor_grants_expected_free_bag(depth):
    g = GameInstance("shoptest_bag")
    floor = g._get_or_create_floor(depth)

    for_sale = [i for i in floor.items.values() if i.for_sale]
    bag_kinds = {i.kind for i in for_sale if i.kind.endswith(("_pouch", "_holder", "_holster", "_bandolier"))}
    assert bag_kinds == {_EXPECTED_BAG_KIND[depth]}
    # VelvetPouch is never a shop item -- every player already starts with one.
    assert "velvet_pouch" not in bag_kinds


def test_shop_floor_20_grants_no_free_bag():
    # Depth 20 (ImpShopRoom) requires imp-quest completion to actually spawn
    # its stock through the floor pipeline; call the generator directly to
    # check the bag-grant mapping in isolation.
    from app.engine.dungeon.spd_levelgen.shop_items import generate_shop_items
    from app.engine.dungeon.spd_random import SPDRandom

    items = generate_shop_items(SPDRandom(), 20)
    bag_kinds = {i.kind for i in items if i.kind.endswith(("_pouch", "_holder", "_holster", "_bandolier"))}
    assert bag_kinds == set()


def test_shop_can_stock_bombs():
    # ShopRoom switch(Random.Int(4)) stocks a Bomb (1x) or DoubleBomb (2x) in
    # 3/4 of shops; only the Honeypot case (1/4) falls back to Mystery Meat.
    from app.engine.dungeon.spd_levelgen.shop_items import generate_shop_items
    from app.engine.dungeon.spd_random import SPDRandom
    from app.engine.entities.items_bombs import Bomb

    saw_single = saw_double = False
    for seed in range(40):
        rng = SPDRandom()
        rng.push_generator(seed)
        items = generate_shop_items(rng, 6)
        rng.pop_generator()
        for b in (i for i in items if isinstance(i, Bomb)):
            assert b.for_sale and b.value() == 15 * b.quantity
            saw_single |= b.quantity == 1
            saw_double |= b.quantity == 2
    assert saw_single and saw_double     # both stock variants are reachable


@pytest.mark.parametrize("depth", [6, 11, 16])
def test_shop_floor_generation_is_deterministic(depth):
    g1 = GameInstance("shoptest_a")
    g2 = GameInstance("shoptest_a")

    floor1 = g1._get_or_create_floor(depth)
    floor2 = g2._get_or_create_floor(depth)

    names1 = sorted(i.name for i in floor1.items.values() if i.for_sale)
    names2 = sorted(i.name for i in floor2.items.values() if i.for_sale)
    assert names1 == names2
