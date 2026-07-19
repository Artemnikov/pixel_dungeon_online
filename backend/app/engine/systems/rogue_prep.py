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
"""Assassin subclass "Preparation" tier lookups -- pure functions over
seconds-invisible, no GameInstance/entity coupling. Split out of game/rogue.py
so systems/combat.py (which resolves the Preparation surprise-attack bonus
during melee combat) can import them without reaching upward into game/;
game/rogue.py imports them back for its own stealth/blink-strike logic,
mirroring how game/movement.py already imports from systems/combat.py.
"""

# Per tier: (seconds_required, damage_bonus, damage_rolls_keep_highest).
PREP_TIERS = [
    (1.0, 0.10, 1),
    (3.0, 0.20, 1),
    (5.0, 0.35, 2),
    (9.0, 0.50, 3),
]
# KO HP%-threshold[prep_tier][enhanced_lethality 0..3]
PREP_KO_THRESHOLDS = [
    [0.03, 0.04, 0.05, 0.06],
    [0.10, 0.13, 0.17, 0.20],
    [0.20, 0.27, 0.33, 0.40],
    [0.50, 0.67, 0.83, 1.00],
]
# Blink range[prep_tier][assassins_reach 0..3]
PREP_BLINK_RANGES = [
    [1, 1, 2, 2],
    [2, 3, 4, 5],
    [3, 4, 6, 7],
    [4, 6, 8, 10],
]


def prep_tier(seconds: float) -> int:
    """0-based Preparation tier for the given seconds invisible (-1 if none)."""
    tier = -1
    for i, (req, _b, _r) in enumerate(PREP_TIERS):
        if seconds >= req:
            tier = i
    return tier


def prep_damage_bonus(seconds: float) -> float:
    t = prep_tier(seconds)
    return PREP_TIERS[t][1] if t >= 0 else 0.0


def prep_damage_rolls(seconds: float) -> int:
    t = prep_tier(seconds)
    return PREP_TIERS[t][2] if t >= 0 else 1


def prep_ko_threshold(seconds: float, enhanced_lethality: int) -> float:
    t = prep_tier(seconds)
    if t < 0:
        return 0.0
    el = max(0, min(3, enhanced_lethality))
    return PREP_KO_THRESHOLDS[t][el]


def prep_blink_range(seconds: float, assassins_reach: int) -> int:
    t = prep_tier(seconds)
    if t < 0:
        return 0
    ar = max(0, min(3, assassins_reach))
    return PREP_BLINK_RANGES[t][ar]
