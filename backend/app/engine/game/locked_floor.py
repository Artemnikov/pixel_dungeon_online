# Copyright (C) 2026 ArtemNikov
#
"""SPD `LockedFloor` buff helpers shared by the sealed-arena bosses."""

from app.engine.game.constants import LOCKED_FLOOR_DURATION, LOCKED_FLOOR_DURATION_STRONG


def is_stronger(game) -> bool:
    return "stronger_bosses" in getattr(game, "challenges", set())


def lock_duration(game) -> float:
    return LOCKED_FLOOR_DURATION_STRONG if is_stronger(game) else LOCKED_FLOOR_DURATION


def apply_locked_floor(game, floor_id: int) -> None:
    left = lock_duration(game)
    for player in game._players_on_floor(floor_id):
        player.locked_floor_left = left


def clear_locked_floor(game, floor_id: int) -> None:
    for player in game._players_on_floor(floor_id):
        player.locked_floor_left = None


def add_locked_floor_time(game, floor_id: int, amount: float) -> None:
    """`LockedFloor.addTime`: extends every sealed-in player's timer, capped at 50."""
    if amount <= 0:
        return
    for player in game._players_on_floor(floor_id):
        if player.locked_floor_left is not None:
            player.locked_floor_left = min(LOCKED_FLOOR_DURATION, player.locked_floor_left + amount)
