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
"""Port of concrete SpecialRoom/SecretRoom subclasses
(rooms/special/*.java, rooms/secret/*.java), split by reward category:

  _shared.py     -- helpers/constants used across 2+ of the files below,
                     plus the one-time SpecialRoom/SecretRoom.paint
                     monkeypatch (abstract-base fallback).
  equip.py       -- EQUIP_SPECIALS (WeakFloorRoom..SacrificeRoom).
  consumable.py  -- CONSUMABLE_SPECIALS (RunestoneRoom..CrystalPathRoom).
  misc.py        -- LaboratoryRoom/PitRoom/DemonSpawnerRoom/MassGraveRoom
                     (not drawn from either general random-special list).
  secret.py      -- ALL_SECRETS (SecretGardenRoom..SecretSummoningRoom).
  registries.py  -- the registration-order tuples above; kept separate since
                     several (CRYSTAL_KEY_SPECIALS, POTION_SPAWN_ROOMS) span
                     multiple of the files above.

This package re-exports everything below so existing call sites
(`from app.engine.dungeon.spd_levelgen import special_rooms as sr`,
`sr.CrystalVaultRoom`, `from ...special_rooms import _IRON_KEY`) keep working
unchanged."""

from __future__ import annotations

from app.engine.dungeon.spd_levelgen.special_rooms import _shared  # noqa: F401 -- runs the paint() monkeypatch
from app.engine.dungeon.spd_levelgen.special_rooms._shared import _IRON_KEY
from app.engine.dungeon.spd_levelgen.special_rooms.consumable import (
    CrystalPathRoom, GardenRoom, LibraryRoom, MagicalFireRoom, MagicWellRoom,
    RunestoneRoom, StorageRoom, ToxicGasRoom, TrapsRoom, TreasuryRoom,
)
from app.engine.dungeon.spd_levelgen.special_rooms.equip import (
    ArmoryRoom, CrystalChoiceRoom, CrystalVaultRoom, CryptRoom, PoolRoom,
    SacrificeRoom, SentryRoom, StatueRoom, WeakFloorRoom,
)
from app.engine.dungeon.spd_levelgen.special_rooms.misc import (
    DemonSpawnerRoom, LaboratoryRoom, MassGraveRoom, PitRoom,
)
from app.engine.dungeon.spd_levelgen.special_rooms.secret import (
    SecretArtilleryRoom, SecretChestChasmRoom, SecretGardenRoom,
    SecretHoardRoom, SecretHoneypotRoom, SecretLaboratoryRoom,
    SecretLarderRoom, SecretLibraryRoom, SecretMazeRoom, SecretRunestoneRoom,
    SecretSummoningRoom, SecretWellRoom,
)
from app.engine.dungeon.spd_levelgen.special_rooms.registries import (
    ALL_SECRETS, CONSUMABLE_SPECIALS, CRYSTAL_KEY_SPECIALS, EQUIP_SPECIALS,
    POTION_SPAWN_ROOMS,
)

__all__ = [
    "_IRON_KEY",
    # equip
    "WeakFloorRoom", "CryptRoom", "PoolRoom", "ArmoryRoom", "SentryRoom",
    "StatueRoom", "CrystalVaultRoom", "CrystalChoiceRoom", "SacrificeRoom",
    # consumable
    "RunestoneRoom", "GardenRoom", "LibraryRoom", "StorageRoom", "TreasuryRoom",
    "MagicWellRoom", "ToxicGasRoom", "MagicalFireRoom", "TrapsRoom", "CrystalPathRoom",
    # misc
    "LaboratoryRoom", "PitRoom", "DemonSpawnerRoom", "MassGraveRoom",
    # secret
    "SecretGardenRoom", "SecretLaboratoryRoom", "SecretLibraryRoom", "SecretLarderRoom",
    "SecretWellRoom", "SecretRunestoneRoom", "SecretArtilleryRoom", "SecretChestChasmRoom",
    "SecretHoneypotRoom", "SecretHoardRoom", "SecretMazeRoom", "SecretSummoningRoom",
    # registries
    "EQUIP_SPECIALS", "CONSUMABLE_SPECIALS", "CRYSTAL_KEY_SPECIALS",
    "POTION_SPAWN_ROOMS", "ALL_SECRETS",
]
