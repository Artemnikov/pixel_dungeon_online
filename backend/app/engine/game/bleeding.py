# Copyright (C) 2026 ArtemNikov
#
"""Port of SPD `actors/buffs/Bleeding.java`.

`set(level)` only ever raises the level. Once per SPD turn the level decays to
`NormalFloat(level / 2, level)` and `round(level)` damage is dealt; at zero the
buff detaches. The "bleeding" buff carries the indicator (its level is the
rounded SPD level); the float level lives on the entity.
"""

from app.engine.entities.base import normal_float
from app.engine.entities.buffs import add_buff, get_buff, remove_buff
from app.engine.game.constants import BLEEDING_BUFF_DURATION, TICKS_PER_TURN
from app.engine.game.dot_death import finish_dot_kill


def apply_bleeding(entity, level: float) -> None:
    """`Buff.affect(target, Bleeding.class).set(level)`."""
    if level <= 0:
        return
    if get_buff(entity.buffs, "bleeding") is None:
        entity.bleeding_level = 0.0
        entity.bleeding_ticks = TICKS_PER_TURN - 1
    if entity.bleeding_level < level:
        entity.bleeding_level = float(level)
    buff = add_buff(entity.buffs, "bleeding", duration=BLEEDING_BUFF_DURATION,
                    level=max(1, round(entity.bleeding_level)), stack_mode="extend")
    if buff is not None:
        buff.level = max(1, round(entity.bleeding_level))


def _detach(entity) -> None:
    remove_buff(entity.buffs, "bleeding")
    entity.bleeding_level = 0.0
    entity.bleeding_ticks = 0


def tick_bleeding(game, entity, floor_id) -> None:
    """Advance the bleed by this call's ticks, acting once per whole SPD turn."""
    buff = get_buff(entity.buffs, "bleeding")
    if buff is None:
        if entity.bleeding_level:
            entity.bleeding_level = 0.0
            entity.bleeding_ticks = 0
        return
    if entity.bleeding_level <= 0:
        entity.bleeding_level = float(max(1, buff.level))
    buff.remaining = max(buff.remaining, BLEEDING_BUFF_DURATION / 2)
    entity.bleeding_ticks += game.sim_ticks
    while entity.bleeding_ticks >= TICKS_PER_TURN:
        entity.bleeding_ticks -= TICKS_PER_TURN
        if not entity.is_alive:
            _detach(entity)
            return
        entity.bleeding_level = normal_float(entity.bleeding_level / 2.0, entity.bleeding_level)
        dmg = round(entity.bleeding_level)
        if dmg <= 0:
            _detach(entity)
            return
        buff.level = dmg
        hurt = getattr(entity, "take_bleed_damage", None) or entity.take_damage
        taken = hurt(dmg)
        game.add_event("DAMAGE", {"target": entity.id, "amount": taken if isinstance(taken, int) else dmg,
                                  "bleed": True}, floor_id=floor_id)
        if not entity.is_alive:
            _detach(entity)
            if getattr(entity, "type", None) != "player":
                finish_dot_kill(game, entity, floor_id)
            return
