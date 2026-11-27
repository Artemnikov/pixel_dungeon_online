# Copyright (C) 2026 ArtemNikov
#
"""Floor 10 (PrisonBossLevel / Tengu) state machine -- port of
PrisonBossLevel.java's `progress()`/`occupyCell()` transitions:
START -> FIGHT_START -> FIGHT_PAUSE -> FIGHT_ARENA -> WON.

Each transition rebuilds `floor.grid` from the hardcoded
`prison_boss_layout` variants and bumps `floor.map_version` so clients
re-fetch a fresh INIT for the floor (see `main.py`)."""

from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from app.engine.dungeon.constants import TileType, TrapType
from app.engine.dungeon.models import TrapInfo
from app.engine.dungeon.spd_levelgen import patch
from app.engine.dungeon.spd_levelgen import prison_boss_layout as layout
from app.engine.dungeon.spd_levelgen.geom import Point
from app.engine.dungeon.spd_random import SPDRandom
from app.engine.entities.base import Faction, Position
from app.engine.entities.mobs import Tengu
from app.engine.game.floor_state import FloorState
from app.engine.game.spd_adapter import _convert_tile

PRISON_BOSS_FLOOR = 10

_NEIGHBOURS8 = (
    (-1, -1), (0, -1), (1, -1),
    (-1, 0), (1, 0),
    (-1, 1), (0, 1), (1, 1),
)


def _grid_from_level(level) -> List[List[int]]:
    w, h = level.width(), level.height()
    return [[_convert_tile(level.map[y * w + x]) for x in range(w)] for y in range(h)]


def _apply_boss_challenge(tengu: Tengu, challenges) -> Tengu:
    """SPD Challenges.STRONGER_BOSSES: Tengu HP/HT 200 -> 250."""
    if "stronger_bosses" in challenges:
        tengu.max_hp = tengu.hp = 250
        tengu.hp_bracket = 7
    return tengu


class PrisonBossMixin:
    def _update_prison_boss(self, floor: FloorState, floor_id: int) -> None:
        if floor_id != PRISON_BOSS_FLOOR:
            return

        state = floor.tengu_state
        if state == "START":
            self._prison_boss_start_to_fight_start(floor, floor_id)
        elif state == "FIGHT_START":
            self._prison_boss_fight_start_to_pause(floor, floor_id)
        elif state == "FIGHT_PAUSE":
            self._prison_boss_pause_to_arena(floor, floor_id)
        elif state == "FIGHT_ARENA":
            self._prison_boss_arena_to_won(floor, floor_id)

    # -- helpers ----------------------------------------------------------

    def _find_tengu(self, floor: FloorState) -> Optional[Tengu]:
        for mob in floor.mobs.values():
            if isinstance(mob, Tengu) and mob.is_alive:
                return mob
        return None

    def _cell_occupied(self, floor: FloorState, floor_id: int, x: int, y: int) -> bool:
        if any(m.is_alive and m.pos.x == x and m.pos.y == y for m in floor.mobs.values()):
            return True
        if any(p.is_alive and p.pos.x == x and p.pos.y == y for p in self._players_on_floor(floor_id)):
            return True
        return False

    def _clear_entities_outside(self, floor: FloorState, floor_id: int, safe_area,
                                 keep_mob_id: Optional[str] = None) -> None:
        """Port of clearEntities(): destroys items/mobs outside `safe_area`,
        stashing dropped items in `prison_stored_items`."""
        for item_id, item in list(floor.items.items()):
            if not safe_area.inside(Point(item.pos.x, item.pos.y)):
                floor.prison_stored_items.append(item)
                del floor.items[item_id]

        for mob_id, mob in list(floor.mobs.items()):
            if mob_id == keep_mob_id:
                continue
            if not safe_area.inside(Point(mob.pos.x, mob.pos.y)):
                del floor.mobs[mob_id]

    def _place_traps_in_tengu_cell(self, floor: FloorState, floor_id: int,
                                    tengu: Tengu, fill: float = 0.65) -> None:
        """Simplified port of placeTrapsInTenguCell(): scatters hidden dart
        traps inside TENGU_CELL via a 7x7 cellular-automaton patch
        (Patch.generate). The original retries until the patch sits a
        specific pathfinder-distance band from the hero; that distance-map
        machinery isn't ported, so this just rerolls a bounded number of
        times and skips Tengu's/the target's own cell."""
        rng = SPDRandom()
        cell = layout.TENGU_CELL
        inner_left, inner_top = cell.left + 1, cell.top + 1
        target = self._find_nearest_player(tengu.pos, floor_id)
        player_positions = {
            (p.pos.x, p.pos.y)
            for p in self._players_on_floor(floor_id)
            if p.is_alive
        }

        # cleanTenguCell(): clear any traps already in the cell before
        # scattering a new patch (Tengu re-rolls traps on every jump).
        cleared = []
        for (tx, ty), trap in list(floor.traps.items()):
            if cell.left < tx < cell.right - 1 and cell.top < ty < cell.bottom - 1:
                del floor.traps[(tx, ty)]
                if floor.grid[ty][tx] in (TileType.SECRET_TRAP, TileType.TRAP):
                    floor.grid[ty][tx] = TileType.FLOOR
                    cleared.append({"x": tx, "y": ty, "tile": TileType.FLOOR})

        trap_cells: List[Tuple[int, int]] = []
        for _ in range(20):
            patch_bits = patch.generate(rng, 7, 7, fill, 0, False)
            trap_cells = []
            for i, bit in enumerate(patch_bits):
                if not bit:
                    continue
                x = inner_left + i % 7
                y = inner_top + i // 7
                if x == tengu.pos.x and y == tengu.pos.y:
                    continue
                if target is not None and x == target.pos.x and y == target.pos.y:
                    continue
                if (x, y) in player_positions:
                    continue
                trap_cells.append((x, y))
            if trap_cells:
                break

        patches = list(cleared)
        for x, y in trap_cells:
            floor.traps[(x, y)] = TrapInfo(x=x, y=y, trap_type=TrapType.TENGU_DART, hidden=True, can_be_searched=False)
            floor.grid[y][x] = TileType.SECRET_TRAP
            patches.append({"x": x, "y": y, "tile": TileType.SECRET_TRAP})

        if patches:
            floor.rebuild_flags()
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)
            self.add_event("TENGU_TRAP_BURST", {
                "cells": [[x, y] for (x, y) in trap_cells],
            }, floor_id=floor_id)

    # -- party prompt & teleport --------------------------------------------

    def _alive_players_on_prison_boss_floor(self, floor_id: int):
        return [
            p for p in self._players_on_floor(floor_id)
            if p.is_alive and not p.is_downed
        ]

    def _maybe_initiate_tengu_door_prompt(self, player, floor: FloorState, x: int, y: int) -> None:
        if floor.floor_id != PRISON_BOSS_FLOOR or floor.tengu_state != "START":
            return
        if (x, y) != (layout.TENGU_CELL_DOOR.x, layout.TENGU_CELL_DOOR.y):
            return
        self._start_tengu_party_prompt(player, floor)

    def _start_tengu_party_prompt(self, initiator, floor: FloorState) -> None:
        floor_id = floor.floor_id
        alive_players = self._alive_players_on_prison_boss_floor(floor_id)
        others = [p for p in alive_players if p.id != initiator.id]
        if not others:
            return

        floor.tengu_prompt = {
            "initiator_id": initiator.id,
            "initiator_name": initiator.name,
            "approved": {initiator.id},
            "declined": set(),
            "pending": {p.id for p in others},
        }
        for p in others:
            self.add_event(
                "TENGU_JOIN_PROMPT",
                {"initiator_id": initiator.id, "initiator_name": initiator.name},
                player_id=p.id,
            )
        self._emit_tengu_party_status(floor)

    def _emit_tengu_party_status(self, floor: FloorState) -> None:
        prompt = floor.tengu_prompt
        if not prompt:
            return
        initiator_id = prompt["initiator_id"]
        if initiator_id not in self.players:
            return
        pending_names = [
            self.players[pid].name for pid in prompt["pending"]
            if pid in self.players and self.players[pid].is_alive
        ]
        declined_names = [
            self.players[pid].name for pid in prompt["declined"]
            if pid in self.players and self.players[pid].is_alive
        ]
        approved_names = [
            self.players[pid].name for pid in prompt["approved"]
            if pid != initiator_id and pid in self.players and self.players[pid].is_alive
        ]
        self.add_event(
            "TENGU_PARTY_STATUS",
            {
                "initiator_id": initiator_id,
                "pending_names": pending_names,
                "declined_names": declined_names,
                "approved_names": approved_names,
                "can_decide": len(declined_names) > 0,
            },
            player_id=initiator_id,
        )

    def _close_tengu_prompts(self, floor: FloorState) -> None:
        prompt = floor.tengu_prompt
        if not prompt:
            return
        all_ids = set(prompt["approved"]) | set(prompt["declined"]) | set(prompt["pending"]) | {prompt["initiator_id"]}
        floor.tengu_prompt = None
        for pid in all_ids:
            if pid in self.players:
                self.add_event("TENGU_PROMPT_CLOSE", {}, player_id=pid)

    def respond_tengu_join(self, player_id: str, approve: bool) -> None:
        player = self.players.get(player_id)
        if not player or player.floor_id != PRISON_BOSS_FLOOR:
            return
        floor = self.floors.get(PRISON_BOSS_FLOOR)
        if not floor or floor.tengu_state != "START" or not floor.tengu_prompt:
            return
        prompt = floor.tengu_prompt
        if player_id == prompt["initiator_id"]:
            return

        prompt["pending"].discard(player_id)
        if approve:
            prompt["declined"].discard(player_id)
            prompt["approved"].add(player_id)
        else:
            prompt["approved"].discard(player_id)
            prompt["declined"].add(player_id)

        self.add_event("TENGU_PROMPT_CLOSE", {}, player_id=player_id)

        # Reconcile with currently alive players on floor 10
        alive_ids = {p.id for p in self._alive_players_on_prison_boss_floor(PRISON_BOSS_FLOOR)}
        prompt["pending"] &= alive_ids
        prompt["declined"] &= alive_ids
        prompt["approved"] &= alive_ids

        if not prompt["pending"] and not prompt["declined"]:
            participants = [
                p for p in self._alive_players_on_prison_boss_floor(PRISON_BOSS_FLOOR)
                if p.id in prompt["approved"]
            ]
            self._close_tengu_prompts(floor)
            self._teleport_and_start_tengu_fight(floor, PRISON_BOSS_FLOOR, participants)
        else:
            self._emit_tengu_party_status(floor)

    def decide_tengu_start(self, player_id: str, action: str) -> None:
        floor = self.floors.get(PRISON_BOSS_FLOOR)
        if not floor or floor.tengu_state != "START" or not floor.tengu_prompt:
            return
        prompt = floor.tengu_prompt
        if player_id != prompt["initiator_id"]:
            return

        if action == "wait":
            self._close_tengu_prompts(floor)
            return

        if action == "start_without":
            approved_ids = set(prompt["approved"])
            participants = [
                p for p in self._alive_players_on_prison_boss_floor(PRISON_BOSS_FLOOR)
                if p.id in approved_ids
            ]
            if not participants:
                initiator = self.players.get(player_id)
                if initiator and initiator.is_alive:
                    participants = [initiator]
            self._close_tengu_prompts(floor)
            self._teleport_and_start_tengu_fight(floor, PRISON_BOSS_FLOOR, participants)

    def _tengu_cell_entry_positions(self, floor: FloorState) -> List[Tuple[int, int]]:
        door_x = layout.TENGU_CELL_DOOR.x
        min_x = layout.TENGU_CELL.left + 1
        max_x = layout.TENGU_CELL.right - 2
        row_xs = [door_x]
        for offset in range(1, max_x - min_x + 1):
            for cand_x in (door_x - offset, door_x + offset):
                if min_x <= cand_x <= max_x:
                    row_xs.append(cand_x)

        positions: List[Tuple[int, int]] = []
        for y in (layout.TENGU_CELL.top + 1, layout.TENGU_CELL.top + 2):
            for x in row_xs:
                if (x, y) == (layout.TENGU_CELL_CENTER.x, layout.TENGU_CELL_CENTER.y):
                    continue
                positions.append((x, y))
        return positions

    def _teleport_players_to_tengu_cell(self, floor: FloorState, floor_id: int, players: list) -> None:
        if not players:
            return
        candidates = self._tengu_cell_entry_positions(floor)
        taken = {
            (m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive
        }
        # Also avoid colliding with any player on the floor not in `players`
        participant_ids = {p.id for p in players}
        for p in self._players_on_floor(floor_id):
            if p.is_alive and p.id not in participant_ids:
                taken.add((p.pos.x, p.pos.y))

        for player in players:
            if not player.is_alive:
                continue
            for nx, ny in candidates:
                if (nx, ny) in taken:
                    continue
                from_x, from_y = player.pos.x, player.pos.y
                player.pos.x, player.pos.y = nx, ny
                player.movement.stop()
                player.movement.path_queue.clear()
                taken.add((nx, ny))
                if (from_x, from_y) != (nx, ny):
                    self.add_event(
                        "TELEPORT",
                        {"player": player.id, "from_x": from_x, "from_y": from_y, "x": nx, "y": ny},
                        floor_id=floor_id,
                    )
                break

    def _teleport_and_start_tengu_fight(self, floor: FloorState, floor_id: int, participants: list) -> None:
        if floor.tengu_state != "START":
            return
        # Finish any pending unlock on the Tengu cell door before sealing it
        door_pos = (layout.TENGU_CELL_DOOR.x, layout.TENGU_CELL_DOOR.y)
        floor.pending_unlocks.pop(door_pos, None)
        self._teleport_players_to_tengu_cell(floor, floor_id, participants)
        self._prison_boss_start_to_fight_start(floor, floor_id)

    # -- transitions --------------------------------------------------------

    def _prison_boss_start_to_fight_start(self, floor: FloorState, floor_id: int) -> None:
        inside_players = [
            p for p in self._players_on_floor(floor_id)
            if p.is_alive and p.pos.y > layout.TENGU_CELL.top
        ]
        if not inside_players:
            return

        # If a player stepped into the cell while others were on the floor:
        alive_players = self._alive_players_on_prison_boss_floor(floor_id)
        if floor.tengu_prompt is not None:
            prompt = floor.tengu_prompt
            approved_ids = set(prompt["approved"])
            participants = [p for p in alive_players if p.id in approved_ids] or inside_players
            self._close_tengu_prompts(floor)
            self._teleport_players_to_tengu_cell(floor, floor_id, participants)
        elif len(inside_players) == 1 and len(alive_players) == 1:
            player = inside_players[0]
            if player.pos.y == layout.TENGU_CELL.top + 1 and player.pos.x == layout.TENGU_CELL_DOOR.x:
                pass
            elif player.pos.y <= layout.TENGU_CELL.top + 1:
                self._teleport_players_to_tengu_cell(floor, floor_id, [player])

        cx, cy = layout.TENGU_CELL_CENTER.x, layout.TENGU_CELL_CENTER.y
        if self._cell_occupied(floor, floor_id, cx, cy):
            candidates = []
            for dx, dy in _NEIGHBOURS8:
                nx, ny = cx + dx, cy + dy
                if not self._cell_occupied(floor, floor_id, nx, ny):
                    candidates.append((nx, ny))
            if not candidates:
                return  # mirrors Java: nothing free, wait and try again next tick
            cx, cy = candidates[0]

        # Seal the cell behind Tengu. "tengu_boss" key = any player may enter
        # freely once the fight starts, but no key is consumed (auto-open).
        dx, dy = layout.TENGU_CELL_DOOR.x, layout.TENGU_CELL_DOOR.y
        floor.grid[dy][dx] = TileType.LOCKED_DOOR
        floor.locked_doors[(dx, dy)] = "tengu_boss"
        floor.rebuild_flags()
        self.add_event("MAP_PATCH", {"tiles": [{"x": dx, "y": dy, "tile": TileType.LOCKED_DOOR}]}, floor_id=floor_id)

        tengu = Tengu(id=str(uuid.uuid4()), pos=Position(x=cx, y=cy), faction=Faction.DUNGEON)
        tengu.floor_id = floor_id
        _apply_boss_challenge(tengu, self.challenges)
        tengu.ai_state = "hunting"
        tengu.fight_started = True
        floor.mobs[tengu.id] = tengu

        self.add_event("TENGU_FIGHT_STARTED", {"mob": tengu.id}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=floor_id)

        # SPD: entering boss fight resets badge eligibility
        self.qualified_for_boss_challenge = True

        self._place_traps_in_tengu_cell(floor, floor_id, tengu)

        floor.tengu_state = "FIGHT_START"

    def _prison_boss_fight_start_to_pause(self, floor: FloorState, floor_id: int) -> None:
        tengu = self._find_tengu(floor)
        if tengu is None or not tengu.is_alive or not tengu.is_enraged():
            return

        self.add_event("BOSS_YELL", {"mob": tengu.id, "text": "Let's make this interesting...",
                                     "x": tengu.pos.x, "y": tengu.pos.y}, floor_id=floor_id)

        self._clear_entities_outside(floor, floor_id, layout.TENGU_CELL, keep_mob_id=tengu.id)

        rng = SPDRandom()
        level = layout._new_level(PRISON_BOSS_FLOOR)
        layout.apply_pause_patch(level, rng)
        floor.grid = _grid_from_level(level)
        floor.traps.clear()
        floor.rebuild_flags()
        floor.map_version += 1

        # Tengu leaves the world during FIGHT_PAUSE; restored in FIGHT_ARENA.
        del floor.mobs[tengu.id]
        floor.generation_meta["tengu_pending"] = tengu

        self.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)
        floor.tengu_state = "FIGHT_PAUSE"

    def _prison_boss_pause_to_arena(self, floor: FloorState, floor_id: int) -> None:
        if not any(p.is_alive and p.pos.y <= layout.START_HALLWAY.top + 1
                   for p in self._players_on_floor(floor_id)):
            return

        self._clear_entities_outside(floor, floor_id, layout.PAUSE_SAFE_AREA)

        level = layout._new_level(PRISON_BOSS_FLOOR)
        layout.build_arena_grid(level)
        floor.grid = _grid_from_level(level)
        floor.rebuild_flags()
        floor.map_version += 1

        tengu = floor.generation_meta.pop("tengu_pending", None)
        if tengu is None:
            tengu = Tengu(id=str(uuid.uuid4()), faction=Faction.DUNGEON)
            _apply_boss_challenge(tengu, self.challenges)
        tengu.pos = Position(x=layout.ARENA.left + layout.ARENA.width() // 2, y=layout.ARENA.top + 2)
        tengu.floor_id = floor_id
        tengu.ai_state = "hunting"
        floor.mobs[tengu.id] = tengu

        # Teleport any player whose tile is now a wall into the arena.
        # This happens when a player stayed in the Tengu cell while their
        # partner triggered the phase transition from the start hallway.
        self._relocate_players_into_arena(floor, floor_id)

        self.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)
        floor.tengu_state = "FIGHT_ARENA"

    def _relocate_players_into_arena(self, floor: FloorState, floor_id: int) -> None:
        """Move players who ended up in walls after the arena grid swap."""
        # Candidate spawn positions: bottom half of arena, center outward,
        # only passable tiles.
        cx = layout.ARENA.left + layout.ARENA.width() // 2
        seen: set = set()
        candidates = []
        for dy in range(0, layout.ARENA.height() // 2):
            y = layout.ARENA.bottom - 2 - dy
            if y < 0:
                break
            for dx in range(0, layout.ARENA.width() // 2 + 1):
                for x in (cx + dx, cx - dx) if dx > 0 else (cx,):
                    if (x, y) in seen:
                        continue
                    seen.add((x, y))
                    if not (0 <= x < floor.width and 0 <= y < floor.height):
                        continue
                    if floor.flags and not floor.flags.passable[y][x]:
                        continue
                    candidates.append((x, y))

        taken = set()
        for player in self._players_on_floor(floor_id):
            if not player.is_alive:
                continue
            tile_passable = (
                floor.flags
                and floor.flags.passable[player.pos.y][player.pos.x]
            )
            if tile_passable:
                taken.add((player.pos.x, player.pos.y))

        for player in self._players_on_floor(floor_id):
            if not player.is_alive:
                continue
            tile_passable = (
                floor.flags
                and floor.flags.passable[player.pos.y][player.pos.x]
            )
            if tile_passable:
                continue
            # Find first free candidate not occupied by a mob or other player.
            for (nx, ny) in candidates:
                if (nx, ny) in taken:
                    continue
                mob_here = any(
                    m.is_alive and m.pos.x == nx and m.pos.y == ny
                    for m in floor.mobs.values()
                )
                if mob_here:
                    continue
                player.pos.x, player.pos.y = nx, ny
                taken.add((nx, ny))
                self.add_event(
                    "TELEPORT",
                    {"entity": player.id, "x": nx, "y": ny},
                    floor_id=floor_id,
                )
                break

    def _prison_boss_arena_to_won(self, floor: FloorState, floor_id: int) -> None:
        if self._find_tengu(floor) is not None:
            return  # Tengu still alive

        self._clear_entities_outside(floor, floor_id, layout.TENGU_CELL)

        for p in self._players_on_floor(floor_id):
            p.pos.x, p.pos.y = layout.TENGU_CELL.left + 4, layout.TENGU_CELL.top + 2

        rng = SPDRandom()
        level = layout._new_level(PRISON_BOSS_FLOOR)
        layout.apply_end_patch(level, rng)
        floor.grid = _grid_from_level(level)
        floor.custom_tiles = list(level.custom_tiles)
        floor.custom_walls = list(level.custom_walls)
        floor.exit_pos = (layout.LEVEL_EXIT.x, layout.LEVEL_EXIT.y)
        floor.rebuild_flags()
        floor.map_version += 1

        for item in floor.prison_stored_items:
            cell = layout.random_tengu_cell_pos(rng, level)
            item.pos.x, item.pos.y = cell % level.width(), cell // level.width()
            floor.items[item.id] = item
        floor.prison_stored_items = []

        self.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)
        floor.tengu_state = "WON"
