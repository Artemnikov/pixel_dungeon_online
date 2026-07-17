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
"""Wandmaker quest turn-in items that aren't CorpseDust (items_consumable.py,
already close to 400 lines). Kept separate from wandmaker_quest.py's mob
classes (Wandmaker/RotHeart/RotLasher/DustWraith) because those need
player.Mob, and importing player.py here would cycle back through
item_union.py's Item discriminated union (which must reach every item kind,
including these)."""

from __future__ import annotations

from typing import ClassVar, List, Literal, Optional

from app.engine.entities.base import Action, ItemBase


class RotberrySeed(ItemBase):
    """plants/Rotberry.java's Seed inner class -- the Rotberry quest's
    turn-in item, dropped by RotHeart on death (see wandmaker_quest.py /
    world.py's handle_mob_death). Inert for quest purposes (no held-item
    side effect, unlike CorpseDust); the "plant it to grow a new Rotberry"
    flavor mechanic is a separate, unrelated Plant/Seed system this port
    doesn't need to build out for the quest to work."""

    kind: Literal["rotberry_seed"] = "rotberry_seed"
    name: str = "seed of the rotberry"
    type: str = "misc"
    category: ClassVar[str] = "misc"
    unique: bool = True
    level_known: bool = True
    cursed_known: bool = True
    DESC: ClassVar[str] = (
        "A dark, wrinkled seed pod, still faintly warm from the plant it "
        "came from. The Wandmaker will want this."
    )


class CeremonialCandle(ItemBase):
    """items/quest/CeremonialCandle.java -- the Ceremonial Candle quest
    variant's collectible. 4 are queued as findPrizeItem() prizes when
    RitualSiteRoom is painted (see room_types.RitualSiteRoom); throwing or
    dropping one onto each of the 4 cells cardinally adjacent to the
    ritual's center completes the ritual (see world.py's
    _check_ritual_candles, hooked from item_actions.action_drop and
    movement.perform_ranged_attack). The `aflame` visual-only flag Java
    flips as candles land is dropped -- purely cosmetic, no gameplay effect."""

    kind: Literal["ceremonial_candle"] = "ceremonial_candle"
    name: str = "ceremonial candle"
    type: str = "misc"
    category: ClassVar[str] = "misc"
    unique: bool = True
    stackable: ClassVar[bool] = True
    level_known: bool = True
    cursed_known: bool = True
    DESC: ClassVar[str] = (
        "A thick, ceremonial candle, its wick untouched by flame. It seems "
        "meant to be placed somewhere significant."
    )

    def default_action(self) -> Optional[str]:
        return Action.THROW

    def actions(self, player=None) -> List[str]:
        return [Action.THROW, Action.DROP]


class Embers(ItemBase):
    """items/quest/Embers.java -- the Ceremonial Candle quest's turn-in
    item, dropped by NewbornFireElemental on death (see wandmaker_quest.py
    / world.py's handle_mob_death). Inert for quest purposes, same as
    RotberrySeed."""

    kind: Literal["embers"] = "embers"
    name: str = "smoldering embers"
    type: str = "misc"
    category: ClassVar[str] = "misc"
    unique: bool = True
    level_known: bool = True
    cursed_known: bool = True
    DESC: ClassVar[str] = (
        "A handful of embers, still glowing faintly with inner fire. They "
        "refuse to go out no matter how long they sit."
    )
