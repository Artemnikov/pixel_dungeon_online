"""Recipe engine parity tests vs shattered-pixel-dungeon/.../items/Recipe.java."""
import pytest

from app.engine.alchemy.recipes import (
    PotionToExotic, ScrollToExotic, ScrollToStone, SimpleRecipe, is_kind_identified,
    usable_in_recipe,
)
from app.engine.alchemy.registry import find_recipes
from app.engine.entities.items_consumable import GooBlob, MysteryMeat
from app.engine.entities.items_potions import (
    HealthPotion, PotionOfFrost, PotionOfMastery, PotionOfShielding, PotionOfStrength,
)
from app.engine.entities.items_scrolls import (
    ExoticScrollOfEnchantment, ScrollOfDivination, ScrollOfRemoveCurse, ScrollOfUpgrade,
)
from app.engine.entities.runestones import (
    StoneOfAugmentation, StoneOfBlast, StoneOfDetectMagic, StoneOfEnchantment,
)
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


def test_transmute_sample_output_none_for_non_matching(game):
    from app.engine.entities.items_scrolls import ScrollOfEnchantment
    assert ScrollToStone().sample_output(game, _units(ScrollOfEnchantment())) is None
    assert PotionToExotic().sample_output(game, _units(GooBlob())) is None
    assert ScrollToExotic().sample_output(game, _units(GooBlob())) is None


from app.engine.alchemy import registry
from app.engine.alchemy.recipes import UnstableBrewRecipe
from app.engine.entities.items_consumable import Seed
from app.engine.entities.items_potions import (
    AquaBrew, BlizzardBrew, CausticBrew, ElixirOfAquaticRejuvenation,
    ElixirOfArcaneArmor, ElixirOfDragonsBlood, ElixirOfFeatherFall,
    ElixirOfHoneyedHealing, ElixirOfIcyTouch, ElixirOfMight, ElixirOfToxicEssence,
    InfernalBrew, PotionOfCorrosiveGas, PotionOfDragonsBreath, PotionOfEarthenArmor,
    PotionOfFrost, PotionOfLevitation, PotionOfLiquidFlame, PotionOfParalyticGas,
    PotionOfSnapFreeze, PotionOfStormClouds, PotionOfStrength, PotionOfToxicGas,
    ShockingBrew, UnstableBrew,
)

# (input classes+quantities, cost, output class, out qty) — from each SPD
# Recipe inner class; see plan Task 4 for the Java sources.
SIMPLE_PARITY = [
    ([(PotionOfFrost, 1)], 8, BlizzardBrew, 1),
    ([(PotionOfLiquidFlame, 1)], 12, InfernalBrew, 1),
    ([(PotionOfStormClouds, 1)], 8, AquaBrew, 8),
    ([(PotionOfParalyticGas, 1)], 10, ShockingBrew, 1),
    ([(PotionOfDragonsBreath, 1)], 10, ElixirOfDragonsBlood, 1),
    ([(PotionOfSnapFreeze, 1)], 6, ElixirOfIcyTouch, 1),
    ([(PotionOfCorrosiveGas, 1)], 8, ElixirOfToxicEssence, 1),
    ([(PotionOfStrength, 1)], 16, ElixirOfMight, 1),
    ([(PotionOfLevitation, 1)], 10, ElixirOfFeatherFall, 1),
    ([(PotionOfToxicGas, 1), (GooBlob, 1)], 1, CausticBrew, 1),
    ([(PotionOfEarthenArmor, 1), (GooBlob, 1)], 8, ElixirOfArcaneArmor, 1),
    ([(HealthPotion, 1), (GooBlob, 1)], 6, ElixirOfAquaticRejuvenation, 1),
]


@pytest.mark.parametrize("inputs,cost,output_cls,out_qty", SIMPLE_PARITY)
def test_brew_elixir_parity(game, inputs, cost, output_cls, out_qty):
    units = []
    for cls, qty in inputs:
        for _ in range(qty):
            item = cls()
            game.identified_kinds.add(item.kind)
            units.extend(_units(item))
    matches = [r for r in registry.find_recipes(game, units)
               if isinstance(r.sample_output(game, units), output_cls)]
    assert len(matches) == 1, f"no unique recipe for {output_cls.__name__}"
    r = matches[0]
    assert r.cost(units) == cost
    out = r.brew(game, units)
    assert isinstance(out, output_cls) and out.quantity == out_qty


def test_unstable_brew_needs_potion_plus_seed(game):
    r = UnstableBrewRecipe()
    game.identified_kinds.add("potion_of_frost")
    seed = Seed(name="Sungrass Seed", plant_type="sungrass")
    assert r.test_ingredients(game, _units(PotionOfFrost(), seed))
    # exotic potions count too
    assert r.test_ingredients(game, _units(PotionOfSnapFreeze(), seed))
    assert not r.test_ingredients(game, _units(PotionOfFrost(), GooBlob()))
    assert r.cost(_units(PotionOfFrost(), seed)) == 1
    assert isinstance(r.brew(game, _units(PotionOfFrost(), seed)), UnstableBrew)


from app.engine.alchemy.recipes import MeatPieRecipe, SeedToPotionRecipe
from app.engine.entities.items_consumable import (
    ChargrilledMeat, MeatPie, Pasty, Ration, StewedMeat,
)


def test_new_food_nutrition_and_value():
    # SPD: STEWED energy = HUNGRY/2 = 150; MeatPie = STARVING*2 = 900, value 40.
    assert StewedMeat().energy == 150
    assert MeatPie().energy == 900
    assert MeatPie().value() == 40
    assert StewedMeat(quantity=2).value(identified=True) == 16


def test_stewed_meat_recipes(game):
    one = _units(MysteryMeat())
    two = _units(MysteryMeat(), MysteryMeat())
    three = _units(MysteryMeat(), MysteryMeat(), MysteryMeat())
    r1 = [r for r in find_recipes(game, one)
          if isinstance(r.sample_output(game, one), StewedMeat)]
    r2 = [r for r in find_recipes(game, two)
          if isinstance(r.sample_output(game, two), StewedMeat)]
    r3 = [r for r in find_recipes(game, three)
          if isinstance(r.sample_output(game, three), StewedMeat)]
    assert (r1[0].cost(one), r1[0].sample_output(game, one).quantity) == (1, 1)
    assert (r2[0].cost(two), r2[0].sample_output(game, two).quantity) == (2, 2)
    assert (r3[0].cost(three), r3[0].sample_output(game, three).quantity) == (2, 3)


def test_meat_pie_recipe(game):
    units = _units(Pasty(), Ration(), ChargrilledMeat())
    r = MeatPieRecipe()
    assert r.test_ingredients(game, units)
    assert r.cost(units) == 6
    assert isinstance(r.brew(game, units), MeatPie)
    # SmallRation is not SPD's generic Food.class — must not qualify
    from app.engine.entities.items_consumable import SmallRation
    assert not r.test_ingredients(game, _units(Pasty(), SmallRation(), ChargrilledMeat()))


def test_seed_to_potion_matching_seeds(game, monkeypatch):
    import random
    r = SeedToPotionRecipe()
    seeds = _units(*(Seed(name="Icecap Seed", plant_type="icecap") for _ in range(3)))
    assert r.test_ingredients(game, seeds)
    assert r.cost(seeds) == 0
    assert r.sample_output(game, seeds) is None  # '?' preview
    out = r.brew(game, seeds)
    assert isinstance(out, PotionOfFrost)
    # single distinct seed type identifies the result for the party
    assert "potion_of_frost" in game.identified_kinds


def test_seed_to_potion_cooking_hp_limiter(game, monkeypatch):
    r = SeedToPotionRecipe()
    seeds = _units(*(Seed(name="Sungrass Seed", plant_type="sungrass") for _ in range(3)))
    game.drop_counters["cooking_hp"] = 10  # limiter saturated: reroll always
    monkeypatch.setattr("app.engine.alchemy.recipes._random.randint", lambda a, b: 0)
    out = r.brew(game, seeds)
    # randint always 0 < counter, so the while-loop rerolls (via the
    # unpatched weighted pick) until the result is NOT a health potion.
    assert not isinstance(out, HealthPotion)


from app.engine.alchemy.recipes import TrinketCatalystRecipe, UpgradeTrinketRecipe
from app.engine.entities.trinkets import ParchmentScrap, TrinketCatalyst


def test_trinket_catalyst_recipe(game):
    r = TrinketCatalystRecipe()
    units = _units(TrinketCatalyst())
    assert r.test_ingredients(game, units)
    assert r.cost(units) == 6
    assert r.brew(game, units) is None       # choice flow, no direct output
    assert r.sample_output(game, units) is None


def test_upgrade_trinket_recipe(game):
    r = UpgradeTrinketRecipe()
    units = _units(ParchmentScrap(level=1))
    assert r.test_ingredients(game, units)
    assert r.cost(units) == 15               # ParchmentScrap: 10 + 5*level
    out = r.brew(game, units)
    assert isinstance(out, ParchmentScrap) and out.level == 2 and out.level_known
    assert not r.test_ingredients(game, _units(ParchmentScrap(level=3)))


def test_trinket_catalyst_has_rolled_kinds_field():
    c = TrinketCatalyst()
    assert c.rolled_kinds == []


def test_legacy_alchemize_action_removed(game):
    from app.engine.entities.item_actions import ITEM_ACTION_DISPATCH
    assert "ALCHEMIZE" not in ITEM_ACTION_DISPATCH
    p = game.add_player("p1", "Bob")
    assert "ALCHEMIZE" not in TrinketCatalyst().actions(p)
    assert "ALCHEMIZE" not in GooBlob().actions(p)


from app.engine.alchemy.energy import energy_val


def test_energy_values_match_spd_table(game):
    # Item.energyVal overrides: potion/scroll 6/q; exotic +4/+6; runestone 3/q;
    # seed 2/q (starflower & rotberry 3/q); trinket 5; catalyst 6; food 0.
    assert energy_val(game, HealthPotion(quantity=2)) == 12
    assert energy_val(game, PotionOfShielding()) == 10          # exotic potion
    assert energy_val(game, ScrollOfRemoveCurse()) == 6
    assert energy_val(game, ScrollOfDivination()) == 12         # exotic scroll
    assert energy_val(game, StoneOfBlast(quantity=3)) == 9
    assert energy_val(game, Seed(name="Icecap Seed", plant_type="icecap")) == 2
    assert energy_val(game, Seed(name="Starflower Seed", plant_type="starflower")) == 3
    assert energy_val(game, Seed(name="Rotberry Seed", plant_type="rotberry")) == 3
    assert energy_val(game, RatSkull()) == 5
    assert energy_val(game, TrinketCatalyst()) == 6
    assert energy_val(game, MysteryMeat()) == 0
    assert energy_val(game, GooBlob()) == 3
    # Elixir/Brew overrides (Elixir.java & Brew.java: 12*q; UnstableBrew 8*q;
    # AquaBrew 12*(q/8); HoneyedHealing flat 8; enchant/augment stones 5*q).
    assert energy_val(game, ElixirOfMight()) == 12
    assert energy_val(game, ElixirOfAquaticRejuvenation(quantity=2)) == 24
    assert energy_val(game, BlizzardBrew()) == 12
    assert energy_val(game, UnstableBrew(quantity=2)) == 16
    assert energy_val(game, AquaBrew(quantity=8)) == 12
    assert energy_val(game, AquaBrew(quantity=4)) == 6
    assert energy_val(game, ElixirOfHoneyedHealing(quantity=2)) == 8
    assert energy_val(game, StoneOfEnchantment(quantity=2)) == 10
    assert energy_val(game, StoneOfAugmentation()) == 5


def test_energy_value_known_boost(game):
    # ScrollOfUpgrade/Transmutation + PotionOfStrength/Experience are worth 10
    # once their kind is identified (SPD isKnown() overrides).
    assert energy_val(game, ScrollOfUpgrade()) == 6
    game.identified_kinds.add("scroll_of_upgrade")
    assert energy_val(game, ScrollOfUpgrade()) == 10
    assert energy_val(game, PotionOfStrength()) == 6
    game.identified_kinds.add("potion_of_strength")
    assert energy_val(game, PotionOfStrength()) == 10
    # exotic of a boosted-known base: (10 + 4) per unit
    assert energy_val(game, PotionOfMastery()) == 14
