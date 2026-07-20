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
"""Terrain-mutation primitives with zero GameInstance/entities coupling.

Split out of terrain_effects.py so entities/ (item/potion/artifact action
handlers) can import these at module scope instead of function-local --
these three touch only a duck-typed `floor` (grid/blob_areas/plants) plus
TileType, so unlike the rest of terrain_effects.py (which needs Player/
Entity/item classes from entities/) they have nothing that could create a
cycle.
"""
from typing import Tuple

from app.engine.dungeon.constants import TileType


GRASS_TILES = {TileType.FLOOR_GRASS, TileType.EMPTY_DECO, TileType.EMBERS,
               TileType.HIGH_GRASS, TileType.FURROWED_GRASS}


def plant_grass(floor, x: int, y: int, furrow: bool = False):
    """Plant grass at (x,y). Sets FURROWED_GRASS if furrow=True and regen off,
    else HIGH_GRASS. Only on empty/deco/embers/grass/furrowed tiles."""
    if not (0 <= x < floor.width and 0 <= y < floor.height):
        return
    t = floor.grid[y][x]
    if t not in GRASS_TILES:
        return
    if floor.plants and (x, y) in floor.plants:
        return
    if furrow:
        floor.grid[y][x] = TileType.FURROWED_GRASS
    else:
        floor.grid[y][x] = TileType.HIGH_GRASS


def _plant_seed_at(floor, pos: Tuple[int, int], plant_type: str):
    plant = {
        "pos": pos,
        "plant_type": plant_type,
        "triggered": False,
    }
    floor.plants[pos] = plant


def _create_gas(floor, pos: Tuple[int, int], strength: int, gas_type: str = "toxic_gas"):
    blob_id = f"{gas_type}_{pos[0]}_{pos[1]}"
    cells = set()
    volume = {}
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                if floor.flags and not floor.flags.solid[ny][nx]:
                    cells.add((nx, ny))
                    volume[(nx, ny)] = strength
    if cells:
        for bid in list(floor.blob_areas.keys()):
            b = floor.blob_areas[bid]
            if b.get("type") == gas_type and b.get("cells", set()) & cells:
                del floor.blob_areas[bid]
        floor.blob_areas[blob_id] = {"type": gas_type, "cells": cells, "volume": volume}
