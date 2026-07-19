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
"""Prison-region StandardRoom subclasses (region-table indices 5-9) + their
entrance/exit variants (registration-table indices 4-7). All still
`paint = _stub_paint` placeholders (see standard_rooms_base.py's module
docstring) -- unreachable on sewers floors, out of this port's current scope.

Split out of standard_rooms.py, which used to hold all ~85 StandardRoom
subclasses across every region in one file.
"""

from app.engine.dungeon.spd_levelgen.room_types import StandardRoom
from app.engine.dungeon.spd_levelgen.standard_rooms_base import StandardBridgeRoom, _stub_paint

# -- Prison standard rooms (region-table indices 5-9) ----------------------

class RegionDecoLineRoom(StandardRoom):
    paint = _stub_paint


class SegmentedRoom(StandardRoom):
    paint = _stub_paint


class PillarsRoom(StandardRoom):
    paint = _stub_paint


class ChasmBridgeRoom(StandardBridgeRoom):
    paint = _stub_paint


class CellBlockRoom(StandardRoom):
    paint = _stub_paint


# -- Prison entrance/exit variants (entrance indices 4-7, exit indices 4-7) -

class RegionDecoLineEntranceRoom(RegionDecoLineRoom):
    def is_entrance(self) -> bool:
        return True


class RegionDecoLineExitRoom(RegionDecoLineRoom):
    def is_exit(self) -> bool:
        return True


class ChasmBridgeEntranceRoom(ChasmBridgeRoom):
    def is_entrance(self) -> bool:
        return True


class ChasmBridgeExitRoom(ChasmBridgeRoom):
    def is_exit(self) -> bool:
        return True


class PillarsEntranceRoom(PillarsRoom):
    def is_entrance(self) -> bool:
        return True


class PillarsExitRoom(PillarsRoom):
    def is_exit(self) -> bool:
        return True


class CellBlockEntranceRoom(CellBlockRoom):
    def is_entrance(self) -> bool:
        return True


class CellBlockExitRoom(CellBlockRoom):
    def is_exit(self) -> bool:
        return True
