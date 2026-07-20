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
"""Module-level gameplay constants for the game engine.

Extracted from manager.py so the per-concern mixin modules can import them
without pulling in the whole GameInstance. manager.py re-exports these for
backward-compatible imports.
"""

MAX_FLOOR_ID = 26
SEWERS_MAX_FLOOR = 4
PRISON_MAX_FLOOR = 9

AUTO_MOVE_INTERVAL = 0.15
KEY_TIME_TO_UNLOCK = 1.0

# How many consecutive blocked steps a queued MOVE_TO path tolerates (a mob
# briefly standing on the next tile) before giving up on the route.
PATH_BLOCKED_GIVE_UP_TICKS = 6

GAME_TURN_TICKS = 20  # 20 game-loop ticks per game turn (at 20 Hz → 1 turn/sec)
HEAL_TICK_INTERVAL = 20
PASSIVE_REGEN_INTERVAL = 10

# Scroll of Recharging aftereffect: multiplier applied to passive wand regen
# rate while the "recharging" buff is active (SPD: Recharging buff speeds up
# wand charge regeneration for 30 turns).
RECHARGING_REGEN_MULTIPLIER = 3.0

# Caustic ooze (SPD Ooze): DURATION=20 turns, ~1 dmg/turn vs the depth-5 Goo,
# washed off by stepping into water. Ticks are throttled so the real-time loop
# applies roughly one point of damage per in-game "turn".
OOZE_DURATION = 20
OOZE_TICK_INTERVAL = 20  # ticks (~1s at 20Hz) between ooze damage applications

# Goo water-heal cadence: ticks between each +heal_inc while standing in water.
GOO_WATER_HEAL_INTERVAL = 20

# Respawn timer: 50 turns (ticks) base
RESPAWN_TURNS = 50
# Boss floors: only the boss respawns, no regular mobs/items/chests.
BOSS_FLOORS = {5, 10, 15, 20, 25}
# No respawns on floor 1 or boss floors.
NO_RESPAWN_FLOORS = {1} | BOSS_FLOORS

# In-place respawn (Easy and Medium difficulty): max resurrections per run,
# spawn-protection turns after each respawn (invulnerability window so a mob
# camping the stairs can't instantly re-kill the reborn hero).
RESPAWN_MAX_USES = 3
RESPAWN_SPAWN_PROTECTION_TURNS = 3

# Public-room-only: item replenishment and boss respawn.
PUBLIC_ROOM_ID = "public"
ITEM_RESPAWN_TURNS = 100          # ticks between item respawn waves (~5s at 20Hz)
ITEM_RESPAWN_BASE_COUNT = 2       # base items per wave
ITEM_RESPAWN_PLAYER_BONUS = 1     # extra items per active player
BOSS_RESPAWN_TICKS = 600          # ticks before a dead boss respawns (~30s)
CHEST_RESPAWN_TICKS = 400         # ticks before a looted chest respawns (~20s)
# Public room uses a faster mob respawn cadence.
PUBLIC_MOB_RESPAWN_SPEEDUP = 0.75  # multiplier on RESPAWN_TURNS (25% faster)

# Canvas seed size handed to the generator. The v2 generator resizes its canvas
# to fit the room layout, so each floor ends up a different size; these are only
# the starting bounds. Per-floor dimensions live on FloorState.width/height.
MAP_WIDTH = 60
MAP_HEIGHT = 40

# Party-size loot scaling (online-only, no SPD equivalent): potion/scroll
# drop rate scales linearly with co-op party size, from 1x solo to 3x at a
# 5-player party (+0.5x per player beyond the first).
PARTY_LOOT_MAX_PLAYERS = 5
PARTY_LOOT_STEP = 0.5


def party_loot_multiplier(player_count: int) -> float:
    n = max(1, min(PARTY_LOOT_MAX_PLAYERS, player_count))
    return 1.0 + PARTY_LOOT_STEP * (n - 1)
