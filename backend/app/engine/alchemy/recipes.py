# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
"""Alchemy recipe engine, ported from SPD's items/Recipe.java.

`units` are quantity-1 deep copies of the player's stacks — one per alchemy
slot (SPD slots hold a single detached unit). Recipes never consume: they only
test/price/roll the output. AlchemyMixin consumes exactly one unit per slot
after a successful brew, which holds for every phase-1 recipe.
"""
from __future__ import annotations

import random as _random
import uuid as _uuid
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from app.engine.entities.base import ItemBase
from app.engine.entities.items_consumable import (
    ChargrilledMeat, FrozenCarpaccio, GooBlob, MeatPie, MysteryMeat, Pasty, Ration,
    Seed, StewedMeat,
)
from app.engine.entities.items_equip import EquipableItem
from app.engine.entities.items_potions import (
    AquaBrew, BlizzardBrew, CausticBrew, ElixirOfAquaticRejuvenation,
    ElixirOfArcaneArmor, ElixirOfDragonsBlood, ElixirOfFeatherFall,
    ElixirOfIcyTouch, ElixirOfMight, ElixirOfToxicEssence, HealthPotion,
    InfernalBrew, PotionOfCleansing, PotionOfCorrosiveGas, PotionOfDivineInspiration,
    PotionOfDragonsBreath, PotionOfEarthenArmor, PotionOfExperience, PotionOfFrost,
    PotionOfHaste, PotionOfInvisibility, PotionOfLevitation, PotionOfLiquidFlame,
    PotionOfMagicalSight, PotionOfMastery, PotionOfMindVision, PotionOfParalyticGas,
    PotionOfPurity, PotionOfShielding, PotionOfShroudingFog, PotionOfSnapFreeze,
    PotionOfStamina, PotionOfStormClouds, PotionOfStrength, PotionOfToxicGas, Potion,
    ShockingBrew, UnstableBrew,
)
from app.engine.entities.items_scrolls import (
    ExoticScrollOfEnchantment, Scroll, ScrollOfAntiMagic, ScrollOfChallenge,
    ScrollOfDivination, ScrollOfDread, ScrollOfForesight, ScrollOfIdentify,
    ScrollOfLullaby, ScrollOfMagicMapping, ScrollOfMetamorphosis,
    ScrollOfMirrorImage, ScrollOfMysticalEnergy, ScrollOfPassage,
    ScrollOfPrismaticImage, ScrollOfPsionicBlast, ScrollOfRage,
    ScrollOfRecharging, ScrollOfRemoveCurse, ScrollOfRetribution,
    ScrollOfSirensSong, ScrollOfTeleportation, ScrollOfTerror,
    ScrollOfTransmutation, ScrollOfUpgrade,
)
from app.engine.entities.items_wands import Wand
from app.engine.entities.runestones import (
    StoneOfAggression, StoneOfAugmentation, StoneOfBlast, StoneOfBlink,
    StoneOfClairvoyance, StoneOfDeepSleep, StoneOfDetectMagic,
    StoneOfEnchantment, StoneOfFear, StoneOfFlock, StoneOfIntuition,
    StoneOfShock,
)
from app.engine.entities.trinkets import Trinket, TrinketCatalyst


def new_item_id() -> str:
    return str(_uuid.uuid4())


def is_kind_identified(game, item: ItemBase) -> bool:
    # SPD Item.isIdentified for recipe purposes: potions/scrolls hinge on the
    # party-shared kind knowledge; everything else phase 1 accepts is always
    # identified (food, GooBlob, trinkets, seeds, stones).
    if isinstance(item, (Potion, Scroll)):
        return item.kind in game.identified_kinds
    return True


def usable_in_recipe(item: ItemBase) -> bool:
    # SPD Recipe.usableInRecipe. Remake's Trinket is equipable (KindofMisc)
    # unlike SPD's, so it is allowed explicitly. Upgradable missile weapons
    # (the only SPD equipment exception) aren't modeled in the remake yet.
    if isinstance(item, Trinket):
        return not item.cursed
    if isinstance(item, Wand):
        return item.cursed_known and not item.cursed
    if isinstance(item, EquipableItem):
        return False
    return not item.cursed


class Recipe:
    def test_ingredients(self, game, units: List[ItemBase]) -> bool:
        raise NotImplementedError

    def cost(self, units: List[ItemBase]) -> int:
        raise NotImplementedError

    def brew(self, game, units: List[ItemBase]) -> Optional[ItemBase]:
        """Roll and return the output item (id assigned), or None if the
        ingredients no longer match. Does not mutate the units."""
        raise NotImplementedError

    def sample_output(self, game, units: List[ItemBase]) -> Optional[ItemBase]:
        """Preview instance; None means "unknown output" (client shows '?')."""
        raise NotImplementedError


@dataclass
class SimpleRecipe(Recipe):
    """Static inputs/output (SPD Recipe.SimpleRecipe)."""
    inputs: List[Tuple[type, int]] = field(default_factory=list)
    energy_cost: int = 0
    output_factory: Callable[[], ItemBase] = None
    out_quantity: int = 1

    def test_ingredients(self, game, units):
        needed = {cls: qty for cls, qty in self.inputs}
        for u in units:
            if not is_kind_identified(game, u):
                return False
            if type(u) in needed:
                needed[type(u)] -= u.quantity
        return all(v <= 0 for v in needed.values())

    def cost(self, units):
        return self.energy_cost

    def brew(self, game, units):
        if not self.test_ingredients(game, units):
            return None
        return self.sample_output(game, units)

    def sample_output(self, game, units):
        out = self.output_factory()
        out.id = new_item_id()
        out.quantity = self.out_quantity
        return out


# Scroll.ScrollToStone mapping (Scroll.java). Remake's StoneOfDetectMagic is
# SPD's current RemoveCurse output.
SCROLL_TO_STONE = {
    ScrollOfIdentify: StoneOfIntuition,
    ScrollOfLullaby: StoneOfDeepSleep,
    ScrollOfMagicMapping: StoneOfClairvoyance,
    ScrollOfMirrorImage: StoneOfFlock,
    ScrollOfRetribution: StoneOfBlast,
    ScrollOfRage: StoneOfAggression,
    ScrollOfRecharging: StoneOfShock,
    ScrollOfRemoveCurse: StoneOfDetectMagic,
    ScrollOfTeleportation: StoneOfBlink,
    ScrollOfTerror: StoneOfFear,
    ScrollOfTransmutation: StoneOfAugmentation,
    ScrollOfUpgrade: StoneOfEnchantment,
}

# ExoticPotion.regToExo (ExoticPotion.java). SPD PotionOfHealing == HealthPotion.
POTION_TO_EXOTIC = {
    PotionOfStrength: PotionOfMastery,
    HealthPotion: PotionOfShielding,
    PotionOfMindVision: PotionOfMagicalSight,
    PotionOfFrost: PotionOfSnapFreeze,
    PotionOfLiquidFlame: PotionOfDragonsBreath,
    PotionOfToxicGas: PotionOfCorrosiveGas,
    PotionOfHaste: PotionOfStamina,
    PotionOfInvisibility: PotionOfShroudingFog,
    PotionOfLevitation: PotionOfStormClouds,
    PotionOfParalyticGas: PotionOfEarthenArmor,
    PotionOfPurity: PotionOfCleansing,
    PotionOfExperience: PotionOfDivineInspiration,
}

# ExoticScroll.regToExo (ExoticScroll.java). SPD's "ScrollOfEnchantment"
# (choice of three enchants) is the remake's ExoticScrollOfEnchantment.
SCROLL_TO_EXOTIC = {
    ScrollOfUpgrade: ExoticScrollOfEnchantment,
    ScrollOfIdentify: ScrollOfDivination,
    ScrollOfRemoveCurse: ScrollOfAntiMagic,
    ScrollOfMirrorImage: ScrollOfPrismaticImage,
    ScrollOfRecharging: ScrollOfMysticalEnergy,
    ScrollOfTeleportation: ScrollOfPassage,
    ScrollOfLullaby: ScrollOfSirensSong,
    ScrollOfMagicMapping: ScrollOfForesight,
    ScrollOfRage: ScrollOfChallenge,
    ScrollOfRetribution: ScrollOfPsionicBlast,
    ScrollOfTerror: ScrollOfDread,
    ScrollOfTransmutation: ScrollOfMetamorphosis,
}


class ScrollToStone(Recipe):
    # Scroll -> 2 runestones, cost 0. Unidentified scrolls allowed; brewing
    # identifies the scroll kind for the party (SPD showIdentify/identify).
    def test_ingredients(self, game, units):
        return len(units) == 1 and type(units[0]) in SCROLL_TO_STONE

    def cost(self, units):
        return 0

    def brew(self, game, units):
        if not self.test_ingredients(game, units):
            return None
        scroll = units[0]
        game.identified_kinds.add(scroll.kind)
        out = SCROLL_TO_STONE[type(scroll)](quantity=2)
        out.id = new_item_id()
        return out

    def sample_output(self, game, units):
        if not self.test_ingredients(game, units):
            return None
        scroll = units[0]
        if scroll.kind not in game.identified_kinds:
            return None
        out = SCROLL_TO_STONE[type(scroll)](quantity=2)
        out.id = new_item_id()
        return out


class _ToExotic(Recipe):
    MAPPING: dict = {}
    COST: int = 0

    def test_ingredients(self, game, units):
        return len(units) == 1 and type(units[0]) in self.MAPPING

    def cost(self, units):
        return self.COST

    def brew(self, game, units):
        if not self.test_ingredients(game, units):
            return None
        return self.sample_output(game, units)

    def sample_output(self, game, units):
        if not self.test_ingredients(game, units):
            return None
        out = self.MAPPING[type(units[0])]()
        out.id = new_item_id()
        out.quantity = 1
        return out


class PotionToExotic(_ToExotic):
    MAPPING = POTION_TO_EXOTIC
    COST = 4


class ScrollToExotic(_ToExotic):
    MAPPING = SCROLL_TO_EXOTIC
    COST = 6


# Seed plant_type -> potion (Potion.SeedToPotion.types). Remake "dreamfoil"
# is SPD Mageroyal. Also consumed by SeedToPotion/UnstableBrew.
SEED_TO_POTION = {
    "blindweed": PotionOfInvisibility,
    "dreamfoil": PotionOfPurity,
    "earthroot": PotionOfParalyticGas,
    "fadeleaf": PotionOfMindVision,
    "firebloom": PotionOfLiquidFlame,
    "icecap": PotionOfFrost,
    "rotberry": PotionOfStrength,
    "sorrowmoss": PotionOfToxicGas,
    "starflower": PotionOfExperience,
    "stormvine": PotionOfLevitation,
    "sungrass": HealthPotion,
    "swiftthistle": PotionOfHaste,
}


class UnstableBrewRecipe(Recipe):
    # UnstableBrew.Recipe: any regular-or-exotic potion + any seed, cost 1.
    def test_ingredients(self, game, units):
        if len(units) != 2:
            return False
        potion = seed = False
        for u in units:
            if isinstance(u, Seed) and u.plant_type in SEED_TO_POTION:
                seed = True
            elif type(u) in POTION_TO_EXOTIC or type(u) in POTION_TO_EXOTIC.values():
                potion = True
        return potion and seed

    def cost(self, units):
        return 1

    def brew(self, game, units):
        if not self.test_ingredients(game, units):
            return None
        return self.sample_output(game, units)

    def sample_output(self, game, units):
        out = UnstableBrew()
        out.id = new_item_id()
        return out


# StewedMeat.oneMeat/twoMeat/threeMeat (StewedMeat.java).
STEWED_ONE = SimpleRecipe(inputs=[(MysteryMeat, 1)], energy_cost=1,
                          output_factory=StewedMeat, out_quantity=1)
STEWED_TWO = SimpleRecipe(inputs=[(MysteryMeat, 2)], energy_cost=2,
                          output_factory=StewedMeat, out_quantity=2)
STEWED_THREE = SimpleRecipe(inputs=[(MysteryMeat, 3)], energy_cost=2,
                            output_factory=StewedMeat, out_quantity=3)


class MeatPieRecipe(Recipe):
    # MeatPie.Recipe: a pasty + a generic ration + any meat, cost 6. SPD's
    # generic Food.class is the remake's Ration (SmallRation doesn't count).
    _MEATS = (MysteryMeat, StewedMeat, ChargrilledMeat, FrozenCarpaccio)

    def test_ingredients(self, game, units):
        pasty = ration = meat = False
        for u in units:
            if isinstance(u, Pasty):
                pasty = True
            elif type(u) is Ration:
                ration = True
            elif isinstance(u, self._MEATS):
                meat = True
        return pasty and ration and meat

    def cost(self, units):
        return 6

    def brew(self, game, units):
        if not self.test_ingredients(game, units):
            return None
        return self.sample_output(game, units)

    def sample_output(self, game, units):
        out = MeatPie()
        out.id = new_item_id()
        return out


# Generator.java POTION classes + defaultProbs — random pool for SeedToPotion.
POTION_GEN_CLASSES = [
    PotionOfStrength, HealthPotion, PotionOfMindVision, PotionOfFrost,
    PotionOfLiquidFlame, PotionOfToxicGas, PotionOfHaste, PotionOfInvisibility,
    PotionOfLevitation, PotionOfParalyticGas, PotionOfPurity, PotionOfExperience,
]
POTION_GEN_PROBS = [0, 3, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1]


def _random_gen_potion():
    return _random.choices(POTION_GEN_CLASSES, weights=POTION_GEN_PROBS)[0]()


class SeedToPotionRecipe(Recipe):
    """Potion.SeedToPotion: 3 seeds -> a potion, cost 0.

    2 distinct seed types: 1/4 chance of a random potion; 3 distinct: 1/2.
    Otherwise the potion of a random ingredient's type. A single seed type
    identifies the output. HealthPotion output is rate-limited by the
    COOKING_HP counter (reroll chance grows each brewed health potion)."""

    def test_ingredients(self, game, units):
        return (len(units) == 3
                and all(isinstance(u, Seed) and u.quantity >= 1
                        and u.plant_type in SEED_TO_POTION for u in units))

    def cost(self, units):
        return 0

    def brew(self, game, units):
        if not self.test_ingredients(game, units):
            return None
        plant_types = []
        for u in units:
            if u.plant_type not in plant_types:
                plant_types.append(u.plant_type)

        if ((len(plant_types) == 2 and _random.randint(0, 3) == 0)
                or (len(plant_types) == 3 and _random.randint(0, 1) == 0)):
            result = _random_gen_potion()
        else:
            result = SEED_TO_POTION[_random.choice(units).plant_type]()

        if len(plant_types) == 1:
            game.identified_kinds.add(result.kind)

        while (isinstance(result, HealthPotion)
               and _random.randint(0, 9) < game.drop_counters.get("cooking_hp", 0)):
            result = _random_gen_potion()
        if isinstance(result, HealthPotion):
            game.drop_counters["cooking_hp"] = game.drop_counters.get("cooking_hp", 0) + 1

        result.id = new_item_id()
        return result

    def sample_output(self, game, units):
        return None  # random output: '?' preview (SPD shows a placeholder)


# Recipe.java one-ingredient brews/elixirs (each SPD <class>.Recipe block).
BREW_ELIXIR_ONE = [
    SimpleRecipe(inputs=[(PotionOfFrost, 1)], energy_cost=8,
                 output_factory=BlizzardBrew),
    SimpleRecipe(inputs=[(PotionOfLiquidFlame, 1)], energy_cost=12,
                 output_factory=InfernalBrew),
    SimpleRecipe(inputs=[(PotionOfStormClouds, 1)], energy_cost=8,
                 output_factory=AquaBrew, out_quantity=8),
    SimpleRecipe(inputs=[(PotionOfParalyticGas, 1)], energy_cost=10,
                 output_factory=ShockingBrew),
    SimpleRecipe(inputs=[(PotionOfDragonsBreath, 1)], energy_cost=10,
                 output_factory=ElixirOfDragonsBlood),
    SimpleRecipe(inputs=[(PotionOfSnapFreeze, 1)], energy_cost=6,
                 output_factory=ElixirOfIcyTouch),
    SimpleRecipe(inputs=[(PotionOfCorrosiveGas, 1)], energy_cost=8,
                 output_factory=ElixirOfToxicEssence),
    SimpleRecipe(inputs=[(PotionOfStrength, 1)], energy_cost=16,
                 output_factory=ElixirOfMight),
    SimpleRecipe(inputs=[(PotionOfLevitation, 1)], energy_cost=10,
                 output_factory=ElixirOfFeatherFall),
]

BREW_ELIXIR_TWO = [
    UnstableBrewRecipe(),
    SimpleRecipe(inputs=[(PotionOfToxicGas, 1), (GooBlob, 1)], energy_cost=1,
                 output_factory=CausticBrew),
    SimpleRecipe(inputs=[(PotionOfEarthenArmor, 1), (GooBlob, 1)], energy_cost=8,
                 output_factory=ElixirOfArcaneArmor),
    SimpleRecipe(inputs=[(HealthPotion, 1), (GooBlob, 1)], energy_cost=6,
                 output_factory=ElixirOfAquaticRejuvenation),
]


class TrinketCatalystRecipe(Recipe):
    # TrinketCatalyst.Recipe: cost 6. brew() returns None: the mixin rolls 4
    # trinket kinds onto the catalyst and the catalyst is consumed only when
    # the player picks one (survives disconnect, mirrors SPD's re-collect).
    def test_ingredients(self, game, units):
        return len(units) == 1 and isinstance(units[0], TrinketCatalyst)

    def cost(self, units):
        # An already-rolled catalyst re-opens its choice for free (re-collect);
        # units are copies of the real stack, so rolled_kinds is visible here.
        return 0 if units[0].rolled_kinds else 6

    def brew(self, game, units):
        return None

    def sample_output(self, game, units):
        return None


class UpgradeTrinketRecipe(Recipe):
    # Trinket.UpgradeTrinket: one trinket below level 3; costs its
    # upgrade_energy_cost(); output is a fresh copy one level higher.
    def test_ingredients(self, game, units):
        return (len(units) == 1 and isinstance(units[0], Trinket)
                and units[0].level < 3)

    def cost(self, units):
        return units[0].upgrade_energy_cost()

    def brew(self, game, units):
        if not self.test_ingredients(game, units):
            return None
        return self.sample_output(game, units)

    def sample_output(self, game, units):
        out = type(units[0])(level=units[0].level + 1, level_known=True)
        out.id = new_item_id()
        return out
