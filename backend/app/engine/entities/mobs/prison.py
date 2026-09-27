# Copyright (C) 2026 ArtemNikov
#
import random
from typing import List, Optional, TYPE_CHECKING

from pydantic import Field

from app.engine.entities.player import Mob as MobEntity, DropEntry

if TYPE_CHECKING:
    from app.engine.entities.base import Entity

# ---------------------------------------------------------------------------
# Prison Enemies (depths 6-9) + Rare Alts + Boss Tengu (floor 10)
# ---------------------------------------------------------------------------

class Tengu(MobEntity):
    type: str = "boss"
    name: str = "Tengu"
    hp: int = 200
    max_hp: int = 200
    attack_skill: int = 20
    defense_skill: int = 15
    damage_min: int = 6
    damage_max: int = 12
    dr_min: int = 0
    dr_max: int = 5
    exp: int = 20
    max_lvl: int = 25
    attack_range: int = 6
    attack_cooldown: float = 1.5
    view_distance: int = 12

    phase2: bool = False
    enrage_announced: bool = False
    fight_started: bool = False

    # Ability/jump state (mirrors Tengu.java's HP-bracket jump and the
    # bomb/fire/shocker ability rotation used while enraged).
    hp_bracket: int = 7
    # Turn-based tick counter (game runs at 20Hz; 20 ticks = 1 game turn).
    # Ability logic only runs when this reaches 20.
    turn_tick: int = 0
    # Cooldown in game turns. Starts at 2 so 1-turn delay before first ability
    # (SPD Tengu.java:443: "starts at 2, so one turn and then first ability").
    ability_cooldown: int = 2
    abilities_used: int = 0
    last_ability: int = -1  # SPD: 90% no-repeat; -1 = none yet
    arena_jumps: int = 0     # SPD: affects targetAbilityUses() cooldown
    bomb_x: int = -1
    bomb_y: int = -1
    bomb_timer: int = 0

    noticed: bool = False  # first-sight yell guard (SPD notice())

    # Persistent shocker state (SPD ShockerAbility buff)
    shocker_active: bool = False
    shocker_x: int = -1
    shocker_y: int = -1
    shocking_ordinals: Optional[bool] = None  # None=just spawned, True=ordinals, False=cardinals

    # SPD Tengu immunities
    immunities: List[str] = Field(default_factory=lambda: ["roots", "blindness", "dread", "terror"])

    loot_table: List[DropEntry] = [
        DropEntry(item_kind="tengu_mask", chance=1.0, max_global=0),
    ]

    def is_enraged(self) -> bool:
        return self.hp * 2 <= self.max_hp

    def target_ability_uses(self) -> int:
        target = 1 + 2 * self.arena_jumps
        target += max(0, self.arena_jumps - 2)
        return target

    # HP bracket clamping: Tengu cannot be hit through multiple HP/8 brackets
    # at once (mirrors Tengu.damage()). Called after damage is dealt.
    def clamp_bracket(self) -> None:
        hp_bracket = self.max_hp // 8
        if hp_bracket == 0:
            return
        curbracket = max(0, (self.hp * 8 - 1) // self.max_hp)  # SPD-style bracket
        if self.hp <= curbracket * hp_bracket:
            self.hp = curbracket * hp_bracket + 1
            if self.hp > self.max_hp:
                self.hp = self.max_hp

class Skeleton(MobEntity):
    name: str = "Skeleton"
    hp: int = 25
    max_hp: int = 25
    attack_skill: int = 12
    defense_skill: int = 9
    damage_min: int = 2
    damage_max: int = 10
    dr_min: int = 0
    dr_max: int = 5
    exp: int = 5
    max_lvl: int = 10
    properties: List[str] = ["UNDEAD", "INORGANIC", "BONES"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="weapon", chance=0.1667, max_global=0),
    ]

    def die(self, attacker=None, floor_mobs=None, tile_x=0, tile_y=0, players=None):
        dmg = random.randint(6, 12)
        targets = []
        seen_ids = set()
        if floor_mobs:
            for m in floor_mobs.values():
                if m.is_alive and m.id != getattr(self, "id", "") and abs(m.pos.x - tile_x) + abs(m.pos.y - tile_y) <= 1:
                    if m.id not in seen_ids:
                        targets.append(m)
                        seen_ids.add(m.id)
        if players:
            for p in players:
                if p.is_alive and abs(p.pos.x - tile_x) + abs(p.pos.y - tile_y) <= 1:
                    if p.id not in seen_ids:
                        targets.append(p)
                        seen_ids.add(p.id)
        if attacker and attacker.id not in seen_ids and abs(attacker.pos.x - tile_x) + abs(attacker.pos.y - tile_y) <= 1:
            targets.append(attacker)
            seen_ids.add(attacker.id)
        for t in targets:
            t.take_damage(dmg)


class Thief(MobEntity):
    name: str = "Thief"
    hp: int = 20
    max_hp: int = 20
    attack_skill: int = 12
    defense_skill: int = 12
    damage_min: int = 1
    damage_max: int = 10
    dr_min: int = 0
    dr_max: int = 3
    speed: float = 1.5
    exp: int = 5
    max_lvl: int = 11
    attack_cooldown: float = 1.5
    attack_delay: float = 0.5
    properties: List[str] = ["UNDEAD"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="ring", chance=0.03, max_global=0),
        DropEntry(item_kind="artifact", chance=0.03, max_global=0),
    ]

    def attack_proc(self, target):
        gold_stolen = min(getattr(target, "gold", 0), random.randint(5, 20))
        if gold_stolen > 0:
            target.gold -= gold_stolen
            self.ai_state = "fleeing"

    def defense_proc(self, damage: int, attacker, floor_mobs: dict, tile_x: int, tile_y: int, **kwargs):
        if self.ai_state == "fleeing":
            pass
        return damage


class DM100(MobEntity):
    name: str = "DM-100"
    hp: int = 20
    max_hp: int = 20
    attack_skill: int = 11
    defense_skill: int = 8
    damage_min: int = 2
    damage_max: int = 8
    dr_min: int = 0
    dr_max: int = 4
    exp: int = 6
    max_lvl: int = 13
    attack_range: int = 8
    properties: List[str] = ["ELECTRIC", "INORGANIC"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="scroll", chance=0.25, max_global=0),
    ]


class Guard(MobEntity):
    name: str = "Guard"
    hp: int = 40
    max_hp: int = 40
    attack_skill: int = 12
    defense_skill: int = 10
    damage_min: int = 4
    damage_max: int = 12
    dr_min: int = 0
    dr_max: int = 7
    exp: int = 7
    max_lvl: int = 14
    properties: List[str] = ["UNDEAD"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="armor", chance=0.2, max_global=0, decay_key="guard_arm"),
    ]
    chain_pulled: bool = False


class NecroSkeleton(Skeleton):
    """Summoned by Necromancer (SPD NecroSkeleton). Weaker than a regular
    Skeleton, gives no exp/loot (Java maxLvl=-5), starts wandering, and is
    rendered with a 0.75 brightness tint on the frontend."""
    name: str = "NecroSkeleton"
    hp: int = 20
    max_hp: int = 25
    exp: int = 0
    max_lvl: int = -5
    ai_state: str = "wandering"
    loot_table: List[DropEntry] = []
    tinted: bool = True


class Necromancer(MobEntity):
    name: str = "Necromancer"
    hp: int = 40
    max_hp: int = 40
    attack_skill: int = 10
    defense_skill: int = 14
    damage_min: int = 2
    damage_max: int = 5
    dr_min: int = 0
    dr_max: int = 5
    exp: int = 7
    max_lvl: int = 14
    properties: List[str] = ["UNDEAD", "DEMONIC"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="health_potion", chance=0.2, max_global=0),
    ]

    # Summon-minion state (mirrors SPD Necromancer summoning/summoningPos/firstSummon/mySkeleton)
    summoning: bool = False
    summoning_x: int = -1
    summoning_y: int = -1
    first_summon: bool = True
    my_skeleton_id: str = ""
    heal_cooldown: int = 0

    def die(self, attacker=None, floor_mobs=None, tile_x=0, tile_y=0, players=None):
        # SPD Necromancer.die(): kill the linked NecroSkeleton when its master dies.
        if floor_mobs and self.my_skeleton_id:
            skeleton = floor_mobs.get(self.my_skeleton_id)
            if skeleton and skeleton.is_alive:
                skeleton.hp = 0
                skeleton.is_alive = False


# ---------------------------------------------------------------------------
# Caves Enemies (depths 11-14)
# ---------------------------------------------------------------------------

class Bat(MobEntity):
    name: str = "Bat"
    hp: int = 30
    max_hp: int = 30
    attack_skill: int = 16
    defense_skill: int = 15
    damage_min: int = 5
    damage_max: int = 18
    dr_min: int = 0
    dr_max: int = 4
    speed: float = 2.0
    exp: int = 7
    max_lvl: int = 15
    flying: bool = True
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="health_potion", chance=0.167, max_global=0),
    ]

    def attack_proc(self, target: "Entity") -> None:
        # SPD Bat.attackProc: heals self for damage dealt (handled in combat)
        heal = random.randint(1, 3)
        self.hp = min(self.max_hp, self.hp + heal)


class Brute(MobEntity):
    name: str = "Brute"
    hp: int = 40
    max_hp: int = 40
    attack_skill: int = 20
    defense_skill: int = 15
    damage_min: int = 5
    damage_max: int = 25
    dr_min: int = 0
    dr_max: int = 8
    exp: int = 8
    max_lvl: int = 16
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="gold", chance=0.5, max_global=0),
    ]

    def get_damage_max(self) -> int:
        return 40 if self.hp * 2 <= self.max_hp else 25


class ArmoredBrute(Brute):
    name: str = "Armored Brute"
    dr_min: int = 4
    dr_max: int = 12


class Shaman(MobEntity):
    name: str = "Shaman"
    hp: int = 35
    max_hp: int = 35
    attack_skill: int = 18
    defense_skill: int = 15
    damage_min: int = 5
    damage_max: int = 10
    dr_min: int = 0
    dr_max: int = 6
    attack_range: int = 4
    exp: int = 8
    max_lvl: int = 16
    view_distance: int = 8

    wand_drop_count: int = 0

    loot_table: List[DropEntry] = [
        DropEntry(item_kind="wand", chance=0.03, max_global=0),
    ]


class RedShaman(Shaman):
    name: str = "Red Shaman"
    bolt_type: str = "shaman_red"

    def attack_proc(self, target: "Entity") -> None:
        if random.random() < 0.5:
            target.add_buff("weakness", duration=10.0, level=1)


class BlueShaman(Shaman):
    name: str = "Blue Shaman"
    bolt_type: str = "shaman_blue"

    def attack_proc(self, target: "Entity") -> None:
        if random.random() < 0.5:
            target.add_buff("vulnerable", duration=15.0, level=1)


class PurpleShaman(Shaman):
    name: str = "Purple Shaman"
    bolt_type: str = "shaman_purple"

    def attack_proc(self, target: "Entity") -> None:
        if random.random() < 0.5:
            target.add_buff("hex", duration=10.0, level=1)

class Bandit(Thief):
    name: str = "Bandit"
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="ring", chance=1.0, max_global=0),
    ]


class SpectralNecromancer(Necromancer):
    name: str = "Spectral Necromancer"
    properties: List[str] = ["UNDEAD", "DEMONIC"]


# ---------------------------------------------------------------------------
# Universal / Environmental Enemies
# ---------------------------------------------------------------------------
