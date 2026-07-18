# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
from __future__ import annotations

import uuid as _uuid
import random as _random
from typing import Annotated, ClassVar, Literal, Optional, List, Dict, Tuple, Union

from pydantic import BaseModel, Field, computed_field, model_validator, SerializeAsAny

from app.engine.entities.buffs import Buff, add_buff, remove_buff, has_buff, get_buff
from app.engine.entities.subclasses import SubclassInfo, TalentInfo, Talent
from app.engine.entities.weapon_defs import WEAPON_DEFS

from app.engine.entities.base import *  # noqa: F401,F403


class Gold(ItemBase):
    kind: Literal["gold"] = "gold"
    type: str = "gold"
    category: ClassVar[str] = ItemCategory.GOLD
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A pile of gold coins. Spend it at shops scattered through the dungeon."


class Food(ItemBase):
    kind: Literal["food"] = "food"
    type: str = "food"
    category: ClassVar[str] = ItemCategory.FOOD
    stackable: ClassVar[bool] = True
    energy: int = 0
    DESC: ClassVar[str] = "Edible provisions. Eat it to stave off hunger."

    def default_action(self) -> Optional[str]:
        return Action.EAT

    def value(self, identified: bool = False) -> int:
        return 10 * self.quantity


class Key(ItemBase):
    kind: Literal["key"] = "key"
    type: str = "key"
    category: ClassVar[str] = ItemCategory.KEY
    key_id: str = ""
    DESC: ClassVar[str] = "A key that unlocks a matching door or chest somewhere on this floor."


class KeyRecord(BaseModel):
    """A held key, tracked outside the bag (mirrors SPD's Notes.KeyRecord).

    Uniqueness is (key_id, depth): a key only unlocks doors on the floor it
    was found on, so two records with the same key_id but different depth
    are tracked separately.
    """
    key_id: str
    depth: int
    quantity: int = 1
    name: str = ""


class TenguMask(ItemBase):
    kind: Literal["tengu_mask"] = "tengu_mask"
    name: str = "Tengu's Mask"
    type: str = "misc"
    category: ClassVar[str] = ItemCategory.MISC
    unique: bool = True
    DESC: ClassVar[str] = "The mask of the infamous Tengu assassin. Wearing it grants the power to choose a subclass path."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.WEAR, Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.WEAR


class ArcaneStylus(ItemBase):
    kind: Literal["arcane_stylus"] = "arcane_stylus"
    name: str = "Arcane Stylus"
    type: str = "stylus"
    category: ClassVar[str] = ItemCategory.STYLUS
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A stylus enchanted with magical energy. Use it to inscribe a random glyph onto a piece of armor."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        from typing import List as _List
        acts: _List[str] = [Action.THROW, Action.DROP]
        if player is not None:
            has_armor = any(isinstance(it, Armor) for it in player.belongings.all_items() if it.id != self.id)
            if has_armor:
                acts.insert(0, Action.INSCRIBE)
        return acts

    def default_action(self) -> Optional[str]:
        return Action.INSCRIBE


class MagicalInfusion(ItemBase):
    kind: Literal["magical_infusion"] = "magical_infusion"
    name: str = "Magical Infusion"
    type: str = "spell"
    category: ClassVar[str] = ItemCategory.MISC
    unique: bool = True
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A magical infusion that upgrades a weapon or armor by one level. If the item already has an enchantment or glyph, it is preserved."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.USE, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.USE

    def value(self, identified: bool = False) -> int:
        return 60 * self.quantity


class KingsCrown(ItemBase):
    kind: Literal["kings_crown"] = "kings_crown"
    name: str = "King's Crown"
    type: str = "misc"
    category: ClassVar[str] = ItemCategory.MISC
    unique: bool = True
    DESC: ClassVar[str] = "A crown taken from a fallen king. Wearing it while armor is equipped grants the power to imbue that armor with a special ability."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.WEAR, Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.WEAR

class Throwable(ItemBase):
    kind: Literal["throwable"] = "throwable"
    type: str = "throwable"
    category: ClassVar[str] = ItemCategory.STONE
    stackable: ClassVar[bool] = True
    damage: int = 1
    range: int = 5
    consumable: bool = True
    projectile_type: str = "users_projectile"
    DESC: ClassVar[str] = "A thrown item. Hurl it at a target to deal damage."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.THROW


class Stone(Throwable):
    kind: Literal["stone"] = "stone"
    name: str = "Stone"
    damage: int = 1
    range: int = 5
    consumable: bool = True
    projectile_type: str = "stone"

    def value(self, identified: bool = False) -> int:
        return round(2.5 * self.quantity)


class Boomerang(Throwable):
    kind: Literal["boomerang"] = "boomerang"
    name: str = "Boomerang"
    damage: int = 3
    range: int = 6
    consumable: bool = False
    projectile_type: str = "boomerang"

    def value(self, identified: bool = False) -> int:
        return 20 * self.quantity


class ThrowableDagger(Throwable):
    kind: Literal["throwable_dagger"] = "throwable_dagger"
    name: str = "Throwable Dagger"
    damage: int = 4
    range: int = 4
    consumable: bool = True
    projectile_type: str = "dagger"

    def value(self, identified: bool = False) -> int:
        return 5 * self.quantity


class Seed(ItemBase):
    kind: Literal["seed"] = "seed"
    type: str = "seed"
    category: ClassVar[str] = ItemCategory.SEED
    stackable: ClassVar[bool] = True
    plant_type: str = "sungrass"
    DESC: ClassVar[str] = "A magical seed. Plant it to release its effect."

    def value(self, identified: bool = False) -> int:
        return 10 * self.quantity


class MysteryMeat(Food):
    kind: Literal["mystery_meat"] = "mystery_meat"
    name: str = "Mystery Meat"
    DESC: ClassVar[str] = "Raw meat from a defeated creature. Eat it to restore some health — if you dare."


class Dewdrop(ItemBase):
    kind: Literal["dewdrop"] = "dewdrop"
    name: str = "Dewdrop"
    type: str = "dewdrop"
    category: ClassVar[str] = ItemCategory.POTION
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A drop of magical dew. It radiates healing energy."


class EnergyCrystal(ItemBase):
    # SPD EnergyCrystal: quantity == energy amount. Never sits in a bag — on
    # pickup it converts straight into the player's alchemical energy
    # (Gold/Dewdrop pickup pattern).
    kind: Literal["energy_crystal"] = "energy_crystal"
    name: str = "Energy Crystal"
    type: str = "energy_crystal"
    category: ClassVar[str] = ItemCategory.MISC
    stackable: ClassVar[bool] = True
    level_known: bool = True
    cursed_known: bool = True
    DESC: ClassVar[str] = "A small crystal of pure alchemical energy. It is absorbed the moment it is picked up."


class Waterskin(ItemBase):
    kind: Literal["waterskin"] = "waterskin"
    name: str = "Waterskin"
    type: str = "waterskin"
    category: ClassVar[str] = ItemCategory.MISC
    stackable: ClassVar[bool] = False
    unique: bool = True
    MAX_VOLUME: ClassVar[int] = 20
    volume: int = 0
    DESC: ClassVar[str] = (
        "A leather pouch that can hold magical dew. Drinking from it restores health."
    )

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if self.volume > 0:
            return [Action.DRINK] + base
        return base

    def default_action(self) -> Optional[str]:
        return Action.DRINK if self.volume > 0 else None

    def value(self, identified: bool = False) -> int:
        return 0

    def is_full(self) -> bool:
        return self.volume >= self.MAX_VOLUME

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        if self.volume == 0:
            return ["It is currently empty."]
        return [f"It contains {self.volume}/{self.MAX_VOLUME} drops of dew."]


class Amulet(ItemBase):
    kind: Literal["amulet"] = "amulet"
    name: str = "Amulet of Yendor"
    type: str = "amulet"
    category: ClassVar[str] = ItemCategory.MISC
    stackable: ClassVar[bool] = False
    unique: bool = True
    DESC: ClassVar[str] = "The legendary Amulet of Yendor. Carry it to the surface to win."


class Berry(Food):
    kind: Literal["berry"] = "berry"
    name: str = "Berry"
    energy: int = 100
    DESC: ClassVar[str] = "A sweet berry. Restores a small amount of food."


class SmallRation(Food):
    kind: Literal["small_ration"] = "small_ration"
    name: str = "Small Ration"
    energy: int = 150
    DESC: ClassVar[str] = "A small bundle of provisions. Better than nothing."


class Ration(Food):
    kind: Literal["ration"] = "ration"
    name: str = "Ration"
    energy: int = 300
    DESC: ClassVar[str] = "A satisfying portion of food. Keeps hunger at bay for a good while."


class Pasty(Food):
    kind: Literal["pasty"] = "pasty"
    name: str = "Pasty"
    energy: int = 450
    DESC: ClassVar[str] = "A hearty pastry stuffed with vegetables and meat. Very filling."


class ChargrilledMeat(Food):
    kind: Literal["chargrilled_meat"] = "chargrilled_meat"
    name: str = "Chargrilled Meat"
    energy: int = 300
    DESC: ClassVar[str] = "Properly cooked mystery meat. Smells delicious."


class FrozenCarpaccio(Food):
    kind: Literal["frozen_carpaccio"] = "frozen_carpaccio"
    name: str = "Frozen Carpaccio"
    energy: int = 300
    DESC: ClassVar[str] = "Raw meat that has been frozen solid. Can be defrosted by cooking it."


class StewedMeat(Food):
    kind: Literal["stewed_meat"] = "stewed_meat"
    name: str = "Stewed Meat"
    energy: int = 150
    DESC: ClassVar[str] = "Mystery meat, gently stewed at an alchemy pot. Safe to eat, if not very filling."

    def value(self, identified: bool = False) -> int:
        return 8 * self.quantity


class MeatPie(Food):
    kind: Literal["meat_pie"] = "meat_pie"
    name: str = "Meat Pie"
    energy: int = 900
    DESC: ClassVar[str] = "A delicious pie cooked from meat, a pasty and a ration. Extremely filling."

    def value(self, identified: bool = False) -> int:
        return 40 * self.quantity


class GooBlob(ItemBase):
    # Goo's death drop (SPD GooBlob): stackable alchemy reagent (see
    # app.engine.alchemy).
    kind: Literal["goo_blob"] = "goo_blob"
    name: str = "Goo Blob"
    type: str = "misc"
    category: ClassVar[str] = ItemCategory.MISC
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A blob of black ooze left behind by Goo. Can be combined with a Health Potion at an Alchemy Pot."

    def value(self, identified: bool = False) -> int:
        return 30 * self.quantity


class CorpseDust(ItemBase):
    # Wandmaker quest item, Corpse Dust variant (SPD items.quest.CorpseDust):
    # unique, always identified/cursed-known, and -- unlike normal items --
    # can't be dropped or thrown (actions() below mirrors Java's actions()
    # returning an empty list). While held it attaches a `dust_ghost_spawner`
    # buff that periodically summons DustWraiths near the holder (see
    # movement.py's pickup handler, tick.py's per-player buff loop, and
    # wandmaker_quest.py for the DustWraith mob itself). Only removed via
    # world.py's wandmaker_claim_reward (no generic on-detach hook exists in
    # this engine for non-equippable items, so the dispel lives there).
    kind: Literal["corpse_dust"] = "corpse_dust"
    name: str = "dust of the corpse"
    type: str = "misc"
    category: ClassVar[str] = ItemCategory.MISC
    unique: bool = True
    cursed: bool = True
    cursed_known: bool = True
    level_known: bool = True
    DESC: ClassVar[str] = (
        "A handful of grim, gritty dust that seems to writhe in your grasp. "
        "You feel it stirring things that would rather stay buried."
    )

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return []


class DwarfToken(ItemBase):
    # Imp quest reward token (SPD items.quest.DwarfToken): stackable, always
    # identified, dropped by Golems/Monks once the quest is given. Not sellable.
    kind: Literal["dwarf_token"] = "dwarf_token"
    name: str = "Dwarf token"
    type: str = "misc"
    category: ClassVar[str] = ItemCategory.MISC
    stackable: ClassVar[bool] = True
    level_known: bool = True
    cursed_known: bool = True
    DESC: ClassVar[str] = "A small clay token, traded by dwarves of the Imp's homeland."
