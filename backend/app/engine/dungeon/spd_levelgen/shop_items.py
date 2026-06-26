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
"""Port of ShopRoom.generateItems() (ShopRoom.java) for the depth-tiered
shops on floors 6/11/16 (Dungeon.shopOnLevel()).

Deviations from SPD, per the approved plan:
 - TippedDart -> 2x Stone
 - Alchemize -> skipped
 - Bag (ChooseBag) -> simplified to a fixed depth->bag mapping (6=Scroll
   Holder, 11=Potion Bandolier, 16=Magical Holster; depth 20 gets none).
   VelvetPouch is excluded since every player already starts with one
   (matches SPD's LimitedDrops state at run start). The original's
   per-player "most inventory savings" weighting needs a specific hero's
   belongings, which isn't available here: shop stock is generated once per
   shared multiplayer floor, not per player.
 - Bomb/DoubleBomb/Honeypot -> +1 Food ("Mystery Meat")
 - Ankh / StoneOfAugmentation / TimekeepersHourglass.sandBag -> skipped
 - Stylus (7/10 rare roll) -> redistributed to Wand/Ring
 - Torch x3 (depth 20/21) -> not reachable (shopOnLevel() is 6/11/16 only)

Item generation + shuffling runs inside a pushed RNG generator (seeded by a
single Long() draw from the main sequence), mirroring SPD's
`Random.pushGenerator(Random.Long())` isolation so shop stock never perturbs
levelgen RNG beyond that one draw.
"""

from __future__ import annotations

from typing import List

from app.engine.dungeon.spd_levelgen.generator import _WEP_T1, _WEP_T2, _WEP_T3, _WEP_T4, _WEP_T5
from app.engine.dungeon.spd_random import SPDRandom
from app.engine.entities.base import (
    Armor,
    ClothArmor, LeatherArmor, MailArmor, ScaleArmor, PlateArmor,
    Artifact,
    Food,
    HealthPotion,
    Item,
    MagicalHolster,
    make_named_melee_weapon,
    MissileWeapon,
    PotionBandolier,
    Ring,
    ScrollHolder,
    ScrollOfIdentify,
    ScrollOfMagicMapping,
    ScrollOfRemoveCurse,
    ScrollOfUpgrade,
    Stone,
    Wand,
)
from app.engine.entities.weapon_defs import WEP_TIER_ORDER
from app.engine.entities.weapon_enchants import ENCHANT_RARITY

_WEP_TIER_PROBS = {1: _WEP_T1, 2: _WEP_T2, 3: _WEP_T3, 4: _WEP_T4, 5: _WEP_T5}

_ENCHANT_NAMES = list(ENCHANT_RARITY)
_ENCHANT_WEIGHTS = list(ENCHANT_RARITY.values())


def _random_melee_weapon(rng: SPDRandom, tier: int) -> Item:
    cat = f"WEP_T{tier}"
    idx = rng.chances(list(_WEP_TIER_PROBS[tier]))
    name = WEP_TIER_ORDER[cat][idx]
    weapon = make_named_melee_weapon(name)

    # Shops don't sell cursed gear; roll level/enchant and reveal both.
    level_roll = rng.chances([75, 20, 5])
    weapon.level = level_roll
    weapon.level_known = True
    if rng.Float() < 0.10:
        weapon.enchantment = _ENCHANT_NAMES[rng.chances(_ENCHANT_WEIGHTS)]
        weapon.cursed_known = True
    return weapon

# depth -> (weapon/missile tier, armor tier) -- ShopRoom.generateItems()'s
# `case 6/11/16` use wepTiers[1]/[2]/[3] (1-indexed tiers 2/3/4) with
# LeatherArmor/MailArmor/ScaleArmor (tiers 1/2/3).
_SHOP_TIERS = {
    6: (2, 1),
    11: (3, 2),
    16: (4, 3),
    # ImpShopRoom (depth 20): wepTiers[4] -> 5, PlateArmor -> 4. The 3x Torch
    # added at case 20/21 are skipped per the existing not-yet-implemented-item
    # substitution table.
    20: (5, 4),
}

# ShopRoom.ChooseBag(), simplified: a fixed depth -> bag class so each shop
# grants exactly one free storage bag, no duplicates across a run. VelvetPouch
# isn't a candidate (every player starts with one already).
_SHOP_BAGS = {
    6: ScrollHolder,
    11: PotionBandolier,
    16: MagicalHolster,
}


_ARMOR_TYPES = {1: ClothArmor, 2: LeatherArmor, 3: MailArmor, 4: ScaleArmor, 5: PlateArmor}

def generate_shop_items(rng: SPDRandom, depth: int) -> List[Item]:
    weapon_tier, armor_tier = _SHOP_TIERS.get(depth, (2, 1))

    armor_cls = _ARMOR_TYPES.get(armor_tier, LeatherArmor)

    items: List[Item] = [
        _random_melee_weapon(rng, weapon_tier),
        MissileWeapon(name="Missile Weapon", tier=weapon_tier),
        armor_cls(),
        # TippedDart.randomTipped(2) -> 2x Stone
        Stone(),
        Stone(),
        HealthPotion(name="Potion of Healing"),
        HealthPotion(),
        HealthPotion(),
        ScrollOfIdentify(),
        ScrollOfRemoveCurse(),
        ScrollOfMagicMapping(),
        ScrollOfUpgrade(),
        HealthPotion(),
        Food(name="Small Ration of Food"),
        Food(name="Small Ration of Food"),
        # Bomb/DoubleBomb/Honeypot substitution
        Food(name="Mystery Meat"),
    ]

    # Rare item roll (Random.Int(10)): 0=wand, 1=ring, 2=artifact, the
    # remaining 7 (Stylus) buckets redistribute evenly to wand/ring.
    roll = rng.IntMax(10)
    if roll == 0:
        rare: Item = Wand(name="Wand", cursed_known=True)
    elif roll == 1:
        rare = Ring(name="Ring", cursed_known=True)
    elif roll == 2:
        rare = Artifact(name="Artifact")
    elif roll % 2 == 1:
        rare = Wand(name="Wand", cursed_known=True)
    else:
        rare = Ring(name="Ring", cursed_known=True)
    items.append(rare)

    bag_cls = _SHOP_BAGS.get(depth)
    if bag_cls is not None:
        items.append(bag_cls())

    rng.shuffle(items)

    for item in items:
        item.for_sale = True
    return items


def shop_room_item_list(rng: SPDRandom, depth: int) -> List[Item]:
    """Generates shop stock isolated from the main RNG sequence (mirrors
    SPD's `Random.pushGenerator(Random.Long())` around the final shuffle,
    extended here to cover the whole generation+shuffle so shop contents
    never perturb levelgen RNG beyond the single Long() draw)."""
    seed = rng.Long()
    rng.push_generator(seed)
    try:
        return generate_shop_items(rng, depth)
    finally:
        rng.pop_generator()
