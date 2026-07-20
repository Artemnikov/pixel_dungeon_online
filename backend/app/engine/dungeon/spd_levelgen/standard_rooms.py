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
"""StandardRoom/EntranceRoom/ExitRoom registration-order tables + factories
(EntranceRoom/ExitRoom/StandardRoom.java): create_entrance/create_exit/
create_standard_room and the RNG-index-parity-critical _ROOM_TYPES/_CHANCES
tuples that back them.

The 85 StandardRoom subclasses these tables reference live in
standard_rooms_base.py (abstract bases + helpers) and one file per region
(standard_rooms_{sewers,fillers,prison,caves,city,halls}.py) -- this used to
be one 1767-line file; split apart since the region-specific room definitions
were an unrelated concern from these shared registration tables. Every class
is re-exported here so existing `from .standard_rooms import X` call sites
keep working unchanged.

`paint()` is fully ported (terrain/loot/mob placement, RNG-exact draw order)
for every StandardRoom class with nonzero `chances[depth]` weight on depths
1-5 (the sewers-exclusive quintet plus the "universal" filler rooms). The
prison/caves/city/halls-region-only StandardRoom variants are unreachable on
sewers floors (weight 0 there) and are out of this port's current scope --
`paint = _stub_paint` placeholders (generic wall+floor box) preserve their
registration-order indices so `Random.chances` still resolves correctly for
other regions.
"""

from typing import Optional, Type

from app.engine.dungeon.spd_levelgen.room import Room
from app.engine.dungeon.spd_levelgen.room_types import StandardRoom
from app.engine.dungeon.spd_random import SPDRandom

# noqa: F401 below -- every name in this block is re-exported so existing
# "from .standard_rooms import X" call sites (regular_level.py, boss_level.py,
# special_rooms/*, tests) keep working unchanged now that the class definitions
# live in per-region files instead of this one.
from app.engine.dungeon.spd_levelgen.standard_rooms_base import (
    EmptyRoom, EntranceRoom, ExitRoom, PatchRoom, StandardBridgeRoom,
    _stub_paint, _neighbours8, _neighbours4, _space_between, _patch_distance_map,
)
from app.engine.dungeon.spd_levelgen.standard_rooms_sewers import (
    SewerPipeRoom, RingRoom, WaterBridgeRoom, RegionDecoPatchRoom, CircleBasinRoom,
    WaterBridgeEntranceRoom, RegionDecoPatchEntranceRoom, RingEntranceRoom, CircleBasinEntranceRoom,
    WaterBridgeExitRoom, RegionDecoPatchExitRoom, RingExitRoom, CircleBasinExitRoom,
)
from app.engine.dungeon.spd_levelgen.standard_rooms_fillers import (
    PlantsRoom, AquariumRoom, PlatformRoom, BurnedRoom, FissureRoom,
    GrassyGraveRoom, StripedRoom, StudyRoom, SuspiciousChestRoom, MinefieldRoom,
    _random_plant_seed,
)
from app.engine.dungeon.spd_levelgen.standard_rooms_prison import (
    RegionDecoLineRoom, SegmentedRoom, PillarsRoom, ChasmBridgeRoom, CellBlockRoom,
    RegionDecoLineEntranceRoom, RegionDecoLineExitRoom, ChasmBridgeEntranceRoom, ChasmBridgeExitRoom,
    PillarsEntranceRoom, PillarsExitRoom, CellBlockEntranceRoom, CellBlockExitRoom,
)
from app.engine.dungeon.spd_levelgen.standard_rooms_caves import (
    CaveRoom, RegionDecoBridgeRoom, CavesFissureRoom, CirclePitRoom, CircleWallRoom,
    CaveEntranceRoom, CaveExitRoom, RegionDecoBridgeEntranceRoom, RegionDecoBridgeExitRoom,
    CavesFissureEntranceRoom, CavesFissureExitRoom, CircleWallEntranceRoom, CircleWallExitRoom,
)
from app.engine.dungeon.spd_levelgen.standard_rooms_city import (
    HallwayRoom, LibraryHallRoom, LibraryRingRoom, StatuesRoom, SegmentedLibraryRoom,
    HallwayEntranceRoom, HallwayExitRoom, StatuesEntranceRoom, StatuesExitRoom,
    LibraryHallEntranceRoom, LibraryHallExitRoom, LibraryRingEntranceRoom, LibraryRingExitRoom,
)
from app.engine.dungeon.spd_levelgen.standard_rooms_halls import (
    RuinsRoom, ChasmRoom, SkullsRoom, RitualRoom,
    RuinsEntranceRoom, RuinsExitRoom, ChasmEntranceRoom, ChasmExitRoom,
    RitualEntranceRoom, RitualExitRoom,
)

# -- registration-order tables + factories (EntranceRoom/ExitRoom/StandardRoom.java) --

# EntranceRoom.rooms / ExitRoom.rooms: only the first 4 entries have nonzero
# `chances[depth]` weight for depths 1-5 (the rest are prison/caves/city/halls
# variants) -- ported in full per the original 20-entry static list, with
# unreachable-on-sewers-floors slots as `None` placeholders preserving index.
_ENTRANCE_ROOM_TYPES: tuple = (
    # Sewers [0-3]
    WaterBridgeEntranceRoom, RegionDecoPatchEntranceRoom, RingEntranceRoom, CircleBasinEntranceRoom,
    # Prison [4-7]
    RegionDecoLineEntranceRoom, ChasmBridgeEntranceRoom, PillarsEntranceRoom, CellBlockEntranceRoom,
    # Caves [8-11]
    CaveEntranceRoom, RegionDecoBridgeEntranceRoom, CavesFissureEntranceRoom, CircleWallEntranceRoom,
    # City [12-15]
    HallwayEntranceRoom, StatuesEntranceRoom, LibraryHallEntranceRoom, LibraryRingEntranceRoom,
    # Halls [16-19] — index 16 reuses RegionDecoPatchEntranceRoom (Java reuses it)
    RegionDecoPatchEntranceRoom, RuinsEntranceRoom, ChasmEntranceRoom, RitualEntranceRoom,
)

_EXIT_ROOM_TYPES: tuple = (
    # Sewers [0-3]
    WaterBridgeExitRoom, RegionDecoPatchExitRoom, RingExitRoom, CircleBasinExitRoom,
    # Prison [4-7]
    RegionDecoLineExitRoom, ChasmBridgeExitRoom, PillarsExitRoom, CellBlockExitRoom,
    # Caves [8-11]
    CaveExitRoom, RegionDecoBridgeExitRoom, CavesFissureExitRoom, CircleWallExitRoom,
    # City [12-15]
    HallwayExitRoom, StatuesExitRoom, LibraryHallExitRoom, LibraryRingExitRoom,
    # Halls [16-19] — index 16 reuses RegionDecoPatchExitRoom (Java reuses it)
    RegionDecoPatchExitRoom, RuinsExitRoom, ChasmExitRoom, RitualExitRoom,
)

# EntranceRoom.chances[depth]
_ENTRANCE_CHANCES = {
    1:  (4.0, 3.0, 0.0, 0.0) + (0.0,) * 16,
    2:  (4.0, 3.0, 0.0, 0.0) + (0.0,) * 16,
    3:  (4.0, 3.0, 2.0, 1.0) + (0.0,) * 16,
    4:  (4.0, 3.0, 2.0, 1.0) + (0.0,) * 16,
    5:  (4.0, 3.0, 2.0, 1.0) + (0.0,) * 16,
    # Prison
    6:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    7:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    8:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    9:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    10: (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    # Caves
    11: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    12: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    13: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    14: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    15: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    # City
    16: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    17: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    18: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    19: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    20: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    # Halls
    21: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    22: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    23: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    24: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    25: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    26: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
}

# ExitRoom.chances[depth]
_EXIT_CHANCES = {
    1:  (4.0, 3.0, 0.0, 0.0) + (0.0,) * 16,
    2:  (4.0, 3.0, 2.0, 1.0) + (0.0,) * 16,
    3:  (4.0, 3.0, 2.0, 1.0) + (0.0,) * 16,
    4:  (4.0, 3.0, 2.0, 1.0) + (0.0,) * 16,
    5:  (4.0, 3.0, 2.0, 1.0) + (0.0,) * 16,
    # Prison
    6:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    7:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    8:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    9:  (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    10: (0.0,) * 4 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 12,
    # Caves
    11: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    12: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    13: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    14: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    15: (0.0,) * 8 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 8,
    # City
    16: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    17: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    18: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    19: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    20: (0.0,) * 12 + (4.0, 3.0, 2.0, 1.0) + (0.0,) * 4,
    # Halls
    21: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    22: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    23: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    24: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    25: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
    26: (0.0,) * 16 + (4.0, 3.0, 2.0, 1.0),
}

# StandardRoom.rooms registration order (35 entries: 5 region-table groups of
# 5 + 10 filler rooms).
_STANDARD_ROOM_TYPES: tuple = (
    # Sewers [0-4]
    SewerPipeRoom, RingRoom, WaterBridgeRoom, RegionDecoPatchRoom, CircleBasinRoom,
    # Prison [5-9]
    RegionDecoLineRoom, SegmentedRoom, PillarsRoom, ChasmBridgeRoom, CellBlockRoom,
    # Caves [10-14]
    CaveRoom, RegionDecoBridgeRoom, CavesFissureRoom, CirclePitRoom, CircleWallRoom,
    # City [15-19]
    HallwayRoom, LibraryHallRoom, LibraryRingRoom, StatuesRoom, SegmentedLibraryRoom,
    # Halls [20-24] — index 21 is RegionDecoPatchRoom again (Java reuses it)
    RuinsRoom, RegionDecoPatchRoom, ChasmRoom, SkullsRoom, RitualRoom,
    # Filler [25-34]
    PlantsRoom, AquariumRoom, PlatformRoom, BurnedRoom, FissureRoom,
    GrassyGraveRoom, StripedRoom, StudyRoom, SuspiciousChestRoom, MinefieldRoom,
)

# StandardRoom.chances[depth]
_STANDARD_CHANCES = {
    1:  (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 20 + (1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0),
    2:  (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 20 + (1.0,) * 10,
    3:  (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 20 + (1.0,) * 10,
    4:  (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 20 + (1.0,) * 10,
    5:  (16.0, 8.0, 8.0, 4.0, 0.0) + (0.0,) * 30,
    # Prison
    6:  (0.0,) * 5 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 15 + (1.0,) * 10,
    7:  (0.0,) * 5 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 15 + (1.0,) * 10,
    8:  (0.0,) * 5 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 15 + (1.0,) * 10,
    9:  (0.0,) * 5 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 15 + (1.0,) * 10,
    10: (0.0,) * 5 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 15 + (1.0,) * 10,
    # Caves
    11: (0.0,) * 10 + (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 10 + (1.0,) * 10,
    12: (0.0,) * 10 + (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 10 + (1.0,) * 10,
    13: (0.0,) * 10 + (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 10 + (1.0,) * 10,
    14: (0.0,) * 10 + (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 10 + (1.0,) * 10,
    15: (0.0,) * 10 + (16.0, 8.0, 8.0, 4.0, 4.0) + (0.0,) * 10 + (1.0,) * 10,
    # City
    16: (0.0,) * 15 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 5 + (1.0,) * 10,
    17: (0.0,) * 15 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 5 + (1.0,) * 10,
    18: (0.0,) * 15 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 5 + (1.0,) * 10,
    19: (0.0,) * 15 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 5 + (1.0,) * 10,
    20: (0.0,) * 15 + (10.0, 10.0, 10.0, 5.0, 5.0) + (0.0,) * 5 + (1.0,) * 10,
    # Halls
    21: (0.0,) * 20 + (10.0, 10.0, 10.0, 5.0, 5.0) + (1.0,) * 10,
    22: (0.0,) * 20 + (10.0, 10.0, 10.0, 5.0, 5.0) + (1.0,) * 10,
    23: (0.0,) * 20 + (10.0, 10.0, 10.0, 5.0, 5.0) + (1.0,) * 10,
    24: (0.0,) * 20 + (10.0, 10.0, 10.0, 5.0, 5.0) + (1.0,) * 10,
    25: (0.0,) * 20 + (10.0, 10.0, 10.0, 5.0, 5.0) + (1.0,) * 10,
    26: (0.0,) * 20 + (10.0, 10.0, 10.0, 5.0, 5.0) + (1.0,) * 10,
}


def _create_from_table(rng: SPDRandom, types: tuple, chances: tuple) -> Room:
    idx = rng.chances(chances)
    room_type: Optional[Type[StandardRoom]] = types[idx]
    room = room_type()
    room.init_size_cat(rng)
    return room


def create_entrance(rng: SPDRandom, depth: int) -> Room:
    """Port of EntranceRoom.createEntrance()."""
    return _create_from_table(rng, _ENTRANCE_ROOM_TYPES, _ENTRANCE_CHANCES[depth])


def create_exit(rng: SPDRandom, depth: int) -> Room:
    """Port of ExitRoom.createExit()."""
    return _create_from_table(rng, _EXIT_ROOM_TYPES, _EXIT_CHANCES[depth])


def create_standard_room(rng: SPDRandom, depth: int) -> Room:
    """Port of StandardRoom.createRoom()."""
    return _create_from_table(rng, _STANDARD_ROOM_TYPES, _STANDARD_CHANCES[depth])
