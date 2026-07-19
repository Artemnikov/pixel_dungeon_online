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
"""City-region StandardRoom subclasses (region-table indices 15-19) + their
entrance/exit variants (registration-table indices 12-15). All still
`paint = _stub_paint` placeholders (see standard_rooms_base.py's module
docstring) -- unreachable on sewers floors, out of this port's current scope.

Split out of standard_rooms.py, which used to hold all ~85 StandardRoom
subclasses across every region in one file.
"""

from app.engine.dungeon.spd_levelgen.room_types import StandardRoom
from app.engine.dungeon.spd_levelgen.standard_rooms_base import _stub_paint

# -- City standard rooms (region-table indices 15-19) ----------------------

class HallwayRoom(StandardRoom):
    paint = _stub_paint


class LibraryHallRoom(StandardRoom):
    paint = _stub_paint


class LibraryRingRoom(StandardRoom):
    paint = _stub_paint


class StatuesRoom(StandardRoom):
    paint = _stub_paint


class SegmentedLibraryRoom(StandardRoom):
    paint = _stub_paint


# -- City entrance/exit variants (entrance indices 12-15, exit indices 12-15) -

class HallwayEntranceRoom(HallwayRoom):
    def is_entrance(self) -> bool:
        return True


class HallwayExitRoom(HallwayRoom):
    def is_exit(self) -> bool:
        return True


class StatuesEntranceRoom(StatuesRoom):
    def is_entrance(self) -> bool:
        return True


class StatuesExitRoom(StatuesRoom):
    def is_exit(self) -> bool:
        return True


class LibraryHallEntranceRoom(LibraryHallRoom):
    def is_entrance(self) -> bool:
        return True


class LibraryHallExitRoom(LibraryHallRoom):
    def is_exit(self) -> bool:
        return True


class LibraryRingEntranceRoom(LibraryRingRoom):
    def is_entrance(self) -> bool:
        return True


class LibraryRingExitRoom(LibraryRingRoom):
    def is_exit(self) -> bool:
        return True
