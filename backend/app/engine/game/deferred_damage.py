# Copyright (C) 2026 ArtemNikov
#
"""Port of SPD `Viscosity.DeferedDamage` as used by the Rusted Fist.

`extend(d)` pools damage; a fresh pool waits one turn (`postpone(TICK)`), then
every SPD turn releases `max(1, (int)(pool * 0.1))` until the pool is empty.
"""

from app.engine.entities.buffs import add_buff, get_buff, remove_buff
from app.engine.game.constants import DEFERRED_BUFF_DURATION, TICKS_PER_TURN
from app.engine.game.dot_death import finish_dot_kill

# The "deferred_damage" buff is the indicator (its level is the pool); the
# pool itself lives on the entity. Removing the buff (a cleanse) clears it.
_BUFF = "deferred_damage"


def _sync_indicator(entity) -> None:
    if entity.deferred_damage > 0:
        buff = add_buff(entity.buffs, _BUFF, duration=DEFERRED_BUFF_DURATION,
                        level=entity.deferred_damage, stack_mode="extend")
        if buff is not None:
            buff.level = entity.deferred_damage
            buff.remaining = DEFERRED_BUFF_DURATION
    else:
        remove_buff(entity.buffs, _BUFF)


def extend_deferred(entity, amount: int) -> None:
    if amount <= 0 and entity.deferred_damage > 0:
        return
    if entity.deferred_damage <= 0:
        entity.deferred_ticks = 0
    entity.deferred_damage += max(0, int(amount))
    _sync_indicator(entity)


def tick_deferred_damage(game, entity, floor_id) -> None:
    if getattr(entity, "deferred_damage", 0) <= 0:
        return
    if get_buff(entity.buffs, _BUFF) is None:
        entity.deferred_damage = 0
        entity.deferred_ticks = 0
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
        _sync_indicator(entity)
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
        _sync_indicator(entity)
