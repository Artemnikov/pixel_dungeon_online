"""Verifies Door.Type.BARRICADE (levels/rooms/Room.java's Door.Type enum,
used by e.g. StorageRoom/MassGraveRoom/MineLargeRoom) round-trips to a
distinct, flammable tile -- not a permanent WALL.

Regression test for a real generator bug: spd_adapter.py used to collapse
spd_terrain.BARRICADE into TileType.WALL, which has no fire-burn behavior.
Any room whose only connection used DoorType.BARRICADE (a deliberate,
common SPD mechanic -- "burn through this to get in") became permanently
sealed, with no way to ever reach its contents. Mirrors Terrain.java:100
(`flags[BARRICADE] = FLAMABLE | SOLID | LOS_BLOCKING`) and Level.destroy()'s
generic "any flammable tile burns to EMBERS" rule.
"""

from app.engine.dungeon.constants import TileType
from app.engine.dungeon.spd_levelgen import terrain as spd_terrain
from app.engine.dungeon.terrain_flags import FLAMABLE, LOS_BLOCKING, SOLID, flags_of
from app.engine.game.blobs import tick_blob_areas
from app.engine.game.floor_state import FloorState
from app.engine.game.spd_adapter import _SPD_TO_TILE


def test_barricade_maps_to_a_distinct_flamable_tile_not_wall():
    assert _SPD_TO_TILE[spd_terrain.BARRICADE] == TileType.BARRICADE
    assert TileType.BARRICADE != TileType.WALL


def test_barricade_is_solid_los_blocking_and_flamable():
    f = flags_of(TileType.BARRICADE)
    assert f & SOLID
    assert f & LOS_BLOCKING
    assert f & FLAMABLE


def _barricade_grid():
    W = TileType.WALL
    F = TileType.FLOOR
    B = TileType.BARRICADE
    return [
        [W, W, W, W, W],
        [W, F, F, F, W],
        [W, F, B, F, W],
        [W, F, F, F, W],
        [W, W, W, W, W],
    ]


def test_burning_barricade_converts_to_embers_and_becomes_passable():
    grid = _barricade_grid()
    floor = FloorState(floor_id=1, grid=grid, rooms=[], mobs={}, items={}, region="sewers")
    floor.rebuild_flags()
    assert floor.flags.flamable[2][2]
    assert not floor.flags.passable[2][2]

    floor.blob_areas["fire_1"] = {"type": "fire", "cells": {(2, 2)}, "volume": {(2, 2): 0.01}}
    events = tick_blob_areas({floor.floor_id: floor}, {})

    assert floor.grid[2][2] == TileType.EMBERS
    assert floor.flags.passable[2][2]
    patches = [e for e in events if e["type"] == "MAP_PATCH"]
    assert patches, events
    tiles = patches[0]["data"]["tiles"]
    assert any(t["x"] == 2 and t["y"] == 2 and t["tile"] == TileType.EMBERS for t in tiles)
