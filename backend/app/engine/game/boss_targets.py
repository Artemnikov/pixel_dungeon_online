# Copyright (C) 2026 ArtemNikov
#
"""Multiplayer stand-ins for SPD's `Dungeon.hero` in boss and minion AI.

SPD has one hero; a room has several. Each attack resolves against its own
chosen target, a "not in the hero's FOV" test uses the union of every player's
FOV, and effects SPD applies only to the hero apply to every player in the arena.
"""

import math
import time
from typing import List, Optional, Set, Tuple

from app.engine.entities.base import Position


def arena_players(game, floor_id: int, include_downed: bool = False) -> List:
    return [
        p for p in game._players_on_floor(floor_id)
        if p.is_alive and (include_downed or not getattr(p, "is_downed", False))
    ]


def player_fov(game, player) -> Set[Tuple[int, int]]:
    return set(game.get_visible_tiles(
        player.pos, radius=game._view_distance(player),
        floor_id=player.floor_id, viewer_id=player.id))


def union_hero_fov(game, floor_id: int) -> Set[Tuple[int, int]]:
    """SPD `Dungeon.level.heroFOV`, unioned over every active player on the floor."""
    cells: Set[Tuple[int, int]] = set()
    for player in arena_players(game, floor_id):
        cells |= player_fov(game, player)
    return cells


def mob_fov(game, mob, floor_id: int) -> Set[Tuple[int, int]]:
    return set(game.get_visible_tiles(
        mob.pos, radius=game._view_distance(mob), floor_id=floor_id))


def choose_enemy(game, mob, floor_id: int, fov: Optional[Set[Tuple[int, int]]] = None):
    """SPD `Mob.chooseEnemy()` for the hero case: the nearest player the mob can
    see who is alive, active and not invisible."""
    if fov is None:
        fov = mob_fov(game, mob, floor_id)
    best = None
    best_dist = None
    for player in arena_players(game, floor_id):
        if getattr(player, "invisible", 0) > 0 or player.has_buff("time_stasis"):
            continue
        if (player.pos.x, player.pos.y) not in fov:
            continue
        dist = game._get_distance(mob.pos, player.pos)
        if best is None or dist < best_dist:
            best, best_dist = player, dist
    return best


def nearest_player(game, pos: Position, floor_id: int):
    return game._find_nearest_player(pos, floor_id)


def hero_cooldown_turns(game, player) -> float:
    """SPD `hero.cooldown()`: SPD turns until the player's next action.

    Turn rooms record the cost of the player's last action. Real-time rooms
    read the remaining `action_until` lock, with a single step as the floor.
    """
    if player is None:
        return 1.0
    last = getattr(player, "_last_turn_cost", None)
    if getattr(game, "game_mode", None) == "turnbased" and last is not None:
        return float(last)
    remaining = getattr(player, "action_until", 0.0) - time.time()
    return max(1.0, remaining)


def spend_gate(player_cooldown: float, lo: float, hi: float) -> float:
    """`GameMath.gate(lo, (int)Math.ceil(hero.cooldown()), hi)`."""
    return max(lo, min(float(math.ceil(player_cooldown)), hi))


def interrupt(game, player) -> None:
    """SPD `Hero.interrupt()`: drop any queued multi-step travel."""
    if player is None:
        return
    actors = getattr(game, "_player_actors", None)
    if actors is not None:
        actor = actors.get(player.id)
        if actor is not None:
            actor.clear_walk()
            return
    movement = getattr(player, "movement", None)
    if movement is not None:
        movement.path_queue.clear()
