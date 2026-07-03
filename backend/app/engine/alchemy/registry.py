# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
"""Recipe registry mirroring Recipe.java's static lists (order preserved).

Entries commented out are later phases: bombs (phase 2), spells + ArcaneResin +
LiquidMetal (phase 3), Blandfruit (phase 4), ElixirOfHoneyedHealing (needs
Honeypot). Tasks 4-6 extend these lists.
"""
from typing import List

from app.engine.alchemy.recipes import (
    PotionToExotic, Recipe, ScrollToExotic, ScrollToStone,
)

ONE_INGREDIENT_RECIPES: List[Recipe] = [
    ScrollToStone(),
    PotionToExotic(),
    ScrollToExotic(),
]

TWO_INGREDIENT_RECIPES: List[Recipe] = []

THREE_INGREDIENT_RECIPES: List[Recipe] = []


def find_recipes(game, units) -> List[Recipe]:
    if not units:
        return []
    if len(units) == 1:
        pool = ONE_INGREDIENT_RECIPES
    elif len(units) == 2:
        pool = TWO_INGREDIENT_RECIPES
    elif len(units) == 3:
        pool = THREE_INGREDIENT_RECIPES
    else:
        return []
    return [r for r in pool if r.test_ingredients(game, units)]
