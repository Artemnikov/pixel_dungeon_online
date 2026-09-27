# Copyright (C) 2026 ArtemNikov
#
import random
from typing import List

from app.engine.entities.mobs.caves import Ghoul, Monk, Warlock, Golem
from app.engine.entities.player import Mob as MobEntity, DropEntry
from app.engine.game.constants import TICKS_PER_TURN

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
    attack_delay: float = 2.0
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="health_potion", chance=1.0, max_global=0),
    ]
    beam_target_id: str = ""
    beam_cooldown: float = 0.0  # ticks remaining until next beam
    beam_charged: bool = False
    charge_ticks: int = 0  # ticks remaining in charge-up (0 = ready to fire)
    charge_target_x: int = 0  # snapshot of target position when charge began
    charge_target_y: int = 0

    def defense_proc(self, damage: int, attacker, floor_mobs: dict, tile_x: int, tile_y: int, **kwargs) -> int:
        if self.beam_charged:
            damage = max(1, damage // 4)
        return damage


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
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="potion", chance=0.5, max_global=0),
    ]


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
    flying: bool = True
    view_distance: int = 6
    attack_cooldown: float = 1.5
    attack_delay: float = 0.5
    properties: List[str] = ["DEMONIC", "UNDEAD"]


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
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="kings_crown", chance=1.0, max_global=0),
    ]

    # Boss runtime state
    phase: int = 1
    summons_made: int = 0
    summon_cooldown: float = 0.0
    ability_cooldown: float = 0.0
    last_ability: int = 0  # 0=NONE, 1=LINK, 2=TELE
    fight_started: bool = False
    enrage_announced: bool = False
    losing_announced: bool = False
    barrier_hp: int = 0
    barrier_max: int = 0
    deferred_damage: int = 0
    phase3_ticks: int = 0
    pending_summons: List[dict] = []
    linked_mob_id: str = ""

    def take_damage(self, amount: int, is_split_damage: bool = False) -> int:
        if not self.is_alive or amount <= 0:
            return 0

        # Phase 1: Melee & Lifelink damage sharing
        if self.phase == 1:
            if not is_split_damage and self.has_buff("life_link"):
                owner = getattr(self, "_owner_ref", None)
                if owner is not None and getattr(owner, "is_alive", False):
                    split = amount // 2
                    amount = amount - split
                    owner.take_damage(split, is_split_damage=True)

            hp_threshold = 100 if self.max_hp > 300 else 50
            max_take = max(0, self.hp - hp_threshold)
            actual_dmg = min(amount, max_take)
            self.hp -= actual_dmg
            if actual_dmg > 0:
                accel = (actual_dmg / 8.0) * TICKS_PER_TURN
                self.summon_cooldown = max(0.0, self.summon_cooldown - accel)
                self.ability_cooldown = max(0.0, self.ability_cooldown - accel)
            return actual_dmg

        # Phase 2: King is invulnerable on throne; shield is broken by killing KingDamager minions
        if self.phase == 2:
            return 0

        # Phase 3: Viscosity deferred damage — direct hits add to deferred pool
        if self.phase == 3:
            if not is_split_damage:
                self.deferred_damage += amount
            else:
                self.hp = max(0, self.hp - amount)
                if self.hp <= 0:
                    self.hp = 0
                    self.is_alive = False
            return 0

        return super().take_damage(amount, is_split_damage=is_split_damage)


class DKGhoul(Ghoul):
    """DwarfKing minion — enhanced Ghoul, always starts hunting."""
    name: str = "DK Ghoul"
    hp: int = 40
    max_hp: int = 40
    attack_skill: int = 15
    defense_skill: int = 10
    damage_min: int = 6
    damage_max: int = 12
    properties: List[str] = ["UNDEAD", "BOSS_MINION"]
    max_lvl: int = -2
    king_damager: bool = False
    linked_king_id: str = ""
    linked_mob_id: str = ""


class DKMonk(Monk):
    """DwarfKing minion — enhanced Monk, always starts hunting."""
    name: str = "DK Monk"
    hp: int = 70
    max_hp: int = 70
    attack_skill: int = 22
    defense_skill: int = 24
    damage_min: int = 10
    damage_max: int = 18
    properties: List[str] = ["BOSS_MINION"]
    max_lvl: int = -2
    king_damager: bool = False
    linked_king_id: str = ""
    linked_mob_id: str = ""


class DKWarlock(Warlock):
    """DwarfKing minion — enhanced Warlock, always starts hunting."""
    name: str = "DK Warlock"
    hp: int = 60
    max_hp: int = 60
    attack_skill: int = 20
    defense_skill: int = 18
    damage_min: int = 10
    damage_max: int = 16
    properties: List[str] = ["UNDEAD", "BOSS_MINION"]
    max_lvl: int = -2
    king_damager: bool = False
    linked_king_id: str = ""
    linked_mob_id: str = ""


class DKGolem(Golem):
    """DwarfKing minion — enhanced Golem, always starts hunting."""
    name: str = "DK Golem"
    hp: int = 110
    max_hp: int = 110
    attack_skill: int = 24
    defense_skill: int = 12
    damage_min: int = 20
    damage_max: int = 35
    properties: List[str] = ["INORGANIC", "BOSS_MINION"]
    max_lvl: int = -2
    king_damager: bool = False
    linked_king_id: str = ""
    linked_mob_id: str = ""
