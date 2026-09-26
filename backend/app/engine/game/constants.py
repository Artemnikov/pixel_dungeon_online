# Copyright (C) 2026 ArtemNikov
#
"""Module-level gameplay constants for the game engine.

Extracted from manager.py so the per-concern mixin modules can import them
without pulling in the whole GameInstance. manager.py re-exports these for
backward-compatible imports.
"""

import os

MAX_FLOOR_ID = 26
SEWERS_MAX_FLOOR = 4
PRISON_MAX_FLOOR = 9

# Base server tick rate (Hz). Reads from env or defaults to 40.0 Hz.
GAME_LOOP_HZ: float = float(os.environ.get("GAME_LOOP_HZ", "40.0"))
TICK_DURATION: float = 1.0 / GAME_LOOP_HZ  # dt per tick in seconds (e.g. 0.025 at 40Hz)
TARGET_TICK_INTERVAL: float = TICK_DURATION

# Movement pacing derived from tick rate
AUTO_MOVE_INTERVAL = 0.15  # real seconds per tile at base speed
BASE_STEP_TICKS = max(1, int(round(AUTO_MOVE_INTERVAL * GAME_LOOP_HZ)))  # ticks per step (e.g. 6 at 40Hz)
MAX_PLAYER_INPUT_QUEUE = 8
KEY_TIME_TO_UNLOCK = 0.5

# Real-time surprise-attack window: when a mob loses LOS on a player and the
# player then reappears in its FOV, the player's strikes count as surprise
# attacks (auto-hit + crit) for this long (SPD's stale-enemySeen window made
# explicit for the real-time loop).
SURPRISE_WINDOW_SECONDS = 2.0

# How many consecutive blocked steps a queued MOVE_TO path tolerates (a mob
# briefly standing on the next tile) before giving up on the route.
PATH_BLOCKED_GIVE_UP_TICKS = 6

GAME_TURN_TICKS = int(round(GAME_LOOP_HZ * 1.0))  # ticks per game turn (e.g. 40 at 40Hz)
HEAL_TICK_INTERVAL = GAME_TURN_TICKS              # 1 turn (~1s at 40Hz) between heal ticks
PASSIVE_REGEN_INTERVAL = max(1, int(round(0.5 * GAME_LOOP_HZ)))  # ~0.5s regen tick

REST_HEAL_INTERVAL = 3.0                          # real seconds for rest healing
REST_STILL_TICKS = int(round(2.0 * GAME_LOOP_HZ)) # ticks of stillness before rest regen (~2s)
REST_ENEMY_RADIUS = 5

# Nourished buff (from eating any food): while active, rest healing is
# multiplied by NOURISHED_HEAL_BOOST, and healing also ticks during combat at
# NOURISHED_COMBAT_HEAL_FRACTION of the base rate. Duration scales with the
# food's energy value (seconds = energy * NOURISHED_DURATION_PER_ENERGY).
NOURISHED_HEAL_BOOST = 2.0
NOURISHED_COMBAT_HEAL_FRACTION = 0.5
NOURISHED_DURATION_PER_ENERGY = 0.2

# Scroll of Recharging aftereffect: each second the buff is active, every
# wand gains RECHARGE_BUFF_BONUS * min(1, buff.remaining) charge (SPD
# Wand.Charger.CHARGE_BUFF_BONUS * Recharging.remainder(), 30-turn buff).
RECHARGE_BUFF_BONUS = 0.25

# Caustic ooze (SPD Ooze): DURATION=20 turns, ~1 dmg/turn vs the depth-5 Goo,
# washed off by stepping into water. Ticks are throttled so the real-time loop
# applies roughly one point of damage per in-game "turn".
OOZE_DURATION = 20
OOZE_TICK_INTERVAL = GAME_TURN_TICKS              # ticks (~1s at 40Hz) between ooze damage applications

# Goo water-heal cadence: ticks between each +heal_inc while standing in water.
GOO_WATER_HEAL_INTERVAL = GAME_TURN_TICKS         # ~1s at 40Hz

# Respawn timer: scales with floor depth and tick rate.
RESPAWN_TURNS = int(round(2.5 * GAME_LOOP_HZ))   # base mob respawn (~2.5s)
RESPAWN_TURNS_FLOOR_SCALE = max(1, int(round(0.15 * GAME_LOOP_HZ)))  # extra ticks per floor depth
MOB_LIMIT_MAX = 12              # cap on per-floor mob limit
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
ITEM_RESPAWN_TURNS = int(round(5.0 * GAME_LOOP_HZ))        # ticks between item respawn waves (~5s)
ITEM_RESPAWN_BASE_COUNT = 2       # base items per wave
ITEM_RESPAWN_PLAYER_BONUS = 1     # extra items per active player
BOSS_RESPAWN_TICKS = int(round(30.0 * GAME_LOOP_HZ))       # ticks before a dead boss respawns (~30s)
CHEST_RESPAWN_TICKS = int(round(20.0 * GAME_LOOP_HZ))      # ticks before a looted chest respawns (~20s)
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


# Game loop runs at GAME_LOOP_HZ ticks/sec (see main.py::global_game_loop); several
# cooldowns are authored in turns and converted to ticks via this factor.
TICKS_PER_TURN = GAME_TURN_TICKS

# Gas/fog tick interval: one gas cloud update per game turn (~1s).
GAS_TICK_INTERVAL = GAME_TURN_TICKS

# Game modes and turn-based scheduler constants.
GAME_MODE_REALTIME = "realtime"
GAME_MODE_TURNBASED = "turnbased"
DEFAULT_TURN_TIMER_SECONDS = 60.0
# Upper bound on actor turns drained inside one 40Hz tick. A long mob cascade
# yields after this many steps so the tick can broadcast and give the event loop
# back; the next tick resumes from where it stopped.
MAX_TURN_STEPS_PER_TICK = 240
# How many upcoming actor ids ride along in the per-viewer turn payload.
TURN_ORDER_PREVIEW = 8

# SPD Actor.spendConstant rounds `time` to a whole number when it lands within
# this distance of one, absorbing float drift (Actor.java:64-67).
TURN_TIME_EPSILON = 0.001

# SPD actor scheduling priorities (Actor.java:45-50). Higher acts first on a
# time tie; positive is before the hero, negative after.
HERO_PRIO = 0
MOB_PRIO = -20

# --- SPD turn costs -------------------------------------------------------
# Action costs in SPD time units, ported from the Java source. One unit is one
# hero turn; a move costs 1/speed so a speed-1.3 mob acts twice per hero turn.

# Char.move(): `c.spend(1 / c.speed())` -- actors/Char.java:298
TIME_TO_MOVE_BASE = 1.0
# Mob/Hero.onAttackComplete(): `spend(attackDelay())`, 1f, /1.5 under Adrenaline
# -- actors/mobs/Mob.java:678, actors/hero/Hero.java:2325
TIME_TO_ATTACK = 1.0
# Hero.TIME_TO_SEARCH -- actors/hero/Hero.java:204
TIME_TO_SEARCH = 2.0
# Hero.TIME_TO_REST -- actors/hero/Hero.java:203
TIME_TO_REST = 1.0
# Item.TIME_TO_PICK_UP / TIME_TO_DROP / TIME_TO_THROW -- items/Item.java:66-68
TIME_TO_PICK_UP = 1.0
TIME_TO_DROP = 1.0
TIME_TO_THROW = 1.0
# Scroll.TIME_TO_READ -- items/scrolls/Scroll.java:71
TIME_TO_READ = 1.0
# Potion.TIME_TO_DRINK -- items/potions/Potion.java:88
TIME_TO_DRINK = 1.0
# Food.TIME_TO_EAT -- items/food/Food.java:47
TIME_TO_EAT = 3.0
# Wand.TIME_TO_ZAP -- items/wands/Wand.java:80
TIME_TO_ZAP = 1.0
# Key.TIME_TO_UNLOCK -- items/keys/Key.java:38
TIME_TO_UNLOCK = 1.0
# Torch.TIME_TO_LIGHT -- items/Torch.java:40
TIME_TO_LIGHT = 1.0
# Stylus.TIME_TO_INSCRIBE -- items/Stylus.java:43
TIME_TO_INSCRIBE = 2.0
# LloydsBeacon.TIME_TO_USE -- items/artifacts/LloydsBeacon.java:55
TIME_TO_ABILITY = 1.0
# Mob.TIME_TO_WAKE_UP -- actors/mobs/Mob.java:134
TIME_TO_WAKE_UP = 1.0
# Mob.TIME_TO_IDLE -- actors/mobs/Mob.java:133. Charged when a mob's act() has
# nothing to do: a sleeping mob, or one that can't reach its target this turn.
TIME_TO_IDLE = 1.0
# Port-only: SPD has no such constant -- burning a turn is Hero.rest() at
# TIME_TO_REST. Used for the turn-timer auto-wait and for the WAIT message.
TIME_TO_WAIT = TIME_TO_REST

