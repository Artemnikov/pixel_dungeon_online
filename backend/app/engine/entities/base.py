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


class EntityType:
    PLAYER = "player"
    MOB = "mob"
    BOSS = "boss"
    ITEM = "item"
    POTION = "potion"

class Faction:
    PLAYER = "player"
    DUNGEON = "dungeon"

class Position(BaseModel):
    x: int
    y: int

class Shield(BaseModel):
    priority: int = 0
    amount: int = 0
    decay: int = 1  # min(1, amount/decay) removed per tick
    name: str = ""  # logical id for identifying a specific shield


def is_immune(entity, effect: str) -> bool:
    return effect in getattr(entity, "immunities", [])


class Entity(BaseModel):
    id: str
    type: str
    name: str
    pos: Position
    hp: int
    max_hp: int
    attack: int = 0
    defense: int = 0
    speed: float = 1.0
    is_alive: bool = True
    faction: str
    last_attack_time: float = 0.0
    attack_cooldown: float = 1.0

    # Vision range in tiles (SPD Char.viewDistance = 8). Single field that future
    # Light/Blindness/Farsight-style buffs adjust; 0 means effectively sightless.
    view_distance: int = 8

    # SPD combat stats
    attack_skill: int = 10
    defense_skill: int = 5
    damage_min: int = 1
    damage_max: int = 4
    dr_min: int = 0
    dr_max: int = 0
    max_lvl: int = 5

    defense_verb: str = "dodged"

    # Status effect fields (mutated by attack_proc/defense_proc)
    bleed_amount: int = 0
    bleed_turns: int = 0
    ooze_amount: int = 0       # remaining ooze "turns" (caustic DoT)
    ooze_cooldown: int = 0     # ticks until the next ooze damage application

    # Burning DoT: accumulating tick timer (seconds) for ~1s burn intervals
    burning_accum: float = 0.0
    burning_total_seconds: float = 0.0  # total time burning (for inventory destruction)

    # Poison / Corrosion DoT: accumulating tick timer (seconds) for ~1s intervals
    poison_accum: float = 0.0
    corrosion_accum: float = 0.0

    # Shields (absorption layers)
    shields: List[Shield] = Field(default_factory=list)

    # Crit / surprise-attack damage bonus multiplier (e.g. 0.5 = +50%)
    crit_damage_bonus: float = 0.0
    # Grim enchantment: max execute chance at 0 HP
    grim_max_chance: float = 0.0
    # Kinetic enchantment: overflow damage carried to next hit
    conserved_damage: int = 0
    # Fury buff: flat 1.5x damage multiplier
    has_fury: bool = False
    fury_turns_remaining: int = 0

    # Stealth / invisibility
    invisible: int = 0

    # Generic buff system
    buffs: List[Buff] = Field(default_factory=list)

    def __setattr__(self, name, value):
        if name in ("hp", "hp_bracket") and value is not None:
            value = int(value)
        super().__setattr__(name, value)

    def add_buff(self, buff_type: str, duration: float, level: int = 0, source_id: str = None, stack_mode: str = "replace") -> Buff:
        result = add_buff(self.buffs, buff_type, duration, level, source_id, stack_mode)
        if buff_type == "invisibility" or buff_type == "shadows":
            self.invisible += 1
        return result

    def remove_buff(self, buff_type: str) -> Optional[Buff]:
        result = remove_buff(self.buffs, buff_type)
        if result and (result.type == "invisibility" or result.type == "shadows"):
            self.invisible = max(0, self.invisible - 1)
        return result

    def has_buff(self, buff_type: str) -> bool:
        return has_buff(self.buffs, buff_type)

    def get_buff(self, buff_type: str) -> Optional[Buff]:
        return get_buff(self.buffs, buff_type)

    def get_stealth(self) -> float:
        base = 0.0
        obf = self.get_buff("obfuscation")
        if obf:
            base += 1 + obf.level / 3
        prep = self.get_buff("preparation")
        if prep:
            base += 2
        return base

    def get_dr_min(self) -> int:
        base = self.dr_min
        barkskin = self.get_buff("barkskin")
        if barkskin:
            base += barkskin.level
        return base

    def get_dr_max(self) -> int:
        base = self.dr_max
        barkskin = self.get_buff("barkskin")
        if barkskin:
            base += barkskin.level * 2
        return base

    def get_damage_min(self) -> int:
        return self.damage_min

    def get_damage_max(self) -> int:
        return self.damage_max

    def get_surprise_damage_floor(self) -> float:
        return 0.0

    def get_effective_defense_skill(self) -> int:
        return self.defense_skill

    def move(self, dx: int, dy: int):
        self.pos.x += dx
        self.pos.y += dy

    def process_shields(self, amount: int) -> int:
        if not self.shields:
            return amount
        sorted_shields = sorted(self.shields, key=lambda s: s.priority, reverse=True)
        remaining = amount
        active = []
        for s in sorted_shields:
            if remaining <= 0:
                active.append(s)
            elif s.amount >= remaining:
                s.amount -= remaining
                remaining = 0
                if s.amount > 0:
                    active.append(s)
            else:
                remaining -= s.amount
        self.shields = active
        return remaining

    def get_shield(self, name: str) -> Optional[Shield]:
        return next((s for s in self.shields if s.name == name), None)

    def add_shield(self, name: str, amount: int, priority: int = 0, decay: int = 1) -> Shield:
        existing = self.get_shield(name)
        if existing:
            existing.amount += amount
            return existing
        s = Shield(name=name, amount=amount, priority=priority, decay=decay)
        self.shields.append(s)
        return s

    def decay_shields(self):
        active = []
        for s in self.shields:
            if s.name == "broken_seal":
                # Doesn't decay over time; removed explicitly when no enemies
                # are nearby (see TickMixin).
                active.append(s)
                continue
            s.amount -= max(1, s.amount // max(1, s.decay))
            if s.amount > 0:
                active.append(s)
        self.shields = active

    def take_damage(self, amount: int):
        amount = self.process_shields(amount)
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.is_alive = False
        return max(0, amount)


# ---------------------------------------------------------------------------
# Inventory system — ported from Shattered Pixel Dungeon's Item/Bag/Belongings.
#
# SPD is single-player libGDX Java with object-identity comparisons and Bundle
# persistence. Here the server is authoritative and broadcasts full Pydantic
# snapshots over WebSocket, and clients only ever send {item_id, action}. So the
# port keeps SPD's *structure* (stacking, equip slots, nested category bags,
# quickslots, action dispatch) but:
#   * every lookup/compare is keyed by `id` (str), never object identity;
#   * `split` clones via model_copy(deep=True) + a fresh id (SPD uses a Bundle
#     round-trip clone);
#   * polymorphism uses a `kind` Literal discriminator so nested items serialize
#     cleanly and the client can switch on `kind`.
# ---------------------------------------------------------------------------

class ItemCategory:
    WEAPON = "weapon"
    ARMOR = "armor"
    RING = "ring"
    ARTIFACT = "artifact"
    WAND = "wand"
    POTION = "potion"
    SCROLL = "scroll"
    SEED = "seed"
    STONE = "stone"
    FOOD = "food"
    GOLD = "gold"
    KEY = "key"
    MISC = "misc"
    BAG = "bag"
    SCENERY = "scenery"

# Sort order inside a bag (mirrors SPD's itemComparator grouping by category).
CATEGORY_ORDER = [
    ItemCategory.WEAPON, ItemCategory.ARMOR, ItemCategory.RING, ItemCategory.ARTIFACT,
    ItemCategory.WAND, ItemCategory.SCROLL, ItemCategory.POTION, ItemCategory.SEED,
    ItemCategory.STONE, ItemCategory.FOOD, ItemCategory.KEY, ItemCategory.GOLD,
    ItemCategory.MISC, ItemCategory.BAG, ItemCategory.SCENERY,
]

class Action:
    DROP = "DROP"
    THROW = "THROW"
    EQUIP = "EQUIP"
    UNEQUIP = "UNEQUIP"
    DRINK = "DRINK"
    READ = "READ"
    ZAP = "ZAP"
    EAT = "EAT"
    OPEN = "OPEN"
    AFFIX = "AFFIX"
    INFO = "INFO"
    STEALTH = "STEALTH"  # Cloak of Shadows: toggle invisibility
    WEAR = "WEAR"        # TengusMask: choose subclass
    ALCHEMIZE = "ALCHEMIZE"  # GooBlob + HealthPotion at an Alchemy Pot -> Elixir of Aquatic Rejuvenation
    IMBUE = "IMBUE"      # MagesStaff: imbue a wand into the staff
    SUMMON = "SUMMON"    # DriedRose: summon the ghost ally
    DIRECT = "DIRECT"    # DriedRose: direct the ghost ally to a target
    SHOOT = "SHOOT"      # SpiritBow: fire an arrow

# Actions that require the player to pick a target cell before resolving.
TARGETED_ACTIONS = {Action.THROW, Action.ZAP, Action.DIRECT, Action.SHOOT}


def _new_id() -> str:
    return str(_uuid.uuid4())


class ItemBase(BaseModel):
    # `kind` is the polymorphic discriminator (overridden as a Literal in each
    # concrete leaf). `type` is the legacy front-end category string kept for
    # backward-compat until the SPD-style UI lands.
    kind: Literal["item"] = "item"
    id: str = ""
    name: str
    type: str = "item"
    pos: Optional[Position] = None

    quantity: int = 1
    level: int = 0
    level_known: bool = False
    cursed: bool = False
    cursed_known: bool = False
    unique: bool = False
    kept_though_lost: bool = False
    # Sitting on a Shopkeeper's stock pile (SPD's Heap.Type.FOR_SALE) — not
    # auto-picked-up by walking over it; bought via SHOP_BUY instead.
    for_sale: bool = False

    # First-discovery latch: set true once this floor item's cell enters a
    # player's FOV (mirrors SPD's Heap.seen).
    seen: bool = False

    # Type-intrinsic, so kept off the wire as ClassVars.
    stackable: ClassVar[bool] = False
    category: ClassVar[str] = ItemCategory.MISC
    # Flavour text shown in the item info window (SPD's Item.desc()).
    DESC: ClassVar[str] = ""

    # --- behaviour ---------------------------------------------------------
    def actions(self, player: Optional["Player"] = None) -> List[str]:
        # SPD's Item.actions defaults to DROP + THROW for everything.
        return [Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return None

    def description(self, player: Optional["Player"] = None) -> str:
        # SPD's Item.info(): flavour text plus any dynamic lines. Subclasses add
        # context (strength requirement, upgrade level, curse) via _info_lines.
        lines = [self.DESC] if self.DESC else []
        lines += self._info_lines(player)
        return "\n\n".join(l for l in lines if l)

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        return []

    def uses_targeting(self, action: str) -> bool:
        return action in TARGETED_ACTIONS

    def is_identified(self) -> bool:
        return self.level_known and self.cursed_known

    def is_similar(self, other: "ItemBase") -> bool:
        return (
            type(self) is type(other)
            and not isinstance(self, Bag)
            and self.level == other.level
            and self.name == other.name
        )

    def merge(self, other: "ItemBase") -> "ItemBase":
        self.quantity += other.quantity
        other.quantity = 0
        return self

    def split(self, amount: int) -> Optional["ItemBase"]:
        if amount <= 0 or amount >= self.quantity:
            return None
        clone = self.model_copy(deep=True)
        clone.id = _new_id()      # id-addressed protocol: halves must not collide
        clone.quantity = amount
        self.quantity -= amount
        return clone

    def value(self, identified: bool = False) -> int:
        # SPD's Item.value(): base price for shop sell-back. `identified` is
        # whether this item's *kind* has been identified this run (used by
        # potions/scrolls whose price depends on identification, not just
        # this instance's level/curse state).
        return 0


def _tiered_value(tier: int, level: int, level_known: bool, cursed: bool, cursed_known: bool) -> int:
    # Shared by MeleeWeapon/Armor: SPD's `20 * tier` formula with
    # cursed/level price modifiers.
    price = 20 * tier
    if cursed_known and cursed:
        price /= 2
    if level_known and level > 0:
        price *= (level + 1)
    return max(1, round(price))


def _charm_value(level: int, level_known: bool, cursed: bool, cursed_known: bool) -> int:
    # Shared by Wand/Ring: SPD's flat 75 base with cursed/level price modifiers.
    price = 75
    if cursed and cursed_known:
        price /= 2
    if level_known:
        if level > 0:
            price *= (level + 1)
        elif level < 0:
            price /= (1 - level)
    return max(1, round(price))


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
    """Builds a concrete melee weapon by its SPD name (one of WEP_TIER_ORDER's
    entries, excluding Mage's Staff/Pickaxe), using WEAPON_DEFS for stats."""
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
    DESC: ClassVar[str] = "Worn armor that absorbs a portion of incoming damage. Equip it for protection."

    def dr_min(self, upgrade_level: int = 0) -> int:
        return upgrade_level

    def dr_max(self, upgrade_level: int = 0) -> int:
        return self.tier * (2 + upgrade_level)

    def value(self, identified: bool = False) -> int:
        return _tiered_value(self.tier, self.level, self.level_known, self.cursed, self.cursed_known)


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


class ZapContext:
    """Data passed to a wand's handle_zap after a ranged zap fires.

    Carries everything the wand-specific effect needs: the attacker, target
    cell, floor state, event emitter, and the result of the generic combat
    resolution (damage/hit/miss).
    """
    __slots__ = (
        "attacker", "target_x", "target_y", "target_entity",
        "damage_dealt", "hit", "crit", "missed",
        "floor", "floor_id", "floor_mobs", "floor_players",
        "add_event",
    )

    def __init__(self, attacker, target_x, target_y, target_entity,
                 damage_dealt, hit, crit, missed,
                 floor, floor_id, floor_mobs, floor_players,
                 add_event):
        self.attacker = attacker
        self.target_x = target_x
        self.target_y = target_y
        self.target_entity = target_entity
        self.damage_dealt = damage_dealt
        self.hit = hit
        self.crit = crit
        self.missed = missed
        self.floor = floor
        self.floor_id = floor_id
        self.floor_mobs = floor_mobs
        self.floor_players = floor_players
        self.add_event = add_event


class Wand(ItemBase):
    kind: Literal["wand"] = "wand"
    type: str = "wand"
    category: ClassVar[str] = ItemCategory.WAND
    damage: int = 0
    charges: int = 2
    max_charges: int = 2
    range: int = 4
    projectile_type: str = "magic_bolt"
    beam_type: Optional[str] = None
    wand_sound: Optional[str] = None
    partial_charge: float = 0.0
    staff_name: str = "Staff"
    recharge_scale: float = 1.0
    DESC: ClassVar[str] = "A wand of magical power. Zap an enemy to spend a charge; charges recover over time."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.ZAP] + super().actions(player)

    def default_action(self) -> Optional[str]:
        return Action.ZAP

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        if hasattr(self, "min") and hasattr(self, "max"):
            lvl = self.level if self.level_known else 0
            lines = [f"Deals {self.min(lvl)}-{self.max(lvl)} damage per hit."]
        else:
            lines = [f"Deals {self.damage} damage per hit."]
        lines.append(f"It currently holds {self.charges} of {self.max_charges} charges.")
        return lines

    def value(self, identified: bool = False) -> int:
        return _charm_value(self.level, self.level_known, self.cursed, self.cursed_known)

    def initial_charges(self) -> int:
        return self.max_charges

    def buffed_lvl(self) -> int:
        return max(0, self.level)

    def get_reach(self) -> int:
        return self.range

    def gain_charge(self, amt: float, overcharge: bool = False):
        self.partial_charge += amt
        while self.partial_charge >= 1.0:
            if overcharge:
                self.charges = min(self.max_charges + int(amt), self.charges + 1)
            else:
                self.charges = min(self.max_charges, self.charges + 1)
            self.partial_charge -= 1.0

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        pass

    def charges_per_cast(self) -> int:
        """Number of charges consumed per zap (override for Fireblast/Regrowth)."""
        return 1

    def handle_zap(self, ctx: ZapContext):
        """Post-damage effects after a ranged zap lands.

        Called by the engine after generic damage is resolved. Subclasses
        override this to implement wand-specific effects (gas clouds, chains,
        summons, terrain changes, etc.).
        """
        pass


class DamageWand(Wand):
    """Base for wands that deal direct damage to a target.

    Subclasses define *min(lvl)* and *max(lvl)*; *damage_roll(lvl)* returns a
    random integer in that range.
    """

    kind: Literal["damage_wand"] = "damage_wand"

    def min(self, lvl: int) -> int:
        raise NotImplementedError

    def max(self, lvl: int) -> int:
        raise NotImplementedError

    def min_damage(self) -> int:
        return self.min(self.buffed_lvl())

    def max_damage(self) -> int:
        return self.max(self.buffed_lvl())

    def damage_roll(self, lvl: int) -> int:
        from app.engine.entities.base import _random
        return _random.randint(self.min(lvl), self.max(lvl))

    def damage_roll_buffed(self, lvl_bonus: int = 0) -> int:
        return self.damage_roll(self.buffed_lvl() + lvl_bonus)

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lvl = self.level if self.level_known else 0
        lines = [f"Deals {self.min(lvl)}-{self.max(lvl)} damage per hit."]
        lines.append(f"It currently holds {self.charges} of {self.max_charges} charges.")
        return lines


# --- Wand subclasses -----------------------------------------------------------

class WandOfMagicMissile(DamageWand):
    kind: Literal["wand_magic_missile"] = "wand_magic_missile"
    name: str = "Wand of Magic Missile"
    type: str = "wand"
    charges: int = 4
    max_charges: int = 4
    projectile_type: str = "magic_missile"
    staff_name: str = "Staff of Magic Missile"
    DESC: ClassVar[str] = "A basic wand that fires a magic missile."

    def min(self, lvl: int) -> int: return 2 + lvl
    def max(self, lvl: int) -> int: return 8 + 2 * lvl

    def initial_charges(self) -> int:
        return 3

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if add_event:
            add_event("SPELL_SPRITE", {
                "x": attacker.pos.x, "y": attacker.pos.y, "index": 2  # SPELL_CHARGE
            })
        belongings = getattr(attacker, "belongings", None)
        if belongings is None:
            return
        for item in belongings.all_items():
            if isinstance(item, Wand) and item.id != self.id and item.charges < item.max_charges:
                item.charges = min(item.max_charges, item.charges + 1)

    def handle_zap(self, ctx):
        if ctx.hit and ctx.damage_dealt > 0:
            lvl = self.buffed_lvl()
            ctx.attacker.add_buff("magic_charge", duration=4.0, level=lvl, stack_mode="extend")


class WandOfFireblast(DamageWand):
    kind: Literal["wand_fireblast"] = "wand_fireblast"
    name: str = "Wand of Fireblast"
    type: str = "wand"
    charges: int = 2
    max_charges: int = 2
    projectile_type: str = "fire_bolt"
    staff_name: str = "Staff of Fireblast"
    DESC: ClassVar[str] = "A catastrophic wand that unleashes fire."

    def min(self, lvl: int) -> int: return (1 + lvl)
    def max(self, lvl: int) -> int: return 8 + 4 * lvl

    def charges_per_cast(self) -> int:
        # SPD: consume ceil(30% of current charges), clamped [1,3]
        consumed = (self.charges * 3 + 9) // 10  # ceil(30%)
        return max(1, min(3, consumed))

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if defender is None or not defender.is_alive:
            return
        proc_chance = 0.0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cx, cy = defender.pos.x + dx, defender.pos.y + dy
                ch = None
                if floor_mobs:
                    ch = next((m for m in floor_mobs.values() if m.is_alive and m.pos.x == cx and m.pos.y == cy), None)
                if ch and ch.has_buff("burning"):
                    proc_chance += 0.25
        proc_chance = min(1.0, proc_chance)
        if _random.random() < proc_chance:
            power_mult = max(1.0, proc_chance)
            lvl = max(0, self.level)
            dmg_range = (2 + 2 * lvl, 8 + 4 * lvl)
            hit_any = False
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cx, cy = defender.pos.x + dx, defender.pos.y + dy
                    ch = None
                    if floor_mobs:
                        ch = next((m for m in floor_mobs.values() if m.is_alive and m.pos.x == cx and m.pos.y == cy), None)
                    if ch and ch != attacker and ch.faction != attacker.faction:
                        aoe_dmg = _random.randint(dmg_range[0], dmg_range[1])
                        aoe_dmg = int(aoe_dmg * power_mult)
                        ch.take_damage(aoe_dmg)
                        hit_any = True
                        if ch.has_buff("burning"):
                            ch.remove_buff("burning")
            if hit_any and add_event:
                add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=getattr(defender, "floor_id", 0))

        if floor is not None:
            strength = 1 + self.charges
            cx, cy = defender.pos.x, defender.pos.y
            if 0 <= cx < floor.width and 0 <= cy < floor.height:
                tile = floor.grid[cy][cx]
                if tile != TileType.FLOOR_WATER:
                    blob_id = f"wand_fireblast_{defender.id}_{cx}_{cy}"
                    floor.blob_areas[blob_id] = {
                        "type": "fire",
                        "cells": {(cx, cy)},
                        "volume": {(cx, cy): strength},
                    }

    def handle_zap(self, ctx):
        charges = self.charges_per_cast()
        fire_vol = 1 + charges
        floor = ctx.floor
        tx, ty = ctx.target_x, ctx.target_y
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = tx + dx, ty + dy
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    tile = floor.grid[ny][nx]
                    if tile == TileType.FLOOR_WATER:
                        continue
                    blob_id = f"wand_fireblast_{ctx.attacker.id}_{nx}_{ny}"
                    floor.blob_areas[blob_id] = {
                        "type": "fire",
                        "cells": {(nx, ny)},
                        "volume": {(nx, ny): fire_vol},
                    }
        if ctx.hit and ctx.target_entity and ctx.target_entity.is_alive:
            if charges >= 2:
                ctx.target_entity.add_buff("cripple", duration=8.0, level=1)
            if charges >= 3:
                ctx.target_entity.add_buff("paralysis", duration=8.0, level=1)
        ctx.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=ctx.floor_id)


class WandOfFrost(DamageWand):
    kind: Literal["wand_frost"] = "wand_frost"
    name: str = "Wand of Frost"
    type: str = "wand"
    charges: int = 3
    max_charges: int = 3
    projectile_type: str = "frost"
    staff_name: str = "Staff of Frost"
    DESC: ClassVar[str] = "A wand that freezes enemies solid."

    def min(self, lvl: int) -> int: return 2 + lvl
    def max(self, lvl: int) -> int: return 8 + 5 * lvl

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if defender is None:
            return
        chill_buff = defender.get_buff("chill")
        if chill_buff:
            chill_turns = int(chill_buff.remaining)
            proc_chance = (chill_turns - 1) / 9.0
            if _random.random() < proc_chance:
                power_mult = max(1.0, proc_chance)
                duration = round(3.0 * power_mult)
                defender.add_buff("frost", duration=duration, level=1)

    def handle_zap(self, ctx):
        if ctx.floor is None:
            return
        lvl = self.buffed_lvl()
        tx, ty = ctx.target_x, ctx.target_y
        # Extinguish fire at target tile
        to_remove = [bid for bid, b in ctx.floor.blob_areas.items()
                     if b.get("type") in ("fire",) and (tx, ty) in b.get("cells", set())]
        for bid in to_remove:
            del ctx.floor.blob_areas[bid]
        if ctx.hit and ctx.target_entity and ctx.target_entity.is_alive:
            chill_turns = 4 + lvl if ctx.floor.grid[ty][tx] == TileType.FLOOR_WATER else 2 + lvl
            ctx.target_entity.add_buff("chill", duration=float(chill_turns), level=1)
            # SPD: if already frozen, no effect; frost proc handled by on_hit for Battlemage


class WandOfLightning(DamageWand):
    kind: Literal["wand_lightning"] = "wand_lightning"
    name: str = "Wand of Lightning"
    type: str = "wand"
    charges: int = 2
    max_charges: int = 2
    projectile_type: str = "lightning"
    wand_sound: str = "LIGHTNING"
    staff_name: str = "Staff of Lightning"
    DESC: ClassVar[str] = "A wand that arcs lightning to its target."

    def min(self, lvl: int) -> int: return 5 + lvl
    def max(self, lvl: int) -> int: return 10 + 5 * lvl

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if attacker is None:
            return
        lvl = max(0, self.level)
        proc_chance = (lvl + 1) / (lvl + 4)
        if has_buff(attacker.buffs, "empowered_strike_tracker"):
            proc_chance *= 2.0
            remove_buff(attacker.buffs, "empowered_strike_tracker")
        if _random.random() < proc_chance:
            attacker.add_buff("lightning_charge", duration=10.0, level=1)
            if add_event:
                add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=getattr(attacker, "floor_id", 0))

    def handle_zap(self, ctx):
        if not ctx.hit or ctx.damage_dealt <= 0 or not ctx.target_entity:
            return
        from collections import deque
        lvl = self.buffed_lvl()
        affected_ids = {ctx.target_entity.id}
        chain_mobs = []
        floor = ctx.floor
        tx, ty = ctx.target_x, ctx.target_y
        is_main_in_water = floor.grid[ty][tx] == TileType.FLOOR_WATER
        has_charge = has_buff(ctx.attacker.buffs, "lightning_charge")

        def _reachable(from_x, from_y, max_dist):
            visited = {(from_x, from_y)}
            q = deque([(from_x, from_y, 0)])
            while q:
                x, y, d = q.popleft()
                if d >= max_dist:
                    continue
                for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < floor.width and 0 <= ny < floor.height:
                        if (nx, ny) not in visited and not floor.flags.solid[ny][nx]:
                            visited.add((nx, ny))
                            q.append((nx, ny, d + 1))
            return visited

        def _wand_find(from_x, from_y):
            dist = 2 if (0 <= from_y < floor.height and 0 <= from_x < floor.width
                        and floor.grid[from_y][from_x] == TileType.FLOOR_WATER) else 1
            if has_charge:
                dist += 1
            reachable = _reachable(from_x, from_y, dist)
            for m in floor.mobs.values():
                if not m.is_alive or m.id in affected_ids:
                    continue
                if m.faction == ctx.attacker.faction:
                    continue
                if (m.pos.x, m.pos.y) not in reachable:
                    continue
                if has_buff(m.buffs, "lightning_charge"):
                    continue
                affected_ids.add(m.id)
                chain_mobs.append(m)
                _wand_find(m.pos.x, m.pos.y)

        _wand_find(tx, ty)

        if chain_mobs:
            base_dmg = self.damage_roll(lvl)
            mult = 1.0 if is_main_in_water else (0.4 + 0.6 / max(len(chain_mobs) + 1, 1))
            for m in chain_mobs:
                dmg = round(base_dmg * mult)
                dr_roll = _random.randint(m.get_dr_min(), m.get_dr_max())
                actual = m.take_damage(max(1, dmg - dr_roll))
                if actual > 0:
                    ctx.add_event("DAMAGE", {"target": m.id, "amount": actual, "shock": True}, floor_id=ctx.floor_id)
                    if not m.is_alive:
                        m.die(floor_mobs=floor.mobs, tile_x=m.pos.x, tile_y=m.pos.y,
                              players=ctx.floor_players)
                        ctx.add_event("DEATH", {"target": m.id}, floor_id=ctx.floor_id)

        ctx.add_event("LIGHTNING_ARC", {
            "source_x": ctx.attacker.pos.x,
            "source_y": ctx.attacker.pos.y,
            "target_x": tx,
            "target_y": ty,
        }, floor_id=ctx.floor_id)
        ctx.add_event("SHOCKING_PROC", {
            "source": ctx.attacker.id,
            "defender": ctx.target_entity.id if ctx.target_entity else ctx.attacker.id,
            "defender_x": tx,
            "defender_y": ty,
            "chain_targets": [{"id": m.id, "x": m.pos.x, "y": m.pos.y} for m in chain_mobs],
        }, floor_id=ctx.floor_id)

        if floor.grid[ty][tx] == TileType.FLOOR_WATER:
            blob_id = f"wand_elec_{ctx.attacker.id}"
            vol = 100
            cells = {(tx, ty)}
            volume = {(tx, ty): vol}
            existing = floor.blob_areas.get(blob_id)
            if existing:
                cells.update(existing["cells"])
                for k, v in existing["volume"].items():
                    volume[k] = max(volume.get(k, 0), v)
            floor.blob_areas[blob_id] = {"type": "electricity", "cells": cells, "volume": volume, "tick_counter": 0}
            cell_list = [(c[0], c[1], volume.get(c, vol)) for c in cells]
            ctx.add_event("BLOB_UPDATE", {"id": blob_id, "type": "electricity", "cells": cell_list}, floor_id=ctx.floor_id)
            ctx.add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=ctx.floor_id)


class WandOfDisintegration(DamageWand):
    kind: Literal["wand_disintegration"] = "wand_disintegration"
    name: str = "Wand of Disintegration"
    type: str = "wand"
    charges: int = 3
    max_charges: int = 3
    range: int = 8
    projectile_type: str = "beam"
    beam_type: str = "death_ray"
    wand_sound: str = "RAY"
    staff_name: str = "Staff of Disintegration"
    DESC: ClassVar[str] = "A wand that fires a deadly disintegration beam."

    def min(self, lvl: int) -> int: return 2 + lvl
    def max(self, lvl: int) -> int: return 8 + 4 * lvl

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        pass

    def handle_zap(self, ctx):
        if not ctx.hit or ctx.damage_dealt <= 0 or not ctx.target_entity:
            return
        lvl = self.buffed_lvl()
        terrain_bonus = 0
        extra_hits = 0
        # SPD: +1 effective level per extra enemy hit, +1 per ~3 solid tiles
        eff_lvl = lvl
        beam_dist = min(self.get_reach(), abs(ctx.attacker.pos.x - ctx.target_x) + abs(ctx.attacker.pos.y - ctx.target_y))
        # Damage ramps per terrain penetrated + extra enemies
        terrain_passed = 2
        eff_lvl += terrain_bonus + extra_hits
        dmg = _random.randint(self.min(eff_lvl), self.max(eff_lvl))
        # Destroy flammable tiles at target
        if ctx.floor and 0 <= ctx.target_y < ctx.floor.height and 0 <= ctx.target_x < ctx.floor.width:
            tile = ctx.floor.grid[ctx.target_y][ctx.target_x]
            if tile in (TileType.BARRICADE, TileType.BOOKSHELF):
                ctx.floor.grid[ctx.target_y][ctx.target_x] = TileType.FLOOR_GRASS
        if dmg > 0:
            ctx.target_entity.take_damage(dmg)
            ctx.add_event("DAMAGE", {
                "target": ctx.target_entity.id,
                "amount": dmg,
                "projectile": "beam",
                "beam_type": "death_ray",
                "source_x": ctx.attacker.pos.x,
                "source_y": ctx.attacker.pos.y,
            }, floor_id=ctx.floor_id)


class WandOfPrismaticLight(DamageWand):
    kind: Literal["wand_prismatic_light"] = "wand_prismatic_light"
    name: str = "Wand of Prismatic Light"
    type: str = "wand"
    charges: int = 4
    max_charges: int = 4
    range: int = 8
    projectile_type: str = "beam"
    beam_type: str = "light_ray"
    wand_sound: str = "RAY"
    staff_name: str = "Staff of Prismatic Light"
    DESC: ClassVar[str] = "A wand that fires a beam of prismatic light."

    def min(self, lvl: int) -> int: return 1 + lvl
    def max(self, lvl: int) -> int: return 5 + 3 * lvl

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if defender is None:
            return
        lvl = max(0, self.level)
        duration = round((1 + lvl))
        defender.add_buff("cripple", duration=float(duration), level=1)

    def handle_zap(self, ctx):
        lvl = self.buffed_lvl()
        # Reveal area around projectile path
        if ctx.floor:
            tx, ty = ctx.target_x, ctx.target_y
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = tx + dx, ty + dy
                    if 0 <= nx < ctx.floor.width and 0 <= ny < ctx.floor.height:
                        if ctx.floor.flags and hasattr(ctx.floor.flags, "discoverable") and ctx.floor.flags.discoverable[ny][nx]:
                            ctx.floor.flags.visited[ny][nx] = True
            # Light buff
            ctx.attacker.add_buff("light", duration=10.0 + lvl * 5, level=1)
        if ctx.hit and ctx.target_entity and ctx.target_entity.is_alive:
            blind_dur = 2.0 + lvl * 0.333
            if _random.random() < 3.0 / (5.0 + lvl):
                ctx.target_entity.add_buff("blindness", duration=blind_dur, level=1)
            # Bonus damage vs demonic/undead (handled generically by movement.py)


class WandOfBlastWave(DamageWand):
    kind: Literal["wand_blast_wave"] = "wand_blast_wave"
    name: str = "Wand of Blast Wave"
    type: str = "wand"
    charges: int = 3
    max_charges: int = 3
    projectile_type: str = "force"
    staff_name: str = "Staff of Blast Wave"
    DESC: ClassVar[str] = "A wand that blasts enemies backwards."

    def min(self, lvl: int) -> int: return 1 + lvl
    def max(self, lvl: int) -> int: return 3 + 3 * lvl

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if defender is None or not defender.is_alive:
            return
        if defender.has_buff("paralysis"):
            defender.remove_buff("paralysis")
            lvl = max(0, self.level)
            dmg = _random.randint(8 + 2 * lvl, 12 + 3 * lvl)
            defender.take_damage(dmg)
            defender.add_buff("blast_on_hit_tracker", duration=3.0, level=1)
            if add_event:
                add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=getattr(defender, "floor_id", 0))

    def handle_zap(self, ctx):
        ctx.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=ctx.floor_id)
        lvl = self.buffed_lvl()
        throw_strength = round(1.5 + lvl / 2.0)
        tx, ty = ctx.target_x, ctx.target_y
        # Knockback enemies in 3x3 from target
        if ctx.floor:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = tx + dx, ty + dy
                    if 0 <= nx < ctx.floor.width and 0 <= ny < ctx.floor.height:
                        for m in list(ctx.floor_mobs.values()):
                            if m.is_alive and m.pos.x == nx and m.pos.y == ny and m.faction != ctx.attacker.faction:
                                # Push away from target center
                                push_x = m.pos.x + (m.pos.x - tx)
                                push_y = m.pos.y + (m.pos.y - ty)
                                if 0 <= push_x < ctx.floor.width and 0 <= push_y < ctx.floor.height:
                                    if ctx.floor.flags and ctx.floor.flags.passable[push_y][push_x]:
                                        coll_dmg = _random.randint(throw_strength, 2 * throw_strength)
                                        if coll_dmg > 0:
                                            m.take_damage(coll_dmg)
                                            m.add_buff("paralysis", duration=1.0 + throw_strength / 2.0, level=1)


class WandOfTransfusion(DamageWand):
    kind: Literal["wand_transfusion"] = "wand_transfusion"
    name: str = "Wand of Transfusion"
    type: str = "wand"
    charges: int = 3
    max_charges: int = 3
    range: int = 6
    projectile_type: str = "beam"
    beam_type: str = "health_ray"
    wand_sound: str = "RAY"
    staff_name: str = "Staff of Transfusion"
    DESC: ClassVar[str] = "A wand that transfers health."

    def min(self, lvl: int) -> int: return 3 + lvl
    def max(self, lvl: int) -> int: return 6 + 2 * lvl

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if defender is None or attacker is None:
            return
        if defender.has_buff("charm"):
            lvl = max(0, self.level)
            shield_amt = int(2 * (5 + lvl))
            attacker.add_shield("transfusion_shield", shield_amt, priority=1, decay=5)

    def handle_zap(self, ctx):
        lvl = self.buffed_lvl()
        target = ctx.target_entity
        player = ctx.attacker
        if target is None:
            return
        # Only affects mobs (not players)
        from app.engine.entities.base import Mob as MobEntity
        if not isinstance(target, MobEntity):
            return
        is_enemy = target.faction != player.faction
        if not is_enemy or target.has_buff("charm"):
            # Ally or charmed: self-damage to heal
            self_dmg = max(1, player.get_total_max_hp() // 20)  # 5% max HP
            healing = self_dmg + 3 * lvl
            target.hp = min(target.get_total_max_hp(), target.hp + healing)
            player.add_shield("transfusion_shield", 5 + lvl, priority=1, decay=5)
            player.take_damage(self_dmg)
            ctx.add_event("PLAY_SOUND", {"sound": "HEAL"}, floor_id=ctx.floor_id)
        else:
            # Enemy: shield self, charm enemy
            player.add_shield("transfusion_shield", 5 + lvl, priority=1, decay=5)
            target.add_buff("charm", duration=10.0, level=1)


class WandOfCorrosion(Wand):
    kind: Literal["wand_corrosion"] = "wand_corrosion"
    name: str = "Wand of Corrosion"
    type: str = "wand"
    damage: int = 0
    charges: int = 3
    max_charges: int = 3
    projectile_type: str = "corrosion"
    wand_sound: str = "GAS"
    staff_name: str = "Staff of Corrosion"
    DESC: ClassVar[str] = "A wand that spews corrosive gas."

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lvl = self.level if self.level_known else 0
        return [
            f"Creates a cloud of corrosive gas (tier {3 + lvl * 2}).",
            f"It currently holds {self.charges} of {self.max_charges} charges.",
        ]

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        self._spawn_gas(attacker, defender, damage, tile_x, tile_y, floor, add_event)

    def _spawn_gas(self, attacker, defender, damage, tile_x, tile_y, floor, add_event):
        lvl = max(0, self.buffed_lvl())
        if tile_x is not None and tile_y is not None:
            cx, cy = tile_x, tile_y
        elif defender is not None:
            cx, cy = defender.pos.x, defender.pos.y
        else:
            return
        if floor is None:
            return
        strength = 3 + lvl * 2
        cells = set()
        volume = {}
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    if floor.flags and not floor.flags.solid[ny][nx]:
                        cells.add((nx, ny))
                        volume[(nx, ny)] = strength
        if not cells:
            return
        for bid in list(floor.blob_areas.keys()):
            b = floor.blob_areas[bid]
            if b.get("type") == "corrosive_gas" and b.get("cells", set()) & cells:
                del floor.blob_areas[bid]
        blob_id = f"wand_corrosion_{cx}_{cy}"
        floor.blob_areas[blob_id] = {
            "type": "corrosive_gas", "cells": cells, "volume": volume,
        }
        cell_list = [(c[0], c[1], volume.get(c, 1)) for c in cells]
        if add_event:
            add_event("BLOB_UPDATE", {"id": blob_id, "type": "corrosive_gas", "cells": cell_list})
            add_event("PLAY_SOUND", {"sound": "GAS"})

    def handle_zap(self, ctx):
        self._spawn_gas(ctx.attacker, ctx.target_entity, ctx.damage_dealt,
                         ctx.target_x, ctx.target_y, ctx.floor, ctx.add_event)
        if ctx.hit and ctx.damage_dealt > 0:
            lvl = self.buffed_lvl()
            ctx.add_event("DAMAGE", {
                "target": ctx.target_entity.id if ctx.target_entity else ctx.attacker.id,
                "amount": 0,
                "projectile": "corrosion",
                "splash_count": lvl // 2 + 2,
                "source_x": ctx.attacker.pos.x,
                "source_y": ctx.attacker.pos.y,
            }, floor_id=ctx.floor_id)


class WandOfCorruption(Wand):
    kind: Literal["wand_corruption"] = "wand_corruption"
    name: str = "Wand of Corruption"
    type: str = "wand"
    damage: int = 0
    charges: int = 3
    max_charges: int = 3
    projectile_type: str = "shadow"
    staff_name: str = "Staff of Corruption"
    DESC: ClassVar[str] = "A wand that corrupts the minds of enemies."

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if defender is None:
            return
        lvl = max(0, self.level)
        proc_chance = (lvl + 1) / (lvl + 6)
        if _random.random() < proc_chance:
            duration = int((4 + lvl * 2))
            defender.add_buff("amok", duration=float(duration), level=1)

    def handle_zap(self, ctx):
        target = ctx.target_entity
        player = ctx.attacker
        if target is None:
            return
        from app.engine.entities.base import Mob as MobEntity
        if not isinstance(target, MobEntity):
            return
        lvl = self.buffed_lvl()
        corrupt_power = 3.0 + lvl / 3.0
        hp_ratio = target.hp / max(1, target.get_total_max_hp())
        enemy_resist = 1.0 + 4.0 * (hp_ratio * hp_ratio)
        # Debuffs reduce resist
        debuff_count = 0
        for debuff in ("amok", "slow", "hex", "paralysis", "weakness", "vulnerable", "cripple", "blindness", "terror"):
            if target.has_buff(debuff):
                debuff_count += 1
        enemy_resist *= (0.5 ** debuff_count)
        if target.has_buff("corruption"):
            enemy_resist = corrupt_power + 0.001  # cannot re-corrupt
        if corrupt_power > enemy_resist:
            target.faction = player.faction
            target.add_buff("corruption", duration=999.0, level=1)
            ctx.add_event("PLAY_SOUND", {"sound": "CURSE"}, floor_id=ctx.floor_id)
        elif _random.random() < corrupt_power / enemy_resist:
            target.add_buff("amok", duration=6.0 + lvl * 3, level=1)
            ctx.add_event("PLAY_SOUND", {"sound": "CURSE"}, floor_id=ctx.floor_id)
        else:
            target.add_buff("weakness", duration=6.0 + lvl * 3, level=1)
            ctx.add_event("PLAY_SOUND", {"sound": "CURSE"}, floor_id=ctx.floor_id)


class WandOfRegrowth(Wand):
    kind: Literal["wand_regrowth"] = "wand_regrowth"
    name: str = "Wand of Regrowth"
    type: str = "wand"
    damage: int = 0
    charges: int = 4
    max_charges: int = 4
    projectile_type: str = "foliage"
    staff_name: str = "Staff of Regrowth"
    DESC: ClassVar[str] = "A wand that causes vegetation to spring forth."

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if attacker is None or damage <= 0:
            return
        from app.engine.dungeon.constants import TileType
        on_grass = False
        if floor and tile_x is not None and tile_y is not None:
            for px, py in [(attacker.pos.x, attacker.pos.y), (tile_x, tile_y)]:
                if 0 <= py < len(floor.grid) and 0 <= px < len(floor.grid[0]):
                    t = floor.grid[py][px]
                    if t in (TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.FURROWED_GRASS):
                        on_grass = True
                        break
        if on_grass:
            lvl = max(0, self.level)
            healing = int(damage * (lvl + 2) / (lvl + 6) / 2)
            if healing > 0:
                attacker.hp = min(attacker.get_total_max_hp(), attacker.hp + healing)

    def charges_per_cast(self) -> int:
        consumed = (self.charges * 3 + 9) // 10
        return max(1, min(3, consumed))

    def handle_zap(self, ctx):
        floor = ctx.floor
        if floor is None:
            return
        lvl = self.buffed_lvl()
        charges = self.charges_per_cast()
        grass_to_place = round((3.67 + lvl / 3.0) * charges)
        tx, ty = ctx.target_x, ctx.target_y
        cells = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = tx + dx, ty + dy
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    t = floor.grid[ny][nx]
                    if t in (TileType.FLOOR_GRASS, TileType.EMPTY_DECO, TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.FURROWED_GRASS):
                        cells.append((nx, ny))
        _random.shuffle(cells)
        placed = 0
        for nx, ny in cells:
            if placed >= grass_to_place:
                break
            floor.grid[ny][nx] = TileType.HIGH_GRASS
            placed += 1
            ctx.add_event("TERRAIN_CHANGE", {"x": nx, "y": ny, "tile": TileType.HIGH_GRASS}, floor_id=ctx.floor_id)
        # Chance to drop seeds/dew
        if cells and _random.random() < 0.5 and _random.randint(1, 6) <= charges:
            sx, sy = _random.choice(cells)
            seed = Seed(id=str(_uuid.uuid4()), pos=Position(x=sx, y=sy), name="Seed")
            floor.items[seed.id] = seed
            ctx.add_event("ITEM_DROP", {"x": sx, "y": sy, "item": seed.id, "kind": seed.kind}, floor_id=ctx.floor_id)


class WandOfWarding(Wand):
    kind: Literal["wand_warding"] = "wand_warding"
    name: str = "Wand of Warding"
    type: str = "wand"
    damage: int = 0
    charges: int = 3
    max_charges: int = 3
    projectile_type: str = "ward"
    staff_name: str = "Staff of Warding"
    DESC: ClassVar[str] = "A wand that deploys a sentry ward."

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if attacker is None or floor_mobs is None:
            return
        lvl = max(0, self.level)
        proc_chance = (lvl + 1) / (lvl + 5)
        if _random.random() < proc_chance:
            for mob in floor_mobs.values():
                if mob.is_alive and getattr(mob, "mob_type", None) == "ward":
                    heal_amt = max(1, lvl)
                    mob.hp = min(mob.max_hp, mob.hp + heal_amt)

    def handle_zap(self, ctx):
        floor = ctx.floor
        if floor is None:
            return
        lvl = self.buffed_lvl()
        tx, ty = ctx.target_x, ctx.target_y
        # Find existing ward at target
        existing_ward = None
        for m in floor.mobs.values():
            if m.is_alive and getattr(m, "mob_type", None) == "ward" and m.pos.x == tx and m.pos.y == ty:
                existing_ward = m
                break
        if existing_ward:
            heal = max(1, lvl)
            existing_ward.hp = min(existing_ward.max_hp, existing_ward.hp + heal)
            ctx.add_event("PLAY_SOUND", {"sound": "HEAL"}, floor_id=ctx.floor_id)
        elif 0 <= ty < floor.height and 0 <= tx < floor.width:
            if floor.flags and floor.flags.passable[ty][tx]:
                ward_id = str(_uuid.uuid4())
                ward = MobEntity(
                    id=ward_id,
                    type="mob",
                    mob_type="ward",
                    name="Ward Sentinel",
                    pos=Position(x=tx, y=ty),
                    hp=15, max_hp=15,
                    attack=5 + lvl, defense=2 + lvl // 2,
                    damage_min=2 + lvl // 2, damage_max=8 + 2 * lvl,
                    faction=ctx.attacker.faction,
                    view_distance=4,
                )
                floor.mobs[ward.id] = ward
                ctx.add_event("SUMMON", {"id": ward.id, "x": tx, "y": ty, "name": "Ward Sentinel"}, floor_id=ctx.floor_id)


class WandOfLivingEarth(DamageWand):
    kind: Literal["wand_living_earth"] = "wand_living_earth"
    name: str = "Wand of Living Earth"
    type: str = "wand"
    charges: int = 3
    max_charges: int = 3
    projectile_type: str = "earth"
    staff_name: str = "Staff of Living Earth"
    DESC: ClassVar[str] = "A wand that summons an earth guardian."

    def min(self, lvl: int) -> int: return 4
    def max(self, lvl: int) -> int: return 6 + 2 * lvl

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if attacker is None or damage <= 0:
            return
        armor = int(damage * 0.33)
        attacker.add_buff("rock_armor", duration=10.0, level=armor)

    def handle_zap(self, ctx):
        lvl = self.buffed_lvl()
        floor = ctx.floor
        if floor is None:
            return
        # Find existing guardian
        guardian = None
        for m in floor.mobs.values():
            if m.is_alive and getattr(m, "mob_type", None) == "earth_guardian" and m.faction == ctx.attacker.faction:
                guardian = m
                break
        tx, ty = ctx.target_x, ctx.target_y
        armor_to_add = self.damage_roll(lvl)
        guardian_threshold = 8 + lvl * 4
        if guardian:
            guardian.max_hp = 16 + 8 * lvl
            guardian.hp = min(guardian.max_hp, guardian.hp + armor_to_add)
            ctx.add_event("PLAY_SOUND", {"sound": "HEAL"}, floor_id=ctx.floor_id)
        elif armor_to_add >= guardian_threshold:
            gx, gy = tx, ty
            if ctx.target_entity and ctx.target_entity.pos:
                # Place nearest free neighbor
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = tx + dx, ty + dy
                        if 0 <= nx < floor.width and 0 <= ny < floor.height:
                            if floor.flags and floor.flags.passable[ny][nx]:
                                gx, gy = nx, ny
                                break
            guard_id = str(_uuid.uuid4())
            guard = MobEntity(
                id=guard_id,
                type="mob",
                mob_type="earth_guardian",
                name="Earth Guardian",
                pos=Position(x=gx, y=gy),
                hp=16 + 8 * lvl, max_hp=16 + 8 * lvl,
                attack=5 + lvl, defense=3 + lvl // 2,
                damage_min=2, damage_max=4 + lvl // 2,
                dr_min=lvl, dr_max=3 + 3 * lvl,
                faction=ctx.attacker.faction,
                view_distance=6,
            )
            floor.mobs[guard.id] = guard
            ctx.add_event("SUMMON", {"id": guard.id, "x": gx, "y": gy, "name": "Earth Guardian"}, floor_id=ctx.floor_id)
        else:
            ctx.attacker.add_buff("rock_armor", duration=20.0, level=armor_to_add)


class Potion(ItemBase):
    kind: Literal["potion"] = "potion"
    type: str = "potion"
    category: ClassVar[str] = ItemCategory.POTION
    stackable: ClassVar[bool] = True
    effect: str = ""
    # Shown only once the potion's type is identified; the masked generic text is
    # substituted server-side for unidentified potions.
    DESC: ClassVar[str] = "A magical potion. Drink it to release its effect."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.DRINK] + super().actions(player)

    def default_action(self) -> Optional[str]:
        return Action.DRINK

    def value(self, identified: bool = False) -> int:
        return 30 * self.quantity


class HealthPotion(Potion):
    kind: Literal["health_potion"] = "health_potion"
    name: str = "Health Potion"
    effect: str = "regen"
    DESC: ClassVar[str] = "Drinking this potion restores a good portion of your health over a short time."


class RevivingPotion(Potion):
    kind: Literal["reviving_potion"] = "reviving_potion"
    name: str = "Reviving Potion"
    effect: str = "revive"
    DESC: ClassVar[str] = "A potent elixir that can bring a fallen hero back from the brink."


class FuryPotion(Potion):
    kind: Literal["fury_potion"] = "fury_potion"
    name: str = "Potion of Fury"
    effect: str = "fury"
    DESC: ClassVar[str] = "Drinking this potion fills you with rage, empowering your attacks for a short time."


class PotionOfStrength(Potion):
    kind: Literal["potion_of_strength"] = "potion_of_strength"
    name: str = "Potion of Strength"
    effect: str = "strength"
    DESC: ClassVar[str] = "A fiery red liquid. Drinking it permanently increases your strength by 1."


class PotionOfHaste(Potion):
    kind: Literal["potion_of_haste"] = "potion_of_haste"
    name: str = "Potion of Haste"
    effect: str = "haste"
    DESC: ClassVar[str] = "Drinking this potion briefly doubles your speed."


class PotionOfInvisibility(Potion):
    kind: Literal["potion_of_invisibility"] = "potion_of_invisibility"
    name: str = "Potion of Invisibility"
    effect: str = "invisibility"
    DESC: ClassVar[str] = "Drinking this potion turns you invisible for a short time. Attacking breaks invisibility."


class PotionOfLevitation(Potion):
    kind: Literal["potion_of_levitation"] = "potion_of_levitation"
    name: str = "Potion of Levitation"
    effect: str = "levitation"
    DESC: ClassVar[str] = "Drinking this potion causes you to levitate briefly, letting you fly over pits and traps."


class PotionOfMindVision(Potion):
    kind: Literal["potion_of_mind_vision"] = "potion_of_mind_vision"
    name: str = "Potion of Mind Vision"
    effect: str = "mind_vision"
    DESC: ClassVar[str] = "Drinking this potion lets you sense the minds of nearby creatures through walls."


class PotionOfFrost(Potion):
    kind: Literal["potion_of_frost"] = "potion_of_frost"
    name: str = "Potion of Frost"
    effect: str = "frost"
    DESC: ClassVar[str] = "A cool blue liquid. Drinking it chills you and nearby enemies."


class PotionOfLiquidFlame(Potion):
    kind: Literal["potion_of_liquid_flame"] = "potion_of_liquid_flame"
    name: str = "Potion of Liquid Flame"
    effect: str = "liquid_flame"
    DESC: ClassVar[str] = "Throw or drink this to unleash a burst of fire."


class PotionOfToxicGas(Potion):
    kind: Literal["potion_of_toxic_gas"] = "potion_of_toxic_gas"
    name: str = "Potion of Toxic Gas"
    effect: str = "toxic_gas"
    DESC: ClassVar[str] = "Smashing this potion releases a choking cloud of poison gas."


class PotionOfParalyticGas(Potion):
    kind: Literal["potion_of_paralytic_gas"] = "potion_of_paralytic_gas"
    name: str = "Potion of Paralytic Gas"
    effect: str = "paralytic_gas"
    DESC: ClassVar[str] = "Smashing this releases a gas that paralyzes everything it touches."


class PotionOfPurity(Potion):
    kind: Literal["potion_of_purity"] = "potion_of_purity"
    name: str = "Potion of Purity"
    effect: str = "purity"
    DESC: ClassVar[str] = "Drinking this removes all negative effects and clears nearby gas clouds."


class PotionOfExperience(Potion):
    kind: Literal["potion_of_experience"] = "potion_of_experience"
    name: str = "Potion of Experience"
    effect: str = "experience"
    DESC: ClassVar[str] = "Drinking this immediately grants a full level's worth of experience."

    def value(self, identified: bool = False) -> int:
        return (50 if identified else 30) * self.quantity


class ElixirOfAquaticRejuvenation(Potion):
    kind: Literal["elixir_aqua_rejuv"] = "elixir_aqua_rejuv"
    name: str = "Elixir of Aquatic Rejuvenation"
    effect: str = "aqua_rejuv"
    DESC: ClassVar[str] = "A murky elixir brewed from a Health Potion and a Goo Blob. While its power lasts, you heal whenever you stand in water."

    def value(self, identified: bool = False) -> int:
        return 60 * self.quantity


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


class BrokenSeal(Artifact):
    kind: Literal["broken_seal"] = "broken_seal"
    name: str = "Broken Seal"
    charge: int = 0
    charge_cap: int = 100
    DESC: ClassVar[str] = "A broken seal from the warrior's armor. It can be affixed to armor to provide shielding as you fight."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        equipped = bool(player and player.belongings.is_equipped(self.id))
        if not equipped:
            return base
        has_armor = bool(player and player.belongings.armor is not None)
        if has_armor:
            return [Action.AFFIX, Action.UNEQUIP] + base
        return [Action.UNEQUIP] + base


class CloakOfShadows(Artifact):
    # The Rogue's signature artifact. Toggling STEALTH turns the hero invisible,
    # draining one charge every few seconds (see tick.py's cloak drain). It self-
    # levels with use (charge_cap grows 3 -> 10). Charge regenerates while not
    # stealthed. Mirrors SPD's CloakOfShadows; turn-based timers are recast as
    # real seconds for this engine.
    kind: Literal["cloak_of_shadows"] = "cloak_of_shadows"
    name: str = "Cloak of Shadows"
    type: str = "artifact"
    unique: bool = True
    charge: int = 3
    charge_cap: int = 3
    level_cap: ClassVar[int] = 10
    exp: int = 0
    DESC: ClassVar[str] = (
        "This cloak is an heirloom, passed down from generation to generation. "
        "Activate it to vanish into the shadows; striking from stealth lands a "
        "guaranteed, more powerful surprise attack."
    )

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None:
            return base
        light_cloak = player.talent_info.has("light_cloak")
        usable = (player.belongings.is_equipped(self.id) or light_cloak) and not self.cursed
        has_charge = self.charge > 0 or player.cloak_stealth_active
        if usable and has_charge:
            return [Action.STEALTH] + base
        return base

    def default_action(self) -> Optional[str]:
        return Action.STEALTH

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = super()._info_lines(player)
        lines.append(f"The cloak holds {self.charge} of {self.charge_cap} charges.")
        return lines

    def on_upgrade(self) -> None:
        self.charge_cap = min(self.charge_cap + 1, self.level_cap)


class DriedRose(Artifact):
    kind: Literal["dried_rose"] = "dried_rose"
    name: str = "Dried Rose"
    type: str = "artifact"
    unique: bool = True
    charge: int = 100
    charge_cap: int = 100
    level_cap: ClassVar[int] = 10
    exp: int = 0
    ghost_id: Optional[str] = None
    weapon: Optional["MeleeWeapon"] = None
    armor: Optional["Armor"] = None
    dropped_petals: int = 0
    DESC: ClassVar[str] = "A dried rose that holds the spirit of a fallen warrior. Equip and charge it to summon the ghost as an ally."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None:
            return base
        equipped = player.belongings.is_equipped(self.id)
        can_summon = (
            equipped
            and self.charge >= self.charge_cap
            and not self.cursed
            and self.has_no_ghost()
        )
        if can_summon:
            return [Action.SUMMON] + base
        if self.has_ghost():
            return [Action.DIRECT, "GHOST_GEAR"] + base
        return base

    def default_action(self) -> Optional[str]:
        return Action.DIRECT if self.has_ghost() else Action.SUMMON

    def has_ghost(self) -> bool:
        return self.ghost_id is not None

    def has_no_ghost(self) -> bool:
        return self.ghost_id is None

    def ghost_strength(self) -> int:
        return 13 + self.level // 2

    def on_upgrade(self) -> None:
        self.charge_cap = min(self.charge_cap + 1, self.level_cap)


class Petal(ItemBase):
    kind: Literal["petal"] = "petal"
    name: str = "Petal"
    type: str = "misc"
    category: ClassVar[str] = ItemCategory.MISC
    stackable: ClassVar[bool] = True
    level_known: bool = True
    cursed_known: bool = True
    DESC: ClassVar[str] = "A dried rose petal. It can upgrade a Dried Rose artifact."


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


class GooBlob(ItemBase):
    # Goo's death drop (SPD GooBlob): stackable quest reagent, used with a
    # Health Potion at an Alchemy Pot to brew an Elixir of Aquatic Rejuvenation
    # (see Action.ALCHEMIZE / action_alchemize).
    kind: Literal["goo_blob"] = "goo_blob"
    name: str = "Goo Blob"
    type: str = "misc"
    category: ClassVar[str] = ItemCategory.MISC
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A blob of black ooze left behind by Goo. Can be combined with a Health Potion at an Alchemy Pot."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is not None and any(isinstance(it, HealthPotion) for it in player.inventory):
            return [Action.ALCHEMIZE] + base
        return base

    def value(self, identified: bool = False) -> int:
        return 30 * self.quantity


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


class Scenery(ItemBase):
    # Non-pickable floor decoration (e.g. graves). Mirrors SPD heaps that aren't
    # collectable. Kept out of AnyItem since it only ever lives on the ground.
    kind: Literal["scenery"] = "scenery"
    type: str = "scenery"
    category: ClassVar[str] = ItemCategory.SCENERY


class Chest(ItemBase):
    kind: Literal["chest"] = "chest"
    type: str = "chest"
    category: ClassVar[str] = ItemCategory.SCENERY
    chest_type: str = "CHEST"
    opened: bool = False
    contents: List["AnyItem"] = Field(default_factory=list)


class Bag(ItemBase):
    kind: Literal["bag"] = "bag"
    type: str = "bag"
    category: ClassVar[str] = ItemCategory.BAG
    unique: bool = True
    capacity: int = 20
    items: List["AnyItem"] = Field(default_factory=list)
    DESC: ClassVar[str] = "A container that expands how much you can carry. Open it to view its contents."

    # None => general backpack (accepts everything). A set => a specialised
    # sub-bag that only accepts those item categories (SPD's pouches/holders).
    accepts: ClassVar[Optional[set]] = None

    def default_action(self) -> Optional[str]:
        return Action.OPEN

    # --- queries -----------------------------------------------------------
    def _local_get(self, item_id: str) -> Optional["ItemBase"]:
        return next((i for i in self.items if i.id == item_id), None)

    def find(self, item_id: str) -> Optional["ItemBase"]:
        local = self._local_get(item_id)
        if local is not None:
            return local
        for sub in self.items:
            if isinstance(sub, Bag):
                found = sub.find(item_id)
                if found is not None:
                    return found
        return None

    def contains(self, item_id: str) -> bool:
        return self.find(item_id) is not None

    def _used_slots(self) -> int:
        # Sub-bags expand storage in SPD rather than consuming a slot.
        return len([i for i in self.items if not isinstance(i, Bag)])

    def _accepts_extra(self, item: "ItemBase") -> bool:
        # Hook for specialised bags that accept a specific item class outside
        # of their category set (e.g. VelvetPouch + GooBlob in SPD).
        return False

    def can_hold(self, item: "ItemBase") -> bool:
        if isinstance(item, Bag) and self.accepts is not None:
            return False  # specialised pouches can't nest bags
        if (self.accepts is not None and item.category not in self.accepts
                and not self._accepts_extra(item)):
            return False
        if item.stackable:
            for it in self.items:
                if it.is_similar(item):
                    return True
        return self._used_slots() < self.capacity

    # --- mutations ---------------------------------------------------------
    def _sort(self) -> None:
        self.items.sort(key=lambda i: CATEGORY_ORDER.index(i.category)
                        if i.category in CATEGORY_ORDER else len(CATEGORY_ORDER))

    def collect(self, item: "ItemBase") -> bool:
        if item.quantity <= 0:
            return True
        # Prefer a matching specialised sub-bag (SPD auto-sorts into pouches).
        for sub in self.items:
            if isinstance(sub, Bag) and sub.can_hold(item) and sub.collect(item):
                return True
        if item.stackable:
            for it in self.items:
                if it.is_similar(item):
                    it.merge(item)
                    return True
        if not self.can_hold(item):
            return False
        self.items.append(item)
        self._sort()
        return True

    def detach(self, item_id: str) -> Optional["ItemBase"]:
        # Remove a single unit (splits a stack), recursing into sub-bags.
        item = self._local_get(item_id)
        if item is None:
            for sub in self.items:
                if isinstance(sub, Bag):
                    r = sub.detach(item_id)
                    if r is not None:
                        return r
            return None
        if item.stackable and item.quantity > 1:
            return item.split(1)
        self.items.remove(item)
        return item

    def detach_all(self, item_id: str) -> Optional["ItemBase"]:
        item = self._local_get(item_id)
        if item is not None:
            self.items.remove(item)
            return item
        for sub in self.items:
            if isinstance(sub, Bag):
                r = sub.detach_all(item_id)
                if r is not None:
                    return r
        return None

    def grab_items(self, source: "Bag") -> None:
        # Pull every item this (specialised) bag accepts out of `source`.
        if self.accepts is None:
            return
        movable = [i for i in list(source.items)
                   if not isinstance(i, Bag)
                   and (i.category in self.accepts or self._accepts_extra(i))]
        for it in movable:
            source.items.remove(it)
            self.collect(it)


class VelvetPouch(Bag):
    kind: Literal["velvet_pouch"] = "velvet_pouch"
    name: str = "Velvet Pouch"
    capacity: int = 19
    accepts: ClassVar[Optional[set]] = {ItemCategory.SEED}
    DESC: ClassVar[str] = "This small velvet pouch can store seeds and other small alchemy ingredients."

    def _accepts_extra(self, item: "ItemBase") -> bool:
        return isinstance(item, GooBlob)

    def value(self, identified: bool = False) -> int:
        return 30


class ScrollHolder(Bag):
    kind: Literal["scroll_holder"] = "scroll_holder"
    name: str = "Scroll Holder"
    accepts: ClassVar[Optional[set]] = {ItemCategory.SCROLL}

    def value(self, identified: bool = False) -> int:
        return 40


class MagicalHolster(Bag):
    kind: Literal["magical_holster"] = "magical_holster"
    name: str = "Magical Holster"
    accepts: ClassVar[Optional[set]] = {ItemCategory.WAND, ItemCategory.STONE}

    def value(self, identified: bool = False) -> int:
        return 60


class PotionBandolier(Bag):
    kind: Literal["potion_bandolier"] = "potion_bandolier"
    name: str = "Potion Bandolier"
    accepts: ClassVar[Optional[set]] = {ItemCategory.POTION}

    def value(self, identified: bool = False) -> int:
        return 40


# Discriminated union of everything that can live inside a Bag / equip slot.
# Keyed by `kind`, so member order is irrelevant and nested items serialize as
# their concrete type. Server never validates inbound items, so this exists only
# for clean outbound dumps + a stable client contract.
from app.engine.entities.rings import (
    RingOfAccuracy, RingOfEvasion, RingOfHaste, RingOfFuror,
    RingOfMight, RingOfTenacity, RingOfEnergy, RingOfArcana, RingOfSharpshooting,
)  # noqa: E402
from app.engine.entities.rings_tier3 import (
    RingOfForce, RingOfElements, RingOfWealth,
)  # noqa: E402

AnyItem = Annotated[
    Union[
        MeleeWeapon, Dagger, WornShortsword, Bow, SpiritBow, Staff, MissileWeapon,
        Armor, Ring, RingOfAccuracy, RingOfEvasion, RingOfHaste, RingOfFuror,
        RingOfMight, RingOfTenacity, RingOfEnergy, RingOfArcana, RingOfSharpshooting,
        RingOfForce, RingOfElements, RingOfWealth,
        Artifact, BrokenSeal, CloakOfShadows, DriedRose,
        DamageWand,
        WandOfMagicMissile, WandOfFireblast, WandOfFrost, WandOfLightning,
        WandOfDisintegration, WandOfPrismaticLight, WandOfBlastWave,
        WandOfTransfusion, WandOfCorrosion, WandOfCorruption,
        WandOfRegrowth, WandOfWarding, WandOfLivingEarth,
        Wand,
        HealthPotion, RevivingPotion, FuryPotion,
        PotionOfStrength, PotionOfHaste, PotionOfInvisibility, PotionOfLevitation,
        PotionOfMindVision, PotionOfFrost, PotionOfLiquidFlame, PotionOfToxicGas,
        PotionOfParalyticGas, PotionOfPurity, PotionOfExperience,
        ElixirOfAquaticRejuvenation,
        Potion,
        ScrollOfRage, ScrollOfMetamorphosis,
        ScrollOfUpgrade, ScrollOfIdentify, ScrollOfMagicMapping, ScrollOfTeleportation,
        ScrollOfRemoveCurse, ScrollOfRecharging, ScrollOfLullaby, ScrollOfTerror,
        ScrollOfMirrorImage, ScrollOfRetribution, ScrollOfTransmutation,
        Scroll,
        Gold,
        MysteryMeat, FrozenCarpaccio, Berry, SmallRation, Ration, Pasty, ChargrilledMeat, Food,
        Key,
        TenguMask, KingsCrown,
        Seed, Dewdrop, Waterskin, Amulet, Stone, Boomerang, ThrowableDagger, Throwable,
        GooBlob, DwarfToken, Petal,
        Chest,
        VelvetPouch, ScrollHolder, MagicalHolster, PotionBandolier, Bag,
    ],
    Field(discriminator="kind"),
]


# --- quickslots ------------------------------------------------------------
QUICKSLOT_SIZE = 6


class QuickSlotEntry(BaseModel):
    item_id: Optional[str] = None
    is_placeholder: bool = False
    placeholder_kind: Optional[str] = None  # re-bind target when a like item returns


class QuickSlot(BaseModel):
    slots: List[QuickSlotEntry] = Field(
        default_factory=lambda: [QuickSlotEntry() for _ in range(QUICKSLOT_SIZE)]
    )

    def index_of(self, item_id: str) -> int:
        return next((i for i, s in enumerate(self.slots) if s.item_id == item_id), -1)

    def clear_item(self, item_id: str) -> None:
        for s in self.slots:
            if s.item_id == item_id:
                s.item_id = None
                s.is_placeholder = False
                s.placeholder_kind = None

    def set_slot(self, index: int, item: "ItemBase") -> None:
        if not (0 <= index < len(self.slots)):
            return
        self.clear_item(item.id)
        self.slots[index] = QuickSlotEntry(item_id=item.id)

    def convert_to_placeholder(self, item: "ItemBase") -> None:
        # Stackable depleted: keep the slot reserved by kind (SPD placeholders).
        for s in self.slots:
            if s.item_id == item.id:
                s.item_id = None
                s.is_placeholder = True
                s.placeholder_kind = item.kind

    def replace_placeholder(self, item: "ItemBase") -> None:
        for s in self.slots:
            if s.is_placeholder and s.placeholder_kind == item.kind:
                s.item_id = item.id
                s.is_placeholder = False
                s.placeholder_kind = None
                return


# --- belongings ------------------------------------------------------------
class Belongings(BaseModel):
    backpack: Bag = Field(default_factory=lambda: Bag(id="backpack", name="Backpack"))
    weapon: Optional[AnyItem] = None
    armor: Optional[AnyItem] = None
    artifact: Optional[AnyItem] = None
    misc: Optional[AnyItem] = None
    ring: Optional[AnyItem] = None

    def equipped_slots(self) -> List[Optional["ItemBase"]]:
        return [self.weapon, self.armor, self.artifact, self.misc, self.ring]

    def is_equipped(self, item_id: str) -> bool:
        return any(s is not None and s.id == item_id for s in self.equipped_slots())

    def all_items(self):
        for s in self.equipped_slots():
            if s is not None:
                yield s
        if isinstance(self.weapon, Staff) and self.weapon.imbued_wand is not None:
            yield self.weapon.imbued_wand
        yield from self._iter_bag(self.backpack)

    def _iter_bag(self, bag: "Bag"):
        for it in bag.items:
            yield it
            if isinstance(it, Bag):
                yield from self._iter_bag(it)

    def get_item(self, item_id: str) -> Optional["ItemBase"]:
        for s in self.equipped_slots():
            if s is not None and s.id == item_id:
                return s
        return self.backpack.find(item_id)

    def slot_name_for(self, item: "ItemBase") -> Optional[str]:
        if isinstance(item, KindOfWeapon):
            return "weapon"
        if isinstance(item, Armor):
            return "armor"
        if isinstance(item, Ring):
            return "ring"
        if isinstance(item, Artifact):
            return "artifact"
        if isinstance(item, KindofMisc):
            return "misc"
        return None


Bag.model_rebuild()
Belongings.model_rebuild()


class Difficulty:
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"


class CharacterClass:
    WARRIOR = "warrior"
    MAGE = "mage"
    ROGUE = "rogue"
    HUNTRESS = "huntress"


class Effect(BaseModel):
    # A generic active buff/debuff, mirroring SPD's Buff + BuffIndicator. `icon`
    # is the index into the buffs.png icon sheet (see BuffIndicator constants).
    key: str
    name: str
    icon: int
    remaining: float = 0.0
    duration: float = 0.0

class DropEntry(BaseModel):
    item_kind: str
    chance: float
    max_global: int = 0

class WeightedCountDrop(BaseModel):
    # Mirrors SPD's Random.chances({...}) weighted pick: weights[i] is the
    # relative weight of dropping (base_count + i) copies of item_kind.
    item_kind: str
    weights: List[float]
    base_count: int = 0
    max_global: int = 0

class Mob(Entity):
    type: str = EntityType.MOB
    faction: str = Faction.DUNGEON
    ai_state: str = "idle"
    target_id: Optional[str] = None
    difficulty: str = Difficulty.NORMAL
    exp: int = 1
    loot_table: List[DropEntry] = Field(default_factory=list)
    weighted_drops: List[WeightedCountDrop] = Field(default_factory=list)
    flying: bool = False
    properties: List[str] = Field(default_factory=list)
    attack_range: int = 1
    # Attack speed is an independent property from movement `speed` (mirrors SPD,
    # where a mob's attackDelay and moveSpeed are separate). Baselined to the
    # player's standard weapon cadence so a basic mob trades blow-for-blow rather
    # than landing several hits between player swings. Faster movers (e.g. Crab,
    # speed=2.0) still chase quicker but attack at this normal rate.
    attack_cooldown: float = 3.0
    # Delay before a mob's FIRST strike after reaching its target, so the player
    # gets a beat to react on contact rather than being hit instantly. `engaged`
    # is runtime state tracking whether the mob is currently in attack range (used
    # to arm the windup once per engagement); see GameInstance.update_tick.
    aggro_windup: float = 1.0
    engaged: bool = False
    # Last known position of the mob's target. When the target goes invisible,
    # the mob moves toward this position before degrading to wandering (mirrors
    # SPD's HUNTING state where the mob paths to the last-seen cell).
    last_known_target_pos: Optional[Position] = None
    # Summoned ally (e.g. Rogue's Shadow Clone): the owning player's id and the
    # remaining real-time lifespan in seconds (0 = permanent until killed).
    owner_id: Optional[str] = None
    summon_lifespan: float = 0.0

    def die(self, attacker=None, floor_mobs=None, tile_x=0, tile_y=0, players=None):
        pass

class Player(Entity):
    type: str = EntityType.PLAYER
    faction: str = Faction.PLAYER
    class_type: str = CharacterClass.WARRIOR # Default
    experience: int = 0
    level: int = 1
    active_effects: List[Effect] = []
    floor_id: int = 1
    strength: int = 10
    belongings: Belongings = Field(default_factory=Belongings)
    quickslot: QuickSlot = Field(default_factory=QuickSlot)
    # Keys never enter the bag (mirrors SPD's Notes-based key tracking) — see
    # add_key/key_count/remove_key.
    keys: List[KeyRecord] = Field(default_factory=list)
    gold: int = 0
    energy: int = 0
    websocket_id: Optional[str] = None
    is_downed: bool = False
    death_processed: bool = False
    kills_count: int = 0
    floors_explored: int = 1
    # Over-time healing, mirroring SPD's Healing buff. Each application heals
    # `heal_pct_per_tick` of the remaining `heal_left` (plus a flat amount), with a
    # minimum of 1, until exhausted. `heal_cooldown` throttles applications so heals
    # land at a readable cadence rather than every 20Hz tick.
    heal_left: float = 0.0
    heal_pct_per_tick: float = 0.0
    heal_flat_per_tick: float = 0.0
    heal_cooldown: int = 0
    # Throttles the passive +10/s healing while standing in a floor's entrance room.
    room_heal_cooldown: int = 0
    # Elixir of Aquatic Rejuvenation healing pool (SPD AquaHealing buff): heals
    # max(1, maxHP/50) per turn while standing in water, until exhausted.
    aqua_heal_left: float = 0.0
    # SPD LockedFloor buff: present while a sealed boss arena (e.g. Goo's) is
    # active. None when absent; while set, passive regen is paused once it
    # drops below 1 — boss damage taken adds time (capped 50), boss healing
    # removes it. Can go negative; only cleared explicitly on unseal.
    locked_floor_left: Optional[float] = None
    # Set by movement.py's move_entity when a player's deliberate step lands
    # on a CHASM tile; cleared unconditionally on every other move_entity
    # call for that player, or once confirm_chasm_fall consumes it.
    pending_chasm_fall: Optional[Tuple[int, int]] = None
    path_queue: List[Tuple[int, int]] = []
    path_blocked_ticks: int = 0
    move_intent: Optional[Tuple[int, int]] = None
    last_auto_move_time: float = 0.0
    action_until: float = 0.0
    # Hold Fast (warrior T3): ticks since the player last moved.
    stationary_ticks: int = 0
    is_admin: bool = False

    # Subclass and talents
    subclass_info: SubclassInfo = Field(default_factory=SubclassInfo)

    # Berserker rage (0.0 – 1.0 + endless_rage bonus)
    berserk_power: float = 0.0
    berserk_active: bool = False
    berserk_cooldown: int = 0
    # Rage % at the moment Berserk last triggered (for Endless Rage's
    # cooldown-reduction effect when power > 1.0).
    berserk_trigger_power: float = 0.0
    # Last action type (for followup strike tracking)
    _last_action: str = ""

    # Gladiator combo (uncapped hit-counter, SPD actors/buffs/Combo.java)
    combo_count: int = 0
    combo_timer: float = 0.0
    # Once-per-buff-lifetime combo move flags
    clobber_used: bool = False
    parry_used: bool = False

    # Ring of Wealth bonus drop counters (SPD TriesToDrop / DropsToEquip)
    wealth_tries_to_drop: float = 0.0
    wealth_drops_to_equip: int = 0

    # Broken Seal (all Warriors): cooldown (in ticks) before the seal can
    # trigger its shield again. 150 on trigger, can go negative via Lethal
    # Defense (instant re-trigger once <= 0).
    seal_cooldown: int = 0
    # Ticks since a hostile mob was last nearby, while the seal shield is up.
    seal_no_enemy_ticks: int = 0

    # Endure (warrior armor ability): banked outgoing-damage bonus
    endure_damage_bonus: float = 0.0
    endure_hits_left: int = 0
    endure_banked: float = 0.0

    # Heroic Leap "Double Jump" (warrior T4): one free re-leap charge ready
    double_jump_ready: bool = False

    # Armor ability charge (0–100, shared resource for Leap/Shockwave/Endure)
    armor_charge: int = 0

    # Armor ability selected by player (Leap/Shockwave/Endure), set via talent
    armor_ability: str = ""

    # Broken Seal was affixed to armor (permanently consumed)
    seal_affixed: bool = False

    # --- Rogue ----------------------------------------------------------------
    # Cloak of Shadows sustained stealth: while active the hero is invisible and
    # the cloak bleeds charge (see tick.py). `_cloak_drain_accum` accumulates
    # real seconds toward the next charge drain; `_cloak_recharge_accum` toward
    # the next regenerated charge while not stealthed.
    # Hunger: 0=full, 300=hungry warning, 450=starving (takes damage)
    hunger: float = 0.0

    cloak_stealth_active: bool = False
    _cloak_drain_accum: float = 0.0
    _cloak_recharge_accum: float = 0.0
    # Assassin Preparation: real seconds spent invisible this stealth window.
    # Drives the surprise damage tier / KO threshold / blink range (see combat).
    prep_seconds: float = 0.0
    # Freerunner Momentum: stacks build per move and decay while standing still;
    # spending them grants a short freerun (speed + evasion).
    momentum_stacks: int = 0
    _momentum_decay_accum: float = 0.0
    freerun_seconds: float = 0.0
    @property
    def talent_info(self):
        return self.subclass_info.talent_info

    # Backward-compat views over Belongings so existing engine/UI code and the
    # current front-end snapshot keep working until the SPD-style UI lands.
    # `inventory` returns the live backpack list, so .append/.pop/.remove still
    # mutate the real store; rebind sites (= []) were migrated to belongings.
    @computed_field
    @property
    def inventory(self) -> List[AnyItem]:
        return self.belongings.backpack.items

    @computed_field
    @property
    def equipped_weapon(self) -> Optional[AnyItem]:
        return self.belongings.weapon

    @computed_field
    @property
    def equipped_wearable(self) -> Optional[AnyItem]:
        return self.belongings.armor

    def take_damage(self, amount: int):
        if self.is_admin:
            return 0
        if self.is_downed:
            return 0

        # Deathless Fury (warrior T3 berserker): a fatal blow while raging with
        # power>=1 triggers Berserk instead of killing (cheat death, SPD
        # Berserk.berserking()).
        if (
            self.hp - amount <= 0
            and self.subclass_info.subclass == "berserker"
            and self.berserk_power >= 1.0
            and not self.berserk_active
        ):
            df = self.subclass_info.talent_info.level("deathless_fury")
            if df > 0:
                self.hp = 1
                self.berserk_active = True
                self.berserk_trigger_power = self.berserk_power
                from app.engine.entities.buffs import add_buff as _add_buff, remove_buff as _remove_buff
                _add_buff(self.buffs, "berserk", duration=10.0, level=1)
                _remove_buff(self.buffs, "berserk_ready")
                self.add_shield("berserk", self.get_berserk_shield_amount(), priority=2, decay=40)
                cooldown = 200 - 50 * df
                if self.berserk_power > 1.0:
                    cooldown = round(cooldown * (2.0 - self.berserk_power))
                self.berserk_cooldown = cooldown
                return 0

        # Provoked Anger (warrior T1): being hit primes a damage bonus on the
        # hero's next attack.
        pa = self.subclass_info.talent_info.level("provoked_anger")
        if pa > 0 and amount > 0:
            add_buff(self.buffs, "provoked_anger_tracker", duration=3.0, level=1)

        # Broken Seal (all Warriors): a hit that drops HP to <=50% (from
        # above 50%) grants instant shielding, then starts a 150-turn
        # cooldown (BrokenSeal.java / WarriorShield).
        if (
            self.seal_affixed
            and self.seal_cooldown <= 0
            and amount > 0
            and self.hp > self.get_total_max_hp() * 0.5
            and self.hp - amount <= self.get_total_max_hp() * 0.5
        ):
            self.add_shield("broken_seal", self.get_broken_seal_max_shield(), priority=2, decay=0)
            self.seal_cooldown = 150
            self.seal_no_enemy_ticks = 0

        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.is_downed = True
            self.is_alive = False
        return max(0, amount)

    def get_total_attack(self) -> int:
        w = self.belongings.weapon
        bonus = w.damage if isinstance(w, KindOfWeapon) else 0
        return self.attack + bonus

    def get_damage_min(self) -> int:
        w = self.belongings.weapon
        if isinstance(w, MeleeWeapon):
            return w.dmg_min(w.level)
        elif isinstance(w, KindOfWeapon):
            return w.damage
        from app.engine.entities.rings_tier3 import using_force, force_damage_range
        if using_force(self):
            return force_damage_range(self)[0]
        return self.damage_min

    def get_damage_max(self) -> int:
        w = self.belongings.weapon
        if isinstance(w, MeleeWeapon):
            return w.dmg_max(w.level)
        elif isinstance(w, KindOfWeapon):
            return w.damage
        from app.engine.entities.rings_tier3 import using_force, force_damage_range
        if using_force(self):
            return force_damage_range(self)[1]
        return self.damage_max

    def get_surprise_damage_floor(self) -> float:
        w = self.belongings.weapon
        if isinstance(w, KindOfWeapon):
            return w.surprise_damage_floor
        return 0.0

    def get_effective_strength(self) -> int:
        """Strongman (warrior T3): effective STR = STR * (1 + 0.03 + 0.05*pts).
        Ring of Might: +ring_bonus (unbuffed)."""
        base = self.strength
        sm = self.subclass_info.talent_info.level(Talent.STRONGMAN)
        if sm > 0:
            base += int(base * (0.03 + 0.05 * sm))
        from app.engine.entities.rings import might_str_bonus
        base += might_str_bonus(self)
        return base

    def get_berserk_shield_amount(self) -> int:
        """Berserk shield on trigger (Berserk.currentShieldBoost):
        base 8 + 2*armor level, multiplier 1..3x by missing HP (cubic), and
        scaled further by rage% above 100% (Endless Rage)."""
        hp_ratio = self.hp / max(self.get_total_max_hp(), 1)
        shield_mult = 1.0 + 2 * (1.0 - hp_ratio) ** 3
        if self.berserk_power > 1.0:
            shield_mult *= self.berserk_power
        armor = self.belongings.armor
        base_shield = 8 + (2 * armor.level if isinstance(armor, Armor) else 0)
        return round(base_shield * shield_mult)

    def get_broken_seal_max_shield(self) -> int:
        """Broken Seal (all Warriors): maxShield = 3 + 2*armorTier + IRON_WILL pts."""
        armor = self.belongings.armor
        armor_tier = armor.tier if isinstance(armor, Armor) else 0
        iw = self.subclass_info.talent_info.level(Talent.IRON_WILL)
        return 3 + 2 * armor_tier + iw

    def get_hold_fast_dr_range(self) -> Tuple[int, int]:
        """Hold Fast (warrior T3): bonus armor DR range while stationary, (pts, 2*pts)."""
        hf = self.subclass_info.talent_info.level(Talent.HOLD_FAST)
        if hf <= 0 or self.stationary_ticks <= 0:
            return (0, 0)
        return (hf, 2 * hf)

    def get_hold_fast_decay_factor(self) -> float:
        """Hold Fast (warrior T3): while stationary, combo/shield decay and
        the Broken Seal cooldown tick at 50%/25%/0% of normal speed for +1/+2/+3."""
        hf = self.subclass_info.talent_info.level(Talent.HOLD_FAST)
        if hf <= 0 or self.stationary_ticks <= 0:
            return 1.0
        return (1.0, 0.5, 0.25, 0.0)[min(hf, 3)]

    def _weapon_dr_bonus(self) -> int:
        w = self.belongings.weapon
        if isinstance(w, KindOfWeapon):
            return w.dr_bonus_base + w.dr_bonus_per_lvl * w.level
        return 0

    def get_dr_min(self) -> int:
        bonus_min, _ = self.get_hold_fast_dr_range()
        bonus_min += self._weapon_dr_bonus()
        a = self.belongings.armor
        if a is not None and isinstance(a, Armor):
            base = a.dr_min(a.level)
            deficit = max(0, a.strength_requirement - self.get_effective_strength())
            return max(0, base - 2 * deficit) + bonus_min
        return bonus_min

    def get_dr_max(self) -> int:
        _, bonus_max = self.get_hold_fast_dr_range()
        bonus_max += self._weapon_dr_bonus()
        a = self.belongings.armor
        if a is not None and isinstance(a, Armor):
            base = a.dr_max(a.level)
            deficit = max(0, a.strength_requirement - self.get_effective_strength())
            return max(0, base - 2 * deficit) + bonus_max
        return bonus_max

    def get_effective_defense_skill(self) -> int:
        base = self.defense_skill
        a = self.belongings.armor
        excess_str = 0
        if a is not None:
            deficit = max(0, a.strength_requirement - self.get_effective_strength())
            if deficit > 0:
                base = int(base / (1.5 ** deficit))
            excess_str = max(0, self.get_effective_strength() - a.strength_requirement)

        ea = self.subclass_info.talent_info.level(Talent.EVASIVE_ARMOR)
        if ea > 0 and self.freerun_seconds > 0:
            base += self.level // 2 + excess_str * ea
        from app.engine.entities.rings import evasion_multiplier
        base = int(base * evasion_multiplier(self))
        return base

    def set_heal(self, amount: float, percent_per_tick: float, flat_per_tick: float):
        # Multiple healing sources don't stack; they combine the best of each
        # property (mirrors Healing.setHeal in the original game).
        self.heal_left = max(self.heal_left, amount)
        self.heal_pct_per_tick = max(self.heal_pct_per_tick, percent_per_tick)
        self.heal_flat_per_tick = max(self.heal_flat_per_tick, flat_per_tick)
        self.heal_cooldown = 0  # first tick applies immediately

    def get_view_distance(self) -> int:
        base = self.view_distance
        fs = self.subclass_info.talent_info.level("farsight")
        if fs > 0:
            base += fs * 2
        return base

    def get_total_max_hp(self) -> int:
        from app.engine.entities.rings import might_ht_multiplier
        return int(self.max_hp * might_ht_multiplier(self))

    def add_to_inventory(self, item: ItemBase) -> bool:
        ok = self.belongings.backpack.collect(item)
        if ok:
            self.quickslot.replace_placeholder(item)
        return ok

    def add_key(self, key_id: str, depth: int, name: str = "", quantity: int = 1) -> None:
        for rec in self.keys:
            if rec.key_id == key_id and rec.depth == depth:
                rec.quantity += quantity
                return
        self.keys.append(KeyRecord(key_id=key_id, depth=depth, quantity=quantity, name=name))

    def key_count(self, key_id: str, depth: int) -> int:
        for rec in self.keys:
            if rec.key_id == key_id and rec.depth == depth:
                return rec.quantity
        return 0

    def remove_key(self, key_id: str, depth: int, quantity: int = 1) -> bool:
        for rec in self.keys:
            if rec.key_id == key_id and rec.depth == depth:
                if rec.quantity < quantity:
                    return False
                rec.quantity -= quantity
                if rec.quantity <= 0:
                    self.keys.remove(rec)
                return True
        return False

    def equip_item(self, item_id: str) -> bool:
        item = self.belongings.backpack.find(item_id)
        if item is None or not isinstance(item, EquipableItem):
            return False
        slot = self.belongings.slot_name_for(item)
        if slot is None:
            return False
        self.belongings.backpack.detach_all(item_id)
        prev = getattr(self.belongings, slot)
        if prev is not None:
            prev.on_unequip(self)
            self.belongings.backpack.collect(prev)
        setattr(self.belongings, slot, item)
        item.on_equip(self)
        return True

    def unequip_item(self, item_id: str) -> bool:
        for slot in ("weapon", "armor", "artifact", "misc", "ring"):
            cur = getattr(self.belongings, slot)
            if cur is not None and cur.id == item_id:
                if cur.cursed and cur.cursed_known:
                    return False  # cursed gear can't be removed (SPD)
                if not self.belongings.backpack.can_hold(cur):
                    return False
                cur.on_unequip(self)
                setattr(self.belongings, slot, None)
                self.belongings.backpack.collect(cur)
                return True
        return False

    def get_talent_damage_bonus(self) -> float:
        """Return a flat damage bonus from talents (added to damage roll)."""
        if has_buff(self.buffs, "provoked_anger_tracker"):
            pa = self.subclass_info.talent_info.level("provoked_anger")
            if pa > 0:
                remove_buff(self.buffs, "provoked_anger_tracker")
                return 1 + 2 * pa
        return 0.0

    def attack_proc(self, target) -> None:
        if self.subclass_info.subclass == "berserker" and self.berserk_cooldown <= 0:
            endless_level = self.subclass_info.talent_info.level("endless_rage")
            max_power = 1.0 + 0.1667 * endless_level
            self.berserk_power = min(max_power, self.berserk_power + 0.05)
        if self.subclass_info.subclass == "gladiator":
            self.combo_count += 1
            self.combo_timer = max(self.combo_timer, 5.0)

    def defense_proc(self, raw_damage: int, attacker, floor_mobs: dict, tile_x: int, tile_y: int) -> int:
        from app.engine.entities.buffs import has_buff

        # Endure (warrior armor ability): bank half of incoming damage and
        # reduce the rest by damageMulti (lowered further by Shrug It Off).
        if has_buff(self.buffs, "endure_tracker"):
            self.endure_banked += raw_damage * 0.5
            shrug = self.subclass_info.talent_info.level("shrug_it_off")
            damage_multi = 0.5 * (0.8 ** shrug)
            raw_damage = int(raw_damage * damage_multi)

        # Protective Shadows (rogue T1): DR while invisible
        ps = self.subclass_info.talent_info.level("protective_shadows")
        if ps > 0 and self.invisible > 0:
            dr_pct = 0.08 * ps
            raw_damage = max(0, raw_damage - int(raw_damage * dr_pct))

        return raw_damage

    MAX_LEVEL: ClassVar[int] = 30

    def max_exp(self) -> int:
        # Mirrors Hero.maxExp(lvl) = 5 + lvl*5 in the original game.
        return 5 + self.level * 5

    def earn_exp(self, amount: int) -> bool:
        # Award experience and apply any level-ups. Mirrors Hero.earnExp + updateHT:
        # each level grants +5 max HP and heals that gain. Returns True if at
        # least one level-up occurred (used to emit a LEVEL_UP event).
        if amount <= 0 or self.level >= self.MAX_LEVEL:
            return False
        self.experience += amount
        leveled_up = False
        while self.experience >= self.max_exp() and self.level < self.MAX_LEVEL:
            self.experience -= self.max_exp()
            self.level += 1
            self.max_hp += 5
            self.hp += 5
            self.attack_skill += 1
            self.defense_skill += 1
            leveled_up = True
            self._try_id_rings()
        if self.level >= self.MAX_LEVEL:
            self.experience = 0
        return leveled_up

    def _try_id_rings(self) -> None:
        """SPD Ring.onHeroGainExp: decrement levelsToID by 1.0 per hero level
        for each equipped un-identified ring. Auto-identifies at <=0."""
        for slot in ("ring", "misc"):
            ring = getattr(self.belongings, slot, None)
            if not isinstance(ring, Ring) or ring.is_identified():
                continue
            ring.levels_to_id -= 1.0
            if ring.levels_to_id <= 0:
                ring.level_known = True
                ring.cursed_known = True


# Legacy aliases — keep existing imports/constructors working during migration.
Item = ItemBase
Weapon = MeleeWeapon
Wearable = Armor
