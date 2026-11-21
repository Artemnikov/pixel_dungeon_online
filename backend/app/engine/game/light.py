# Copyright (C) 2026 ArtemNikov
#
"""SPD `actors/buffs/Light.java` helpers (the "light" buff)."""

from app.engine.entities.buffs import get_buff, remove_buff


def weaken_light(entity, amount: float) -> None:
    """`Light.weaken(n)`: `spend(-n)`, i.e. the remaining duration drops by n."""
    buff = get_buff(entity.buffs, "light")
    if buff is None:
        return
    buff.remaining -= amount
    if buff.remaining <= 0:
        remove_buff(entity.buffs, "light")


def detach_light(entity) -> None:
    remove_buff(entity.buffs, "light")
