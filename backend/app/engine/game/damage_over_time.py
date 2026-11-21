# Copyright (C) 2026 ArtemNikov
#
"""Damage-over-time ticking: bleeding, ooze, burning, poison/corrosion, and
their side effects (inventory burning, igniting flammable floor tiles).
"""

import random
from typing import List

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import is_immune
from app.engine.entities.buffs import get_buff, has_buff, remove_buff
from app.engine.entities.items.consumables import ChargrilledMeat, FrozenCarpaccio, Gold, MysteryMeat
from app.engine.entities.mobs import MobEntity
from app.engine.entities.player import Player
from app.engine.game.constants import OOZE_TICK_INTERVAL
from app.engine.game.floor_state import FloorState
from app.engine.systems.loot import roll_drops


def _ooze_damage(depth: int) -> int:
    if depth > 5:
        return 1 + depth // 5
    if depth == 5:
        return 1
    return 1 if random.randint(0, 1) == 0 else 0


class DamageOverTimeMixin:
    def _process_bleed_ooze(self, floor_id: int, active_players: List[Player]):
        """SPD `Ooze.act()` once per turn: washed off by water, otherwise
        `1 + depth/5` damage past depth 5, 1 at depth 5, a 50% chance of 1
        in the sewers. (Bleeding is its own buff -- see game/bleeding.py.)"""
        floor = self._get_or_create_floor(floor_id)
        for player in active_players:
            if player.ooze_amount <= 0:
                continue
            in_water = (floor.grid[player.pos.y][player.pos.x] == TileType.FLOOR_WATER
                        and not getattr(player, "flying", False))
            if in_water:
                player.ooze_amount = 0
                player.ooze_cooldown = 0
                continue
            player.ooze_cooldown -= self.sim_ticks
            if player.ooze_cooldown > 0:
                continue
            player.ooze_cooldown += OOZE_TICK_INTERVAL
            dmg = _ooze_damage(floor_id)
            if dmg > 0:
                player.take_damage(dmg)
                self.add_event("DAMAGE", {"target": player.id, "amount": dmg, "ooze": True}, floor_id=floor_id)
            player.ooze_amount -= 1
            if player.ooze_amount <= 0:
                player.ooze_amount = 0
                player.ooze_cooldown = 0

    def _process_burning(self, floor_id: int, active_players: List[Player]):
        floor = self._get_or_create_floor(floor_id)
        for player in active_players:
            if not has_buff(player.buffs, "burning"):
                player.burning_accum = 0.0
                continue

            is_water = floor.grid[player.pos.y][player.pos.x] == TileType.FLOOR_WATER
            if is_water:
                remove_buff(player.buffs, "burning")
                player.burning_accum = 0.0
                continue

            player.burning_accum += self.sim_unit
            if player.burning_accum < 1.0 - 1e-9:
                continue
            player.burning_accum = 0.0

            remove_buff(player.buffs, "chill")

            dmg = random.randint(1, 3 + player.floor_id // 4)
            player.take_damage(dmg)
            self.add_event("DAMAGE", {"target": player.id, "amount": dmg, "burning": True}, floor_id=floor_id)
            self._ignite_floor_if_flammable(player, floor, floor_id)

            self._burn_player_inventory(player, floor_id)

        for mob in floor.mobs.values():
            if not mob.is_alive or not has_buff(mob.buffs, "burning"):
                mob.burning_accum = 0.0
                continue

            is_water = floor.grid[mob.pos.y][mob.pos.x] == TileType.FLOOR_WATER
            if is_water:
                remove_buff(mob.buffs, "burning")
                mob.burning_accum = 0.0
                continue

            mob.burning_accum += self.sim_unit
            if mob.burning_accum < 1.0 - 1e-9:
                continue
            mob.burning_accum = 0.0

            if is_immune(mob, "burning"):
                remove_buff(mob.buffs, "burning")
                self._ignite_floor_if_flammable(mob, floor, floor_id)
                continue

            dmg = random.randint(1, 3 + floor_id // 4)
            hurt = getattr(mob, "take_burning_damage", None) or mob.take_damage
            taken = hurt(dmg)
            self.add_event("DAMAGE", {"target": mob.id, "amount": taken if isinstance(taken, int) else dmg,
                                      "burning": True}, floor_id=floor_id)
            self._ignite_floor_if_flammable(mob, floor, floor_id)
            if mob.hp <= 0 or not mob.is_alive:
                mob.hp = 0
                mob.is_alive = False
                mob.die(
                    floor_mobs=floor.mobs,
                    tile_x=mob.pos.x,
                    tile_y=mob.pos.y,
                    players=list(self._players_on_floor(floor_id)),
                )
                self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)
                self.handle_mob_death(mob, floor, floor_id)
                drops = roll_drops(mob, self.drop_counters, mob.pos.x, mob.pos.y, players=list(self._players_on_floor(floor_id)))
                for item in drops:
                    floor.items[item.id] = item
                if any(isinstance(d, Gold) for d in drops):
                    self.add_event("GOLD_DROP", {"x": mob.pos.x, "y": mob.pos.y}, floor_id=floor_id)

    def _process_poison_corrosion(self, floor_id: int, active_players: List[Player]):
        floor = self._get_or_create_floor(floor_id)

        def do_dot(entity, buff_type: str, dmg_per_tick: int):
            buff = get_buff(entity.buffs, buff_type)
            if buff is None:
                return
            accum_key = f"{buff_type}_accum"
            accum = getattr(entity, accum_key, 0.0)
            accum += self.sim_unit
            if accum < 1.0 - 1e-9:
                setattr(entity, accum_key, accum)
                return
            setattr(entity, accum_key, 0.0)

            if is_immune(entity, buff_type):
                remove_buff(entity.buffs, buff_type)
                return

            dmg = dmg_per_tick + buff.level
            actual = entity.take_damage(dmg)
            source = f"{buff_type}_dot"
            self.add_event("DAMAGE", {"target": entity.id, "amount": actual, source: True}, floor_id=floor_id)

            if isinstance(entity, MobEntity) and not entity.is_alive:
                entity.die(floor_mobs=floor.mobs, tile_x=entity.pos.x, tile_y=entity.pos.y,
                           players=list(self._players_on_floor(floor_id)))
                self.add_event("DEATH", {"target": entity.id}, floor_id=floor_id)
                self.handle_mob_death(entity, floor, floor_id)
                from app.engine.systems.loot import roll_drops
                drops = roll_drops(entity, self.drop_counters, entity.pos.x, entity.pos.y,
                                   players=list(self._players_on_floor(floor_id)))
                for item in drops:
                    floor.items[item.id] = item
                if any(isinstance(d, Gold) for d in drops):
                    self.add_event("GOLD_DROP", {"x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id)

        for player in active_players:
            do_dot(player, "poison", 0)
            do_dot(player, "corrosion", 1)

        for mob in floor.mobs.values():
            if not mob.is_alive:
                continue
            do_dot(mob, "poison", 0)
            do_dot(mob, "corrosion", 1)

    def _burn_player_inventory(self, player: Player, floor_id: int):
        player.burning_total_seconds += 1.0
        if player.burning_total_seconds < 4.0:
            return

        chance = (player.burning_total_seconds - 3.0) / 3.0
        if random.random() >= chance:
            return

        player.burning_total_seconds = 0.0

        inv = player.inventory
        for item in list(inv):
            if item.kind == "scroll" and not item.unique:
                inv.remove(item)
                self.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
                return

        for item in list(inv):
            if isinstance(item, (MysteryMeat, FrozenCarpaccio)):
                idx = inv.index(item)
                cooked = ChargrilledMeat(id=item.id, quantity=item.quantity)
                inv[idx] = cooked
                self.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
                return

    def _ignite_floor_if_flammable(self, entity, floor: FloorState, floor_id: int):
        """Seed fire under a burning entity standing on a flammable tile w/o fire.
        Mirrors SPD Burning.act() lines 161-163."""
        x, y = entity.pos.x, entity.pos.y
        if not (floor.flags and floor.flags.flamable[y][x]):
            return
        has_fire = any(
            b.get("type") == "fire" and (x, y) in b.get("cells", set())
            for b in floor.blob_areas.values()
        )
        if has_fire:
            return
        blob_id = f"burning_footprint_{entity.id}"
        floor.blob_areas[blob_id] = {
            "type": "fire",
            "cells": {(x, y)},
            "volume": {(x, y): 4},
        }
