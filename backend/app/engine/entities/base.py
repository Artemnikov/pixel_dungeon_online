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
        # Armor glyph: Obfuscation (passive stealth when equipped)
        from app.engine.entities.armor_glyphs import stealth_boost
        belongings = getattr(self, "belongings", None)
        if belongings is not None:
            armor = getattr(belongings, "armor", None)
            if armor is not None:
                base += stealth_boost(self, armor)
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
    RUNESTONE = "runestone"
    FOOD = "food"
    GOLD = "gold"
    KEY = "key"
    MISC = "misc"
    BAG = "bag"
    TRINKET = "trinket"
    SCENERY = "scenery"
    STYLUS = "stylus"

# Sort order inside a bag (mirrors SPD's itemComparator grouping by category).
CATEGORY_ORDER = [
    ItemCategory.WEAPON, ItemCategory.ARMOR, ItemCategory.RING, ItemCategory.ARTIFACT,
    ItemCategory.WAND, ItemCategory.SCROLL, ItemCategory.POTION, ItemCategory.SEED,
    ItemCategory.STONE, ItemCategory.RUNESTONE, ItemCategory.FOOD, ItemCategory.KEY,
    ItemCategory.GOLD, ItemCategory.TRINKET, ItemCategory.MISC, ItemCategory.BAG,
    ItemCategory.SCENERY,
]

class Action:
    DROP = "DROP"
    THROW = "THROW"
    USE = "USE"
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
    IMBUE = "IMBUE"      # MagesStaff: imbue a wand into the staff
    SUMMON = "SUMMON"    # DriedRose: summon the ghost ally
    DIRECT = "DIRECT"    # DriedRose: direct the ghost ally to a target
    SHOOT = "SHOOT"      # SpiritBow: fire an arrow
    INSCRIBE = "INSCRIBE"  # ArcaneStylus: inscribe a glyph on armor
    # Artifact actions
    BREW = "BREW"          # AlchemistsToolkit
    ENERGIZE = "ENERGIZE"  # AlchemistsToolkit
    PRICK = "PRICK"        # ChaliceOfBlood
    CAST = "CAST"          # EtherealChains
    BLESS = "BLESS"        # HolyTome
    SNACK = "SNACK"        # HornOfPlenty
    STORE = "STORE"        # HornOfPlenty
    BEACON_SET = "BEACON_SET"      # LloydsBeacon
    BEACON_RETURN = "BEACON_RETURN"  # LloydsBeacon
    STEAL = "STEAL"        # MasterThievesArmband
    PLANT_SEED = "PLANT_SEED"    # SandalsOfNature
    IDENTIFY_SEED = "IDENTIFY_SEED"  # SandalsOfNature
    UNLOCK = "UNLOCK"      # SkeletonKey
    KEY_REVEAL = "KEY_REVEAL"    # SkeletonKey
    SCRY = "SCRY"          # TalismanOfForesight
    FREEZE = "FREEZE"      # TimekeepersHourglass (halt mobs)
    STASIS = "STASIS"      # TimekeepersHourglass (self invuln/untargetable)
    BOOK_READ = "BOOK_READ"      # UnstableSpellbook
    BOOK_READ_RESOLVE = "BOOK_READ_RESOLVE"  # UnstableSpellbook exotic choice
    BOOK_INFUSE = "BOOK_INFUSE"  # UnstableSpellbook (feed a scroll to level up)

# Actions that require the player to pick a target cell before resolving.
TARGETED_ACTIONS = {Action.THROW, Action.ZAP, Action.DIRECT, Action.SHOOT,
                    Action.CAST, Action.STEAL, Action.PLANT_SEED,
                    Action.UNLOCK, Action.KEY_REVEAL}


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
    # True for Bag (a container). Kept as a flag so base need not import Bag,
    # which lives in the item_union module (avoids an import cycle).
    is_bag: ClassVar[bool] = False
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
            and not self.is_bag
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

