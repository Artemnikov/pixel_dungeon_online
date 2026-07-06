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
"""Sewers Ghost-quest content (Ghost.java + FetidRat/GnollTrickster/
GreatCrab.java): the wandering Ghost NPC (depths 2-4) and the three
depth-specific quest bosses it sends the player after. Kept in their own
file rather than mobs.py (already very large) since this is a single
self-contained feature.

Scoping notes (deliberate simplifications, not oversights):
  - FetidRat.defenseProc originally seeds a StenchGas (paralysis-gas cloud)
    blob when hit; this engine's gas-blob types are cosmetic-only today (no
    debuff application -- see blobs.py), so building that out is a separate,
    pre-existing gap. Substituted with a direct single-target paralysis
    application to the attacker, preserving "hitting this miniboss is
    risky" without rebuilding gas mechanics.
  - The custom per-mob Wandering/getCloser/canAttack overrides (closer-of-
    two-destinations wander bias, GreatCrab's 1-in-3 movement throttle,
    GnollTrickster's strict no-melee kiting) have no equivalent hook in this
    engine's AI loop (tick.py drives all mobs generically, with no per-mob
    movement-override mechanism) -- porting them would mean adding new
    shared AI infrastructure well beyond this feature's scope. GnollTrickster
    still never melees in practice via the existing generic `attack_range`
    field (same mechanism Shaman already uses); the wander-bias and
    movement-throttle flavor are dropped.
  - GreatCrab's melee block targets only its current `enemy` in the
    original; this engine doesn't persist a per-mob "current enemy" outside
    of the live AI tick (no reliable field to check), so the port blocks
    melee from any attacker while awake -- equivalent in single-player and a
    sensible multiplayer default.
"""

from __future__ import annotations

from typing import List

from app.engine.entities.base import Faction
from app.engine.entities.player import DropEntry, Mob as MobEntity, WeightedCountDrop
from app.engine.entities.mobs import Crab, Gnoll, Rat


class FetidRat(Rat):
    """FetidRat.java -- depth 2 quest boss."""

    name: str = "Fetid Rat"
    hp: int = 20
    max_hp: int = 20
    defense_skill: int = 5
    attack_skill: int = 12
    dr_min: int = 0
    dr_max: int = 3
    exp: int = 4
    properties: List[str] = ["DEMONIC"]

    def attack_proc(self, target) -> None:
        # FetidRat.attackProc(): 1/3 chance to ooze the target on a landed hit.
        import random
        from app.engine.game.constants import OOZE_DURATION
        if random.randint(0, 2) == 0:
            target.ooze_amount = OOZE_DURATION

    def defense_proc(self, damage: int, attacker, floor_mobs: dict, tile_x: int, tile_y: int) -> int:
        # Substitute for StenchGas-on-hit -- see module docstring.
        if attacker is not None:
            attacker.add_buff("paralysis", duration=2.0, level=1)
        return damage


class GnollTrickster(Gnoll):
    """GnollTrickster.java -- depth 3 quest boss."""

    name: str = "Gnoll Trickster"
    hp: int = 20
    max_hp: int = 20
    defense_skill: int = 5
    attack_skill: int = 16
    attack_range: int = 4  # never melees -- mirrors Shaman's ranged pattern
    exp: int = 5
    combo: int = 0

    def attack_proc(self, target) -> None:
        # GnollTrickster.attackProc(): combo escalates with consecutive hits;
        # effect > 2 poisons, effect >= 6 sets the target on fire instead.
        import random
        self.combo += 1
        effect = random.randint(0, 3) + self.combo
        if effect >= 6:
            target.add_buff("burning", duration=8.0, level=1, stack_mode="extend")
        elif effect > 2:
            target.add_buff("poison", duration=float(effect - 2), level=1, stack_mode="extend")


class GreatCrab(Crab):
    """GreatCrab.java -- depth 4 quest boss."""

    name: str = "Great Crab"
    hp: int = 25
    max_hp: int = 25
    defense_skill: int = 0  # see get_effective_defense_skill
    speed: float = 1.0
    exp: int = 6
    weighted_drops: List[WeightedCountDrop] = [
        WeightedCountDrop(item_kind="mystery_meat", weights=[1.0], base_count=2),
    ]

    def get_effective_defense_skill(self) -> int:
        # GreatCrab.defenseSkill(): blocks melee while awake & not paralyzed
        # (see module docstring for the "any attacker" simplification).
        if self.is_alive and self.ai_state != "sleeping" and not self.has_buff("paralysis"):
            return 10 ** 9
        return super().get_effective_defense_skill()

    def blocks_ranged_source(self, attacker) -> bool:
        # GreatCrab.damage(): negates direct wand/spell damage while awake,
        # not paralyzed, and the attacker isn't invisible. Checked by the
        # caller only when the source is a wand (see movement.py).
        if not self.is_alive or self.ai_state == "sleeping" or self.has_buff("paralysis"):
            return False
        return getattr(attacker, "invisible", 0) <= 0


class Ghost(MobEntity):
    """Ghost.java -- sewers wandering quest-giver NPC (depths 2-4). Flying,
    unattackable, undamageable; offers the FetidRat/GnollTrickster/GreatCrab
    side quest. Unlike Imp/RatKing/Shopkeeper it actively wanders rather than
    sleeping forever (never_wakes still prevents it from ever aggroing)."""

    name: str = "Ghost"
    type: str = "npc"
    faction: str = Faction.PLAYER
    hp: int = 1
    max_hp: int = 1
    attack_skill: int = 0
    defense_skill: int = 0
    damage_min: int = 0
    damage_max: int = 0
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    loot_table: List[DropEntry] = []
    flying: bool = True
    ai_state: str = "wandering"
    never_wakes: bool = True

    def take_damage(self, amount: int):
        # Ghost.damage(): does nothing -- immune to all damage.
        return 0

    def get_effective_defense_skill(self) -> int:
        # Ghost.defenseSkill(): INFINITE_EVASION -- always dodges.
        return 10 ** 9
