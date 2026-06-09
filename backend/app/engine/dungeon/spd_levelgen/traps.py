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
"""Minimal port of com.shatteredpixel.shatteredpixeldungeon.levels.traps.Trap --
just enough surface (`avoidsHallways`/`visible`/`set`/`reveal`/`hide`) for
RegularPainter.paintTraps to run; reveal()/hide()/set() consume no RNG in the
original, and the concrete trap subclasses used by sewers levels override
nothing relevant beyond `avoidsHallways` (verified against Trap.java + the 11
sewers trap class files)."""

from __future__ import annotations


class Trap:
    avoids_hallways = False

    def __init__(self):
        self.visible = True
        self.pos = -1

    def set(self, pos: int) -> "Trap":
        self.pos = pos
        return self

    def reveal(self) -> "Trap":
        self.visible = True
        return self

    def hide(self) -> "Trap":
        self.visible = False
        return self


class WornDartTrap(Trap):
    avoids_hallways = True


class ChillingTrap(Trap):
    pass


class ShockingTrap(Trap):
    pass


class ToxicTrap(Trap):
    pass


class AlarmTrap(Trap):
    pass


class OozeTrap(Trap):
    pass


class ConfusionTrap(Trap):
    pass


class FlockTrap(Trap):
    pass


class SummoningTrap(Trap):
    pass


class TeleportationTrap(Trap):
    pass


class GatewayTrap(Trap):
    avoids_hallways = True


# SewerLevel.trapClasses()/trapChances() -- depth==1 vs depth>1 (Random.java
# source confirms depth-1 sewers floors only ever roll WornDartTrap).
_DEPTH1_TRAP_CLASSES = (WornDartTrap,)
_DEPTH1_TRAP_CHANCES = (1.0,)

_REGULAR_TRAP_CLASSES = (
    ChillingTrap, ShockingTrap, ToxicTrap, WornDartTrap,
    AlarmTrap, OozeTrap,
    ConfusionTrap, FlockTrap, SummoningTrap, TeleportationTrap, GatewayTrap,
)
_REGULAR_TRAP_CHANCES = (4.0, 4.0, 4.0, 4.0, 2.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0)


def sewer_trap_classes(depth: int):
    return _DEPTH1_TRAP_CLASSES if depth == 1 else _REGULAR_TRAP_CLASSES


def sewer_trap_chances(depth: int):
    return _DEPTH1_TRAP_CHANCES if depth == 1 else _REGULAR_TRAP_CHANCES


def reveal_hidden_trap_chance() -> float:
    """TrapMechanism.revealHiddenTrapChance() -- depends on trinketLevel()
    (hero meta-state); fresh game -> 0 (no TrapMechanism trinket found)."""
    return 0.0
