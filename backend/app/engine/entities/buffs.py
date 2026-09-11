from __future__ import annotations

import uuid
from typing import Dict, Optional, Tuple

from pydantic import BaseModel, Field


class Buff(BaseModel):
    id: str
    type: str
    remaining: float = 0.0
    level: int = 0
    source_id: Optional[str] = None
    interval: float = 1.0
    stack_mode: str = "replace"  # "replace" | "extend" | "stack"


class BuffDefinition(BaseModel):
    """Metadata for a buff: opposing buffs cleansed on attach and immunities granted."""
    type: str
    cleanses: Tuple[str, ...] = ()
    immunities: Tuple[str, ...] = ()


BUFF_DEFINITIONS: Dict[str, BuffDefinition] = {
    "frost": BuffDefinition(type="frost", cleanses=("burning", "chill", "chilled")),
    "frozen": BuffDefinition(type="frozen", cleanses=("burning", "chill", "chilled")),
    "chill": BuffDefinition(type="chill", cleanses=("burning",)),
    "chilled": BuffDefinition(type="chilled", cleanses=("burning",)),
    "frost_imbue": BuffDefinition(
        type="frost_imbue",
        cleanses=("frost", "frozen", "chill", "chilled"),
        immunities=("frost", "frozen", "chill", "chilled"),
    ),
    "fire_imbue": BuffDefinition(
        type="fire_imbue",
        cleanses=("chill", "chilled", "frost", "frozen"),
        immunities=("burning",),
    ),
    "toxic_imbue": BuffDefinition(
        type="toxic_imbue",
        cleanses=("poison", "poisoned"),
        immunities=("poison", "poisoned", "toxic_gas"),
    ),
}

# SPD Frost = full paralysis: a frozen char cannot move or act (Frost.paralysed++).
# Both names occur in the remake -- "frost" (potions/snap-freeze) and "frozen"
# (bombs, frost trap) -- and both root the character.
FREEZE_BUFFS = ("frost", "frozen")


def is_frozen(buffs: list[Buff]) -> bool:
    return any(b.type in FREEZE_BUFFS for b in buffs)


def add_buff(buffs: list[Buff], buff_type: str, duration: float, level: int = 0, source_id: Optional[str] = None, stack_mode: str = "replace") -> Optional[Buff]:
    for active in buffs:
        active_defn = BUFF_DEFINITIONS.get(active.type)
        if active_defn and buff_type in active_defn.immunities:
            return None

    defn = BUFF_DEFINITIONS.get(buff_type)
    if defn:
        for opposed in defn.cleanses:
            remove_buff(buffs, opposed)

    existing = next((b for b in buffs if b.type == buff_type), None)
    if existing:
        if stack_mode == "replace":
            existing.remaining = duration
            existing.level = level
            existing.source_id = source_id
            return existing
        elif stack_mode == "extend":
            existing.remaining = max(existing.remaining, duration)
            existing.level = max(existing.level, level)
            return existing
        elif stack_mode == "stack":
            existing.remaining += duration
            existing.level += level
            return existing
    buff = Buff(
        id=str(uuid.uuid4()),
        type=buff_type,
        remaining=duration,
        level=level,
        source_id=source_id,
        stack_mode=stack_mode,
    )
    buffs.append(buff)
    return buff


def remove_buff(buffs: list[Buff], buff_type: str) -> Optional[Buff]:
    for i, b in enumerate(buffs):
        if b.type == buff_type:
            return buffs.pop(i)
    return None


def has_buff(buffs: list[Buff], buff_type: str) -> bool:
    return any(b.type == buff_type for b in buffs)


def get_buff(buffs: list[Buff], buff_type: str) -> Optional[Buff]:
    return next((b for b in buffs if b.type == buff_type), None)


def process_buffs(buffs: list[Buff], dt: float) -> list[str]:
    removed: list[str] = []
    for b in list(buffs):
        b.remaining -= dt
        if b.remaining <= 0:
            buffs.remove(b)
            removed.append(b.type)
    return removed


def break_stationary_plant_buffs(entity) -> None:
    """SPD Sungrass/Earthroot effects last only while standing on the plant tile.
    Breaks any stationary plant buffs (stamped with source_id 'x,y') if the entity
    is no longer on that tile (due to movement, knockback, or teleportation)."""
    buffs = getattr(entity, "buffs", None)
    pos = getattr(entity, "pos", None)
    if buffs is None or pos is None:
        return
    for buff_type in ("sungrass_health", "earthroot_armor"):
        buff = get_buff(buffs, buff_type)
        if buff is not None and buff.source_id:
            try:
                parts = buff.source_id.split(",")
                if len(parts) == 2:
                    sx, sy = int(parts[0]), int(parts[1])
                    if (pos.x, pos.y) != (sx, sy):
                        remove_buff(buffs, buff_type)
            except (ValueError, AttributeError):
                continue
