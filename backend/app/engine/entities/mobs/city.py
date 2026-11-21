# Copyright (C) 2026 ArtemNikov
#
import math
import random
from typing import ClassVar, List, Optional, Tuple

from pydantic import Field, PrivateAttr

from app.engine.entities.mobs.caves import Ghoul, Monk, Warlock, Golem
from app.engine.entities.buffs import add_buff
from app.engine.entities.player import Mob as MobEntity, DropEntry
from app.engine.game.constants import CRIPPLE_DURATION, SCORPIO_CRIPPLE_CHANCE

# ---------------------------------------------------------------------------
# City Enemies (depths 16-19) + Boss DwarfKing (floor 20)
# ---------------------------------------------------------------------------

class Succubus(MobEntity):
    name: str = "Succubus"
    hp: int = 80
    max_hp: int = 80
    attack_skill: int = 40
    defense_skill: int = 25
    damage_min: int = 25
    damage_max: int = 30
    dr_min: int = 0
    dr_max: int = 10
    exp: int = 12
    max_lvl: int = 25
    flying: bool = True
    view_distance: int = 6
    properties: List[str] = ["DEMONIC"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="scroll", chance=0.33, max_global=0),
    ]

    def attack_proc(self, target):
        if target.has_buff("charm"):
            dmg = random.randint(self.damage_min, self.damage_max)
            shield = (self.hp - self.max_hp) + (5 + dmg)
            if shield > 0:
                self.hp = self.max_hp
                self.add_shield("succubus_charm", shield, priority=1, decay=5)
            else:
                self.hp = min(self.max_hp, self.hp + 5 + dmg)
        elif random.random() < 0.33:
            target.add_buff("charm", duration=2.5, source_id=self.id)
        self._pending_sound = "CHARMS"


class Eye(MobEntity):
    name: str = "Evil Eye"
    hp: int = 100
    max_hp: int = 100
    attack_skill: int = 30
    defense_skill: int = 20
    damage_min: int = 20
    damage_max: int = 30
    dr_min: int = 0
    dr_max: int = 10
    attack_range: int = 8
    exp: int = 13
    max_lvl: int = 26
    flying: bool = True
    view_distance: int = 6
    attack_delay: float = 1.0
    properties: List[str] = ["DEMONIC"]
    owns_attacks: ClassVar[bool] = True
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="health_potion", chance=1.0, max_global=0),
    ]
    # SPD Eye beam state (game/ai_eye.py): beam cooldown in SPD turns, whether
    # the gaze is charged, and the cell it was aimed at (beamTarget).
    beam_target_id: str = ""
    beam_cooldown: int = 0
    beam_charged: bool = False
    has_beam_target: bool = False
    beam_target_x: int = 0
    beam_target_y: int = 0

    def take_damage(self, amount: int, is_split_damage: bool = False):
        if self.beam_charged:
            amount = amount // 4
        return super().take_damage(amount, is_split_damage)


class Scorpio(MobEntity):
    name: str = "Scorpio"
    hp: int = 110
    max_hp: int = 110
    attack_skill: int = 36
    defense_skill: int = 24
    damage_min: int = 30
    damage_max: int = 40
    dr_min: int = 0
    dr_max: int = 16
    attack_range: int = 5
    exp: int = 14
    max_lvl: int = 27
    view_distance: int = 6
    properties: List[str] = ["DEMONIC"]
    owns_attacks: ClassVar[bool] = True
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="potion", chance=0.5, max_global=0),
    ]

    def attack_proc(self, target):
        # Scorpio.attackProc: 50% Buff.prolong(enemy, Cripple, Cripple.DURATION).
        if random.random() < SCORPIO_CRIPPLE_CHANCE:
            add_buff(target.buffs, "cripple", duration=CRIPPLE_DURATION, level=1, stack_mode="extend")


class AcidicScorpio(Scorpio):
    name: str = "Acidic Scorpio"
    properties: List[str] = ["ACIDIC"]


class RipperDemon(MobEntity):
    name: str = "Ripper Demon"
    hp: int = 60
    max_hp: int = 60
    attack_skill: int = 30
    defense_skill: int = 22
    damage_min: int = 15
    damage_max: int = 25
    dr_min: int = 0
    dr_max: int = 4
    exp: int = 9
    max_lvl: int = -2
    view_distance: int = 6
    attack_cooldown: float = 1.5
    attack_delay: float = 0.5
    properties: List[str] = ["DEMONIC", "UNDEAD"]
    owns_attacks: ClassVar[bool] = True
    # RipperDemon leap state: the aimed cell, the leap cooldown (acts), and
    # where the enemy stood last act (used to aim past it).
    leap_pos: Optional[Tuple[int, int]] = None
    leap_cooldown: float = 0.0
    last_enemy_pos: Optional[Tuple[int, int]] = None


# ---------------------------------------------------------------------------
# Prison Rare Alt Enemies
# ---------------------------------------------------------------------------

class DwarfKing(MobEntity):
    type: str = "boss"
    name: str = "Dwarf King"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 26
    defense_skill: int = 22
    damage_min: int = 15
    damage_max: int = 25
    dr_min: int = 0
    dr_max: int = 10
    exp: int = 40
    max_lvl: int = -2
    properties: List[str] = ["UNDEAD", "BOSS"]
    attack_cooldown: float = 1.0

    # Boss runtime state; cooldowns/delays are in game turns (DwarfKing.act() runs once per turn)
    phase: int = 1
    summons_made: int = 0
    summon_cooldown: float = 0.0
    ability_cooldown: float = 0.0
    last_ability: int = 0  # 0=NONE, 1=LINK, 2=TELE
    fight_started: bool = False
    barrier_hp: int = 0
    barrier_max: int = 0
    deferred_damage: int = 0
    phase3_ticks: int = 0
    act_ticks: int = 0
    wave_wait: int = 0
    turn_spent: bool = False
    pending_summons: List[dict] = Field(default_factory=list)
    king_damager_ids: List[str] = Field(default_factory=list)

    _life_links: list = PrivateAttr(default_factory=list)
    _deferred_popups: list = PrivateAttr(default_factory=list)
    _locked_floor_credit: float = PrivateAttr(default=0.0)

    def take_damage(self, amount: int, is_split_damage: bool = False) -> int:
        """DwarfKing.damage(): phase 1 shares damage over LifeLinks and cannot drop
        below the phase-2 threshold, phase 2 is invulnerable (KingDamager is applied
        by the AI), phase 3 defers every hit into Viscosity.DeferedDamage."""
        if not self.is_alive or amount <= 0:
            return 0

        if self.phase == 1:
            if not is_split_damage:
                links = [link[0] for link in self._life_links if link[0].is_alive]
                if links:
                    amount = math.ceil(amount / (len(links) + 1))
                    for linked in links:
                        linked.take_damage(amount, is_split_damage=True)
            amount, _ = self.process_shields(amount)
            self.hp -= amount
            turns = amount / 8.0
            self.summon_cooldown -= turns
            self.ability_cooldown -= turns
            self._locked_floor_credit += amount
            threshold = 100 if self.max_hp > 300 else 50
            if self.hp <= threshold:
                self.hp = threshold
            return amount

        if self.phase == 2:
            return 0

        if self.deferred_damage == 0:
            self.phase3_ticks = 0
        self.deferred_damage += amount
        self._deferred_popups.append(amount)
        return 0


class DKGhoul(Ghoul):
    """DwarfKing minion — Ghoul that always starts hunting and never partners."""
    name: str = "DK Ghoul"
    exp: int = 0
    loot_table: List[DropEntry] = []
    properties: List[str] = ["UNDEAD", "BOSS_MINION"]
    max_lvl: int = -2
    king_damager: bool = False
    linked_king_id: str = ""


class DKMonk(Monk):
    """DwarfKing minion — Monk that always starts hunting."""
    name: str = "DK Monk"
    exp: int = 0
    loot_table: List[DropEntry] = []
    properties: List[str] = ["UNDEAD", "BOSS_MINION"]
    max_lvl: int = -2
    king_damager: bool = False
    linked_king_id: str = ""


class DKWarlock(Warlock):
    """DwarfKing minion — Warlock that always starts hunting."""
    name: str = "DK Warlock"
    exp: int = 0
    loot_table: List[DropEntry] = []
    properties: List[str] = ["UNDEAD", "BOSS_MINION"]
    max_lvl: int = -2
    king_damager: bool = False
    linked_king_id: str = ""


class DKGolem(Golem):
    """DwarfKing minion — Golem that always starts hunting."""
    name: str = "DK Golem"
    exp: int = 0
    loot_table: List[DropEntry] = []
    properties: List[str] = ["INORGANIC", "LARGE", "BOSS_MINION"]
    max_lvl: int = -2
    king_damager: bool = False
    linked_king_id: str = ""
