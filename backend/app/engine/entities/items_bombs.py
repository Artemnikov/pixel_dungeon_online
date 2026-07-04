# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
"""Bombs (SPD items/bombs/*) and MetalShard (items/quest/MetalShard.java).

A thrown bomb detaches one unit and lands as a floor item with `fuse_ticks`
set (lit); BombsMixin ticks it down and explodes it. Picking a lit bomb up
snuffs the fuse — except an armed Noisemaker, which detonates instead.
"""
from __future__ import annotations

from typing import ClassVar, List, Literal, Optional

from app.engine.entities.base import Action, ItemBase, ItemCategory


class Bomb(ItemBase):
    kind: Literal["bomb"] = "bomb"
    name: str = "Bomb"
    type: str = "bomb"
    category: ClassVar[str] = ItemCategory.MISC
    stackable: ClassVar[bool] = True
    level_known: bool = True
    cursed_known: bool = True
    # Lit state: ticks until explosion (None = unlit). Noisemaker arms
    # instead of exploding when its fuse runs out.
    fuse_ticks: Optional[int] = None
    armed: bool = False

    EXPLOSION_RANGE: ClassVar[int] = 1
    DESTRUCTIVE: ClassVar[bool] = True
    FUSE_TICKS: ClassVar[int] = 40            # 2 SPD turns at 20Hz
    PIERCES_ARMOR: ClassVar[bool] = False
    # Shrapnel alone hits by line-of-sight (ShadowCaster) instead of the
    # flood-fill BFS every other bomb uses; see BombsMixin._explosion_cells.
    USES_LOS: ClassVar[bool] = False
    # RegrowthBomb is SPD's only damage-free bomb; Arcane/Shrapnel roll the
    # same base formula in their Java overrides, reproduced by the core loop.
    DEALS_BASE_DAMAGE: ClassVar[bool] = True
    DESC: ClassVar[str] = "A crude but powerful explosive. Throwing it lights the fuse; the blast harms everything nearby and tears up the terrain."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.THROW

    def is_similar(self, other: "ItemBase") -> bool:
        # SPD Bomb.isSimilar: lit bombs never merge with unlit stacks.
        return super().is_similar(other) and self.fuse_ticks == getattr(other, "fuse_ticks", None)

    def value(self, identified: bool = False) -> int:
        return 15 * self.quantity


class Firebomb(Bomb):
    kind: Literal["firebomb"] = "firebomb"
    name: str = "Firebomb"
    EXPLOSION_RANGE: ClassVar[int] = 2
    DESC: ClassVar[str] = "This bomb bursts into flame, igniting everything around the blast."

    def value(self, identified: bool = False) -> int:
        return 50 * self.quantity


class FrostBomb(Bomb):
    kind: Literal["frost_bomb"] = "frost_bomb"
    name: str = "Frost Bomb"
    EXPLOSION_RANGE: ClassVar[int] = 2
    DESC: ClassVar[str] = "This bomb releases a wave of intense cold, freezing everything near the blast."

    def value(self, identified: bool = False) -> int:
        return 50 * self.quantity


class SmokeBomb(Bomb):
    kind: Literal["smoke_bomb"] = "smoke_bomb"
    name: str = "Smoke Bomb"
    EXPLOSION_RANGE: ClassVar[int] = 2
    DESC: ClassVar[str] = "This bomb blankets the area in thick blinding smoke."

    def value(self, identified: bool = False) -> int:
        return 60 * self.quantity


class FlashBangBomb(Bomb):
    kind: Literal["flashbang_bomb"] = "flashbang_bomb"
    name: str = "Flashbang"
    EXPLOSION_RANGE: ClassVar[int] = 2
    DESC: ClassVar[str] = "This bomb detonates with a blinding electric flash, stunning everything nearby."

    def value(self, identified: bool = False) -> int:
        return 50 * self.quantity


class HolyBomb(Bomb):
    kind: Literal["holy_bomb"] = "holy_bomb"
    name: str = "Holy Bomb"
    EXPLOSION_RANGE: ClassVar[int] = 2
    DESC: ClassVar[str] = "This bomb erupts with cleansing light, dealing extra damage to undead and demonic creatures."

    def value(self, identified: bool = False) -> int:
        return 50 * self.quantity


class RegrowthBomb(Bomb):
    kind: Literal["regrowth_bomb"] = "regrowth_bomb"
    name: str = "Regrowth Bomb"
    EXPLOSION_RANGE: ClassVar[int] = 3
    DESTRUCTIVE: ClassVar[bool] = False
    DEALS_BASE_DAMAGE: ClassVar[bool] = False
    DESC: ClassVar[str] = "Instead of exploding violently, this bomb showers the area with healing energy and fresh growth."

    def value(self, identified: bool = False) -> int:
        return 50 * self.quantity


class WoollyBomb(Bomb):
    kind: Literal["woolly_bomb"] = "woolly_bomb"
    name: str = "Woolly Bomb"
    EXPLOSION_RANGE: ClassVar[int] = 2
    DESC: ClassVar[str] = "This bomb bursts into a flock of magical sheep, blocking the paths of your enemies."

    def value(self, identified: bool = False) -> int:
        return 50 * self.quantity


class Noisemaker(Bomb):
    kind: Literal["noisemaker"] = "noisemaker"
    name: str = "Noisemaker"
    EXPLOSION_RANGE: ClassVar[int] = 2
    DESC: ClassVar[str] = "Instead of exploding immediately, this bomb arms itself and blares noise, luring monsters toward it. It detonates when something reaches it."

    def value(self, identified: bool = False) -> int:
        return 60 * self.quantity


class ArcaneBomb(Bomb):
    kind: Literal["arcane_bomb"] = "arcane_bomb"
    name: str = "Arcane Bomb"
    EXPLOSION_RANGE: ClassVar[int] = 2
    DESTRUCTIVE: ClassVar[bool] = False
    PIERCES_ARMOR: ClassVar[bool] = True
    DESC: ClassVar[str] = "This bomb explodes with arcane goo that ignores armor and covers a wide area."

    def value(self, identified: bool = False) -> int:
        return 50 * self.quantity


class ShrapnelBomb(Bomb):
    kind: Literal["shrapnel_bomb"] = "shrapnel_bomb"
    name: str = "Shrapnel Bomb"
    EXPLOSION_RANGE: ClassVar[int] = 8
    DESTRUCTIVE: ClassVar[bool] = False
    USES_LOS: ClassVar[bool] = True
    DESC: ClassVar[str] = "This bomb sprays deadly shrapnel over everything in sight of the blast."

    def value(self, identified: bool = False) -> int:
        return 70 * self.quantity


class MetalShard(ItemBase):
    # DM-300's death drop (SPD items/quest/MetalShard): alchemy reagent for
    # the Shrapnel Bomb.
    kind: Literal["metal_shard"] = "metal_shard"
    name: str = "Metal Shard"
    type: str = "misc"
    category: ClassVar[str] = ItemCategory.MISC
    stackable: ClassVar[bool] = True
    level_known: bool = True
    cursed_known: bool = True
    DESC: ClassVar[str] = "A shard of metal torn from DM-300's hull. It can be worked into a devastating bomb at an alchemy pot."

    def value(self, identified: bool = False) -> int:
        return 50 * self.quantity


BOMB_CLASSES = [
    Bomb, Firebomb, FrostBomb, SmokeBomb, FlashBangBomb, HolyBomb,
    RegrowthBomb, WoollyBomb, Noisemaker, ArcaneBomb, ShrapnelBomb,
]
