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
+ its 3 quest variants' mobs): the stationary Wandmaker NPC plus each
variant's mob(s). Kept in their own file (mobs.py is already very large)
since this is a single self-contained feature, matching quest_bosses.py's
precedent. Quest *items* live in wandmaker_quest_items.py, not here -- a
Mob subclass needs player.Mob, which (via item_union.py's Item discriminated
union) would create an import cycle with any item class defined alongside it.

Variants ported so far: Corpse Dust (phase 1: DustWraith; CorpseDust item
in items_consumable.py) and Rotberry (phase 2: RotHeart, RotLasher;
RotberrySeed item in wandmaker_quest_items.py). Ceremonial Candle (type 2)
is still deferred -- see run_state.py's WandmakerQuestState docstring for
how its RNG draw is still consumed even though it currently produces no
room, keeping future floor generation byte-identical to vanilla SPD for a
given seed regardless.

Scoping notes (deliberate simplifications, not oversights):
  - DustWraith.attack()'s atkCount score-penalty tracking, RotLasher.attack()'s
    same, and RotHeart/RotLasher's "die instantly to Burning regardless of
    remaining HP" damage() overrides are all dropped -- this engine has no
    per-run score-breakdown system hooked up to mob subclasses elsewhere
    either (see WndScoreBreakdown.jsx for what does exist), and no per-hit
    "damage source type" tag reaches take_damage() to special-case fire.
    Both mobs remain killable via normal combat regardless.
  - RotHeart.defenseProc() (spreads a ToxicGas cloud on every hit) is
    substituted with a direct poison application to the attacker -- this
    engine's gas blobs are cosmetic-only (no debuff application), the same
    pre-existing gap quest_bosses.py's FetidRat already works around.
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


class RotHeart(MobEntity):
    """RotHeart.java -- stationary Rotberry-quest miniboss guarding
    RotGardenRoom. PASSIVE ai_state (tick.py's generic handling: never
    attacks/chases while at full HP) plus IMMOVABLE (tick.py: never
    chases even once damaged) reproduce getCloser()==false / effectively-
    zero attack stats without any custom AI. Killable via normal combat;
    see module docstring for the dropped instant-death-to-fire shortcut."""

    name: str = "Rot Heart"
    hp: int = 80
    max_hp: int = 80
    attack_skill: int = 0
    defense_skill: int = 0
    damage_min: int = 0
    damage_max: int = 0
    dr_min: int = 0
    dr_max: int = 5
    exp: int = 4
    loot_table: List[DropEntry] = []
    ai_state: str = "passive"
    properties: List[str] = ["IMMOVABLE"]

    def defense_proc(self, damage: int, attacker, floor_mobs: dict, tile_x: int, tile_y: int) -> int:
        # RotHeart.defenseProc(): spreads ToxicGas on every hit taken --
        # substituted with a direct poison application (see module docstring).
        if attacker is not None:
            attacker.add_buff("poison", duration=3.0, level=1, stack_mode="extend")
        return damage


class RotLasher(MobEntity):
    """RotLasher.java -- stationary Rotberry-quest miniboss "vine lasher".
    IMMOVABLE (tick.py: never chases) + view_distance=1 approximates the
    Waiting.noticeEnemy() 1-tile detection radius via the existing generic
    wandering-detection code (see tick.py) rather than a custom AI mixin.
    Heals 5/turn while not adjacent to an enemy (tick.py); cripples on a
    landed hit (attack_proc, mirrors quest_bosses.py's established hook)."""

    name: str = "Rot Lasher"
    hp: int = 80
    max_hp: int = 80
    attack_skill: int = 25
    defense_skill: int = 0
    damage_min: int = 10
    damage_max: int = 20
    dr_min: int = 0
    dr_max: int = 8
    exp: int = 1
    view_distance: int = 1
    ai_state: str = "wandering"
    properties: List[str] = ["IMMOVABLE"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="seed", chance=0.75, max_global=0),
    ]

    def attack_proc(self, target) -> None:
        target.add_buff("cripple", duration=2.0, level=1)
