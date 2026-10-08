"""Tap-to-travel for turn-based rooms: one tile per hero turn, SPD-style.

A real-time room walks a client-supplied path by consuming one queued delta per
tick (`TickMixin._tick_player` -> `PlayerTickMixin._process_player_movement`).
A turn room has no such pump -- it never calls `_tick_player` -- so the same
`path_queue` is drained here instead: `TurnBasedGameInstance._player_walk_turn`
takes the head of the queue on the hero's own turn and charges the SPD move
cost, which is the turn-mode equivalent of `HeroAction.Move`: one click, one
tile now, one tile per following turn.

The path itself stays client-computed, as in real time: `resolveTapAction` runs
the BFS in the browser and ships unit deltas, and every step is validated by
`move_entity` before it moves anybody. The consequence is that this mode cannot
re-path the way SPD's `Hero.getCloser` does -- a mob that walks into the
corridor ends the trip rather than being routed around.

Two rules come from SPD's hero, both of which exist to stop a walk that is no
longer what the player asked for:

* A hostile that becomes visible interrupts (`Hero.checkVisibleMobs`), and the
  trip is dropped rather than turned into an attack. SPD re-paths around a
  visible char; there is no re-path here, so stopping is the honest outcome.
* The next tile being occupied ends the trip for the same reason, which is also
  why the walk never bump-attacks: attacking is an explicit action, the way
  SPD's `Hero.handle` only creates a `HeroAction.Attack` for a clicked mob.
"""

from typing import FrozenSet, Iterable, List, Optional, Tuple

Step = Tuple[int, int]


def sanitize_path_steps(steps: Iterable) -> List[Step]:
    """The unit deltas of a client path, in order, with anything else dropped.

    `move_entity` only validates the cell a step lands on, so a non-unit delta
    is the one input that could carry a hero further than a tile, and a zero
    delta is a turn spent standing still. Deliberately uncapped, like the
    real-time ingress in `api/ws_handlers.py`: a walk costs a turn per tile and
    any player action replaces it, so a long path is a long walk rather than a
    way to hold the room.
    """
    result: List[Step] = []
    for step in steps or []:
        try:
            dx, dy = int(step[0]), int(step[1])
        except (TypeError, ValueError, IndexError):
            continue
        if (dx or dy) and max(abs(dx), abs(dy)) <= 1:
            result.append((dx, dy))
    return result


def visible_hostiles(game, player) -> FrozenSet[Step]:
    """Living non-allied mobs the player can currently see, by tile.

    Uses the player's own sight radius so a Light or Farsight buff widens the
    same way it does for every other FOV consumer (`VisionMixin._view_distance`).
    Alignment is the engine's faction test, as in `TurnBasedGameInstance._mob_can_strike`.
    """
    floor = game._get_or_create_floor(player.floor_id)
    if floor is None or not floor.mobs:
        return frozenset()

    visible = set(
        game.get_visible_tiles(
            player.pos,
            radius=game._view_distance(player),
            floor_id=player.floor_id,
            viewer_id=player.id,
        )
    )
    if not visible:
        return frozenset()

    return frozenset(
        (mob.pos.x, mob.pos.y)
        for mob in floor.mobs.values()
        if mob.is_alive
        and mob.faction != player.faction
        and (mob.pos.x, mob.pos.y) in visible
    )


def refresh_visible_enemies(game, actor) -> None:
    """Record what the hero can see, so the next call can spot a new arrival.

    SPD keeps this list on the hero and rewrites it on every `act`, which makes
    the interrupt edge-triggered: an enemy already in view does not stop you
    again. A hero parked waiting for input takes no turns, so this is also
    called when a walk starts -- otherwise a rat that has been sitting in view
    for three turns would read as newly visible and kill the trip on step one.
    """
    if actor.cancelled or not actor.player.is_active:
        return
    actor.visible_enemies = visible_hostiles(game, actor.player)


def walk_interrupted(game, actor) -> bool:
    """Whether a hostile has come into view since the last check.

    The comparison is against `refresh_visible_enemies`, so it fires on the turn
    a mob steps into the FOV and never fires again for a mob that was already
    there when the trip started.
    """
    return bool(visible_hostiles(game, actor.player) - actor.visible_enemies)
