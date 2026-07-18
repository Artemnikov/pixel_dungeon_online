from __future__ import annotations

from dataclasses import dataclass, field
from typing import Set, Tuple

from app.engine.dungeon.constants import RoomKind


@dataclass
class Room:
    x: int
    y: int
    width: int
    height: int
    kind: str = RoomKind.STANDARD
    template: str = "standard"
    tags: Set[str] = field(default_factory=set)
    room_id: int = -1

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def intersects(self, other: Room, padding: int = 1) -> bool:
        return (
            self.x - padding <= other.x + other.width
            and self.x + self.width + padding >= other.x
            and self.y - padding <= other.y + other.height
            and self.y + self.height + padding >= other.y
        )

    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

    def is_perimeter(self, x: int, y: int) -> bool:
        on_lr = x in (self.x - 1, self.x + self.width)
        on_tb = y in (self.y - 1, self.y + self.height)
        if on_lr and not on_tb:
            return self.y <= y < self.y + self.height
        if on_tb and not on_lr:
            return self.x <= x < self.x + self.width
        return False


@dataclass
class TrapInfo:
    x: int
    y: int
    trap_type: str
    hidden: bool = True
    active: bool = True
    can_be_searched: bool = True
