"""Verifies REGION_DECO/REGION_DECO_ALT (sewers barrel props) are SOLID-only
(not LOS-blocking) in every region, flamable only on sewers floors, and burn
to WATER/FLOOR (not EMBERS) -- mirrors SewerLevel.java's buildFlagMaps()/
destroy() overrides on top of Terrain.java's region-agnostic SOLID-only base.
"""

from app.engine.dungeon.constants import TileType
from app.engine.dungeon.terrain_flags import (
    LOS_BLOCKING,
    SOLID,
    build_flag_maps,
    flags_of,
)
from app.engine.game.blobs import tick_blob_areas
from app.engine.game.floor_state import FloorState


def test_region_deco_is_solid_not_los_blocking():
    for tile in (TileType.REGION_DECO, TileType.REGION_DECO_ALT):
        f = flags_of(tile)
        assert f & SOLID
        assert not f & LOS_BLOCKING


def _region_deco_grid():
    W = TileType.WALL
    F = TileType.FLOOR
    R = TileType.REGION_DECO
    return [
        [W, W, W, W, W],
        [W, F, F, F, W],
        [W, F, R, F, W],
        [W, F, F, F, W],
        [W, W, W, W, W],
    ]


def test_region_deco_flamable_only_in_sewers_region():
    grid = _region_deco_grid()

    sewers_maps = build_flag_maps(grid, region="sewers")
    assert sewers_maps.flamable[2][2]

    other_maps = build_flag_maps(grid, region="prison")
    assert not other_maps.flamable[2][2]

    default_maps = build_flag_maps(grid)
    assert not default_maps.flamable[2][2]


def _make_floor(region: str, grid) -> FloorState:
    floor = FloorState(floor_id=2, grid=grid, rooms=[], mobs={}, items={}, region=region)
    floor.rebuild_flags()
    return floor


def _ignite(floor: FloorState, x: int, y: int) -> None:
    floor.blob_areas["fire_1"] = {"type": "fire", "cells": {(x, y)}, "volume": {(x, y): 0.01}}


def test_burning_region_deco_converts_to_water_on_sewers_floor():
    grid = _region_deco_grid()
    floor = _make_floor("sewers", grid)
    assert floor.flags.flamable[2][2]

    _ignite(floor, 2, 2)
    events = tick_blob_areas({floor.floor_id: floor}, {})

    assert floor.grid[2][2] == TileType.FLOOR_WATER
    patches = [e for e in events if e["type"] == "MAP_PATCH"]
    assert patches, events
    tiles = patches[0]["data"]["tiles"]
    assert any(t["x"] == 2 and t["y"] == 2 and t["tile"] == TileType.FLOOR_WATER for t in tiles)


def test_region_deco_alt_converts_to_floor_on_sewers_floor():
    W = TileType.WALL
    F = TileType.FLOOR
    A = TileType.REGION_DECO_ALT
    grid = [
        [W, W, W, W, W],
        [W, F, F, F, W],
        [W, F, A, F, W],
        [W, F, F, F, W],
        [W, W, W, W, W],
    ]
    floor = _make_floor("sewers", grid)
    _ignite(floor, 2, 2)
    tick_blob_areas({floor.floor_id: floor}, {})

    assert floor.grid[2][2] == TileType.FLOOR


def test_region_deco_inert_in_caves_region():
    grid = _region_deco_grid()
    floor = _make_floor("caves", grid)
    assert not floor.flags.flamable[2][2]

    _ignite(floor, 2, 2)
    tick_blob_areas({floor.floor_id: floor}, {})

    # Not flamable -> the fire-blob loop's `if vol <= 0: if flamable: ...`
    # branch never fires; the tile is untouched and the blob just depletes.
    assert floor.grid[2][2] == TileType.REGION_DECO
