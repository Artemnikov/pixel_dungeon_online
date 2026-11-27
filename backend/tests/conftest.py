# Copyright (C) 2026 ArtemNikov
#
"""Shared pytest fixtures and factory helpers for the engine test suite.

Most `GameInstance(...)` call sites across this suite build one of a few
standard scenarios. Rather than re-implement the setup per file (under names
like `make_game`/`_open_game`/`make_floor`), tests import the helpers below or
use the fixtures. A file-specific variant stays local only when it carries
behavior the shared helper does not -- a custom region, an extra counter, a
seeded timer -- and then it wraps the shared call rather than re-deriving it.

Three shapes cover the suite:

1. `game` -- a real generated depth-1 floor, just cleared of mobs.
2. `make_open_game` / `open_game_factory` -- a floor cleared to an open,
   all-FLOOR rectangle, for full control over layout.
3. `make_open_floor` + `make_game_with_floors` -- an open `FloorState` installed
   under a specific floor id, for boss/arena tests that skip generation.
"""

from functools import partial  # noqa: F401  (re-exported for test modules)

import pytest

from app.engine.dungeon.constants import TileType
from app.engine.game.floor_state import FloorState
from app.engine.manager import GameInstance


@pytest.fixture
def game() -> GameInstance:
    """A fresh GameInstance with a real generated depth-1 floor, no mobs."""
    g = GameInstance("test-game")
    g.mobs = {}
    return g


def make_open_game(
    width: int = 10,
    height: int = 10,
    depth: int = 1,
    *,
    game_id: str = "test-game",
    difficulty=None,
) -> GameInstance:
    """A GameInstance whose `depth` floor is an open, all-FLOOR rectangle.

    Clears the floor's mobs, items, traps and plants so the only content is the
    grid the test paints. `difficulty` is only assigned when given.
    """
    g = GameInstance(game_id)
    g.players = {}
    floor = g._get_or_create_floor(depth)
    floor.grid = [[TileType.FLOOR for _ in range(width)] for _ in range(height)]
    floor.mobs.clear()
    floor.items.clear()
    floor.traps.clear()
    floor.plants.clear()
    floor.rebuild_flags()
    if difficulty is not None:
        g.difficulty = difficulty
    return g


def make_open_floor(
    floor_id: int = 1,
    w: int = 10,
    h: int = 10,
    *,
    region: str = "halls",
    mob_limit=None,
) -> FloorState:
    """An open FloorState for tests that install their own floor."""
    floor = FloorState(
        floor_id=floor_id,
        grid=[[TileType.FLOOR for _ in range(w)] for _ in range(h)],
        rooms=[],
        mobs={},
        items={},
        region=region,
    )
    floor.rebuild_flags()
    if mob_limit is not None:
        floor.mob_limit = mob_limit
    return floor


def make_game_with_floors(*floors: FloorState, game_id: str = "test-game", set_depth: bool = True) -> GameInstance:
    """A GameInstance with the given FloorStates installed.

    `set_depth` mirrors the two idioms in the suite: most install a floor and
    point `depth` at it, a few (dm300) keep `depth` at its default.
    """
    g = GameInstance(game_id)
    g.players = {}
    for floor in floors:
        g.floors[floor.floor_id] = floor
    if set_depth and floors:
        g.depth = floors[-1].floor_id
    return g


def make_grid_game(grid) -> GameInstance:
    """A GameInstance whose only floor is `grid` (rows of tile ids)."""
    g = GameInstance("test-game")
    floor = FloorState(floor_id=g.depth, grid=grid, rooms=[], mobs={}, items={})
    floor.rebuild_flags()
    g.floors[g.depth] = floor
    return g


def open_grid(width: int, height: int):
    """A width x height all-FLOOR grid (rows of tile ids)."""
    return [[TileType.FLOOR for _ in range(width)] for _ in range(height)]


def open_floor_on_game(game, depth: int = 1, w: int = 20, h: int = 20):
    """Clear and reshape `depth` floor on an existing GameInstance to an all-FLOOR rectangle."""
    floor = game._get_or_create_floor(depth)
    floor.grid = [[TileType.FLOOR for _ in range(w)] for _ in range(h)]
    floor.mobs.clear()
    floor.items.clear()
    floor.traps.clear()
    floor.plants.clear()
    floor.rebuild_flags()
    return floor


@pytest.fixture
def open_game_factory():
    """Factory for a GameInstance with an open, all-FLOOR rectangle floor.

    Usage: `game = open_game_factory(width=12, height=12)`.
    """
    return partial(make_open_game)
