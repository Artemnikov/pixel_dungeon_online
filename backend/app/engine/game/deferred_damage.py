# Copyright (C) 2026 ArtemNikov
#
"""Port of SPD `Viscosity.DeferedDamage` as used by the Rusted Fist.

`extend(d)` pools damage; a fresh pool waits one turn (`postpone(TICK)`), then
every SPD turn releases `max(1, (int)(pool * 0.1))` until the pool is empty.
"""

from app.engine.game.constants import TICKS_PER_TURN
from app.engine.game.dot_death import finish_dot_kill


def extend_deferred(entity, amount: int) -> None:
    if amount <= 0 and entity.deferred_damage > 0:
        return
    if entity.deferred_damage <= 0:
        entity.deferred_ticks = 0
    entity.deferred_damage += max(0, int(amount))


def tick_deferred_damage(game, entity, floor_id) -> None:
    if getattr(entity, "deferred_damage", 0) <= 0:
        return
    entity.deferred_ticks += game.sim_ticks
    while entity.deferred_ticks >= TICKS_PER_TURN and entity.deferred_damage > 0:
        entity.deferred_ticks -= TICKS_PER_TURN
        if not entity.is_alive:
            entity.deferred_damage = 0
            return
        release = max(1, int(entity.deferred_damage * 0.1))
        hurt = getattr(entity, "take_deferred_damage", None) or entity.take_damage
        taken = hurt(release)
        entity.deferred_damage -= release
        game.add_event("DAMAGE", {"target": entity.id, "amount": taken if isinstance(taken, int) else release,
                                  "deferred": True}, floor_id=floor_id)
        if not entity.is_alive:
            entity.deferred_damage = 0
            if getattr(entity, "type", None) != "player":
                finish_dot_kill(game, entity, floor_id)
            return
    if entity.deferred_damage <= 0:
        entity.deferred_damage = 0
        entity.deferred_ticks = 0
