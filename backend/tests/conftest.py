# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
"""Shared pytest fixtures for the engine test suite.

Two patterns account for most of the ~300 `GameInstance(...)` call sites
across this test suite:

1. `GameInstance("test-game"); game.mobs = {}` -- a real generated depth-1
   floor, just cleared of its default mob spawns.
2. A locally-defined helper (re-implemented per test file under names like
   `_open_game`/`make_game`/`make_floor`) that clears the current floor's
   grid to an open, all-FLOOR rectangle for full control over layout.

`game` and `open_game_factory` below cover both for *new* tests. Existing
call sites aren't migrated here -- with ~300 of them, many carrying
test-specific tweaks, a blind mechanical migration is its own large,
separate, risk-bearing change, not a drive-by part of adding this file.
"""

import pytest

from app.engine.dungeon.constants import TileType
from app.engine.manager import GameInstance


@pytest.fixture
def game() -> GameInstance:
    """A fresh GameInstance with a real generated depth-1 floor, no mobs."""
    g = GameInstance("test-game")
    g.mobs = {}
    return g


@pytest.fixture
def open_game_factory():
    """Factory for a GameInstance whose current floor is cleared to an open,
    all-FLOOR rectangle -- for tests that need full control over the grid
    instead of a real generated layout.

    Usage: `game = open_game_factory(width=12, height=12)`.
    """
    def _make(width: int = 10, height: int = 10, depth: int = 1,
              game_id: str = "test-game") -> GameInstance:
        g = GameInstance(game_id)
        g.players = {}
        g.mobs = {}
        floor = g._get_or_create_floor(depth)
        floor.grid = [[TileType.FLOOR for _ in range(width)] for _ in range(height)]
        floor.rebuild_flags()
        return g
    return _make
