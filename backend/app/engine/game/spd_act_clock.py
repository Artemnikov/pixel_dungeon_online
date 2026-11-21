# Copyright (C) 2026 ArtemNikov
#
"""Runs a ported SPD `act()` once per SPD turn of the mob's own time.

A ported act returns the time it `spend()`s, or None when it decided to move
(SPD `getCloser`), which the generic movement AI performs.

* Real-time rooms call `run` every tick. One SPD turn is `TICKS_PER_TURN`
  ticks, so `act_cooldown` drains by `sim_ticks / TICKS_PER_TURN` per tick and
  the act runs whenever it reaches zero. After an act that spent its time on
  an attack or ability the generic AI is held off until the next act; after a
  move it may keep stepping on its own real-time cadence, as every mob does.
* Turn rooms charge time through the scheduler instead
  (`turn/mob_actors.SpdActMobActor`): the actor zeroes `act_cooldown` when
  the mob is due, `run` performs exactly one act, and the spend is handed back
  through `mob.act_spent`.
"""

from typing import Callable, Optional

from app.engine.game.constants import (
    SPD_ACT_LOOP_GUARD, TICKS_PER_TURN, TIME_TO_MOVE_BASE, TURN_TIME_EPSILON,
)

ActFn = Callable[[], Optional[float]]


def spend(mob, turns: float) -> None:
    mob.act_cooldown += float(turns)


def add_with_delay(mob, delay: float) -> None:
    """SPD `GameScene.add(mob, delay)`: the mob's first act waits `delay` turns."""
    mob.spawn_delay = float(delay)
    mob.act_cooldown = float(delay)
    mob.act_blocking = delay > 0


def _is_turn_room(game) -> bool:
    return getattr(game, "game_mode", None) == "turnbased"


def run(game, mob, act_fn: ActFn) -> bool:
    """Advance the mob's SPD time and act when due.

    Returns True when the generic movement AI must not run this tick.
    """
    if _is_turn_room(game):
        mob.act_cooldown = 0.0
        spent = act_fn()
        mob.act_spent = spent
        mob.act_blocking = spent is not None
        return spent is not None

    mob.act_cooldown -= game.sim_ticks / TICKS_PER_TURN
    acted_move = False
    guard = 0
    while mob.act_cooldown <= TURN_TIME_EPSILON and guard < SPD_ACT_LOOP_GUARD and mob.is_alive:
        guard += 1
        spent = act_fn()
        if spent is None:
            mob.act_cooldown += TIME_TO_MOVE_BASE / max(0.1, float(getattr(mob, "speed", 1.0)))
            mob.act_blocking = False
            acted_move = True
            break
        mob.act_cooldown += float(spent)
        mob.act_blocking = True
    if acted_move:
        return False
    return bool(mob.act_blocking)
