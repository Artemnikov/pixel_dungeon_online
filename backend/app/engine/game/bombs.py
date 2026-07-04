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
from app.engine.entities.items_equip import EquipableItem
from app.engine.entities.items_wands import Wand


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
        cells = set(self._explosion_cells(floor, cx, cy, bomb))
        self.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)
        self.add_event("BOMB_BLAST", {
            "x": cx, "y": cy, "kind": bomb.kind,
            "cells": [[x, y] for x, y in sorted(cells)],
        }, floor_id=floor_id)

        chained = []
        if bomb.DESTRUCTIVE:
            self._explosion_destroy(floor, floor_id, cells, chained)

        depth = floor_id
        victims = [e for e in self._explosion_victims(floor, floor_id, cells)]
        if bomb.DEALS_BASE_DAMAGE:
            for ch in victims:
                if not ch.is_alive:
                    continue
                dmg = _normal_int_range(4 + depth, 12 + 3 * depth)
                if not bomb.PIERCES_ARMOR:
                    dmg -= _random.randint(ch.get_dr_min(), ch.get_dr_max())
                if dmg > 0:
                    taken = ch.take_damage(dmg)
                    self.add_event("DAMAGE", {"target": ch.id, "amount": taken},
                                   floor_id=floor_id)
                    if not ch.is_alive and ch.id in floor.mobs:
                        # Mirrors _blast_effect (runestone_actions.py): die() ->
                        # DEATH event -> handle_mob_death -> roll_drops, exactly.
                        from app.engine.systems.loot import roll_drops
                        ch.die(floor_mobs=floor.mobs, tile_x=ch.pos.x, tile_y=ch.pos.y,
                               players=list(self._players_on_floor(floor_id)))
                        self.add_event("DEATH", {"target": ch.id}, floor_id=floor_id)
                        self.handle_mob_death(ch, floor, floor_id)
                        for drop in roll_drops(ch, self.drop_counters, ch.pos.x, ch.pos.y,
                                                players=list(self._players_on_floor(floor_id))):
                            floor.items[drop.id] = drop

        self._bomb_effect(floor, floor_id, bomb, cells, victims)

        for other in chained:
            if other.id in floor.items:
                self.explode_bomb(floor, floor_id, other)

    def _explosion_victims(self, floor, floor_id: int, cells):
        for m in floor.mobs.values():
            if m.is_alive and (m.pos.x, m.pos.y) in cells:
                yield m
        for p in self._players_on_floor(floor_id):
            if p.is_alive and not p.is_downed and (p.pos.x, p.pos.y) in cells:
                yield p

    def _explosion_destroy(self, floor, floor_id: int, cells, chained: list) -> None:
        from app.engine.game.blobs import _BURN_RESULT  # underscore-private; repo precedent for cross-module reuse
        from app.engine.dungeon.generator import TileType
        patches = []
        for (x, y) in cells:
            if floor.flags and floor.flags.flamable[y][x]:
                new_tile = _BURN_RESULT.get(floor.grid[y][x], TileType.EMBERS)
                floor.grid[y][x] = new_tile
                patches.append({"x": x, "y": y, "tile": new_tile})
        destroyed = []
        for item_id in list(floor.items.keys()):
            item = floor.items[item_id]
            if item.pos is None or (item.pos.x, item.pos.y) not in cells:
                continue
            if getattr(item, "for_sale", False) or item.type in ("grave", "chest", "scenery"):
                continue
            # Heap.explode: unique/upgradable/equipable items survive explosions.
            if item.unique or isinstance(item, (EquipableItem, Wand)):
                continue
            if isinstance(item, Bomb):
                chained.append(item)      # detonated after this blast resolves
                continue
            del floor.items[item_id]
            destroyed.append({"x": item.pos.x, "y": item.pos.y})
        if patches:
            floor.rebuild_flags()
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)
        if destroyed:
            self.add_event("ITEMS_DESTROYED", {"tiles": destroyed}, floor_id=floor_id)

    def _bomb_effect(self, floor, floor_id: int, bomb, cells, victims) -> None:
        # Per-kind effects: Tasks 4-6 dispatch on bomb.kind here.
        pass

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
