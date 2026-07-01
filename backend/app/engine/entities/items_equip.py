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
from app.engine.entities.items_wands import Wand
from app.engine.entities.base import _tiered_value, _charm_value


class EquipableItem(ItemBase):
    strength_requirement: int = 10

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        equipped = bool(player and player.belongings.is_equipped(self.id))
        return [Action.UNEQUIP if equipped else Action.EQUIP] + base

    def default_action(self) -> Optional[str]:
        return Action.EQUIP

    def on_equip(self, player: "Player") -> None:
        """Hook called after the item is placed in an equip slot (SPD activate)."""

    def on_unequip(self, player: "Player") -> None:
        """Hook called before the item is removed from an equip slot (SPD doUnequip)."""

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines: List[str] = []
        req = f"It requires {self.strength_requirement} points of strength."
        if player is not None and player.strength < self.strength_requirement:
            req += f" Which is more than your {player.strength} points."
        lines.append(req)
        if self.level_known and self.level != 0:
            sign = "+" if self.level > 0 else ""
            lines.append(f"It is currently upgraded to {sign}{self.level}.")
        if self.cursed_known and self.cursed:
            lines.append("It is cursed, and you can't remove it.")
        return lines


class KindOfWeapon(EquipableItem):
    type: str = "weapon"
    category: ClassVar[str] = ItemCategory.WEAPON
    damage: int = 1
    range: int = 1
    attack_cooldown: float = 1.0
    enchantment: Optional[str] = None
    augment: Optional[str] = None
    projectile_type: Optional[str] = None
    # On surprise attacks, damage floor is raised by this fraction of the range
    surprise_damage_floor: float = 0.0
    # Accuracy multiplier (e.g. Cudgel 1.40, Sickle 0.68)
    acc_factor: float = 1.0
    # Flat DR bonus while wielded: dr_bonus_base + dr_bonus_per_lvl * level
    dr_bonus_base: int = 0
    dr_bonus_per_lvl: int = 0
    # Sound + pitch played on a successful melee hit (mirrors SPD's
    # KindOfWeapon.hitSound / hitSoundPitch). Defaults match SPD's HIT / 1.0.
    hit_sound: str = "HIT_BODY"
    hit_sound_pitch: float = 1.0

    def buffed_lvl(self) -> int:
        # SPD's weapon.buffedLvl(): proc formulas never see a negative
        # (cursed/degraded) level.
        return max(0, self.level)

    def get_reach(self) -> int:
        # Projecting enchant: +1 to missile throw range / melee reach.
        bonus = 1 if self.enchantment == "projecting" else 0
        return self.range + bonus

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines: List[str] = []
        if isinstance(self, MeleeWeapon):
            lvl = self.level if self.level_known else 0
            lines.append(f"Deals {self.dmg_min(lvl)}-{self.dmg_max(lvl)} damage per hit.")
        else:
            lines.append(f"Deals {self.damage} damage per hit.")
        if self.cursed_known and self.enchantment:
            label = self.enchantment.replace("_", " ").title()
            if self.cursed:
                lines.append(f"It is cursed with {label}.")
            else:
                lines.append(f"It is enchanted with {label}.")
        lines += super()._info_lines(player)
        return lines


class MeleeWeapon(KindOfWeapon):
    kind: Literal["melee_weapon"] = "melee_weapon"
    tier: int = 1
    DESC: ClassVar[str] = "A reliable melee weapon. Equip it to strike enemies in close combat."

    def dmg_min(self, lvl: int = 0) -> int:
        return self.tier + lvl

    def dmg_max(self, lvl: int = 0) -> int:
        defn = WEAPON_DEFS.get(self.name)
        if defn is not None:
            return defn.max0 + defn.max_per_lvl * lvl
        return 5 * (self.tier + 1) + lvl * (self.tier + 1)

    def value(self, identified: bool = False) -> int:
        return _tiered_value(self.tier, self.level, self.level_known, self.cursed, self.cursed_known)


class Dagger(MeleeWeapon):
    kind: Literal["dagger"] = "dagger"
    name: str = "Dagger"
    attack_cooldown: float = 0.84
    strength_requirement: int = 9
    surprise_damage_floor: float = 0.75
    hit_sound: str = "HIT_STAB"
    hit_sound_pitch: float = 1.1
    DESC: ClassVar[str] = "A quick dagger. Surprise attacks deal more consistent damage."

    def dmg_max(self, lvl: int = 0) -> int:
        return 4 * (self.tier + 1) + lvl * (self.tier + 1)


class WornShortsword(MeleeWeapon):
    kind: Literal["worn_shortsword"] = "worn_shortsword"
    name: str = "Worn Shortsword"
    attack_cooldown: float = 1.2
    strength_requirement: int = 10
    hit_sound: str = "HIT_SLASH"
    hit_sound_pitch: float = 1.1
    DESC: ClassVar[str] = "A basic shortsword, somewhat the worse for wear. All warriors start with one."


def make_named_melee_weapon(name: str, level: int = 0, **kwargs) -> MeleeWeapon:
    if name == "Worn Shortsword":
        return WornShortsword(level=level, **kwargs)
    if name == "Dagger":
        return Dagger(level=level, **kwargs)
    defn = WEAPON_DEFS[name]
    return MeleeWeapon(
        name=name, tier=defn.tier, level=level,
        strength_requirement=defn.str_req, attack_cooldown=defn.dly_factor,
        range=defn.reach, acc_factor=defn.acc_factor,
        dr_bonus_base=defn.dr_bonus_base, dr_bonus_per_lvl=defn.dr_bonus_per_lvl,
        hit_sound=defn.hit_sound, hit_sound_pitch=defn.hit_sound_pitch,
        **kwargs,
    )


class Bow(KindOfWeapon):
    kind: Literal["bow"] = "bow"
    name: str = "Bow"
    range: int = 6
    projectile_type: str = "arrow"
    DESC: ClassVar[str] = "A ranged weapon that fires arrows at distant foes. Equip it, then target an enemy to shoot."


class SpiritBow(KindOfWeapon):
    kind: Literal["spirit_bow"] = "spirit_bow"
    name: str = "Spirit Bow"
    unique: bool = True
    bones: bool = False
    range: int = 6
    projectile_type: str = "spirit_arrow"
    attack_cooldown: float = 1.0
    acc_factor: float = 1.0
    strength_requirement: int = 10
    hit_sound: str = "HIT_ARROW"
    DESC: ClassVar[str] = "The spirit bow of the Huntress. Its magic arrows grow stronger as you delve deeper."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.SHOOT, Action.DROP, Action.INFO]

    def default_action(self) -> Optional[str]:
        return Action.SHOOT

    def uses_targeting(self, action: str) -> bool:
        return action == Action.SHOOT

    def dmg_min(self, hero_level: int) -> int:
        return 1 + hero_level // 5

    def dmg_max(self, hero_level: int) -> int:
        return 6 + int(hero_level / 2.5)

    def is_upgradable(self) -> bool:
        return False

    def get_reach(self) -> int:
        bonus = 1 if self.enchantment == "projecting" else 0
        return self.range + bonus

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = []
        if player is not None:
            hero_lvl = player.level
            lines.append(f"Deals {self.dmg_min(hero_lvl)}-{self.dmg_max(hero_lvl)} magic damage.")
        else:
            lines.append("Deals magic damage that scales with the wielder.")
        return lines

    def value(self, identified: bool = False) -> int:
        return 0


class Staff(MeleeWeapon):
    kind: Literal["staff"] = "staff"
    name: str = "Mage's Staff"
    magic_damage: int = 0
    projectile_type: str = "magic_bolt"
    imbued_wand: Optional[SerializeAsAny["Wand"]] = None
    unique: bool = True
    bones: bool = False
    tier: int = 1
    strength_requirement: int = 10
    attack_cooldown: float = 1.0
    acc_factor: float = 1.0
    hit_sound: str = "HIT_BODY"
    hit_sound_pitch: float = 1.1
    DESC: ClassVar[str] = "A magical staff that hurls bolts of energy at a distance."

    @model_validator(mode='after')
    def _sync_imbued_wand(self):
        if self.imbued_wand is not None:
            self.name = self.imbued_wand.staff_name
            self.projectile_type = self.imbued_wand.projectile_type
        return self

    def dmg_min(self, lvl: int = 0) -> int:
        return 1

    def dmg_max(self, lvl: int = 0) -> int:
        return 6 + 2 * lvl

    @computed_field
    @property
    def charges(self) -> int:
        return self.imbued_wand.charges if self.imbued_wand else 0

    @computed_field
    @property
    def max_charges(self) -> int:
        return self.imbued_wand.max_charges if self.imbued_wand else 0

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        actions = [Action.IMBUE] + super().actions(player)
        if self.imbued_wand is not None and self.imbued_wand.charges > 0:
            actions.append(Action.ZAP)
        return actions

    def default_action(self) -> Optional[str]:
        if self.imbued_wand is not None and self.imbued_wand.charges > 0:
            return Action.ZAP
        return Action.IMBUE

    def update_wand(self, levelled: bool = False):
        """Sync wand level/staff level. SPD MagesStaff.updateWand."""
        if self.imbued_wand is None:
            return
        cur_charges = self.imbued_wand.charges
        self.imbued_wand.level = self.level
        base = self.imbued_wand.initial_charges()
        self.imbued_wand.max_charges = min(base + self.level + 1, 10)
        self.imbued_wand.charges = min(
            cur_charges + (1 if levelled else 0),
            self.imbued_wand.max_charges,
        )
        self.imbued_wand.recharge_scale = 0.75

    def upgrade(self, enchant: bool = True) -> "Staff":
        self.level += 1
        self.update_wand(True)
        return self

    def degrade(self) -> "Staff":
        self.level -= 1
        self.update_wand(False)
        return self

    def imbue_wand(self, wand: "Wand", owner=None) -> Optional["Wand"]:
        """SPD MagesStaff.imbueWand — full level/charge sync.

        Returns the displaced old wand if Wand Preservation triggered but
        the backpack had no room to hold it (caller should drop it on the
        floor instead of losing it); otherwise None.
        """
        old_charges = self.imbued_wand.charges if self.imbued_wand else 0
        old_wand = self.imbued_wand
        displaced_wand: Optional["Wand"] = None

        target_level = max(self.level, wand.level)
        if wand.level >= self.level and self.level > 0:
            target_level += 1

        self.level = target_level
        self.imbued_wand = wand
        wand.level_known = True
        wand.cursed_known = True
        self.name = wand.staff_name
        self.update_wand(False)
        self.imbued_wand.charges = min(
            self.imbued_wand.max_charges,
            self.imbued_wand.charges + old_charges,
        )

        if owner is not None:
            self._apply_wand_charge_buff(owner)

        if wand.cursed and (not self.cursed or not self._has_curse_enchant()):
            self.cursed = True
            self.cursed_known = True

        if old_wand is not None and owner is not None:
            preservation_talent = getattr(getattr(owner, 'talent_info', None), 'level', lambda x: 0)('wand_preservation')
            if preservation_talent > 0:
                counter_buff = next((b for b in getattr(owner, 'buffs', []) if getattr(b, 'name', None) == 'wand_preservation_counter'), None)
                if counter_buff is None:
                    old_wand.level = 0
                    from app.engine.entities.buffs import add_buff
                    add_buff(owner.buffs, "wand_preservation_counter", duration=999999, level=1)
                    if not (hasattr(owner, 'belongings') and owner.belongings.backpack.collect(old_wand)):
                        displaced_wand = old_wand

        return displaced_wand

    def _apply_wand_charge_buff(self, owner: "Char"):
        if self.imbued_wand is not None:
            self.imbued_wand.recharge_scale = 0.75

    def _has_curse_enchant(self) -> bool:
        from app.engine.entities.weapon_enchants import CURSES
        return self.enchantment in CURSES

    def get_reach(self) -> int:
        if self.imbued_wand is not None:
            return self.imbued_wand.get_reach()
        return super().get_reach()

    def status(self) -> str:
        if self.imbued_wand is not None:
            return f"{self.imbued_wand.charges}/{self.imbued_wand.max_charges}"
        return super().status()

    def value(self, identified: bool = False) -> int:
        return 0

    def reach_factor(self, owner: Optional["Char"] = None) -> int:
        reach = super().reach_factor(owner)
        if self.imbued_wand is not None and owner is not None:
            subclass = getattr(getattr(owner, 'subclass_info', None), 'subclass', None)
            if subclass == "battlemage" and isinstance(self.imbued_wand, WandOfDisintegration):
                reach += 1
        return reach

    def targeting_pos(self, user: "Player", dst: int) -> int:
        if self.imbued_wand is not None:
            return self.imbued_wand.targeting_pos(user, dst)
        return super().targeting_pos(user, dst)

    def buffed_visibly_upgraded(self) -> int:
        if self.imbued_wand is not None:
            return max(super().buffed_visibly_upgraded(), self.imbued_wand.buffed_lvl())
        return super().buffed_visibly_upgraded()


class MissileWeapon(KindOfWeapon):
    kind: Literal["missile_weapon"] = "missile_weapon"
    tier: int = 1
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A thrown weapon. Hurl it at an enemy from afar."

    def default_action(self) -> Optional[str]:
        return Action.THROW

    def value(self, identified: bool = False) -> int:
        price = 5 * self.tier * self.quantity
        if self.cursed_known and self.cursed:
            price /= 2
        if self.level_known and self.level > 0:
            price *= (self.level + 1)
        return max(1, round(price))


class ArmorEnchantment(BaseModel):
    type: str = "none"
    level: int = 0


class Armor(EquipableItem):
    kind: Literal["armor"] = "armor"
    type: str = "wearable"
    category: ClassVar[str] = ItemCategory.ARMOR
    tier: int = 1
    enchantment: ArmorEnchantment = Field(default_factory=ArmorEnchantment)
    augment: Optional[str] = None
    DESC: ClassVar[str] = "Worn armor that absorbs a portion of incoming damage. Equip it for protection."

    def buffed_lvl(self) -> int:
        return max(0, self.level)

    def dr_min(self, upgrade_level: int = 0) -> int:
        return upgrade_level

    def dr_max(self, upgrade_level: int = 0) -> int:
        return self.tier * (2 + upgrade_level)

    def value(self, identified: bool = False) -> int:
        return _tiered_value(self.tier, self.level, self.level_known, self.cursed, self.cursed_known)

    def _info_lines(self, player=None) -> List[str]:
        glyph = self.enchantment.type
        if not glyph or glyph == "none":
            return []
        from app.engine.entities.armor_glyphs import GLYPH_DESC
        desc = GLYPH_DESC.get(glyph)
        if not desc:
            return []
        label = glyph.replace("_", " ").title()
        return [f"Glyph of {label}: {desc}"]


class ClothArmor(Armor):
    kind: Literal["cloth_armor"] = "cloth_armor"; name: str = "Cloth Armor"; tier: int = 1; strength_requirement: int = 10

class LeatherArmor(Armor):
    kind: Literal["leather_armor"] = "leather_armor"; name: str = "Leather Armor"; tier: int = 2; strength_requirement: int = 12

class MailArmor(Armor):
    kind: Literal["mail_armor"] = "mail_armor"; name: str = "Mail Armor"; tier: int = 3; strength_requirement: int = 14

class ScaleArmor(Armor):
    kind: Literal["scale_armor"] = "scale_armor"; name: str = "Scale Armor"; tier: int = 4; strength_requirement: int = 16

class PlateArmor(Armor):
    kind: Literal["plate_armor"] = "plate_armor"; name: str = "Plate Armor"; tier: int = 5; strength_requirement: int = 18


class KindofMisc(EquipableItem):
    pass


class Ring(KindofMisc):
    kind: Literal["ring"] = "ring"
    type: str = "ring"
    category: ClassVar[str] = ItemCategory.RING
    # Identifies which RingBuff subclass this ring grants (e.g. "accuracy",
    # "haste"). Used by ring_bonus() to find matching rings across both slots.
    buff_class: Optional[str] = None
    # Per-run gem appearance (SPD ItemStatusHandler): assigned by serialization
    # layer. Unidentified rings display as "Ring of {gem}".
    gem: str = "garnet"
    # SPD: rings ID via hero XP while equipped. Starts at 1.0; decremented by
    # levelPercent per hero level gained. At <=0 the ring auto-identifies.
    levels_to_id: float = 1.0
    DESC: ClassVar[str] = "A magical ring that grants a passive bonus while worn."

    def upgrade(self) -> "Ring":
        self.level += 1
        if _random.randint(0, 2) == 0:
            self.cursed = False
        return self

    def value(self, identified: bool = False) -> int:
        return _charm_value(self.level, self.level_known, self.cursed, self.cursed_known)


class Artifact(KindofMisc):
    kind: Literal["artifact"] = "artifact"
    type: str = "artifact"
    category: ClassVar[str] = ItemCategory.ARTIFACT
    charge: int = 0
    charge_cap: int = 100
    DESC: ClassVar[str] = "A unique artifact with a special power that grows as you use it."
