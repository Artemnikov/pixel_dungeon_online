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
"""World interaction for GameInstance: searching, locked doors, and traps.

Reveals hidden doors/traps around a searching player, consumes keys to open
locked doors, and resolves trap triggers when a player steps onto one.

Mob-death handling lives in mob_death.py, NPC shop/quest-reward economy in
npc_economy.py -- this file used to hold all three; split apart since they
were unrelated concerns bundled under one 1300-line mixin.
"""

import time
from typing import Callable, Dict, List

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction
from app.engine.entities.player import CharacterClass, Player, hurt_warning_sound
from app.engine.game.floor_state import FloorState
from app.engine.game.constants import KEY_TIME_TO_UNLOCK

_FIRE_CARDINALS = [(0, -1), (1, 0), (0, 1), (-1, 0)]
_ELECTRIC_CARDINALS = [(0, -1), (1, 0), (0, 1), (-1, 0)]


def _electric_reachable_cells(floor: FloorState, cx: int, cy: int, max_dist: int):
    """BFS returning set of (x,y) reachable within max_dist cardinal steps, avoiding solids."""
    from collections import deque
    visited = {(cx, cy)}
    q = deque([(cx, cy, 0)])
    while q:
        x, y, d = q.popleft()
        if d >= max_dist:
            continue
        for dx, dy in _ELECTRIC_CARDINALS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                if (nx, ny) not in visited and not floor.flags.solid[ny][nx]:
                    visited.add((nx, ny))
                    q.append((nx, ny, d + 1))
    return visited


def _spawn_trap_electricity(floor: FloorState, cx: int, cy: int, radius: int, strength: int) -> None:
    """Seed an electricity blob covering all cells within radius.
    radius=1 uses square (NEIGHBOURS9 matching SPD); radius>1 uses BFS pathfinding."""
    blob_id = f"electric_trap_{cx}_{cy}"
    cells = set()
    volume = {}
    if radius <= 1:
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    if floor.flags and not floor.flags.solid[ny][nx]:
                        cells.add((nx, ny))
                        volume[(nx, ny)] = strength
    else:
        for nx, ny in _electric_reachable_cells(floor, cx, cy, radius):
            cells.add((nx, ny))
            volume[(nx, ny)] = strength
    if cells:
        floor.blob_areas[blob_id] = {"type": "electricity", "cells": cells, "volume": volume}


def _spawn_trap_fire(floor: FloorState, cx: int, cy: int, radius: int, strength: int) -> None:
    blob_id = f"fire_trap_{cx}_{cy}"
    cells = set()
    volume = {}
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                tile = floor.grid[ny][nx]
                if tile == TileType.FLOOR_WATER:
                    continue
                can_burn = (floor.flags.flamable[ny][nx] if floor.flags else False)
                can_burn = can_burn or tile in (TileType.FLOOR, TileType.EMPTY_DECO)
                if can_burn or tile not in (TileType.WALL, TileType.VOID):
                    cells.add((nx, ny))
                    volume[(nx, ny)] = strength
    if cells:
        floor.blob_areas[blob_id] = {"type": "fire", "cells": cells, "volume": volume}


def _spawn_blazing_trap_fire(floor: FloorState, cx: int, cy: int) -> None:
    blob_id = f"blazing_trap_{cx}_{cy}"
    cells = set()
    volume = {}
    visited = set()
    queue = [(cx, cy, 0)]
    while queue:
        nx, ny, dist = queue.pop(0)
        if (nx, ny) in visited or dist > 2:
            continue
        visited.add((nx, ny))
        if not (0 <= nx < floor.width and 0 <= ny < floor.height):
            continue
        tile = floor.grid[ny][nx]
        if tile in (TileType.WALL, TileType.VOID, TileType.FLOOR_WATER):
            continue
        if dist > 0:
            cells.add((nx, ny))
            volume[(nx, ny)] = 5
        for dx, dy in _FIRE_CARDINALS:
            queue.append((nx + dx, ny + dy, dist + 1))
    if cells:
        floor.blob_areas[blob_id] = {"type": "fire", "cells": cells, "volume": volume}

# --- Trap handlers, dispatched by _trigger_trap_if_needed ------------------
# Each handler returns (damage, dealt) for the common MAP_PATCH/TRAP_TRIGGERED/
# DAMAGE epilogue, or None if it already fully handled its own event emission
# and outcome (pitfall_trap's hero-fall path -- see its docstring).

def _trap_tengu_dart(game, floor, player, floor_id, is_player, patches):
    damage = 8
    dealt = player.take_damage(damage)
    from app.engine.entities.buffs import add_buff
    add_buff(player.buffs, "poison", duration=8.0, level=1, stack_mode="extend")
    if is_player:
        game.boss_scores[1] -= 100
        game.qualified_for_boss_challenge = False
    return damage, dealt


def _trap_burning(game, floor, player, floor_id, is_player, patches):
    _spawn_trap_fire(floor, player.pos.x, player.pos.y, 2, 2)
    game.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
    return 0, 0


def _trap_blazing(game, floor, player, floor_id, is_player, patches):
    _spawn_blazing_trap_fire(floor, player.pos.x, player.pos.y)
    game.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
    return 0, 0


def _trap_shocking(game, floor, player, floor_id, is_player, patches):
    _spawn_trap_electricity(floor, player.pos.x, player.pos.y, 1, 10)
    game.add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=floor_id)
    return 0, 0


def _trap_storm(game, floor, player, floor_id, is_player, patches):
    _spawn_trap_electricity(floor, player.pos.x, player.pos.y, 2, 20)
    game.add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=floor_id)
    return 0, 0


def _trap_toxic(game, floor, player, floor_id, is_player, patches):
    from app.engine.game.terrain_effects import _create_gas
    _create_gas(floor, (player.pos.x, player.pos.y), 4 + floor_id // 3, "toxic_gas")
    game.add_event("PLAY_SOUND", {"sound": "GAS"}, floor_id=floor_id)
    return 0, 0


def _trap_poison_dart(game, floor, player, floor_id, is_player, patches):
    from app.engine.entities.buffs import add_buff
    from app.engine.game.terrain_effects import _create_gas
    add_buff(player.buffs, "poison", duration=10.0, level=1, stack_mode="extend")
    _create_gas(floor, (player.pos.x, player.pos.y), 2, "toxic_gas")
    game.add_event("PLAY_SOUND", {"sound": "GAS"}, floor_id=floor_id)
    return 0, 0


def _trap_chilling(game, floor, player, floor_id, is_player, patches):
    from app.engine.game.terrain_effects import _freeze_area
    _freeze_area(floor, (player.pos.x, player.pos.y))
    player.add_buff("chilled", duration=5.0, level=1, stack_mode="extend")
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
    return 0, 0


def _trap_frost(game, floor, player, floor_id, is_player, patches):
    from app.engine.game.terrain_effects import _freeze_area
    _freeze_area(floor, (player.pos.x, player.pos.y))
    player.add_buff("frozen", duration=5.0, level=1, stack_mode="extend")
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
    return 0, 0


def _trap_confusion(game, floor, player, floor_id, is_player, patches):
    player.add_buff("vertigo", duration=5.0, level=1, stack_mode="replace")
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
    return 0, 0


def _trap_ooze(game, floor, player, floor_id, is_player, patches):
    player.add_buff("ooze", duration=10.0, level=1, stack_mode="extend")
    return 0, 0


def _trap_corrosion(game, floor, player, floor_id, is_player, patches):
    from app.engine.game.terrain_effects import _create_gas
    _create_gas(floor, (player.pos.x, player.pos.y), 1 + floor_id // 4, "corrosive_gas")
    game.add_event("PLAY_SOUND", {"sound": "GAS"}, floor_id=floor_id)
    return 0, 0


def _trap_flock(game, floor, player, floor_id, is_player, patches):
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
    return 0, 0


def _trap_weakening(game, floor, player, floor_id, is_player, patches):
    player.add_buff("weakness", duration=10.0, level=1, stack_mode="extend")
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
    return 0, 0


def _trap_gripping(game, floor, player, floor_id, is_player, patches):
    _spawn_trap_fire(floor, player.pos.x, player.pos.y, 1, 1)
    game.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
    return 0, 0


def _trap_geyser(game, floor, player, floor_id, is_player, patches):
    _spawn_trap_electricity(floor, player.pos.x, player.pos.y, 1, 5)
    game.add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=floor_id)
    return 0, 0


def _trap_explosive(game, floor, player, floor_id, is_player, patches):
    damage = max(1, player.hp // 6)
    dealt = player.take_damage(damage)
    game.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)
    blast_cells = []
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            blast_cells.append([player.pos.x + ox, player.pos.y + oy])
    game.add_event("BOMB_BLAST", {
        "x": player.pos.x, "y": player.pos.y,
        "kind": "bomb", "cells": blast_cells,
    }, floor_id=floor_id)
    game.add_event("SCREEN_SHAKE", {"intensity": 2, "duration_ms": 300},
                   floor_id=floor_id)
    return damage, dealt


def _trap_pitfall(game, floor, player, floor_id, is_player, patches):
    """SPD PitfallTrap: opens a 3x3 pit around the trap cell; mobs on those
    cells fall to their death (Chasm.mobFall) and the hero falls to the next
    floor (Chasm.heroFall). No-op on boss floors or beyond depth 25 (SPD:
    "the ground is too solid").

    Returns None instead of a (damage, dealt) pair when the hero-fall path
    already fully handled its own event emission and outcome: it must emit
    TRAP_TRIGGERED itself before the fall moves the player to the next floor
    (after which floor_id is stale), so _trigger_trap_if_needed's common
    epilogue has to be skipped entirely in that case.
    """
    from app.engine.dungeon.spd_levelgen.run_state import is_boss_level
    from app.engine.game.constants import MAX_FLOOR_ID
    dealt = 0
    if is_boss_level(floor_id) or floor_id > 25 or floor_id >= MAX_FLOOR_ID:
        # Too solid — trap triggers but no pit opens.
        if is_player:
            game.add_event("MESSAGE",
                {"text": "The ground is too solid for a pitfall trap to work here."},
                player_id=player.id)
        return 0, dealt

    # PitfallParticle burst on the 3x3 around the trap cell.
    pit_cells = []
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            cx, cy = player.pos.x + ox, player.pos.y + oy
            if 0 <= cx < floor.width and 0 <= cy < floor.height:
                if floor.flags and floor.flags.passable[cy][cx]:
                    pit_cells.append((cx, cy))
    # Emit VFX for the pit opening (reuses LEAF_BURST-style per-cell
    # particle spawn; the client renders a dust/earth burst).
    for cx, cy in pit_cells:
        game.add_event("LEAF_BURST", {"x": cx, "y": cy}, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)

    # Mobs on pit cells fall to their death (Chasm.mobFall).
    for cx, cy in pit_cells:
        for mob in list(floor.mobs.values()):
            if mob.is_alive and mob.pos.x == cx and mob.pos.y == cy:
                if not mob.flying and mob.faction != Faction.PLAYER:
                    mob.is_alive = False
                    game.add_event("MOB_CHASM_FALL",
                        {"mob": mob.id, "x": cx, "y": cy},
                        floor_id=floor_id)
                    # DEATH event so the client's death animation
                    # triggers alongside the fall VFX.
                    game.add_event("DEATH", {"target": mob.id},
                        floor_id=floor_id)
                    game.handle_mob_death(mob, floor, floor_id)

    # Hero falls last (SPD: "process hero falling last").
    if is_player and not player.has_buff("levitation"):
        # Emit TRAP_TRIGGERED before the fall moves the player to
        # the next floor (after which floor_id is stale).
        if patches:
            game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)
        game.add_event("TRAP_TRIGGERED",
            {"player": player.id, "trap": "pitfall_trap", "damage": 0,
             "x": player.pos.x, "y": player.pos.y},
            floor_id=floor_id)
        game._perform_chasm_fall(player, floor_id, player.pos.x, player.pos.y)
        return None
    # Non-player entity falls to death in the pit.
    elif not is_player and not player.has_buff("levitation"):
        player.is_alive = False
        game.add_event("MOB_CHASM_FALL",
            {"mob": player.id, "x": player.pos.x, "y": player.pos.y},
            floor_id=floor_id)
        game.add_event("DEATH", {"target": player.id}, floor_id=floor_id)
        game.handle_mob_death(player, floor, floor_id)
    return 0, dealt


_TRAP_HANDLERS: Dict[str, Callable] = {
    "tengu_dart": _trap_tengu_dart,
    "burning_trap": _trap_burning,
    "blazing_trap": _trap_blazing,
    "shocking_trap": _trap_shocking,
    "storm_trap": _trap_storm,
    "toxic_trap": _trap_toxic,
    "poison_dart_trap": _trap_poison_dart,
    "chilling_trap": _trap_chilling,
    "frost_trap": _trap_frost,
    "confusion_trap": _trap_confusion,
    "ooze_trap": _trap_ooze,
    "corrosion_trap": _trap_corrosion,
    "flock_trap": _trap_flock,
    "weakening_trap": _trap_weakening,
    "gripping_trap": _trap_gripping,
    "geyser_trap": _trap_geyser,
    "explosive_trap": _trap_explosive,
    "pitfall_trap": _trap_pitfall,
}




class WorldInteractionMixin:
    def search(self, player_id: str):
        player = self.players.get(player_id)
        if not player:
            return

        floor = self._get_or_create_floor(player.floor_id)
        patches: List[dict] = []
        # Every in-bounds cell scanned this search, so the client can sweep a
        # CheckedCell ring over the whole radius (mirrors the original drawing a
        # CheckedCell on each cell in range, not only the ones that revealed something).
        checked: List[List[int]] = []
        found_secret = False

        wide_search = player.subclass_info.talent_info.level("wide_search")
        distance = 2 if player.class_type == CharacterClass.ROGUE else 1
        circular = False
        if wide_search > 0:
            distance += 1
            circular = wide_search == 1

        for dy in range(-distance, distance + 1):
            for dx in range(-distance, distance + 1):
                if dx == 0 and dy == 0:
                    continue
                if circular and dx * dx + dy * dy > distance * distance:
                    continue
                tx = player.pos.x + dx
                ty = player.pos.y + dy
                if not (0 <= tx < floor.width and 0 <= ty < floor.height):
                    continue

                checked.append([tx, ty])
                pos = (tx, ty)
                if pos in floor.hidden_doors:
                    actual_tile = floor.hidden_doors.pop(pos)
                    floor.grid[ty][tx] = actual_tile
                    patches.append({"x": tx, "y": ty, "tile": actual_tile})
                    found_secret = True

                trap = floor.traps.get(pos)
                if trap and trap.hidden and trap.can_be_searched:
                    trap.hidden = False
                    found_secret = True
                    if floor.grid[ty][tx] == TileType.SECRET_TRAP:
                        floor.grid[ty][tx] = TileType.TRAP
                        patches.append({"x": tx, "y": ty, "tile": TileType.TRAP})

        if patches:
            # Tile mutations changed the grid — refresh derived flag maps
            # so LOS / pathfinding / openSpace pick up the new state on
            # the next query (a revealed door is now passable + see-through).
            floor.rebuild_flags()
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=player.floor_id)

        # Original plays the SECRET sound whenever a door OR a trap is revealed.
        if found_secret:
            self.add_event("PLAY_SOUND", {"sound": "SECRET"}, player_id=player_id)

        # Searcher-only: drives the operate (hand-raise) animation + the cyan ring
        # sweep on the searching client. x/y is the hero position the rings emanate from.
        self.add_event(
            "SEARCH",
            {
                "player": player_id,
                "x": player.pos.x,
                "y": player.pos.y,
                "cells": checked,
                "revealed_tiles": len(patches),
            },
            player_id=player_id,
        )

    def _try_unlock_locked_door(self, player: Player, floor: FloorState, x: int, y: int) -> bool:
        key_id = floor.locked_doors.get((x, y))
        if not key_id:
            return False

        # Tengu cell entrance: any player may pass freely once fight starts.
        if key_id != "tengu_boss" and not player.remove_key(key_id, floor.floor_id):
            self.add_event("LOCKED", {"player": player.id, "x": x, "y": y}, floor_id=player.floor_id)
            return False

        floor.locked_doors.pop((x, y), None)
        tile = floor.grid[y][x]
        if tile == TileType.LOCKED_EXIT or key_id == "goo_door":
            new_tile = TileType.STAIRS_DOWN
        elif tile == TileType.CRYSTAL_DOOR:
            new_tile = TileType.FLOOR
        else:
            new_tile = TileType.DOOR
        floor.grid[y][x] = new_tile
        # Tile mutated from LOCKED_DOOR to DOOR/STAIRS_DOWN — refresh flag maps
        # so LOS/pathfinding sees the door as passable now.
        floor.rebuild_flags()

        self.add_event("MAP_PATCH", {"tiles": [{"x": x, "y": y, "tile": new_tile}]}, floor_id=player.floor_id)
        self.add_event("UNLOCK", {"player": player.id, "x": x, "y": y}, floor_id=player.floor_id)
        if tile == TileType.CRYSTAL_DOOR:
            self.add_event("PLAY_SOUND", {"sound": "TELEPORT"}, floor_id=player.floor_id)
        else:
            self.add_event("PLAY_SOUND", {"sound": "UNLOCK"}, floor_id=player.floor_id)
        player.action_until = max(player.action_until, time.time() + KEY_TIME_TO_UNLOCK)
        return True

    def _trigger_trap_if_needed(self, floor: FloorState, player, floor_id: int):
        from app.engine.entities.base import Entity as _Entity
        if player.has_buff("levitation"):
            return
        pos = (player.pos.x, player.pos.y)
        trap = floor.traps.get(pos)
        if not trap or not trap.active:
            return

        is_player = isinstance(player, Player)
        patches: List[dict] = []
        if trap.hidden:
            trap.hidden = False

        # Any trap tile -> INACTIVE_TRAP on trigger
        tile = floor.grid[player.pos.y][player.pos.x]
        if tile in (TileType.SECRET_TRAP, TileType.TRAP):
            floor.grid[player.pos.y][player.pos.x] = TileType.INACTIVE_TRAP
            patches.append({"x": player.pos.x, "y": player.pos.y, "tile": TileType.INACTIVE_TRAP})

        trap.active = False

        handler = _TRAP_HANDLERS.get(trap.trap_type)
        if handler is not None:
            result = handler(self, floor, player, floor_id, is_player, patches)
            if result is None:
                return
            damage, dealt = result
        else:
            damage = 2
            dealt = player.take_damage(damage)

        if patches:
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)

        self.add_event(
            "TRAP_TRIGGERED",
            {"player": player.id, "trap": trap.trap_type, "damage": dealt,
             "x": player.pos.x, "y": player.pos.y},
            floor_id=floor_id,
        )
        if dealt > 0:
            self.add_event("DAMAGE", {"target": player.id, "amount": dealt}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id, source_player_id=player.id if is_player else None)
            if is_player:
                warn_sound = hurt_warning_sound(dealt, player.hp, player.get_total_max_hp())
                if warn_sound:
                    self.add_event("PLAY_SOUND", {"sound": warn_sound}, player_id=player.id)

