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
"""Halls-region StandardRoom subclasses (region-table indices 20-24) + their
entrance/exit variants (registration-table indices 16-19). All still
`paint = _stub_paint` placeholders (see standard_rooms_base.py's module
docstring) -- unreachable on sewers floors, out of this port's current scope.

Index 21 (region-table) and index 16 (entrance/exit tables) intentionally
have no class here -- they reuse RegionDecoPatchRoom/RegionDecoPatchEntranceRoom/
RegionDecoPatchExitRoom from standard_rooms_sewers.py (SPD does
`rooms.add(RegionDecoPatchRoom.class)` a second time); see the registration
tables in standard_rooms.py.

Split out of standard_rooms.py, which used to hold all ~85 StandardRoom
subclasses across every region in one file.
"""

from app.engine.dungeon.spd_levelgen.room_types import StandardRoom
from app.engine.dungeon.spd_levelgen.standard_rooms_base import _stub_paint

# -- Halls standard rooms (region-table indices 20-24) ---------------------

class RuinsRoom(StandardRoom):
    paint = _stub_paint


# index 21 reuses RegionDecoPatchRoom (Java does rooms.add(RegionDecoPatchRoom.class) again)

class ChasmRoom(StandardRoom):
    paint = _stub_paint


class SkullsRoom(StandardRoom):
    paint = _stub_paint


class RitualRoom(StandardRoom):
    paint = _stub_paint


# -- Halls entrance/exit variants (entrance indices 16-19, exit indices 16-19) -

# index 16 reuses RegionDecoPatchEntranceRoom/RegionDecoPatchExitRoom (already defined)

class RuinsEntranceRoom(RuinsRoom):
    def is_entrance(self) -> bool:
        return True


class RuinsExitRoom(RuinsRoom):
    def is_exit(self) -> bool:
        return True


class ChasmEntranceRoom(ChasmRoom):
    def is_entrance(self) -> bool:
        return True


class ChasmExitRoom(ChasmRoom):
    def is_exit(self) -> bool:
        return True


class RitualEntranceRoom(RitualRoom):
    def is_entrance(self) -> bool:
        return True


class RitualExitRoom(RitualRoom):
    def is_exit(self) -> bool:
        return True
