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
from app.engine.entities.items_equip import *
from app.engine.entities.items_wands import *
from app.engine.entities.items_potions import *
from app.engine.entities.items_scrolls import *
from app.engine.entities.items_consumable import *
from app.engine.entities.items_artifacts import *


class Scenery(ItemBase):
    # Non-pickable floor decoration (e.g. graves). Mirrors SPD heaps that aren't
    # collectable. Kept out of AnyItem since it only ever lives on the ground.
    kind: Literal["scenery"] = "scenery"
    type: str = "scenery"
    category: ClassVar[str] = ItemCategory.SCENERY


class Chest(ItemBase):
    kind: Literal["chest"] = "chest"
    name: str = "Chest"
    type: str = "chest"
    category: ClassVar[str] = ItemCategory.SCENERY
    chest_type: str = "CHEST"
    opened: bool = False
    contents: List["AnyItem"] = Field(default_factory=list)
    item_category: Optional[str] = None


class Bag(ItemBase):
    kind: Literal["bag"] = "bag"
    type: str = "bag"
    category: ClassVar[str] = ItemCategory.BAG
    is_bag: ClassVar[bool] = True
    unique: bool = True
    capacity: int = 20
    items: List["AnyItem"] = Field(default_factory=list)
    DESC: ClassVar[str] = "A container that expands how much you can carry. Open it to view its contents."

    # None => general backpack (accepts everything). A set => a specialised
    # sub-bag that only accepts those item categories (SPD's pouches/holders).
    accepts: ClassVar[Optional[set]] = None

    def default_action(self) -> Optional[str]:
        return Action.OPEN

    # --- queries -----------------------------------------------------------
    def _local_get(self, item_id: str) -> Optional["ItemBase"]:
        return next((i for i in self.items if i.id == item_id), None)

    def find(self, item_id: str) -> Optional["ItemBase"]:
        local = self._local_get(item_id)
        if local is not None:
            return local
        for sub in self.items:
            if isinstance(sub, Bag):
                found = sub.find(item_id)
                if found is not None:
                    return found
        return None

    def contains(self, item_id: str) -> bool:
        return self.find(item_id) is not None

    def _used_slots(self) -> int:
        # Sub-bags expand storage in SPD rather than consuming a slot.
        return len([i for i in self.items if not isinstance(i, Bag)])

    def _accepts_extra(self, item: "ItemBase") -> bool:
        # Hook for specialised bags that accept a specific item class outside
        # of their category set (e.g. VelvetPouch + GooBlob in SPD).
        return False

    def can_hold(self, item: "ItemBase") -> bool:
        if isinstance(item, Bag) and self.accepts is not None:
            return False  # specialised pouches can't nest bags
        if (self.accepts is not None and item.category not in self.accepts
                and not self._accepts_extra(item)):
            return False
        if item.stackable:
            for it in self.items:
                if it.is_similar(item):
                    return True
        return self._used_slots() < self.capacity

    # --- mutations ---------------------------------------------------------
    def _sort(self) -> None:
        self.items.sort(key=lambda i: CATEGORY_ORDER.index(i.category)
                        if i.category in CATEGORY_ORDER else len(CATEGORY_ORDER))

    def collect(self, item: "ItemBase") -> bool:
        if item.quantity <= 0:
            return True
        # Prefer a matching specialised sub-bag (SPD auto-sorts into pouches).
        for sub in self.items:
            if isinstance(sub, Bag) and sub.can_hold(item) and sub.collect(item):
                return True
        if item.stackable:
            for it in self.items:
                if it.is_similar(item):
                    it.merge(item)
                    return True
        if not self.can_hold(item):
            return False
        self.items.append(item)
        self._sort()
        return True

    def detach(self, item_id: str) -> Optional["ItemBase"]:
        # Remove a single unit (splits a stack), recursing into sub-bags.
        item = self._local_get(item_id)
        if item is None:
            for sub in self.items:
                if isinstance(sub, Bag):
                    r = sub.detach(item_id)
                    if r is not None:
                        return r
            return None
        if item.stackable and item.quantity > 1:
            return item.split(1)
        self.items.remove(item)
        return item

    def detach_all(self, item_id: str) -> Optional["ItemBase"]:
        item = self._local_get(item_id)
        if item is not None:
            self.items.remove(item)
            return item
        for sub in self.items:
            if isinstance(sub, Bag):
                r = sub.detach_all(item_id)
                if r is not None:
                    return r
        return None

    def grab_items(self, source: "Bag") -> None:
        # Pull every item this (specialised) bag accepts out of `source`.
        if self.accepts is None:
            return
        movable = [i for i in list(source.items)
                   if not isinstance(i, Bag)
                   and (i.category in self.accepts or self._accepts_extra(i))]
        for it in movable:
            source.items.remove(it)
            self.collect(it)


class VelvetPouch(Bag):
    kind: Literal["velvet_pouch"] = "velvet_pouch"
    name: str = "Velvet Pouch"
    capacity: int = 19
    accepts: ClassVar[Optional[set]] = {ItemCategory.SEED, ItemCategory.RUNESTONE}
    DESC: ClassVar[str] = "This small velvet pouch can store seeds and other small alchemy ingredients."

    def _accepts_extra(self, item: "ItemBase") -> bool:
        return isinstance(item, GooBlob)

    def value(self, identified: bool = False) -> int:
        return 30


class ScrollHolder(Bag):
    kind: Literal["scroll_holder"] = "scroll_holder"
    name: str = "Scroll Holder"
    accepts: ClassVar[Optional[set]] = {ItemCategory.SCROLL}

    def value(self, identified: bool = False) -> int:
        return 40


class MagicalHolster(Bag):
    kind: Literal["magical_holster"] = "magical_holster"
    name: str = "Magical Holster"
    accepts: ClassVar[Optional[set]] = {ItemCategory.WAND, ItemCategory.STONE}

    def value(self, identified: bool = False) -> int:
        return 60


class PotionBandolier(Bag):
    kind: Literal["potion_bandolier"] = "potion_bandolier"
    name: str = "Potion Bandolier"
    accepts: ClassVar[Optional[set]] = {ItemCategory.POTION}

    def value(self, identified: bool = False) -> int:
        return 40


# Discriminated union of everything that can live inside a Bag / equip slot.
# Keyed by `kind`, so member order is irrelevant and nested items serialize as
# their concrete type. Server never validates inbound items, so this exists only
# for clean outbound dumps + a stable client contract.
from app.engine.entities.rings import (
    RingOfAccuracy, RingOfEvasion, RingOfHaste, RingOfFuror,
    RingOfMight, RingOfTenacity, RingOfEnergy, RingOfArcana, RingOfSharpshooting,
)  # noqa: E402
from app.engine.entities.rings_tier3 import (
    RingOfForce, RingOfElements, RingOfWealth,
)  # noqa: E402
from app.engine.entities.trinkets import (
    RatSkull, ParchmentScrap, PetrifiedSeed, ExoticCrystals,
    MossyClump, DimensionalSundial, ThirteenLeafClover, TrapMechanism,
    MimicTooth, WondrousResin, EyeOfNewt, SaltCube, VialOfBlood,
    ShardOfOblivion, ChaoticCenser, FerretTuft, CrackedSpyglass,
    TrinketCatalyst,
)  # noqa: E402
from app.engine.entities.runestones import (
    Runestone, InventoryStone,
    StoneOfBlast, StoneOfBlink, StoneOfDeepSleep, StoneOfClairvoyance,
    StoneOfAggression, StoneOfFlock, StoneOfShock, StoneOfFear,
    StoneOfIntuition, StoneOfAugmentation, StoneOfDetectMagic, StoneOfEnchantment,
)  # noqa: E402
from app.engine.entities.items_bombs import (
    Bomb, Firebomb, FrostBomb, SmokeBomb, FlashBangBomb, HolyBomb,
    RegrowthBomb, WoollyBomb, Noisemaker, ArcaneBomb, ShrapnelBomb, MetalShard,
)  # noqa: E402

AnyItem = Annotated[
    Union[
        MeleeWeapon, Dagger, WornShortsword, Bow, SpiritBow, Staff, MissileWeapon,
        Armor, ClothArmor, LeatherArmor, MailArmor, ScaleArmor, PlateArmor, Ring, RingOfAccuracy, RingOfEvasion, RingOfHaste, RingOfFuror,
        RingOfMight, RingOfTenacity, RingOfEnergy, RingOfArcana, RingOfSharpshooting,
        RingOfForce, RingOfElements, RingOfWealth,
        Artifact, BrokenSeal, CloakOfShadows, DriedRose,
        AlchemistsToolkit, CapeOfThorns, ChaliceOfBlood, EtherealChains,
        HolyTome, HornOfPlenty, LloydsBeacon, MasterThievesArmband,
        SandalsOfNature, SkeletonKey, TalismanOfForesight,
        TimekeepersHourglass, UnstableSpellbook,
        DamageWand,
        WandOfMagicMissile, WandOfFireblast, WandOfFrost, WandOfLightning,
        WandOfDisintegration, WandOfPrismaticLight, WandOfBlastWave,
        WandOfTransfusion, WandOfCorrosion, WandOfCorruption,
        WandOfRegrowth, WandOfWarding, WandOfLivingEarth, CursedWand,
        Wand,
        HealthPotion, RevivingPotion, FuryPotion,
        PotionOfStrength, PotionOfHaste, PotionOfInvisibility, PotionOfLevitation,
        PotionOfMindVision, PotionOfFrost, PotionOfLiquidFlame, PotionOfToxicGas,
        PotionOfParalyticGas, PotionOfPurity, PotionOfExperience,
        ElixirOfAquaticRejuvenation,
        PotionOfCleansing, PotionOfCorrosiveGas, PotionOfDragonsBreath,
        PotionOfEarthenArmor, PotionOfMagicalSight, PotionOfMastery,
        PotionOfShielding, PotionOfShroudingFog, PotionOfSnapFreeze,
        PotionOfStamina, PotionOfStormClouds, PotionOfDivineInspiration,
        ElixirOfArcaneArmor, ElixirOfDragonsBlood, ElixirOfFeatherFall,
        ElixirOfHoneyedHealing, ElixirOfIcyTouch, ElixirOfMight, ElixirOfToxicEssence,
        AquaBrew, BlizzardBrew, CausticBrew, InfernalBrew, ShockingBrew, UnstableBrew,
        Potion,
        ScrollOfRage, ScrollOfMetamorphosis,
        ScrollOfUpgrade, ScrollOfIdentify, ScrollOfMagicMapping, ScrollOfTeleportation,
        ScrollOfRemoveCurse, ScrollOfRecharging, ScrollOfLullaby, ScrollOfTerror,
        ScrollOfMirrorImage, ScrollOfRetribution, ScrollOfTransmutation,
        ScrollOfEnchantment, ExoticScrollOfEnchantment,
        ScrollOfAntiMagic, ScrollOfChallenge, ScrollOfDivination, ScrollOfDread,
        ScrollOfForesight, ScrollOfMysticalEnergy, ScrollOfPassage,
        ScrollOfPrismaticImage, ScrollOfPsionicBlast, ScrollOfSirensSong,
        Scroll,
        Gold,
        MysteryMeat, FrozenCarpaccio, StewedMeat, MeatPie, Berry, SmallRation, Ration, Pasty, ChargrilledMeat, Food,
        Key,
        TenguMask, KingsCrown,
        Seed, Dewdrop, Waterskin, Amulet, Stone, Boomerang, ThrowableDagger, Throwable,
        EnergyCrystal,
        Bomb, Firebomb, FrostBomb, SmokeBomb, FlashBangBomb, HolyBomb,
        RegrowthBomb, WoollyBomb, Noisemaker, ArcaneBomb, ShrapnelBomb,
        MetalShard,
        ArcaneStylus, MagicalInfusion,
        GooBlob, DwarfToken, Petal,
        Chest,
        VelvetPouch, ScrollHolder, MagicalHolster, PotionBandolier, Bag,
        RatSkull, ParchmentScrap, PetrifiedSeed, ExoticCrystals,
        MossyClump, DimensionalSundial, ThirteenLeafClover, TrapMechanism,
        MimicTooth, WondrousResin, EyeOfNewt, SaltCube, VialOfBlood,
        ShardOfOblivion, ChaoticCenser, FerretTuft, CrackedSpyglass,
        TrinketCatalyst,
        StoneOfBlast, StoneOfBlink, StoneOfDeepSleep, StoneOfClairvoyance,
        StoneOfAggression, StoneOfFlock, StoneOfShock, StoneOfFear,
        StoneOfIntuition, StoneOfAugmentation, StoneOfDetectMagic, StoneOfEnchantment,
    ],
    Field(discriminator="kind"),
]


# --- quickslots ------------------------------------------------------------
