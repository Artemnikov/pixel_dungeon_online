# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
"""BombsMixin: real-time fuses for floor bombs + the shared explosion core.

A lit bomb is just a floor item with fuse_ticks set — serialized with the
floor, so reconnects can't lose a fuse. update_tick calls tick_bombs per
active floor (tengu bomb-timer pattern)."""
import random as _random
import uuid as _uuid
from typing import List, Tuple

from app.engine.entities.base import Position
from app.engine.entities.items_bombs import Bomb, Noisemaker


def _normal_int_range(lo: int, hi: int) -> int:
    # SPD Random.NormalIntRange: mean-biased average of two uniforms.
    return round((_random.randint(lo, hi) + _random.randint(lo, hi)) / 2)


class BombsMixin:
    def tick_bombs(self, floor, floor_id: int) -> None:
        for item_id in list(floor.items.keys()):
            item = floor.items.get(item_id)
            if not isinstance(item, Bomb) or item.fuse_ticks is None:
                continue
            item.fuse_ticks -= 1
            if item.fuse_ticks > 0:
                continue
            if isinstance(item, Noisemaker) and not item.armed:
                self._arm_noisemaker(floor, floor_id, item)
            else:
                self.explode_bomb(floor, floor_id, item)

    def _arm_noisemaker(self, floor, floor_id: int, bomb) -> None:
        # Filled in fully in Task 5; arming keeps the fuse alive.
        bomb.armed = True
        bomb.fuse_ticks = 120  # 6 SPD turns between alerts

    def explode_bomb(self, floor, floor_id: int, bomb) -> None:
        # Remove first: chain detonations must never recurse into this bomb.
        floor.items.pop(bomb.id, None)
        cx, cy = bomb.pos.x, bomb.pos.y
        cells = self._explosion_cells(floor, cx, cy, bomb)
        self.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)
        self.add_event("BOMB_BLAST", {
            "x": cx, "y": cy, "kind": bomb.kind,
            "cells": [[x, y] for x, y in sorted(cells)],
        }, floor_id=floor_id)
        # Damage + destruction land in Task 3; per-kind effects in Tasks 4-6.

    def _explosion_cells(self, floor, cx: int, cy: int, bomb) -> List[Tuple[int, int]]:
        # BFS distance map over non-solid cells (SPD also lets the blast
        # reach flammable solids like doors — handled with the destruction
        # pass in Task 3 by including flamable cells as traversable).
        radius = bomb.EXPLOSION_RANGE
        seen = {(cx, cy)}
        frontier = [(cx, cy)]
        for _ in range(radius):
            nxt = []
            for x, y in frontier:
                for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0),
                               (-1, -1), (1, -1), (-1, 1), (1, 1)):
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                        continue
                    if (nx, ny) in seen:
                        continue
                    solid = floor.flags.solid[ny][nx] if floor.flags else False
                    flamable = floor.flags.flamable[ny][nx] if floor.flags else False
                    if solid and not flamable:
                        continue
                    seen.add((nx, ny))
                    if not solid:
                        nxt.append((nx, ny))
            frontier = nxt
        return sorted(seen)

    def light_bomb(self, player, floor, floor_id: int, bomb_cls_instance, tx: int, ty: int) -> None:
        unit = bomb_cls_instance
        unit.id = unit.id or str(_uuid.uuid4())
        unit.pos = Position(x=tx, y=ty)
        unit.fuse_ticks = unit.FUSE_TICKS
        floor.items[unit.id] = unit
        self.add_event("BOMB_LIT", {"x": tx, "y": ty, "kind": unit.kind},
                       floor_id=floor_id)

    def handle_bomb_pickup(self, player, floor, floor_id: int, item_id: str, bomb) -> bool:
        """Lit-bomb pickup: snuff the fuse (SPD), or detonate an armed
        Noisemaker. Returns True when this handled the pickup."""
        if bomb.fuse_ticks is None:
            return False
        if isinstance(bomb, Noisemaker) and bomb.armed:
            self.explode_bomb(floor, floor_id, bomb)
            return True
        bomb.fuse_ticks = None
        self.add_event("MESSAGE", {"text": "You quickly snuff the bomb's fuse."},
                       floor_id=floor_id, player_id=player.id)
        return False  # continue with the normal collect path
