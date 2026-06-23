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
"""Admin item catalog: one representative instance of every `AnyItem` kind.

Backs the admin "give item" debug tool (`GET /api/items/catalog` and the
`ADMIN_GIVE_ITEM` message). Not used by normal gameplay systems.
"""

from typing import Callable, List, Optional, TypedDict

from app.engine.entities.base import (
    Amulet,
    Armor,
    Artifact,
    Bag,
    Berry,
    Boomerang,
    Bow,
    BrokenSeal,
    SpiritBow,
    ChargrilledMeat,
    CloakOfShadows,
    DriedRose,
    Dagger,
    Dewdrop,
    DwarfToken,
    ElixirOfAquaticRejuvenation,
    Food,
    FuryPotion,
    GooBlob,
    Petal,
    Gold,
    HealthPotion,
    ItemBase,
    Key,
    KingsCrown,
    MagicalHolster,
    MeleeWeapon,
    MissileWeapon,
    MysteryMeat,
    Pasty,
    Potion,
    PotionBandolier,
    PotionOfExperience,
    PotionOfFrost,
    PotionOfHaste,
    PotionOfInvisibility,
    PotionOfLevitation,
    PotionOfLiquidFlame,
    PotionOfMindVision,
    PotionOfParalyticGas,
    PotionOfPurity,
    PotionOfStrength,
    PotionOfToxicGas,
    Ration,
    RevivingPotion,
    Ring,
    RingOfAccuracy,
    RingOfEvasion,
    RingOfHaste,
    RingOfFuror,
    RingOfMight,
    RingOfTenacity,
    RingOfEnergy,
    RingOfArcana,
    RingOfSharpshooting,
    Scroll,
    ScrollHolder,
    ScrollOfIdentify,
    ScrollOfLullaby,
    ScrollOfMagicMapping,
    ScrollOfMetamorphosis,
    ScrollOfMirrorImage,
    ScrollOfRage,
    ScrollOfRecharging,
    ScrollOfRemoveCurse,
    ScrollOfRetribution,
    ScrollOfTeleportation,
    ScrollOfTerror,
    ScrollOfTransmutation,
    ScrollOfUpgrade,
    Seed,
    SmallRation,
    Staff,
    Stone,
    Throwable,
    ThrowableDagger,
    TenguMask,
    VelvetPouch,
    Wand,
    WandOfMagicMissile,
    WandOfFireblast,
    WandOfFrost,
    WandOfLightning,
    WandOfDisintegration,
    WandOfPrismaticLight,
    WandOfBlastWave,
    WandOfTransfusion,
    WandOfCorrosion,
    WandOfCorruption,
    WandOfRegrowth,
    WandOfWarding,
    WandOfLivingEarth,
    Waterskin,
    WornShortsword,
)


class ItemCatalogEntry(TypedDict):
    kind: str
    name: str
    category: str


# (kind, name, category, factory). `name` is the catalog display name and is
# also used as the item's `name` field for kinds that require one.
_CATALOG: List[tuple] = [
    # Weapons
    ("melee_weapon", "Short Sword", "weapon", lambda: MeleeWeapon(name="Short Sword", tier=1)),
    ("dagger", "Dagger", "weapon", lambda: Dagger()),
    ("worn_shortsword", "Worn Shortsword", "weapon", lambda: WornShortsword()),
    ("bow", "Bow", "weapon", lambda: Bow()),
    ("spirit_bow", "Spirit Bow", "weapon", lambda: SpiritBow()),
    ("staff", "Staff", "weapon", lambda: Staff()),
    ("missile_weapon", "Throwing Knife", "weapon", lambda: MissileWeapon(name="Throwing Knife", tier=1)),

    # Armor / accessories
    ("armor", "Leather Armor", "armor", lambda: Armor(name="Leather Armor", tier=1)),
    ("ring", "Ring", "ring", lambda: Ring(name="Ring")),
    ("ring_accuracy", "Ring of Accuracy", "ring", lambda: RingOfAccuracy()),
    ("ring_evasion", "Ring of Evasion", "ring", lambda: RingOfEvasion()),
    ("ring_haste", "Ring of Haste", "ring", lambda: RingOfHaste()),
    ("ring_furor", "Ring of Furor", "ring", lambda: RingOfFuror()),
    ("ring_might", "Ring of Might", "ring", lambda: RingOfMight()),
    ("ring_tenacity", "Ring of Tenacity", "ring", lambda: RingOfTenacity()),
    ("ring_energy", "Ring of Energy", "ring", lambda: RingOfEnergy()),
    ("ring_arcana", "Ring of Arcana", "ring", lambda: RingOfArcana()),
    ("ring_sharpshooting", "Ring of Sharpshooting", "ring", lambda: RingOfSharpshooting()),
    ("artifact", "Artifact", "artifact", lambda: Artifact(name="Artifact")),
    ("broken_seal", "Broken Seal", "artifact", lambda: BrokenSeal()),
    ("cloak_of_shadows", "Cloak of Shadows", "artifact", lambda: CloakOfShadows()),
    ("dried_rose", "Dried Rose", "artifact", lambda: DriedRose()),
    ("wand", "Wand", "wand", lambda: Wand(name="Wand")),
    ("wand_magic_missile", "Wand of Magic Missile", "wand", lambda: WandOfMagicMissile()),
    ("wand_fireblast", "Wand of Fireblast", "wand", lambda: WandOfFireblast()),
    ("wand_frost", "Wand of Frost", "wand", lambda: WandOfFrost()),
    ("wand_lightning", "Wand of Lightning", "wand", lambda: WandOfLightning()),
    ("wand_disintegration", "Wand of Disintegration", "wand", lambda: WandOfDisintegration()),
    ("wand_prismatic_light", "Wand of Prismatic Light", "wand", lambda: WandOfPrismaticLight()),
    ("wand_blast_wave", "Wand of Blast Wave", "wand", lambda: WandOfBlastWave()),
    ("wand_transfusion", "Wand of Transfusion", "wand", lambda: WandOfTransfusion()),
    ("wand_corrosion", "Wand of Corrosion", "wand", lambda: WandOfCorrosion()),
    ("wand_corruption", "Wand of Corruption", "wand", lambda: WandOfCorruption()),
    ("wand_regrowth", "Wand of Regrowth", "wand", lambda: WandOfRegrowth()),
    ("wand_warding", "Wand of Warding", "wand", lambda: WandOfWarding()),
    ("wand_living_earth", "Wand of Living Earth", "wand", lambda: WandOfLivingEarth()),

    # Potions
    ("health_potion", "Health Potion", "potion", lambda: HealthPotion()),
    ("reviving_potion", "Reviving Potion", "potion", lambda: RevivingPotion()),
    ("fury_potion", "Potion of Fury", "potion", lambda: FuryPotion()),
    ("potion_of_strength", "Potion of Strength", "potion", lambda: PotionOfStrength()),
    ("potion_of_haste", "Potion of Haste", "potion", lambda: PotionOfHaste()),
    ("potion_of_invisibility", "Potion of Invisibility", "potion", lambda: PotionOfInvisibility()),
    ("potion_of_levitation", "Potion of Levitation", "potion", lambda: PotionOfLevitation()),
    ("potion_of_mind_vision", "Potion of Mind Vision", "potion", lambda: PotionOfMindVision()),
    ("potion_of_frost", "Potion of Frost", "potion", lambda: PotionOfFrost()),
    ("potion_of_liquid_flame", "Potion of Liquid Flame", "potion", lambda: PotionOfLiquidFlame()),
    ("potion_of_toxic_gas", "Potion of Toxic Gas", "potion", lambda: PotionOfToxicGas()),
    ("potion_of_paralytic_gas", "Potion of Paralytic Gas", "potion", lambda: PotionOfParalyticGas()),
    ("potion_of_purity", "Potion of Purity", "potion", lambda: PotionOfPurity()),
    ("potion_of_experience", "Potion of Experience", "potion", lambda: PotionOfExperience()),
    ("elixir_aqua_rejuv", "Elixir of Aquatic Rejuvenation", "potion", lambda: ElixirOfAquaticRejuvenation()),
    ("potion", "Potion", "potion", lambda: Potion(name="Potion")),

    # Scrolls
    ("scroll_of_rage", "Scroll of Rage", "scroll", lambda: ScrollOfRage()),
    ("scroll_of_metamorphosis", "Scroll of Metamorphosis", "scroll", lambda: ScrollOfMetamorphosis()),
    ("scroll_of_upgrade", "Scroll of Upgrade", "scroll", lambda: ScrollOfUpgrade()),
    ("scroll_of_identify", "Scroll of Identify", "scroll", lambda: ScrollOfIdentify()),
    ("scroll_of_magic_mapping", "Scroll of Magic Mapping", "scroll", lambda: ScrollOfMagicMapping()),
    ("scroll_of_teleportation", "Scroll of Teleportation", "scroll", lambda: ScrollOfTeleportation()),
    ("scroll_of_remove_curse", "Scroll of Remove Curse", "scroll", lambda: ScrollOfRemoveCurse()),
    ("scroll_of_recharging", "Scroll of Recharging", "scroll", lambda: ScrollOfRecharging()),
    ("scroll_of_lullaby", "Scroll of Lullaby", "scroll", lambda: ScrollOfLullaby()),
    ("scroll_of_terror", "Scroll of Terror", "scroll", lambda: ScrollOfTerror()),
    ("scroll_of_mirror_image", "Scroll of Mirror Image", "scroll", lambda: ScrollOfMirrorImage()),
    ("scroll_of_retribution", "Scroll of Retribution", "scroll", lambda: ScrollOfRetribution()),
    ("scroll_of_transmutation", "Scroll of Transmutation", "scroll", lambda: ScrollOfTransmutation()),

    # Currency
    ("gold", "Gold", "currency", lambda: Gold(name="Gold", quantity=100)),

    # Food
    ("mystery_meat", "Mystery Meat", "food", lambda: MysteryMeat()),
    ("berry", "Berry", "food", lambda: Berry()),
    ("small_ration", "Small Ration", "food", lambda: SmallRation()),
    ("ration", "Ration", "food", lambda: Ration()),
    ("pasty", "Pasty", "food", lambda: Pasty()),
    ("chargrilled_meat", "Chargrilled Meat", "food", lambda: ChargrilledMeat()),
    ("food", "Food", "food", lambda: Food(name="Food")),

    # Misc
    ("key", "Key", "misc", lambda: Key(name="Key")),
    ("seed", "Seed of Sunlight", "misc", lambda: Seed(name="Seed of Sunlight")),
    ("dewdrop", "Dewdrop", "misc", lambda: Dewdrop()),
    ("waterskin", "Waterskin", "misc", lambda: Waterskin()),
    ("stone", "Stone", "misc", lambda: Stone()),
    ("boomerang", "Boomerang", "misc", lambda: Boomerang()),
    ("throwable_dagger", "Throwable Dagger", "misc", lambda: ThrowableDagger()),
    ("throwable", "Throwable", "misc", lambda: Throwable(name="Throwable")),
    ("goo_blob", "Goo Blob", "misc", lambda: GooBlob()),
    ("petal", "Petal", "misc", lambda: Petal()),
    ("dwarf_token", "Dwarf Token", "misc", lambda: DwarfToken()),
    ("tengu_mask", "Tengu's Mask", "misc", lambda: TenguMask()),
    ("kings_crown", "King's Crown", "misc", lambda: KingsCrown()),
    ("amulet", "Amulet of Yendor", "misc", lambda: Amulet()),

    # Containers
    ("velvet_pouch", "Velvet Pouch", "container", lambda: VelvetPouch()),
    ("scroll_holder", "Scroll Holder", "container", lambda: ScrollHolder()),
    ("magical_holster", "Magical Holster", "container", lambda: MagicalHolster()),
    ("potion_bandolier", "Potion Bandolier", "container", lambda: PotionBandolier()),
    ("bag", "Bag", "container", lambda: Bag(name="Bag")),
]

_FACTORIES: dict = {kind: factory for kind, _name, _category, factory in _CATALOG}


def get_item_catalog() -> List[ItemCatalogEntry]:
    """Returns the full catalog as plain dicts for the REST endpoint."""
    return [{"kind": kind, "name": name, "category": category} for kind, name, category, _factory in _CATALOG]


def make_catalog_item(item_kind: str) -> Optional[ItemBase]:
    """Constructs a fresh instance of the given catalog kind, or None if unknown."""
    factory: Optional[Callable[[], ItemBase]] = _FACTORIES.get(item_kind)
    return factory() if factory is not None else None


# Scroll of Transmutation: broad item groups and the catalog kinds within
# each. `_apply_transmutation` (scroll_actions.py) picks a different kind from
# the same group as the target item.
# NOTE: TRANSMUTE_GROUPS["scroll"] excludes scroll_of_transmutation to prevent
# self-transmutation. Use FLOOR_SCROLL_KINDS for random floor loot pools.
TRANSMUTE_GROUPS: dict = {
    # Staff is grouped with melee weapons: there's no separate "magic weapon"
    # transmute pool in this codebase.
    "weapon_melee": ["melee_weapon", "dagger", "staff"],
    "weapon_missile": ["bow", "missile_weapon"],
    "armor": ["armor"],
    "wand": [kind for kind, _name, category, _factory in _CATALOG
             if category == "wand"],
    "ring": ["ring"] + [kind for kind, _name, category, _factory in _CATALOG
                         if category == "ring" and kind != "ring"],
    "artifact": [kind for kind, _name, category, _factory in _CATALOG
                 if category == "artifact" and kind != "artifact"],
    "potion": [kind for kind, _name, category, _factory in _CATALOG
               if category == "potion" and kind != "potion"],
    "scroll": [kind for kind, _name, category, _factory in _CATALOG
               if category == "scroll" and kind != "scroll_of_transmutation"],
    "seed": [kind for kind, _name, category, _factory in _CATALOG
             if category == "misc" and kind == "seed"],
    "stone": [kind for kind, _name, category, _factory in _CATALOG
              if category == "misc" and kind == "stone"],
}

# All scroll kinds including scroll_of_transmutation — for random floor loot.
FLOOR_SCROLL_KINDS: list = [
    kind for kind, _name, category, _factory in _CATALOG if category == "scroll"
]
