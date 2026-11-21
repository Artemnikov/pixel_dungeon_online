# Copyright (C) 2026 ArtemNikov
#
import math
import random
from typing import List, TYPE_CHECKING, ClassVar

from app.engine.entities.base import Position, normal_float
from app.engine.entities.player import Mob as MobEntity, DropEntry, WeightedCountDrop
from app.engine.game.constants import OOZE_DURATION

if TYPE_CHECKING:
    from app.engine.entities.base import Entity

# ---------------------------------------------------------------------------
# Standard Sewer Enemies + Rare Alts + Boss Goo (floor 5)
# ---------------------------------------------------------------------------

class Rat(MobEntity):
    name: str = "Rat"
    hp: int = 8
    max_hp: int = 8
    attack_skill: int = 8
    defense_skill: int = 2
    damage_min: int = 1
    damage_max: int = 4
    dr_min: int = 0
    dr_max: int = 1
    exp: int = 1
    max_lvl: int = 5


class Snake(MobEntity):
    name: str = "Snake"
    hp: int = 4
    max_hp: int = 4
    attack_skill: int = 10
    defense_skill: int = 25
    damage_min: int = 1
    damage_max: int = 4
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 2
    max_lvl: int = 7
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="seed", chance=0.25, max_global=0),
    ]


class Gnoll(MobEntity):
    name: str = "Gnoll"
    defense_verb: str = "blocked"
    hp: int = 12
    max_hp: int = 12
    attack_skill: int = 10
    defense_skill: int = 4
    damage_min: int = 1
    damage_max: int = 6
    dr_min: int = 0
    dr_max: int = 2
    exp: int = 2
    max_lvl: int = 8
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="gold", chance=0.5, max_global=0),
    ]


class Swarm(MobEntity):
    name: str = "Swarm"
    hp: int = 50
    max_hp: int = 50
    attack_skill: int = 10
    defense_skill: int = 5
    damage_min: int = 1
    damage_max: int = 4
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 3
    max_lvl: int = 9
    flying: bool = True
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="health_potion", chance=0.167, max_global=5),
    ]

    def defense_proc(self, damage: int, attacker: "Entity", floor_mobs: dict, tile_x: int, tile_y: int,
                      floor=None, game=None):
        # Splits into a clone on hit (SPD Swarm.defenseProc), but always returns
        # the unchanged damage so the resolver still applies it. Candidates are
        # cells adjacent to *this* Swarm (not tile_x/tile_y, which is the
        # attacker's tile) so clones never appear behind the player.
        if self.hp >= damage + 2 and self.is_alive:
            blocked = {(m.pos.x, m.pos.y) for m in floor_mobs.values() if m.is_alive}
            if attacker is not None and hasattr(attacker, "pos"):
                blocked.add((attacker.pos.x, attacker.pos.y))
            if game is not None and floor is not None:
                blocked |= {
                    (p.pos.x, p.pos.y)
                    for p in game._players_on_floor(floor.floor_id)
                    if p.is_alive
                }

            candidates = []
            for ox, oy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                cx, cy = self.pos.x + ox, self.pos.y + oy
                if (cx, cy) in blocked:
                    continue
                if floor is not None:
                    if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                        continue
                    if floor.flags and not (floor.flags.passable[cy][cx] or floor.flags.avoid[cy][cx]):
                        continue
                candidates.append(Position(x=cx, y=cy))

            if candidates:
                clone_id = f"{self.id}_split_{random.randint(0, 99999)}"
                clone = self.model_copy(deep=True)
                clone.id = clone_id
                # SPD Swarm.java: clone.HP = (HP - damage) / 2; HP -= clone.HP
                # -- conserves total HP across the split instead of growing it.
                clone.hp = (self.hp - damage) // 2
                clone.max_hp = self.max_hp
                clone.exp = 0
                clone.pos = random.choice(candidates)
                self.hp -= clone.hp
                floor_mobs[clone_id] = clone
        return damage


class Crab(MobEntity):
    name: str = "Crab"
    defense_verb: str = "blocked"
    hp: int = 15
    max_hp: int = 15
    attack_skill: int = 12
    defense_skill: int = 5
    damage_min: int = 1
    damage_max: int = 7
    dr_min: int = 0
    dr_max: int = 4
    speed: float = 2.0
    exp: int = 4
    max_lvl: int = 9
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="mystery_meat", chance=0.167, max_global=0),
    ]


class Slime(MobEntity):
    name: str = "Slime"
    defense_verb: str = "blocked"
    hp: int = 20
    max_hp: int = 20
    attack_skill: int = 12
    defense_skill: int = 5
    damage_min: int = 2
    damage_max: int = 5
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 4
    max_lvl: int = 9
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="tier2_weapon", chance=0.2, max_global=1),
    ]

    def take_damage(self, amount: int):
        if amount > 5:
            amount = 4 + int((math.sqrt(8 * (amount - 4) + 1) - 1) / 2)
        return super().take_damage(amount)


# ---------------------------------------------------------------------------
# Rare Alt Enemies (2% chance to replace a normal spawn)
# ---------------------------------------------------------------------------

class AlbinoRat(MobEntity):
    name: str = "Albino Rat"
    hp: int = 12
    max_hp: int = 12
    attack_skill: int = 8
    defense_skill: int = 2
    damage_min: int = 1
    damage_max: int = 4
    dr_min: int = 0
    dr_max: int = 1
    exp: int = 2
    max_lvl: int = 7
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="mystery_meat", chance=1.0, max_global=0),
    ]

    def attack_proc(self, target: "Entity"):
        if random.random() < 0.5:
            from app.engine.game.bleeding import apply_bleeding
            apply_bleeding(target, normal_float(2, 3))


class GnollExile(MobEntity):
    name: str = "Gnoll Exile"
    melee_reach: ClassVar[int] = 2
    defense_verb: str = "blocked"
    hp: int = 24
    max_hp: int = 24
    attack_skill: int = 15
    defense_skill: int = 6
    damage_min: int = 1
    damage_max: int = 10
    dr_min: int = 0
    dr_max: int = 1
    exp: int = 5
    max_lvl: int = 10
    ai_state: str = "passive"
    attack_range: int = 2
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="weapon", chance=0.5, max_global=0),
        DropEntry(item_kind="armor", chance=0.5, max_global=0),
        DropEntry(item_kind="potion", chance=0.5, max_global=0),
        DropEntry(item_kind="gold", chance=0.8, max_global=0),
    ]


class HermitCrab(MobEntity):
    name: str = "Hermit Crab"
    defense_verb: str = "blocked"
    hp: int = 25
    max_hp: int = 25
    attack_skill: int = 12
    defense_skill: int = 5
    damage_min: int = 1
    damage_max: int = 7
    dr_min: int = 2
    dr_max: int = 6
    speed: float = 1.0
    exp: int = 5
    max_lvl: int = 10
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="armor", chance=1.0, max_global=0),
        DropEntry(item_kind="mystery_meat", chance=0.5, max_global=0),
    ]


class CausticSlime(MobEntity):
    name: str = "Caustic Slime"
    defense_verb: str = "blocked"
    hp: int = 20
    max_hp: int = 20
    attack_skill: int = 12
    defense_skill: int = 5
    damage_min: int = 2
    damage_max: int = 5
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 5
    max_lvl: int = 10
    properties: List[str] = ["ACIDIC"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="goo_blob", chance=1.0, max_global=0),
    ]

    def attack_proc(self, target: "Entity"):
        if random.random() < 0.5:
            target.ooze_amount = 1


class Goo(MobEntity):
    # Stats mirror the original single-player Goo (Goo.java): 100 HP, attack 10
    # (15 enraged), damage 1-8 (1-12 enraged), DR 0-2. Enrage, water-heal and the
    # pumped-up charge are driven by GameInstance._update_goo / _process_bleed_ooze.
    type: str = "boss"
    name: str = "Goo"
    defense_verb: str = "blocked"
    hp: int = 100
    max_hp: int = 100
    attack_skill: int = 10
    defense_skill: int = 8
    damage_min: int = 1
    damage_max: int = 8
    dr_min: int = 0
    dr_max: int = 2
    speed: float = 1.0
    exp: int = 10
    max_lvl: int = 15
    # Paces both Goo's melee swing and each beat of the pumped-up charge.
    attack_cooldown: float = 1.5

    # Runtime boss state (serialized via model_dump so the client can render the
    # charge telegraph / pump animation, and so it survives reconnects).
    pumped_up: int = 0            # 0 idle, 1 charging, 2 ready to release
    heal_inc: int = 1            # water-heal ramp (SPD Goo.healInc)
    heal_cooldown: int = 0       # ticks until the next water-heal application
    enraged_announced: bool = False
    fight_started: bool = False  # one-shot: fires GOO_FIGHT_STARTED on first notice

    # 2-4 goo blobs on death: SPD's Random.chances({0,0,6,3,1}) -> 60% chance of
    # 2, 30% of 3, 10% of 4 (avg 2.5). The boss-floor key is dropped separately
    # (see GameInstance.handle_boss_death) because it needs the floor-specific
    # lock id.
    weighted_drops: List[WeightedCountDrop] = [
        WeightedCountDrop(item_kind="goo_blob", weights=[6, 3, 1], base_count=2),
    ]

    def is_enraged(self) -> bool:
        # SPD: Goo enrages once at or below half health (HP*2 <= HT).
        return self.hp * 2 <= self.max_hp

    def get_damage_min(self) -> int:
        return 1

    def get_damage_max(self) -> int:
        return 12 if self.is_enraged() else 8

    def get_effective_defense_skill(self) -> int:
        base = self.defense_skill
        if self.is_enraged():
            base = int(base * 1.5)
        # Staggered characters lose 1 point of evasion.
        if self.has_buff("stagger"):
            base -= 1
        return base

    def attack_proc(self, target: "Entity") -> None:
        # 1/3 chance to coat the target in caustic ooze (SPD Goo.attackProc).
        if random.randint(0, 2) == 0:
            target.ooze_amount = OOZE_DURATION
