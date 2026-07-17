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

from typing import ClassVar, Literal

from app.engine.entities.base import ItemBase


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
