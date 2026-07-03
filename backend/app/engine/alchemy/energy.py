# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
"""energy_val(): SPD Item.energyVal() and its overrides."""
from app.engine.alchemy.recipes import POTION_TO_EXOTIC, SCROLL_TO_EXOTIC
from app.engine.entities.base import ItemBase
from app.engine.entities.items_consumable import GooBlob, Seed
from app.engine.entities.items_potions import (
    AquaBrew, ElixirOfHoneyedHealing, Potion, UnstableBrew,
)
from app.engine.entities.items_scrolls import Scroll
from app.engine.entities.runestones import Runestone, StoneOfAugmentation, StoneOfEnchantment
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

# Elixir.java / Brew.java override energyVal() to 12*q. The remake's elixirs
# and brews subclass Potion directly, so they are matched by kind here.
# (AquaBrew, UnstableBrew and ElixirOfHoneyedHealing have their own overrides.)
_ELIXIR_BREW_KINDS_12 = {
    "elixir_of_arcane_armor", "elixir_of_dragons_blood", "elixir_of_feather_fall",
    "elixir_of_icy_touch", "elixir_of_might", "elixir_of_toxic_essence",
    "elixir_aqua_rejuv",
    "blizzard_brew", "caustic_brew", "infernal_brew", "shocking_brew",
}


def _base_val(game, kind: str) -> int:
    if kind in _BOOSTED_WHEN_KNOWN and kind in game.identified_kinds:
        return 10
    return 6


def energy_val(game, item: ItemBase) -> int:
    q = item.quantity
    if isinstance(item, TrinketCatalyst):
        return item.energy_val()
    if isinstance(item, Trinket):
        return item.energy_val()
    if isinstance(item, (StoneOfEnchantment, StoneOfAugmentation)):
        return 5 * q  # both override energyVal() to 5*quantity in SPD
    if isinstance(item, Runestone):
        return 3 * q
    if isinstance(item, Seed):
        return (3 if item.plant_type in _SEED_3_PLANTS else 2) * q
    if isinstance(item, GooBlob):
        return 3 * q  # GooBlob.java energyVal
    if isinstance(item, Potion):
        if isinstance(item, AquaBrew):
            return int(12 * (q / 8))  # AquaBrew.java: 12 * (q / OUT_QUANTITY=8)
        if isinstance(item, UnstableBrew):
            return 8 * q
        if isinstance(item, ElixirOfHoneyedHealing):
            return 8  # flat override in SPD
        if item.kind in _ELIXIR_BREW_KINDS_12:
            return 12 * q
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
