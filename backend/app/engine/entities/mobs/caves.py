# Copyright (C) 2026 ArtemNikov
#
import random
from typing import List, Optional, TYPE_CHECKING

from pydantic import Field

from app.engine.entities.player import Mob as MobEntity, DropEntry, WeightedCountDrop

if TYPE_CHECKING:
    from app.engine.entities.base import Entity

# ---------------------------------------------------------------------------
# Caves Enemies (depths 11-14) + Boss DM-300 (floor 15)
# ---------------------------------------------------------------------------

class DM300(MobEntity):
    # Stats mirror DM300.java: HP=300, attackSkill=20, defenseSkill=15,
    # damageRoll 15-25, drRoll 0-10. BOSS+LARGE+INORGANIC, immune to Sleep.
    type: str = "boss"
    name: str = "DM-300"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 20
    defense_skill: int = 15
    damage_min: int = 15
    damage_max: int = 25
    dr_min: int = 0
    dr_max: int = 10
    exp: int = 30
    max_lvl: int = 30
    attack_cooldown: float = 2.0
    ai_state: str = "wandering"
    properties: List[str] = ["BOSS", "INORGANIC", "LARGE"]
    immunities: List[str] = ["sleep", "magical_sleep", "drowsy"]

    fight_started: bool = False

    # Ability scheduler (DM300.java turnsSinceLastAbility/abilityCooldown/
    # lastAbility, in game-loop ticks): GAS (toxic vent) and ROCKS (boulder
    # drop) alternate with SPD's probabilities every 5-9 turns.
    turns_since_last_ability: int = -1
    ability_cooldown: int = 0
    last_ability: str = ""
    # Delayed boulder drop (DM300.FallingRockBuff): telegraphed cells and
    # the tick countdown until they land.
    pending_rockfall: Optional[dict] = None

    # Supercharge mechanic (DM300.java damage/supercharge/loseSupercharge).
    pylons_activated: int = 0
    supercharged: bool = False
    charge_announced: bool = False
    # Set by take_damage when a supercharge threshold is crossed; the combat
    # mixin reads/clears this to trigger CavesBossLevel.activatePylon (which
    # needs floor/player context that take_damage doesn't have).
    pending_pylon_activation: bool = False

    loot_table: List[DropEntry] = [
        DropEntry(item_kind="overloaded_charger", chance=1.0, max_global=0),
    ]
    # DM300.die(): drops 2 shards 60% / 3 shards 30% / 4 shards 10% (avg 2.5),
    # via Random.chances({0,0,6,3,1}). These are the Shrapnel Bomb reagent.
    weighted_drops: List[WeightedCountDrop] = [
        WeightedCountDrop(item_kind="metal_shard", weights=[0, 0, 6, 3, 1]),
    ]

    def is_enraged(self) -> bool:
        return self.hp * 2 <= self.max_hp

    def total_pylons_to_activate(self) -> int:
        # SPD: Challenges.STRONGER_BOSSES would raise this to 3; not implemented.
        return 2

    def take_damage(self, amount: int):
        # DM300.isInvulnerable(): true while supercharged.
        if self.supercharged:
            return 0

        dealt = super().take_damage(amount)

        # DM300.damage(): after applying damage, check the supercharge
        # threshold for the *next* pylon (HT/3 * (2 - pylonsActivated)).
        threshold = self.max_hp // 3 * (2 - self.pylons_activated)
        if self.hp <= threshold and threshold > 0:
            self.hp = threshold
            self.is_alive = True
            self.supercharged = True
            self.pylons_activated += 1
            self.pending_pylon_activation = True

        return dealt

    def lose_supercharge(self) -> None:
        # DM300.loseSupercharge(): vulnerable again; the ability timer is
        # clamped so DM-300 doesn't instantly fire an ability on charge end.
        self.supercharged = False
        if self.turns_since_last_ability >= 0:
            from app.engine.game.constants import GAME_TURN_TICKS
            self.turns_since_last_ability = min(
                self.turns_since_last_ability, (5 - 3) * GAME_TURN_TICKS)

class Spinner(MobEntity):
    name: str = "Spinner"
    hp: int = 50
    max_hp: int = 50
    attack_skill: int = 22
    defense_skill: int = 17
    damage_min: int = 10
    damage_max: int = 20
    dr_min: int = 0
    dr_max: int = 6
    exp: int = 9
    max_lvl: int = 17
    # Java's Spinner has no fixed web range -- webPos() just needs a valid,
    # unobstructed path within FOV -- so this mirrors the "range capped only
    # by FOV/view_distance" convention used by DM100/DM200 (attack_range=8).
    attack_range: int = 8
    web_cooldown: int = 0
    bolt_type: str = "magic_missile"
    immunities: List[str] = ["root"]
    resistances: List[str] = ["poison"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="mystery_meat", chance=0.125, max_global=0),
    ]

    def attack_proc(self, target: "Entity") -> None:
        if random.random() < 0.5:
            target.add_buff("poison", duration=8.0, level=1, stack_mode="extend")
            self.ai_state = "fleeing"


class DM200(MobEntity):
    name: str = "DM-200"
    hp: int = 80
    max_hp: int = 80
    attack_skill: int = 20
    defense_skill: int = 12
    damage_min: int = 10
    damage_max: int = 25
    dr_min: int = 0
    dr_max: int = 8
    attack_range: int = 8
    bolt_type: str = "toxic_gas"
    vent_cooldown: int = 0
    exp: int = 9
    max_lvl: int = 17
    properties: List[str] = ["INORGANIC", "LARGE"]
    immunities: List[str] = ["poison"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="weapon", chance=0.2, max_global=0),
    ]


class DM201(DM200):
    name: str = "DM-201"
    properties: List[str] = ["INORGANIC", "ELECTRIC", "LARGE"]
    bolt_type: str = "toxic_gas"


# ---------------------------------------------------------------------------
# City Enemies (depths 16-19)
# ---------------------------------------------------------------------------

class Ghoul(MobEntity):
    name: str = "Ghoul"
    hp: int = 45
    max_hp: int = 45
    attack_skill: int = 24
    defense_skill: int = 20
    damage_min: int = 16
    damage_max: int = 22
    dr_min: int = 0
    dr_max: int = 4
    exp: int = 5
    max_lvl: int = 20
    properties: List[str] = ["UNDEAD"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="gold", chance=0.2, max_global=0),
    ]


class FireElemental(MobEntity):
    name: str = "Fire Elemental"
    hp: int = 60
    max_hp: int = 60
    attack_skill: int = 25
    defense_skill: int = 20
    damage_min: int = 20
    damage_max: int = 25
    dr_min: int = 0
    dr_max: int = 5
    exp: int = 10
    max_lvl: int = 20
    properties: List[str] = ["FIERY", "INORGANIC"]
    immunities: List[str] = Field(default_factory=lambda: ["burning"])


class FrostElemental(FireElemental):
    name: str = "Frost Elemental"
    properties: List[str] = ["ICY", "INORGANIC"]


class ShockElemental(FireElemental):
    name: str = "Shock Elemental"
    properties: List[str] = ["ELECTRIC", "INORGANIC"]


class ChaosElemental(FireElemental):
    name: str = "Chaos Elemental"
    properties: List[str] = ["INORGANIC"]


class Warlock(MobEntity):
    name: str = "Warlock"
    hp: int = 70
    max_hp: int = 70
    attack_skill: int = 25
    defense_skill: int = 18
    damage_min: int = 12
    damage_max: int = 18
    dr_min: int = 0
    dr_max: int = 8
    attack_range: int = 5
    bolt_type: str = "shadow"
    exp: int = 11
    max_lvl: int = 21
    properties: List[str] = ["UNDEAD"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="potion", chance=0.5, max_global=0),
    ]

    def attack_proc(self, target: "Entity") -> None:
        if random.random() < 0.5:
            target.add_buff("degrade", duration=30.0, level=1)


class Monk(MobEntity):
    name: str = "Monk"
    hp: int = 70
    max_hp: int = 70
    attack_skill: int = 30
    defense_skill: int = 30
    damage_min: int = 12
    damage_max: int = 25
    dr_min: int = 0
    dr_max: int = 2
    exp: int = 11
    max_lvl: int = 21
    attack_cooldown: float = 1.5
    attack_delay: float = 0.5
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="food", chance=0.083, max_global=0),
    ]


class Senior(Monk):
    name: str = "Senior"
    damage_min: int = 16
    damage_max: int = 25
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="food", chance=1.0, max_global=0),
    ]


class Golem(MobEntity):
    name: str = "Golem"
    hp: int = 120
    max_hp: int = 120
    attack_skill: int = 28
    defense_skill: int = 15
    damage_min: int = 25
    damage_max: int = 30
    dr_min: int = 0
    dr_max: int = 12
    exp: int = 12
    max_lvl: int = 22
    properties: List[str] = ["INORGANIC"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="weapon", chance=0.2, max_global=0),
        DropEntry(item_kind="armor", chance=0.2, max_global=0),
    ]
