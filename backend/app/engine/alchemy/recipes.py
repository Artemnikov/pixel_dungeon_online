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
from app.engine.entities.items_equip import EquipableItem
from app.engine.entities.items_potions import Potion
from app.engine.entities.items_scrolls import Scroll
from app.engine.entities.items_wands import Wand
from app.engine.entities.trinkets import Trinket


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
