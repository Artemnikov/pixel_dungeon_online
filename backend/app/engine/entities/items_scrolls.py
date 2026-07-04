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


class Scroll(ItemBase):
    kind: Literal["scroll"] = "scroll"
    type: str = "scroll"
    category: ClassVar[str] = ItemCategory.SCROLL
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A magical scroll inscribed with arcane runes. Read it to invoke its power."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.READ] + super().actions(player)

    def default_action(self) -> Optional[str]:
        return Action.READ

    def value(self, identified: bool = False) -> int:
        return 30 * self.quantity

class ScrollOfRage(Scroll):
    kind: Literal["scroll_of_rage"] = "scroll_of_rage"
    name: str = "Scroll of Rage"
    DESC: ClassVar[str] = "A scroll that fills you with fury. Read it in the heat of battle to deliver devastating attacks."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.READ, Action.THROW, Action.DROP]


class ScrollOfMetamorphosis(Scroll):
    kind: Literal["scroll_of_metamorphosis"] = "scroll_of_metamorphosis"
    name: str = "Scroll of Metamorphosis"
    DESC: ClassVar[str] = "A scroll that lets you replace one of your talents with a talent from another class."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.READ, Action.THROW, Action.DROP]


class ScrollOfUpgrade(Scroll):
    kind: Literal["scroll_of_upgrade"] = "scroll_of_upgrade"
    name: str = "Scroll of Upgrade"
    DESC: ClassVar[str] = "Reading this scroll permanently upgrades one of your equipped items."

    def value(self, identified: bool = False) -> int:
        return (50 if identified else 30) * self.quantity


class ScrollOfIdentify(Scroll):
    kind: Literal["scroll_of_identify"] = "scroll_of_identify"
    name: str = "Scroll of Identify"
    DESC: ClassVar[str] = "Reading this scroll reveals the true nature of an unknown item."


class ScrollOfMagicMapping(Scroll):
    kind: Literal["scroll_of_magic_mapping"] = "scroll_of_magic_mapping"
    name: str = "Scroll of Magic Mapping"
    DESC: ClassVar[str] = "Reading this scroll reveals the entire layout of the current floor."

    def value(self, identified: bool = False) -> int:
        return (40 if identified else 30) * self.quantity


class ScrollOfTeleportation(Scroll):
    kind: Literal["scroll_of_teleportation"] = "scroll_of_teleportation"
    name: str = "Scroll of Teleportation"
    DESC: ClassVar[str] = "Reading this scroll teleports you to a random location on the floor."


class ScrollOfRemoveCurse(Scroll):
    kind: Literal["scroll_of_remove_curse"] = "scroll_of_remove_curse"
    name: str = "Scroll of Remove Curse"
    DESC: ClassVar[str] = "Reading this scroll removes all curses from your equipped items."


class ScrollOfRecharging(Scroll):
    kind: Literal["scroll_of_recharging"] = "scroll_of_recharging"
    name: str = "Scroll of Recharging"
    DESC: ClassVar[str] = "Reading this scroll temporarily speeds up the recharge rate of your wands."


class ScrollOfLullaby(Scroll):
    kind: Literal["scroll_of_lullaby"] = "scroll_of_lullaby"
    name: str = "Scroll of Lullaby"
    DESC: ClassVar[str] = "Reading this scroll causes nearby creatures to fall asleep."


class ScrollOfTerror(Scroll):
    kind: Literal["scroll_of_terror"] = "scroll_of_terror"
    name: str = "Scroll of Terror"
    DESC: ClassVar[str] = "Reading this scroll fills nearby enemies with overwhelming fear."


class ScrollOfMirrorImage(Scroll):
    kind: Literal["scroll_of_mirror_image"] = "scroll_of_mirror_image"
    name: str = "Scroll of Mirror Image"
    DESC: ClassVar[str] = "Reading this scroll creates illusory copies of yourself to confuse enemies."


class ScrollOfRetribution(Scroll):
    kind: Literal["scroll_of_retribution"] = "scroll_of_retribution"
    name: str = "Scroll of Retribution"
    DESC: ClassVar[str] = "Reading this scroll damages all nearby enemies proportional to your missing health."


class ScrollOfTransmutation(Scroll):
    kind: Literal["scroll_of_transmutation"] = "scroll_of_transmutation"
    name: str = "Scroll of Transmutation"
    DESC: ClassVar[str] = "Reading this scroll transforms a held item into another of the same category."


class ScrollOfEnchantment(Scroll):
    kind: Literal["scroll_of_enchantment"] = "scroll_of_enchantment"
    name: str = "Scroll of Enchantment"
    DESC: ClassVar[str] = "Imbues a weapon or armor with a random enchantment or glyph."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.READ, Action.DROP]


class ExoticScrollOfEnchantment(Scroll):
    kind: Literal["scroll_of_exotic_enchantment"] = "scroll_of_exotic_enchantment"
    name: str = "Exotic Scroll of Enchantment"
    DESC: ClassVar[str] = "Imbues a weapon or armor with a choice of three enchantments or glyphs."
    unique: bool = True


# ── Exotic Scrolls ────────────────────────────────────────────────────────────

class ScrollOfAntiMagic(Scroll):
    kind: Literal["scroll_of_anti_magic"] = "scroll_of_anti_magic"
    name: str = "Scroll of Anti-Magic"
    DESC: ClassVar[str] = "Grants temporary immunity to all magical effects."


class ScrollOfChallenge(Scroll):
    kind: Literal["scroll_of_challenge"] = "scroll_of_challenge"
    name: str = "Scroll of Challenge"
    DESC: ClassVar[str] = "Summons every creature on the floor to your location for a grand melee."


class ScrollOfDivination(Scroll):
    kind: Literal["scroll_of_divination"] = "scroll_of_divination"
    name: str = "Scroll of Divination"
    DESC: ClassVar[str] = "Reveals the identity of several unknown items in your possession."


class ScrollOfDread(Scroll):
    kind: Literal["scroll_of_dread"] = "scroll_of_dread"
    name: str = "Scroll of Dread"
    DESC: ClassVar[str] = "Fills all visible creatures with overwhelming terror and permanent dread."


class ScrollOfForesight(Scroll):
    kind: Literal["scroll_of_foresight"] = "scroll_of_foresight"
    name: str = "Scroll of Foresight"
    DESC: ClassVar[str] = "Greatly expands your field of vision for a very long duration."


class ScrollOfMysticalEnergy(Scroll):
    kind: Literal["scroll_of_mystical_energy"] = "scroll_of_mystical_energy"
    name: str = "Scroll of Mystical Energy"
    DESC: ClassVar[str] = "Recharges all your wands and artifacts."


class ScrollOfPassage(Scroll):
    kind: Literal["scroll_of_passage"] = "scroll_of_passage"
    name: str = "Scroll of Passage"
    DESC: ClassVar[str] = "Opens a portal back to the previous floor."


class ScrollOfPrismaticImage(Scroll):
    kind: Literal["scroll_of_prismatic_image"] = "scroll_of_prismatic_image"
    name: str = "Scroll of Prismatic Image"
    DESC: ClassVar[str] = "Creates a vivid shimmering decoy that draws enemy attacks."


class ScrollOfPsionicBlast(Scroll):
    kind: Literal["scroll_of_psionic_blast"] = "scroll_of_psionic_blast"
    name: str = "Scroll of Psionic Blast"
    DESC: ClassVar[str] = "Releases a mental shockwave that devastates all nearby creatures but also harms you."


class ScrollOfSirensSong(Scroll):
    kind: Literal["scroll_of_sirens_song"] = "scroll_of_sirens_song"
    name: str = "Scroll of Siren's Song"
    DESC: ClassVar[str] = "Charms all visible creatures, and enthralls one as a permanent ally."
