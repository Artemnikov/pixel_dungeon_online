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
    ClothArmor, LeatherArmor, MailArmor, ScaleArmor, PlateArmor,
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
from app.engine.entities.weapon_defs import WEP_TIER_ORDER
from app.engine.entities.base import make_named_melee_weapon  # noqa: E402
from app.engine.entities.rings_tier3 import RingOfForce, RingOfElements, RingOfWealth  # noqa: E402


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
    ("gloves", "Gloves", "weapon", lambda: make_named_melee_weapon("Gloves")),
    ("rapier", "Rapier", "weapon", lambda: make_named_melee_weapon("Rapier")),
    ("cudgel", "Cudgel", "weapon", lambda: make_named_melee_weapon("Cudgel")),
    ("shortsword", "Shortsword", "weapon", lambda: make_named_melee_weapon("Shortsword")),
    ("hand_axe", "Hand Axe", "weapon", lambda: make_named_melee_weapon("Hand Axe")),
    ("spear", "Spear", "weapon", lambda: make_named_melee_weapon("Spear")),
    ("quarterstaff", "Quarterstaff", "weapon", lambda: make_named_melee_weapon("Quarterstaff")),
    ("dirk", "Dirk", "weapon", lambda: make_named_melee_weapon("Dirk")),
    ("sickle", "Sickle", "weapon", lambda: make_named_melee_weapon("Sickle")),
    ("sword", "Sword", "weapon", lambda: make_named_melee_weapon("Sword")),
    ("mace", "Mace", "weapon", lambda: make_named_melee_weapon("Mace")),
    ("scimitar", "Scimitar", "weapon", lambda: make_named_melee_weapon("Scimitar")),
    ("round_shield", "Round Shield", "weapon", lambda: make_named_melee_weapon("Round Shield")),
    ("sai", "Sai", "weapon", lambda: make_named_melee_weapon("Sai")),
    ("whip", "Whip", "weapon", lambda: make_named_melee_weapon("Whip")),
    ("longsword", "Longsword", "weapon", lambda: make_named_melee_weapon("Longsword")),
    ("battle_axe", "Battle Axe", "weapon", lambda: make_named_melee_weapon("Battle Axe")),
    ("flail", "Flail", "weapon", lambda: make_named_melee_weapon("Flail")),
    ("runic_blade", "Runic Blade", "weapon", lambda: make_named_melee_weapon("Runic Blade")),
    ("assassins_blade", "Assassin's Blade", "weapon", lambda: make_named_melee_weapon("Assassin's Blade")),
    ("crossbow", "Crossbow", "weapon", lambda: make_named_melee_weapon("Crossbow")),
    ("katana", "Katana", "weapon", lambda: make_named_melee_weapon("Katana")),
    ("greatsword", "Greatsword", "weapon", lambda: make_named_melee_weapon("Greatsword")),
    ("war_hammer", "War Hammer", "weapon", lambda: make_named_melee_weapon("War Hammer")),
    ("glaive", "Glaive", "weapon", lambda: make_named_melee_weapon("Glaive")),
    ("greataxe", "Greataxe", "weapon", lambda: make_named_melee_weapon("Greataxe")),
    ("greatshield", "Greatshield", "weapon", lambda: make_named_melee_weapon("Greatshield")),
    ("gauntlet", "Gauntlet", "weapon", lambda: make_named_melee_weapon("Gauntlet")),
    ("war_scythe", "War Scythe", "weapon", lambda: make_named_melee_weapon("War Scythe")),
    ("bow", "Bow", "weapon", lambda: Bow()),
    ("spirit_bow", "Spirit Bow", "weapon", lambda: SpiritBow()),
    ("staff", "Staff", "weapon", lambda: Staff()),
    ("missile_weapon", "Throwing Knife", "weapon", lambda: MissileWeapon(name="Throwing Knife", tier=1)),

    # Armor / accessories
    ("armor", "Armor", "armor", lambda: Armor(name="Armor", tier=1)),
    ("cloth_armor", "Cloth Armor", "armor", lambda: ClothArmor()),
    ("leather_armor", "Leather Armor", "armor", lambda: LeatherArmor()),
    ("mail_armor", "Mail Armor", "armor", lambda: MailArmor()),
    ("scale_armor", "Scale Armor", "armor", lambda: ScaleArmor()),
    ("plate_armor", "Plate Armor", "armor", lambda: PlateArmor()),
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
    ("ring_force", "Ring of Force", "ring", lambda: RingOfForce()),
    ("ring_elements", "Ring of Elements", "ring", lambda: RingOfElements()),
    ("ring_wealth", "Ring of Wealth", "ring", lambda: RingOfWealth()),
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
    "weapon_melee": [kind for kind, _name, _category, _factory in _CATALOG if kind in (
        "melee_weapon", "dagger", "staff",
        "gloves", "rapier", "cudgel",
        "shortsword", "hand_axe", "spear", "quarterstaff", "dirk", "sickle",
        "sword", "mace", "scimitar", "round_shield", "sai", "whip",
        "longsword", "battle_axe", "flail", "runic_blade", "assassins_blade",
        "crossbow", "katana",
        "greatsword", "war_hammer", "glaive", "greataxe", "greatshield",
        "gauntlet", "war_scythe",
    )],
    "weapon_missile": ["bow", "missile_weapon"],
    "armor": [kind for kind, _name, _category, _factory in _CATALOG
              if kind in ("armor", "cloth_armor", "leather_armor", "mail_armor", "scale_armor", "plate_armor")],
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
