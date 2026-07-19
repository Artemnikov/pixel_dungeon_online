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
"""Helpers/constants shared by 2+ special_rooms submodules (equip/consumable/
misc/secret) -- everything here is either used across multiple of those
files or is a one-time side effect (the SpecialRoom/SecretRoom.paint
monkeypatch) that must run once regardless of import order."""

from __future__ import annotations

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.geom import gate
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import DoorType
from app.engine.dungeon.spd_levelgen.room_types import SecretRoom, SpecialRoom
from app.engine.dungeon.spd_random import SPDRandom

# IronKey descriptor -- distinguishable from other empty-frozenset placeholders
# (SPAWN_FOOD/SPAWN_STYLUS/etc.) so the adapter can spawn a real Key item.
# "IronKey" is never a findPrizeItem match-target, so this label is safe.
_IRON_KEY = frozenset({"IronKey"})


def _stub_paint(self, level, rng) -> None:
    Painter.fill(level, self, terrain.WALL)
    Painter.fill(level, self, 1, terrain.EMPTY)
    self.entrance().set(DoorType.REGULAR)


# Generator.floorSetTierProbs (Generator.java:613-619) -- weighted pick of a
# weapon/missile tier (T1-T5) based on `Dungeon.depth / 5`, gated [0,4].
_FLOOR_SET_TIER_PROBS = (
    (0.0, 75.0, 20.0, 4.0, 1.0),
    (0.0, 25.0, 50.0, 20.0, 5.0),
    (0.0, 0.0, 40.0, 50.0, 10.0),
    (0.0, 0.0, 20.0, 40.0, 40.0),
    (0.0, 0.0, 0.0, 20.0, 80.0),
)


def _consume_random_equipment_floorset(rng: SPDRandom, floor_set: int) -> None:
    """Shared outer-sequence draw shape for Generator.randomWeapon(floorSet)
    and Generator.randomArmor(floorSet):
      1. Random.chances(floorSetTierProbs[gated floorSet]) -- selects the
         tier/class index (deck-backed for weapons -- push/pop is invisible
         to the parent -- and a direct array index for armor; either way
         it's exactly one outer chances() draw)
      2. The resulting MeleeWeapon/Armor instance's .random(): Int(4),
         conditionally Int(5), then Random.Long() to seed
         Random.pushGenerator() (contents invisible to the parent).
    Identity is irrelevant for layout-parity -- only the draw shape matters."""
    floor_set = int(gate(0, floor_set, len(_FLOOR_SET_TIER_PROBS) - 1))
    rng.chances(_FLOOR_SET_TIER_PROBS[floor_set])

    if rng.IntMax(4) == 0:
        rng.IntMax(5)
    rng.Long()  # Random.pushGenerator(Random.Long()) -- seed draw only; contents skipped


def _consume_gold_random(rng: SPDRandom, depth: int) -> None:
    """Port of `new Gold().random()`'s RNG draw (Gold.java:91 --
    `quantity = Random.IntRange(30 + Dungeon.depth*10, 60 + Dungeon.depth*20)`).
    Item identity/quantity is out of layout-parity scope (level.drop is
    zero-RNG and omitted), but the roll itself must still be consumed."""
    rng.IntRange(30 + depth * 10, 60 + depth * 20)


# Every concrete SpecialRoom/SecretRoom subclass overrides paint() with its
# real implementation; this is only the abstract-base fallback.
SpecialRoom.paint = _stub_paint
SecretRoom.paint = _stub_paint
