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
"""Stat tables for the generic (non-unique) melee weapon roster, ported from
`items/weapon/melee/*.java` per docs/spd_items/01-weapons-bombs.md §2.

`dmg_min(lvl) = tier + lvl` is uniform across all melee weapons and is already
implemented in `MeleeWeapon.dmg_min`. `dmg_max(lvl) = max0 + max_per_lvl*lvl`
is per-weapon, captured here as (max0, max_per_lvl).

`WEP_TIER_ORDER` mirrors the deck order of `_WEP_T1.._WEP_T5` in
`spd_levelgen/generator.py` -- the index `RolledItem.item_index` selects into
these tuples. `Worn Shortsword`/`Dagger` are handled by their own classes/items
elsewhere. Staff is unique (mage only). Pickaxe never drops -- weight 0."""

from __future__ import annotations

from typing import Dict, NamedTuple, Tuple


class WeaponDef(NamedTuple):
    tier: int
    str_req: int
    max0: int
    max_per_lvl: int
    acc_factor: float = 1.0
    dly_factor: float = 1.0
    reach: int = 1
    dr_bonus_base: int = 0
    dr_bonus_per_lvl: int = 0


WEAPON_DEFS: Dict[str, WeaponDef] = {
    # Tier 1 (str_req=10)
    "Gloves": WeaponDef(tier=1, str_req=10, max0=5, max_per_lvl=1, dly_factor=0.5),
    "Rapier": WeaponDef(tier=1, str_req=10, max0=8, max_per_lvl=2, dr_bonus_base=1),
    "Cudgel": WeaponDef(tier=1, str_req=10, max0=8, max_per_lvl=2, acc_factor=1.40),

    # Tier 2 (str_req=12)
    "Shortsword": WeaponDef(tier=2, str_req=12, max0=12, max_per_lvl=3),
    "Hand Axe": WeaponDef(tier=2, str_req=12, max0=12, max_per_lvl=3, acc_factor=1.32),
    "Spear": WeaponDef(tier=2, str_req=12, max0=20, max_per_lvl=4, dly_factor=1.5, reach=2),
    "Quarterstaff": WeaponDef(tier=2, str_req=12, max0=12, max_per_lvl=3, dr_bonus_base=2),
    "Dirk": WeaponDef(tier=2, str_req=12, max0=12, max_per_lvl=3),
    "Sickle": WeaponDef(tier=2, str_req=12, max0=20, max_per_lvl=3, acc_factor=0.68),

    # Tier 3 (str_req=14)
    "Sword": WeaponDef(tier=3, str_req=14, max0=16, max_per_lvl=4),
    "Mace": WeaponDef(tier=3, str_req=14, max0=16, max_per_lvl=4, acc_factor=1.28),
    "Scimitar": WeaponDef(tier=3, str_req=14, max0=16, max_per_lvl=4, dly_factor=0.8),
    "Round Shield": WeaponDef(tier=3, str_req=14, max0=12, max_per_lvl=2, dr_bonus_base=4, dr_bonus_per_lvl=1),
    "Sai": WeaponDef(tier=3, str_req=14, max0=10, max_per_lvl=2, dly_factor=0.5),
    "Whip": WeaponDef(tier=3, str_req=14, max0=15, max_per_lvl=3, reach=3),

    # Tier 4 (str_req=16)
    "Longsword": WeaponDef(tier=4, str_req=16, max0=20, max_per_lvl=5),
    "Battle Axe": WeaponDef(tier=4, str_req=16, max0=20, max_per_lvl=5, acc_factor=1.24),
    "Flail": WeaponDef(tier=4, str_req=16, max0=35, max_per_lvl=8, acc_factor=0.8),
    "Runic Blade": WeaponDef(tier=4, str_req=16, max0=20, max_per_lvl=6),
    "Assassin's Blade": WeaponDef(tier=4, str_req=16, max0=20, max_per_lvl=5),
    "Crossbow": WeaponDef(tier=4, str_req=16, max0=20, max_per_lvl=4),
    "Katana": WeaponDef(tier=4, str_req=16, max0=20, max_per_lvl=5, dr_bonus_base=3),

    # Tier 5 (str_req=18 except Greataxe=20)
    "Greatsword": WeaponDef(tier=5, str_req=18, max0=24, max_per_lvl=6),
    "War Hammer": WeaponDef(tier=5, str_req=18, max0=24, max_per_lvl=6, acc_factor=1.20),
    "Glaive": WeaponDef(tier=5, str_req=18, max0=40, max_per_lvl=8, dly_factor=1.5, reach=2),
    "Greataxe": WeaponDef(tier=5, str_req=20, max0=45, max_per_lvl=6),
    "Greatshield": WeaponDef(tier=5, str_req=18, max0=18, max_per_lvl=3, dr_bonus_base=6, dr_bonus_per_lvl=2),
    "Gauntlet": WeaponDef(tier=5, str_req=18, max0=15, max_per_lvl=3, dly_factor=0.5),
    "War Scythe": WeaponDef(tier=5, str_req=18, max0=40, max_per_lvl=6, acc_factor=0.8),
}


# Deck order of `_WEP_T1.._WEP_T5` (generator.py) -- index = drop weight slot.
# "Pickaxe" has weight 0 and is never selected. Staff is unique, never drops.
WEP_TIER_ORDER: Dict[str, Tuple[str, ...]] = {
    "WEP_T1": ("Worn Shortsword", "Dagger", "Gloves", "Rapier", "Cudgel"),
    "WEP_T2": ("Shortsword", "Hand Axe", "Spear", "Quarterstaff", "Dirk", "Sickle", "Pickaxe"),
    "WEP_T3": ("Sword", "Mace", "Scimitar", "Round Shield", "Sai", "Whip"),
    "WEP_T4": ("Longsword", "Battle Axe", "Flail", "Runic Blade", "Assassin's Blade", "Crossbow", "Katana"),
    "WEP_T5": ("Greatsword", "War Hammer", "Glaive", "Greataxe", "Greatshield", "Gauntlet", "War Scythe"),
}
