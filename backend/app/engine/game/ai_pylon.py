# Copyright (C) 2026 ArtemNikov
#
import random
from typing import Optional

from app.engine.dungeon.constants import TileType
from app.engine.dungeon.spd_levelgen.level import _CIRCLE8_OFFSETS
from app.engine.entities.base import Position
from app.engine.entities.mobs import DM300, Pylon
from app.engine.game.constants import GAME_TURN_TICKS
from app.engine.game.floor_state import FloorState


def _update_pylon(game, pylon: Pylon, floor: FloorState, floor_id: int):
    if not pylon.activated:
        return

    pylon.bolt_cooldown -= 1
    if pylon.bolt_cooldown > 0:
        return

    idx_a = pylon.fire_target_idx
    idx_b = (pylon.fire_target_idx + 4) % 8
    shock_cells = []
    for idx in (idx_a, idx_b):
        ox, oy = _CIRCLE8_OFFSETS[idx]
        shock_cells.append((pylon.pos.x + ox, pylon.pos.y + oy))

    for cx, cy in shock_cells:
        game.add_event("LIGHTNING_ARC", {
            "source_x": pylon.pos.x, "source_y": pylon.pos.y,
            "target_x": cx, "target_y": cy,
            "x": pylon.pos.x, "y": pylon.pos.y,
        }, floor_id=floor_id)
        for p in game._players_on_floor(floor_id):
            if p.is_alive and p.pos.x == cx and p.pos.y == cy:
                dmg = random.randint(10, 20)
                taken = p.take_damage(dmg)
                game.add_event("ATTACK", {"source": pylon.id, "target": p.id,
                                          "damage": taken, "surprise": False},
                               floor_id=floor_id)
                if taken > 0:
                    game.add_event("DAMAGE", {"target": p.id, "amount": taken, "shock": True}, floor_id=floor_id)
        for m in floor.mobs.values():
            if m.is_alive and m.id != pylon.id and not isinstance(m, DM300) and m.pos.x == cx and m.pos.y == cy:
                dmg = random.randint(10, 20)
                taken = m.take_damage(dmg)
                game.add_event("ATTACK", {"source": pylon.id, "target": m.id,
                                          "damage": taken, "surprise": False},
                               floor_id=floor_id)
                if taken > 0:
                    game.add_event("DAMAGE", {"target": m.id, "amount": taken, "shock": True}, floor_id=floor_id)

    game.add_event("PLAY_SOUND", {"sound": "LIGHTNING",
                                  "x": pylon.pos.x, "y": pylon.pos.y}, floor_id=floor_id)

    pylon.fire_target_idx = (pylon.fire_target_idx + 1) % 8
    pylon.bolt_cooldown = GAME_TURN_TICKS


def _activate_pylon(game, floor: FloorState, floor_id: int, near_pos: Optional[Position] = None):
    candidates = [m for m in floor.mobs.values() if isinstance(m, Pylon) and not m.activated]
    if not candidates:
        return

    if len(candidates) > 1 and near_pos is not None:
        closest = min(candidates, key=lambda p: game._get_distance(p.pos, near_pos))
        pool = [p for p in candidates if p.id != closest.id]
    else:
        pool = candidates

    chosen = random.choice(pool) if pool else candidates[0]
    chosen.activated = True
    game.add_event("PYLON_ACTIVATED", {"mob": chosen.id,
                                       "x": chosen.pos.x, "y": chosen.pos.y}, floor_id=floor_id)

    # Port of CavesBossLevel.activatePylon(): seeds PylonEnergy blob on all
    # wires (INACTIVE_TRAP), water (FLOOR_WATER), and gate (WALL_DECO) cells
    # within the arena region.
    energy_cells = set()
    start_y = 13  # mainArena.top - 1
    for y in range(start_y, floor.height):
        for x in range(floor.width):
            tile = floor.grid[y][x]
            if tile in (TileType.INACTIVE_TRAP, TileType.FLOOR_WATER, TileType.WALL_DECO):
                energy_cells.add((x, y))

    if energy_cells:
        blob_id = "dm300_pylon_energy"
        floor.blob_areas[blob_id] = {
            "type": "pylon_energy",
            "cells": energy_cells,
            "volume": {c: 1 for c in energy_cells},
            "tick_counter": 0,
        }
        cell_list = [(c[0], c[1], 1) for c in energy_cells]
        game.add_event("BLOB_UPDATE", {"id": blob_id, "type": "pylon_energy", "cells": cell_list}, floor_id=floor_id)

