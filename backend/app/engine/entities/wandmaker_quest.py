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
"""Prison depths 6-9 Wandmaker-quest content (actors/mobs/npcs/Wandmaker.java
+ items/quest/CorpseDust.java's DustWraith): the stationary Wandmaker NPC and
the DustWraith it indirectly summons via the Corpse Dust quest variant. Kept
in their own file (mobs.py is already very large) since this is a single
self-contained feature, matching quest_bosses.py's precedent.

Scoping notes (deliberate simplifications, not oversights) -- phase 1 only
ports the Corpse Dust quest variant (of Wandmaker's 3: Corpse Dust/Ceremonial
Candle/Rotberry). See run_state.py's WandmakerQuestState docstring for how
the type roll still consumes RNG identically to vanilla even when it lands on
an unimplemented variant, to keep future floor generation byte-identical to
vanilla SPD for a given seed:
  - DustWraith.attack()'s atkCount score-penalty tracking (Statistics.
    questScores[1] -= 100 on a wraith's 2nd/3rd hit) is dropped -- this
    engine has no per-run score-breakdown system hooked up to mob subclasses
    elsewhere either (see WndScoreBreakdown.jsx for what does exist).
  - Wandmaker.add()/reset() (Java: reject all buffs, always "resets" cleanly
    on load) have no equivalent hook in this engine's buff/save system --
    skipped, same as RatKing/Shopkeeper/Imp before it.
"""

from __future__ import annotations

from typing import List

from app.engine.entities.base import Faction
from app.engine.entities.player import DropEntry, Mob as MobEntity
from app.engine.entities.mobs import Wraith


class Wandmaker(MobEntity):
    """Wandmaker.java -- stationary Prison quest-giver NPC. Immune to damage,
    infinite evasion, never wakes/attacks (mirrors Shopkeeper/Imp/RatKing)."""

    name: str = "Wandmaker"
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
    ai_state: str = "sleeping"
    never_wakes: bool = True
    properties: List[str] = ["IMMOVABLE"]

    def take_damage(self, amount: int):
        # Wandmaker.damage(): does nothing -- immune to all damage.
        return 0

    def get_effective_defense_skill(self) -> int:
        # Wandmaker.defenseSkill(): INFINITE_EVASION -- always dodges.
        return 10 ** 9


class DustWraith(Wraith):
    """CorpseDust.DustWraith -- periodically summoned near whoever holds the
    cursed Corpse Dust quest item (see tick.py's dust_ghost_spawner buff
    handling). Plain Wraith stats/behavior; see module docstring for the
    dropped atkCount score-penalty tracking."""

    name: str = "Dust Wraith"
