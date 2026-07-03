"""Recipe engine parity tests vs shattered-pixel-dungeon/.../items/Recipe.java."""
import pytest

from app.engine.alchemy.recipes import (
    PotionToExotic, ScrollToExotic, ScrollToStone, SimpleRecipe, is_kind_identified,
    usable_in_recipe,
)
from app.engine.alchemy.registry import find_recipes
from app.engine.entities.items_consumable import GooBlob, MysteryMeat
from app.engine.entities.items_potions import HealthPotion, PotionOfFrost, PotionOfShielding
from app.engine.entities.items_scrolls import (
    ExoticScrollOfEnchantment, ScrollOfRemoveCurse, ScrollOfUpgrade,
)
from app.engine.entities.runestones import StoneOfDetectMagic, StoneOfEnchantment
from app.engine.entities.trinkets import RatSkull
from app.engine.manager import GameInstance


@pytest.fixture
def game():
    return GameInstance("t-recipes")


def _units(*items):
    out = []
    for it in items:
        u = it.model_copy(deep=True)
        u.quantity = 1
        out.append(u)
    return out


def test_simple_recipe_requires_kind_identified(game):
    r = SimpleRecipe(inputs=[(PotionOfFrost, 1)], energy_cost=8,
                     output_factory=HealthPotion, out_quantity=1)
    units = _units(PotionOfFrost())
    assert not r.test_ingredients(game, units)          # unidentified potion
    game.identified_kinds.add("potion_of_frost")
    assert r.test_ingredients(game, units)


def test_simple_recipe_exact_class_match(game):
    # SPD matches getClass()==; a subclass or sibling potion must not count.
    r = SimpleRecipe(inputs=[(PotionOfFrost, 1)], energy_cost=8,
                     output_factory=HealthPotion, out_quantity=1)
    game.identified_kinds.add("health_potion")
    assert not r.test_ingredients(game, _units(HealthPotion()))


def test_simple_recipe_sums_quantities_across_slots(game):
    r = SimpleRecipe(inputs=[(MysteryMeat, 2)], energy_cost=2,
                     output_factory=MysteryMeat, out_quantity=2)
    assert not r.test_ingredients(game, _units(MysteryMeat()))
    assert r.test_ingredients(game, _units(MysteryMeat(), MysteryMeat()))


def test_simple_recipe_brew_and_sample(game):
    r = SimpleRecipe(inputs=[(MysteryMeat, 1)], energy_cost=1,
                     output_factory=MysteryMeat, out_quantity=1)
    out = r.brew(game, _units(MysteryMeat()))
    assert isinstance(out, MysteryMeat) and out.quantity == 1
    assert r.brew(game, _units(GooBlob())) is None
    assert r.cost(_units(MysteryMeat())) == 1


def test_non_consumables_pass_identity_gate(game):
    assert is_kind_identified(game, GooBlob())
    assert is_kind_identified(game, MysteryMeat())
    assert not is_kind_identified(game, HealthPotion())


def test_usable_in_recipe_bans_cursed():
    assert usable_in_recipe(GooBlob())
    assert not usable_in_recipe(GooBlob(cursed=True))
    assert usable_in_recipe(RatSkull())
    assert not usable_in_recipe(RatSkull(cursed=True))


def test_scroll_to_stone_mapping_and_identify(game):
    r = ScrollToStone()
    units = _units(ScrollOfRemoveCurse())
    assert r.test_ingredients(game, units)   # unidentified scrolls ARE allowed
    assert r.cost(units) == 0
    assert r.sample_output(game, units) is None  # unknown kind -> '?' preview
    out = r.brew(game, units)
    assert isinstance(out, StoneOfDetectMagic) and out.quantity == 2
    assert "scroll_of_remove_curse" in game.identified_kinds
    assert isinstance(r.sample_output(game, units), StoneOfDetectMagic)


def test_potion_to_exotic(game):
    r = PotionToExotic()
    units = _units(HealthPotion())
    assert r.test_ingredients(game, units)
    assert r.cost(units) == 4
    assert isinstance(r.brew(game, units), PotionOfShielding)


def test_scroll_to_exotic(game):
    r = ScrollToExotic()
    units = _units(ScrollOfUpgrade())
    assert r.test_ingredients(game, units)
    assert r.cost(units) == 6
    assert isinstance(r.brew(game, units), ExoticScrollOfEnchantment)


def test_find_recipes_scroll_matches_stone_and_exotic(game):
    units = _units(ScrollOfUpgrade())
    found = [type(r).__name__ for r in find_recipes(game, units)]
    assert found == ["ScrollToStone", "ScrollToExotic"]  # Recipe.java order


def test_find_recipes_empty_for_unknown_combo(game):
    assert find_recipes(game, _units(GooBlob())) == []
