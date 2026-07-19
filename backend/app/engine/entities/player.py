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
from app.engine.entities.items_equip import *
from app.engine.entities.items_wands import *
from app.engine.entities.items_potions import *
from app.engine.entities.items_scrolls import *
from app.engine.entities.items_consumable import *
from app.engine.entities.items_artifacts import *
from app.engine.entities.item_union import *


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

    _EQUIP_SLOT_NAMES = ("weapon", "armor", "artifact", "misc", "ring")

    def equipped_slots(self) -> List[Optional["ItemBase"]]:
        return [self.weapon, self.armor, self.artifact, self.misc, self.ring]

    def is_equipped(self, item_id: str) -> bool:
        return any(s is not None and s.id == item_id for s in self.equipped_slots())

    def find_equipped_slot(self, item_id: str) -> Optional[str]:
        """Name of whichever equip slot holds `item_id`, or None."""
        for slot in self._EQUIP_SLOT_NAMES:
            cur = getattr(self, slot)
            if cur is not None and cur.id == item_id:
                return slot
        return None

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
    # Internal ids are unchanged from their original meaning, but the UI now
    # displays NORMAL as "Medium" and HARD as "Normal" -- only the label
    # moved, not the difficulty progression (easy < normal < hard) or the
    # mob-AI aggression tiers keyed off these same values.
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"


class CharacterClass:
    WARRIOR = "warrior"
    MAGE = "mage"
    ROGUE = "rogue"
    HUNTRESS = "huntress"
    DUELIST = "duelist"
    CLERIC = "cleric"


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
    mob_type: Optional[str] = None
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
    # TimekeepersHourglass: remaining ticks of time-freeze (0 = not frozen).
    freeze_ticks: int = 0
    # Summoned ally (e.g. Rogue's Shadow Clone): the owning player's id and the
    # remaining real-time lifespan in seconds (0 = permanent until killed).
    owner_id: Optional[str] = None
    summon_lifespan: float = 0.0
    # SPD Mob.aggro(Char): when set, the mob prioritises chasing this specific
    # entity over scanning for the nearest player. Cleared when the target dies
    # or leaves the floor.
    aggro_target_id: Optional[str] = None

    def die(self, attacker=None, floor_mobs=None, tile_x=0, tile_y=0, players=None):
        pass

def hurt_warning_sound(damage_dealt: int, post_hp: int, max_hp: int) -> Optional[str]:
    """SPD Hero.damage(): picks between the low-health warning sound and the
    louder critical one based on a "flash intensity" combining how much of
    current HP was just lost and how little HP remains. Audio-only port —
    SPD also flashes the screen red at the same intensity; not replicated here.
    """
    if damage_dealt <= 0 or post_hp <= 0 or max_hp <= 0:
        return None
    pre_hp = post_hp + damage_dealt
    percent_dmg = damage_dealt / pre_hp
    percent_hp = post_hp / max_hp
    flash_intensity = 0.25 * percent_dmg * percent_dmg / percent_hp
    if flash_intensity < 0.05:
        return None
    return "HEALTH_CRITICAL" if flash_intensity >= 1 / 6 else "HEALTH_WARN"


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
    # SPD Hero.Doom cause flavour (mirrors Chasm implementing Hero.Doom). Set by
    # chasm-fall damage so the death screen can show "You fell to death..." and
    # the DEATH event can carry death_cause. Cleared on resurrect.
    death_cause: Optional[str] = None
    # True while the hero's WS is disconnected (grace window before reap kills
    # them) -- non-solid ghost: skipped by collision/AI targeting, "(AFK)" tag
    # shown above their head client-side.
    is_afk: bool = False
    # Easy-mode respawn counters. `respawns_used` ticks up each time this hero
    # accepts an easy-mode resurrection (cap 3). `witnessed_respawns` ticks up
    # for every *other* player's resurrection witnessed on the same run -- both
    # feed score penalties in _score_breakdown.
    respawns_used: int = 0
    witnessed_respawns: int = 0
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
    # Turns since a hostile mob was last nearby, while the seal shield is up.
    # Float to support Hold Fast's buffDecayFactor (0/0.25/0.5/1.0 per turn).
    seal_no_enemy_ticks: float = 0.0
    # maxShield() snapshot at activation time — used for the cooldown refund
    # ratio when the shield decays with no enemies nearby (WarriorShield.act).
    seal_initial_shield: int = 0

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
    # HolyTome: next scroll read is blessed (doubled effect).
    holy_tome_buffed: bool = False
    # Assassin Preparation: real seconds spent invisible this stealth window.
    # Drives the surprise damage tier / KO threshold / blink range (see combat).
    prep_seconds: float = 0.0
    # Freerunner Momentum: stacks build per move and decay while standing still;
    # spending them grants a short freerun (speed + evasion).
    momentum_stacks: int = 0
    _momentum_decay_accum: float = 0.0
    freerun_seconds: float = 0.0

    # --- Duelist --------------------------------------------------------------
    # Weapon charge (0-100): builds per melee hit, used by Champion/Monk finishers.
    weapon_charge: int = 0
    _weapon_charge_accum: float = 0.0
    # Finisher eligibility: True once combo_count >= threshold for Duelist.
    finisher_ready: bool = False
    # Duel mode: set while Challenge armor ability 1v1 is active.
    duel_mode_active: bool = False
    duel_mode_target_id: Optional[str] = None
    # Elemental strike last weapon kind (for enchant cone bonus).
    last_weapon_enchant: str = ""

    # --- Cleric ---------------------------------------------------------------
    # Spells cast this tick (for per-turn spell limits / Trinity tracking).
    spells_cast_this_turn: List[str] = Field(default_factory=list)
    # Spell cooldowns: {spell_name -> remaining_seconds}
    spell_cooldowns: Dict[str, float] = Field(default_factory=dict)
    # Trinity: list of borrowed item kinds (max 3)
    current_trinity_forms: List[str] = Field(default_factory=list)
    # Ascended Form (Cleric armor ability): active flag
    ascended_form_active: bool = False
    ascended_form_timer: float = 0.0
    # Power of Many: ally mob id
    powered_ally_id: Optional[str] = None
    # Paladin subclass: blessed weapon turns
    blessed_weapon_turns: int = 0

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
        # Timekeeper's Hourglass Stasis: suspended outside time — immune to harm.
        if self.has_buff("time_stasis"):
            return 0
        # Easy-mode spawn protection: brief invulnerability window after a
        # resurrection so a mob camping STAIRS_UP can't instantly re-kill
        # the reborn hero.
        if self.has_buff("spawn_protection"):
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

        # Broken Seal (WarriorShield): a hit that drops HP to <=50% (or
        # HP is already at <=50%) grants instant shielding, then starts a
        # 150-turn cooldown (Char.java:937-946 / WarriorShield.activate).
        # The freshly-activated shield absorbs part of the incoming hit.
        max_hp = self.get_total_max_hp()
        seal_max = self.get_broken_seal_max_shield()
        if (
            seal_max > 0
            and self.seal_cooldown <= 0
            and amount > 0
            and (
                self.hp <= max_hp * 0.5
                or self.hp + self.get_total_shield() - amount <= max_hp * 0.5
            )
        ):
            self.add_shield("broken_seal", seal_max, priority=2, decay=0)
            self.seal_cooldown = 150
            self.seal_no_enemy_ticks = 0
            self.seal_initial_shield = seal_max

        # Shield absorption (SPD ShieldBuff.processDamage): shields absorb
        # damage before it reaches HP, by priority (highest first).
        amount = self.process_shields(amount)

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

    def get_total_shield(self) -> int:
        """Total shielding from all active shield entries (SPD shielding())."""
        return sum(s.amount for s in self.shields)

    def get_broken_seal_max_shield(self) -> int:
        """Broken Seal (WarriorShield.maxShield): requires Iron Will talent
        to be upgraded. Base = 3 + 2*armorTier, +1/+2 per Iron Will point.
        Returns 0 if seal not affixed or Iron Will not upgraded."""
        if not self.seal_affixed:
            return 0
        iw = self.subclass_info.talent_info.level(Talent.IRON_WILL)
        if iw <= 0:
            return 0
        armor = self.belongings.armor
        armor_tier = armor.tier if isinstance(armor, Armor) else 0
        return 3 + 2 * armor_tier + iw

    def get_hold_fast_dr_range(self) -> Tuple[int, int]:
        """Hold Fast (warrior T3): bonus armor DR range while stationary, (pts, 2*pts)."""
        hf = self.subclass_info.talent_info.level(Talent.HOLD_FAST)
        if hf <= 0 or self.stationary_ticks <= 0:
            return (0, 0)
        return (hf, 2 * hf)

    def get_hold_fast_decay_factor(self) -> float:
        """Hold Fast (warrior T3): while stationary, combo decay and the
        Broken Seal no-enemy counter tick at 50%/25%/0% of normal speed
        for +1/+2/+3 (HoldFast.buffDecayFactor)."""
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
        # FerretTuft trinket: multiplies evasion
        from app.engine.entities.trinkets import FerretTuft as _FerretTuft
        from app.engine.entities.trinkets import trinket_level
        ft_lvl = trinket_level(self, "ferret_tuft")
        if ft_lvl >= 0:
            base = int(base * _FerretTuft.evasion_multiplier(ft_lvl))
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

    def count_worn_unidentified(self) -> int:
        count = 0
        for item in self.belongings.equipped_slots():
            if item is not None and not item.identified:
                count += 1
        return count

    def unequip_item(self, item_id: str) -> bool:
        slot = self.belongings.find_equipped_slot(item_id)
        if slot is None:
            return False
        cur = getattr(self.belongings, slot)
        if cur.cursed and cur.cursed_known:
            return False  # cursed gear can't be removed (SPD)
        if not self.belongings.backpack.can_hold(cur):
            return False
        cur.on_unequip(self)
        setattr(self.belongings, slot, None)
        self.belongings.backpack.collect(cur)
        return True

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

    def defense_proc(self, raw_damage: int, attacker, floor_mobs: dict, tile_x: int, tile_y: int, **kwargs) -> int:
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
        if amount <= 0:
            return False
        self._toolkit_gain_charge(amount)
        if self.level >= self.MAX_LEVEL:
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
        for ring in self.belongings.equipped_slots():
            if not isinstance(ring, Ring) or ring.is_identified():
                continue
            ring.levels_to_id -= 1.0
            if ring.levels_to_id <= 0:
                ring.level_known = True
                ring.cursed_known = True

    def _toolkit_gain_charge(self, exp_amount: int) -> None:
        """SPD AlchemistsToolkit.kitEnergy.gainCharge: (2 + kit level) energy
        per hero level, accumulated fractionally per exp gain."""
        from app.engine.entities.items_artifacts import AlchemistsToolkit
        kit = self.belongings.artifact
        if not isinstance(kit, AlchemistsToolkit) or kit.cursed:
            return
        kit._exp_charge_accum += (2 + kit.level) * (exp_amount / self.max_exp())
        while kit._exp_charge_accum >= 1 and kit.charge < kit.charge_cap:
            kit.charge += 1
            kit._exp_charge_accum -= 1


# Legacy aliases — keep existing imports/constructors working during migration.
Item = ItemBase
Weapon = MeleeWeapon
Wearable = Armor
