# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
"""energy_val(): SPD Item.energyVal() and its overrides."""
from app.engine.alchemy.recipes import POTION_TO_EXOTIC, SCROLL_TO_EXOTIC
from app.engine.entities.base import ItemBase
from app.engine.entities.items_consumable import Seed
from app.engine.entities.items_potions import Potion
from app.engine.entities.items_scrolls import Scroll
from app.engine.entities.runestones import Runestone
from app.engine.entities.trinkets import Trinket, TrinketCatalyst

# kind -> its regular base kind, for exotic energyVal ((base + 4/6) * q).
_EXOTIC_POTION_TO_REG = {
    exo.model_fields["kind"].default: reg.model_fields["kind"].default
    for reg, exo in POTION_TO_EXOTIC.items()
}
_EXOTIC_SCROLL_TO_REG = {
    exo.model_fields["kind"].default: reg.model_fields["kind"].default
    for reg, exo in SCROLL_TO_EXOTIC.items()
}

# isKnown() overrides worth 10/q instead of 6/q once identified.
_BOOSTED_WHEN_KNOWN = {
    "scroll_of_upgrade", "scroll_of_transmutation",
    "potion_of_strength", "potion_of_experience",
}

# Plant.Seed is 2/q; Starflower and Rotberry override to 3/q.
_SEED_3_PLANTS = {"starflower", "rotberry"}


def _base_val(game, kind: str) -> int:
    if kind in _BOOSTED_WHEN_KNOWN and kind in game.identified_kinds:
        return 10
    return 6


def energy_val(game, item: ItemBase) -> int:
    q = item.quantity
    if isinstance(item, TrinketCatalyst):
        return 6
    if isinstance(item, Trinket):
        return 5
    if isinstance(item, Runestone):
        return 3 * q
    if isinstance(item, Seed):
        return (3 if item.plant_type in _SEED_3_PLANTS else 2) * q
    if isinstance(item, Potion):
        reg = _EXOTIC_POTION_TO_REG.get(item.kind)
        if reg is not None:
            return (_base_val(game, reg) + 4) * q
        return _base_val(game, item.kind) * q
    if isinstance(item, Scroll):
        reg = _EXOTIC_SCROLL_TO_REG.get(item.kind)
        if reg is not None:
            return (_base_val(game, reg) + 6) * q
        return _base_val(game, item.kind) * q
    return 0
