# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
from __future__ import annotations

import uuid as _uuid
import random as _random
from typing import Annotated, ClassVar, Literal, Optional, List, Dict, Tuple, Union

from pydantic import BaseModel, Field, computed_field, model_validator, SerializeAsAny

from app.engine.entities.buffs import Buff, add_buff, remove_buff, has_buff, get_buff
from app.engine.entities.subclasses import SubclassInfo, TalentInfo, Talent
from app.engine.entities.weapon_defs import WEAPON_DEFS

from app.engine.entities.base import *  # noqa: F401,F403


class Potion(ItemBase):
    kind: Literal["potion"] = "potion"
    type: str = "potion"
    category: ClassVar[str] = ItemCategory.POTION
    stackable: ClassVar[bool] = True
    effect: str = ""
    # Shown only once the potion's type is identified; the masked generic text is
    # substituted server-side for unidentified potions.
    DESC: ClassVar[str] = "A magical potion. Drink it to release its effect."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.DRINK] + super().actions(player)

    def default_action(self) -> Optional[str]:
        return Action.DRINK

    def value(self, identified: bool = False) -> int:
        return 30 * self.quantity


class HealthPotion(Potion):
    kind: Literal["health_potion"] = "health_potion"
    name: str = "Health Potion"
    effect: str = "regen"
    DESC: ClassVar[str] = "Drinking this potion restores a good portion of your health over a short time."


class RevivingPotion(Potion):
    kind: Literal["reviving_potion"] = "reviving_potion"
    name: str = "Reviving Potion"
    effect: str = "revive"
    DESC: ClassVar[str] = "A potent elixir that can bring a fallen hero back from the brink."


class FuryPotion(Potion):
    kind: Literal["fury_potion"] = "fury_potion"
    name: str = "Potion of Fury"
    effect: str = "fury"
    DESC: ClassVar[str] = "Drinking this potion fills you with rage, empowering your attacks for a short time."


class PotionOfStrength(Potion):
    kind: Literal["potion_of_strength"] = "potion_of_strength"
    name: str = "Potion of Strength"
    effect: str = "strength"
    DESC: ClassVar[str] = "A fiery red liquid. Drinking it permanently increases your strength by 1."


class PotionOfHaste(Potion):
    kind: Literal["potion_of_haste"] = "potion_of_haste"
    name: str = "Potion of Haste"
    effect: str = "haste"
    DESC: ClassVar[str] = "Drinking this potion briefly doubles your speed."


class PotionOfInvisibility(Potion):
    kind: Literal["potion_of_invisibility"] = "potion_of_invisibility"
    name: str = "Potion of Invisibility"
    effect: str = "invisibility"
    DESC: ClassVar[str] = "Drinking this potion turns you invisible for a short time. Attacking breaks invisibility."


class PotionOfLevitation(Potion):
    kind: Literal["potion_of_levitation"] = "potion_of_levitation"
    name: str = "Potion of Levitation"
    effect: str = "levitation"
    DESC: ClassVar[str] = "Drinking this potion causes you to levitate briefly, letting you fly over pits and traps."


class PotionOfMindVision(Potion):
    kind: Literal["potion_of_mind_vision"] = "potion_of_mind_vision"
    name: str = "Potion of Mind Vision"
    effect: str = "mind_vision"
    DESC: ClassVar[str] = "Drinking this potion lets you sense the minds of nearby creatures through walls."


class PotionOfFrost(Potion):
    kind: Literal["potion_of_frost"] = "potion_of_frost"
    name: str = "Potion of Frost"
    effect: str = "frost"
    DESC: ClassVar[str] = "A cool blue liquid. Drinking it chills you and nearby enemies."


class PotionOfLiquidFlame(Potion):
    kind: Literal["potion_of_liquid_flame"] = "potion_of_liquid_flame"
    name: str = "Potion of Liquid Flame"
    effect: str = "liquid_flame"
    DESC: ClassVar[str] = "Throw or drink this to unleash a burst of fire."


class PotionOfToxicGas(Potion):
    kind: Literal["potion_of_toxic_gas"] = "potion_of_toxic_gas"
    name: str = "Potion of Toxic Gas"
    effect: str = "toxic_gas"
    DESC: ClassVar[str] = "Smashing this potion releases a choking cloud of poison gas."


class PotionOfParalyticGas(Potion):
    kind: Literal["potion_of_paralytic_gas"] = "potion_of_paralytic_gas"
    name: str = "Potion of Paralytic Gas"
    effect: str = "paralytic_gas"
    DESC: ClassVar[str] = "Smashing this releases a gas that paralyzes everything it touches."


class PotionOfPurity(Potion):
    kind: Literal["potion_of_purity"] = "potion_of_purity"
    name: str = "Potion of Purity"
    effect: str = "purity"
    DESC: ClassVar[str] = "Drinking this removes all negative effects and clears nearby gas clouds."


class PotionOfExperience(Potion):
    kind: Literal["potion_of_experience"] = "potion_of_experience"
    name: str = "Potion of Experience"
    effect: str = "experience"
    DESC: ClassVar[str] = "Drinking this immediately grants a full level's worth of experience."

    def value(self, identified: bool = False) -> int:
        return (50 if identified else 30) * self.quantity


class ElixirOfAquaticRejuvenation(Potion):
    kind: Literal["elixir_aqua_rejuv"] = "elixir_aqua_rejuv"
    name: str = "Elixir of Aquatic Rejuvenation"
    effect: str = "aqua_rejuv"
    DESC: ClassVar[str] = "A murky elixir brewed from a Health Potion and a Goo Blob. While its power lasts, you heal whenever you stand in water."

    def value(self, identified: bool = False) -> int:
        return 60 * self.quantity


# ── Exotic Potions ────────────────────────────────────────────────────────────

class PotionOfCleansing(Potion):
    kind: Literal["potion_of_cleansing"] = "potion_of_cleansing"
    name: str = "Potion of Cleansing"
    effect: str = "cleansing"
    DESC: ClassVar[str] = "Removes all debuffs and clears nearby gas clouds."


class PotionOfCorrosiveGas(Potion):
    kind: Literal["potion_of_corrosive_gas"] = "potion_of_corrosive_gas"
    name: str = "Potion of Corrosive Gas"
    effect: str = "corrosive_gas"
    DESC: ClassVar[str] = "Smash to release a cloud of acid that eats through armor."


class PotionOfDragonsBreath(Potion):
    kind: Literal["potion_of_dragons_breath"] = "potion_of_dragons_breath"
    name: str = "Potion of Dragon's Breath"
    effect: str = "dragons_breath"
    DESC: ClassVar[str] = "Drink to breathe fire in the direction you're facing."


class PotionOfEarthenArmor(Potion):
    kind: Literal["potion_of_earthen_armor"] = "potion_of_earthen_armor"
    name: str = "Potion of Earthen Armor"
    effect: str = "earthen_armor"
    DESC: ClassVar[str] = "Hardens your skin like bark, providing temporary armor."


class PotionOfMagicalSight(Potion):
    kind: Literal["potion_of_magical_sight"] = "potion_of_magical_sight"
    name: str = "Potion of Magical Sight"
    effect: str = "magical_sight"
    DESC: ClassVar[str] = "Drastically increases your vision range for a time."


class PotionOfMastery(Potion):
    kind: Literal["potion_of_mastery"] = "potion_of_mastery"
    name: str = "Potion of Mastery"
    effect: str = "mastery"
    DESC: ClassVar[str] = "Lowers the strength requirement of one held item."


class PotionOfShielding(Potion):
    kind: Literal["potion_of_shielding"] = "potion_of_shielding"
    name: str = "Potion of Shielding"
    effect: str = "shielding"
    DESC: ClassVar[str] = "Creates a magical shield that absorbs damage."


class PotionOfShroudingFog(Potion):
    kind: Literal["potion_of_shrouding_fog"] = "potion_of_shrouding_fog"
    name: str = "Potion of Shrouding Fog"
    effect: str = "shrouding_fog"
    DESC: ClassVar[str] = "Smash to create blinding smoke that obscures vision."


class PotionOfSnapFreeze(Potion):
    kind: Literal["potion_of_snap_freeze"] = "potion_of_snap_freeze"
    name: str = "Potion of Snap Freeze"
    effect: str = "snap_freeze"
    DESC: ClassVar[str] = "Smash to instantly freeze everything in a wide area."


class PotionOfStamina(Potion):
    kind: Literal["potion_of_stamina"] = "potion_of_stamina"
    name: str = "Potion of Stamina"
    effect: str = "stamina"
    DESC: ClassVar[str] = "Reduces food cost of all actions for a long duration."


class PotionOfStormClouds(Potion):
    kind: Literal["potion_of_storm_clouds"] = "potion_of_storm_clouds"
    name: str = "Potion of Storm Clouds"
    effect: str = "storm_clouds"
    DESC: ClassVar[str] = "Smash to call a thunderstorm that electrocutes your foes."


class PotionOfDivineInspiration(Potion):
    kind: Literal["potion_of_divine_inspiration"] = "potion_of_divine_inspiration"
    name: str = "Potion of Divine Inspiration"
    effect: str = "divine_inspiration"
    DESC: ClassVar[str] = "Grants a powerful one-time boost to all your talents."


# ── Elixirs ───────────────────────────────────────────────────────────────────

class ElixirOfArcaneArmor(Potion):
    kind: Literal["elixir_of_arcane_armor"] = "elixir_of_arcane_armor"
    name: str = "Elixir of Arcane Armor"
    effect: str = "arcane_armor"
    DESC: ClassVar[str] = "Wraps you in magical protection that reduces all damage."


class ElixirOfDragonsBlood(Potion):
    kind: Literal["elixir_of_dragons_blood"] = "elixir_of_dragons_blood"
    name: str = "Elixir of Dragon's Blood"
    effect: str = "dragons_blood"
    DESC: ClassVar[str] = "Imbues your attacks with searing fire for a time."


class ElixirOfFeatherFall(Potion):
    kind: Literal["elixir_of_feather_fall"] = "elixir_of_feather_fall"
    name: str = "Elixir of Feather Fall"
    effect: str = "feather_fall"
    DESC: ClassVar[str] = "Allows you to fall into pits safely for a long duration."


class ElixirOfHoneyedHealing(Potion):
    kind: Literal["elixir_of_honeyed_healing"] = "elixir_of_honeyed_healing"
    name: str = "Elixir of Honeyed Healing"
    effect: str = "honeyed_healing"
    DESC: ClassVar[str] = "Fully restores health and cleanses all debuffs."


class ElixirOfIcyTouch(Potion):
    kind: Literal["elixir_of_icy_touch"] = "elixir_of_icy_touch"
    name: str = "Elixir of Icy Touch"
    effect: str = "icy_touch"
    DESC: ClassVar[str] = "Imbues your attacks with chilling frost for a time."


class ElixirOfMight(Potion):
    kind: Literal["elixir_of_might"] = "elixir_of_might"
    name: str = "Elixir of Might"
    effect: str = "might"
    DESC: ClassVar[str] = "Permanently increases your strength and maximum health."


class ElixirOfToxicEssence(Potion):
    kind: Literal["elixir_of_toxic_essence"] = "elixir_of_toxic_essence"
    name: str = "Elixir of Toxic Essence"
    effect: str = "toxic_essence"
    DESC: ClassVar[str] = "Imbues your attacks with toxic poison for a time."


# ── Brews (throw-only) ────────────────────────────────────────────────────────

class AquaBrew(Potion):
    kind: Literal["aqua_brew"] = "aqua_brew"
    name: str = "Aqua Brew"
    effect: str = "aqua_brew"
    DESC: ClassVar[str] = "Throw to create a powerful geyser of water."

    def actions(self, player=None) -> List[str]:
        return [Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.THROW


class BlizzardBrew(Potion):
    kind: Literal["blizzard_brew"] = "blizzard_brew"
    name: str = "Blizzard Brew"
    effect: str = "blizzard_brew"
    DESC: ClassVar[str] = "Throw to create a blizzard of ice and snow."

    def actions(self, player=None) -> List[str]:
        return [Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.THROW


class CausticBrew(Potion):
    kind: Literal["caustic_brew"] = "caustic_brew"
    name: str = "Caustic Brew"
    effect: str = "caustic_brew"
    DESC: ClassVar[str] = "Throw to coat a large area in caustic ooze."

    def actions(self, player=None) -> List[str]:
        return [Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.THROW


class InfernalBrew(Potion):
    kind: Literal["infernal_brew"] = "infernal_brew"
    name: str = "Infernal Brew"
    effect: str = "infernal_brew"
    DESC: ClassVar[str] = "Throw to create an intense firestorm."

    def actions(self, player=None) -> List[str]:
        return [Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.THROW


class ShockingBrew(Potion):
    kind: Literal["shocking_brew"] = "shocking_brew"
    name: str = "Shocking Brew"
    effect: str = "shocking_brew"
    DESC: ClassVar[str] = "Throw to electrify a large area."

    def actions(self, player=None) -> List[str]:
        return [Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.THROW


class UnstableBrew(Potion):
    kind: Literal["unstable_brew"] = "unstable_brew"
    name: str = "Unstable Brew"
    effect: str = "unstable_brew"
    DESC: ClassVar[str] = "Throw for a completely random explosive effect."

    def actions(self, player=None) -> List[str]:
        return [Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.THROW
