# Copyright (C) 2026 ArtemNikov
#
"""SPD `RatKing` AI: asleep until a hero talks to him, then wandering at
double speed with no enemy ever chosen (`chooseEnemy()` returns null)."""
import time

from app.engine.entities.mobs import RatKing
from app.engine.game.ai_spd_common import mob_speed
from app.engine.game.constants import AUTO_MOVE_INTERVAL
from app.engine.game.floor_state import FloorState


def _update_rat_king(game, king: RatKing, floor: FloorState, floor_id: int) -> None:
    if king.ai_state != "wandering":
        return
    move_times = getattr(game, "_mob_move_times", None)
    if move_times is None:
        move_times = game._mob_move_times = {}
    now = time.time()
    if now - move_times.get(king.id, 0.0) < 2 * AUTO_MOVE_INTERVAL / max(0.1, mob_speed(king)):
        return
    step = game._pick_wander_step(king, floor, floor_id, now)
    if step:
        move_times[king.id] = now
        game.move_entity(king.id, *step)
