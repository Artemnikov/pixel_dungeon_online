# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
from typing import ClassVar, List, Optional, Literal

from app.engine.entities.base import (
    Action, ItemBase, ItemCategory,
)


class Runestone(ItemBase):
    kind: Literal["runestone"] = "runestone"
    type: str = "runestone"
    category: ClassVar[str] = ItemCategory.RUNESTONE
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A small stone inscribed with arcane runes."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.THROW

    def is_identified(self) -> bool:
        return True

    def value(self, identified: bool = False) -> int:
        return 15 * self.quantity


class InventoryStone(Runestone):
    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.USE, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.USE


class StoneOfBlast(Runestone):
    kind: Literal["stone_of_blast"] = "stone_of_blast"
    name: str = "Stone of Blast"
    DESC: ClassVar[str] = "Creates an explosion at the target location."


class StoneOfBlink(Runestone):
    kind: Literal["stone_of_blink"] = "stone_of_blink"
    name: str = "Stone of Blink"
    DESC: ClassVar[str] = "Teleports you to the target location."


class StoneOfDeepSleep(Runestone):
    kind: Literal["stone_of_deep_sleep"] = "stone_of_deep_sleep"
    name: str = "Stone of Deep Sleep"
    DESC: ClassVar[str] = "Puts an enemy into a deep slumber."


class StoneOfClairvoyance(Runestone):
    kind: Literal["stone_of_clairvoyance"] = "stone_of_clairvoyance"
    name: str = "Stone of Clairvoyance"
    DESC: ClassVar[str] = "Reveals the surrounding area."


class StoneOfAggression(Runestone):
    kind: Literal["stone_of_aggression"] = "stone_of_aggression"
    name: str = "Stone of Aggression"
    DESC: ClassVar[str] = "Enrages an enemy, causing it to attack everything."


class StoneOfFlock(Runestone):
    kind: Literal["stone_of_flock"] = "stone_of_flock"
    name: str = "Stone of Flock"
    DESC: ClassVar[str] = "Spawn a flock of sheep at the target location."


class StoneOfShock(Runestone):
    kind: Literal["stone_of_shock"] = "stone_of_shock"
    name: str = "Stone of Shock"
    DESC: ClassVar[str] = "Shocks all enemies in an area and recharges your wands."


class StoneOfFear(Runestone):
    kind: Literal["stone_of_fear"] = "stone_of_fear"
    name: str = "Stone of Fear"
    DESC: ClassVar[str] = "Terrifies an enemy, causing it to flee."


class StoneOfIntuition(InventoryStone):
    kind: Literal["stone_of_intuition"] = "stone_of_intuition"
    name: str = "Stone of Intuition"
    DESC: ClassVar[str] = "Allows you to guess the identity of an unidentified item."


class StoneOfAugmentation(InventoryStone):
    kind: Literal["stone_of_augmentation"] = "stone_of_augmentation"
    name: str = "Stone of Augmentation"
    DESC: ClassVar[str] = "Augments weapon speed or damage."

    def value(self, identified: bool = False) -> int:
        return 30 * self.quantity


class StoneOfDetectMagic(InventoryStone):
    kind: Literal["stone_of_detect_magic"] = "stone_of_detect_magic"
    name: str = "Stone of Detect Magic"
    DESC: ClassVar[str] = "Reveals the magical properties of an item."


class StoneOfEnchantment(InventoryStone):
    kind: Literal["stone_of_enchantment"] = "stone_of_enchantment"
    name: str = "Stone of Enchantment"
    DESC: ClassVar[str] = "Enchants a weapon or inscribes armor."

    def value(self, identified: bool = False) -> int:
        return 30 * self.quantity
