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
"""Mob spawning/scaling on tick: floor-scaled stat rolls for universal extra
spawns, day/night-adjusted respawn rolls, and the cursed Corpse Dust ghost
spawner. `_universal_extra_pool` is imported back into tick.py for backward
compatible ``from app.engine.game.tick import _universal_extra_pool``.
"""

import random
import time
from typing import List, Type

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.buffs import get_buff
from app.engine.entities.items_consumable import CorpseDust
from app.engine.entities.mobs import Bee, CrystalMimic, EbonyMimic, MobEntity, Rat, TormentedSpirit, Wraith
from app.engine.entities.player import Player
from app.engine.entities.wandmaker_quest import DustWraith
from app.engine.game.constants import (
    BOSS_FLOORS, NO_RESPAWN_FLOORS, PRISON_MAX_FLOOR, PUBLIC_MOB_RESPAWN_SPEEDUP,
    PUBLIC_ROOM_ID, RESPAWN_TURNS, SEWERS_MAX_FLOOR,
)
from app.engine.game.floor_state import FloorState


def _apply_floor_scaling(mob: MobEntity, floor_id: int) -> None:
    level = floor_id
    if isinstance(mob, TormentedSpirit):
        attack = 10 + round(1.5 * level)
        mob.floor_level = level
        mob.attack_skill = attack
        mob.defense_skill = attack * 5
        mob.damage_min = 1 + (round(1.5 * level) // 2)
        mob.damage_max = 2 + round(1.5 * level)
    elif isinstance(mob, Wraith):
        attack = 10 + level
        mob.floor_level = level
        mob.attack_skill = attack
        mob.defense_skill = attack * 5
        mob.damage_min = 1 + level // 2
        mob.damage_max = 2 + level
    elif isinstance(mob, Bee):
        max_hp = (2 + level) * 4
        mob.floor_level = level
        mob.max_hp = max_hp
        mob.hp = max_hp
        mob.defense_skill = 9 + level
        mob.attack_skill = mob.defense_skill
        mob.damage_min = max(1, max_hp // 10)
        mob.damage_max = max(1, max_hp // 4)
    elif isinstance(mob, CrystalMimic):
        max_hp = (1 + level) * 6
        mob.floor_level = level
        mob.max_hp = max_hp
        mob.hp = max_hp
        mob.defense_skill = 2 + level // 2
        mob.attack_skill = 6 + level
        # CrystalMimic starts disguised; scaling doesn't reveal it
    elif isinstance(mob, EbonyMimic):
        max_hp = (1 + level) * 6
        mob.floor_level = level
        mob.max_hp = max_hp
        mob.hp = max_hp
        mob.defense_skill = 2 + level // 2
        mob.attack_skill = 6 + level
        mob.disguised = False


def _is_nighttime(game_start_time: float) -> bool:
    """SPD DayNight parity: first 60s always day, then cycles 120s day / 120s night."""
    elapsed = time.time() - game_start_time
    if elapsed < 60:
        return False
    cycle_time = (elapsed - 60) % 240
    return cycle_time >= 120


def _universal_extra_pool(floor_id: int) -> List[Type[MobEntity]]:
    extras: List[Type[MobEntity]] = [
        TormentedSpirit if random.random() < 0.01 else Wraith,
        Bee,
    ]
    if floor_id > 1:
        extras.append(EbonyMimic)
    return extras


class SpawnTickMixin:
    def _daynight_multiplier(self, player) -> float:
        from app.engine.entities.trinkets import DimensionalSundial as _DS
        from app.engine.entities.trinkets import trinket_level
        ds_lvl = trinket_level(player, "dimensional_sundial")
        if ds_lvl < 0:
            return 1.0
        if _is_nighttime(self.game_start_time):
            return _DS.nighttime_spawn_multiplier(ds_lvl)
        return _DS.daytime_spawn_multiplier(ds_lvl)

    def _process_respawns(self, floor_id: int, floor: FloorState, active_players: List[Player]):
        if floor_id in BOSS_FLOORS:
            return
        # Public room: floor 1 also respawns; tooms keep original behavior.
        is_public = self.game_id == PUBLIC_ROOM_ID
        if not is_public and floor_id in NO_RESPAWN_FLOORS:
            return
        live_mobs = sum(1 for m in floor.mobs.values() if m.is_alive)
        if live_mobs >= floor.mob_limit:
            floor.respawn_counter = 0
            return
        floor.respawn_counter += 1
        threshold = int(RESPAWN_TURNS * PUBLIC_MOB_RESPAWN_SPEEDUP) if is_public else RESPAWN_TURNS
        if floor.respawn_counter < threshold:
            return
        floor.respawn_counter = 0

        # DimensionalSundial: adjust respawn probability based on day/night
        if active_players:
            dn_mult = max(self._daynight_multiplier(active_players[0]), 0.25)
            if random.random() >= dn_mult:
                return

        universal_extra = random.random() < 0.01
        if universal_extra:
            cls = random.choice(_universal_extra_pool(floor_id))
        elif floor_id <= SEWERS_MAX_FLOOR:
            rotation = self._get_sewers_rotation(floor_id)
            cls = random.choice(rotation) if rotation else Rat
        elif floor_id <= PRISON_MAX_FLOOR:
            rotation = self._get_prison_rotation(floor_id)
            cls = random.choice(rotation) if rotation else Rat
        else:
            rotation = self._get_sewers_rotation(floor_id)
            cls = random.choice(rotation) if rotation else Rat
        floor_tiles = [
            (x, y) for y in range(floor.height) for x in range(floor.width)
            if floor.grid[y][x] in [TileType.FLOOR, TileType.FLOOR_WOOD, TileType.FLOOR_WATER, TileType.FLOOR_COBBLE, TileType.FLOOR_GRASS]
            and not any(m.pos.x == x and m.pos.y == y for m in floor.mobs.values() if m.is_alive)
        ]
        if not floor_tiles:
            return
        x, y = random.choice(floor_tiles)
        mob = self._spawn_mob_at(cls, x, y)
        if universal_extra:
            _apply_floor_scaling(mob, floor_id)
        floor.mobs[mob.id] = mob

    def _tick_dust_ghost_spawner(self, player: Player) -> None:
        """CorpseDust.DustGhostSpawner.act(): while the cursed Corpse Dust
        quest item is held, escalating "spawn power" periodically summons a
        DustWraith in the holder's FOV, at least view_distance/3 cells away.
        Buff.level doubles as the spawnPower counter (same repurposing the
        "bleeding" buff's level already uses above for its damage amount)."""
        dust_buff = get_buff(player.buffs, "dust_ghost_spawner")
        if dust_buff is None:
            return
        if not any(isinstance(i, CorpseDust) for i in player.inventory):
            dust_buff.level = 0
            return

        dust_buff.level += 1
        floor = self._get_or_create_floor(player.floor_id)
        wraiths = 1 + sum(1 for m in floor.mobs.values() if isinstance(m, DustWraith) and m.is_alive)
        power_needed = min(49, wraiths * wraiths)
        if power_needed > dust_buff.level:
            return

        view_dist = self._view_distance(player)
        fov = self._fov_from(player.pos, floor, view_dist, viewer_id=player.id)
        min_dist = round(view_dist / 3)
        occupied = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
        occupied |= {(p.pos.x, p.pos.y) for p in self._players_on_floor(player.floor_id) if p.is_alive}
        candidates = []
        for cell_idx, visible in enumerate(fov):
            if not visible:
                continue
            x, y = cell_idx % floor.width, cell_idx // floor.width
            if floor.flags and floor.flags.solid[y][x]:
                continue
            if (x, y) in occupied:
                continue
            if self._get_distance(player.pos, Position(x=x, y=y)) <= min_dist:
                continue
            candidates.append((x, y))

        if not candidates:
            # Prevents excessive spawn power buildup while no cell qualifies.
            dust_buff.level = min(dust_buff.level, 2 * wraiths)
            return

        x, y = random.choice(candidates)
        wraith = self._spawn_mob_at(DustWraith, x, y)
        wraith.ai_state = "hunting"
        _apply_floor_scaling(wraith, player.floor_id)
        floor.mobs[wraith.id] = wraith
        dust_buff.level -= power_needed
