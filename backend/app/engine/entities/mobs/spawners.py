# Copyright (C) 2026 ArtemNikov
#
import math
import random
from typing import List

from pydantic import Field

from app.engine.entities.player import Mob as MobEntity, DropEntry

# ---------------------------------------------------------------------------
# Static Spawners
# ---------------------------------------------------------------------------

class DemonSpawner(MobEntity):
    """Immovable. Spawns RipperDemons periodically. DEMONIC+IMMOVABLE.
    HP=120, DR 0-12. loot=health_potion 100%. Passive until damaged."""
    name: str = "Demon Spawner"
    hp: int = 120
    max_hp: int = 120
    attack_skill: int = 0
    defense_skill: int = 0
    damage_min: int = 0
    damage_max: int = 0
    dr_min: int = 0
    dr_max: int = 12
    exp: int = 15
    max_lvl: int = 29
    properties: List[str] = ["DEMONIC", "INORGANIC", "IMMOVABLE", "MINIBOSS"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="health_potion", chance=1.0, max_global=0),
    ]

    # Runtime
    spawn_cooldown: int = 20
    first_spawn_done: bool = False


class Pylon(MobEntity):
    """Immovable. Fires lightning bolts when activated. ELECTRIC+INORGANIC+IMMOVABLE.
    HP=50 (normal) / 80 (challenge). Inactive until DM-300 fight begins."""
    name: str = "Pylon"
    hp: int = 50
    max_hp: int = 50
    attack_skill: int = 0
    defense_skill: int = 0
    damage_min: int = 10
    damage_max: int = 20
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    properties: List[str] = ["ELECTRIC", "INORGANIC", "IMMOVABLE", "MINIBOSS"]
    loot_table: List[DropEntry] = []

    # Runtime
    bolt_cooldown: int = 5
    linked_pylon_id: str = ""
    activated: bool = False
    # Pylon.targetNeighbor = Random.Int(8) at spawn.
    fire_target_idx: int = Field(default_factory=lambda: random.randint(0, 7))

    def take_damage(self, amount: int):
        # Immune to all damage while inactive (Pylon.isInvulnerable: alignment == NEUTRAL).
        if not self.activated:
            return 0
        if amount >= 15:
            amount = 14 + int((math.sqrt(8 * (amount - 14) + 1) - 1) / 2)
        return super().take_damage(amount)
