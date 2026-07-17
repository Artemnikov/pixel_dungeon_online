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
"""Per-player per-tick updates: auto-move/pathing, heal ticks, passive regen,
combo/shield/berserk decay, and trinket procs. Extracted from TickMixin.update_tick.
"""

import random
import time

from app.engine.entities.base import Faction
from app.engine.entities.buffs import get_buff, is_frozen
from app.engine.entities.player import Player
from app.engine.game.constants import AUTO_MOVE_INTERVAL, PATH_BLOCKED_GIVE_UP_TICKS


class PlayerTickMixin:
    def _tick_player(self, player: Player, dt: float) -> None:
        if player.is_downed or not player.is_alive:
            return

        move_interval = AUTO_MOVE_INTERVAL
        if player.invisible > 0 and player.subclass_info.talent_info.level("speedy_stealth") >= 3:
            move_interval /= 2
        if player.has_buff("slow") or player.has_buff("chill"):
            move_interval *= 2
        if player.has_buff("paralysis") or is_frozen(player.buffs):
            move_interval = 9999
        from app.engine.entities.rings import haste_multiplier
        move_interval /= haste_multiplier(player)
        # Armor glyph speed boost (Swiftness, Flow, Bulk)
        from app.engine.entities.armor_glyphs import speed_boost
        armor = getattr(player.belongings, "armor", None)
        if armor is not None:
            pf = self._get_or_create_floor(player.floor_id)
            enemies_nearby = any(
                m.is_alive for m in pf.mobs.values()
                if abs(m.pos.x - player.pos.x) + abs(m.pos.y - player.pos.y) <= 3
            )
            s = speed_boost(player, armor, enemies_nearby)
            move_interval /= s

        if player.move_intent:
            now = time.time()
            if now - player.last_auto_move_time >= move_interval:
                dx, dy = player.move_intent
                player.last_auto_move_time = now
                self.move_entity(player.id, dx, dy)
        elif player.path_queue:
            now = time.time()
            if now - player.last_auto_move_time >= move_interval:
                dx, dy = player.path_queue[0]
                floor = self._get_or_create_floor(player.floor_id)
                nx, ny = player.pos.x + dx, player.pos.y + dy
                if any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values()):
                    # Next tile is briefly occupied (e.g. a wandering mob).
                    # Keep the queued path and retry next tick instead of
                    # abandoning the route; give up if it stays blocked.
                    player.path_blocked_ticks += 1
                    if player.path_blocked_ticks > PATH_BLOCKED_GIVE_UP_TICKS:
                        player.path_queue = []
                        player.path_blocked_ticks = 0
                else:
                    player.path_queue.pop(0)
                    player.path_blocked_ticks = 0
                    player.last_auto_move_time = now
                    self.move_entity(player.id, dx, dy)

        self._apply_heal_tick(player)
        self._apply_aqua_heal_tick(player)
        self._apply_room_heal_tick(player)
        self._apply_passive_regen(player)
        heal_buff = get_buff(player.buffs, "healing")
        if heal_buff and player.hp < player.get_total_max_hp():
            player.set_heal(float(heal_buff.level * 2), 0.1, 1.0)
        self._tick_passive_wand_recharge(player, dt)

        if player.armor_charge < 100:
            player.armor_charge = min(100, player.armor_charge + 2)

        moved = bool(player.move_intent or player.path_queue)
        self.tick_rogue(player, dt, moved=moved)
        self.tick_artifacts(player, dt)
        self.tick_duelist(player, dt)
        self.tick_cleric(player, dt)

        if moved:
            player.stationary_ticks = 0
        else:
            player.stationary_ticks += 1

        # Hold Fast (warrior T3): while stationary, slows combo/shield
        # decay and the Broken Seal cooldown (0% decay at +3).
        hf_factor = player.get_hold_fast_decay_factor()
        hf_tick = hf_factor >= 1.0 or random.random() < hf_factor

        # Broken Seal (all Warriors): once triggered (see Player.take_damage),
        # the shield holds until no enemies are nearby for a couple of
        # turns; unused shield then reduces the remaining cooldown by up
        # to 50%. The cooldown itself ticks down toward 0 regardless.
        if player.seal_affixed:
            seal_shield = player.get_shield("broken_seal")
            if seal_shield is not None:
                floor = self._get_or_create_floor(player.floor_id)
                nearby = any(
                    m.is_alive and m.faction != Faction.PLAYER
                    and max(abs(m.pos.x - player.pos.x), abs(m.pos.y - player.pos.y)) <= player.get_view_distance()
                    for m in floor.mobs.values()
                )
                if nearby:
                    player.seal_no_enemy_ticks = 0
                else:
                    player.seal_no_enemy_ticks += 1
                    if player.seal_no_enemy_ticks >= 2:
                        max_shield = max(1, player.get_broken_seal_max_shield())
                        unused_frac = seal_shield.amount / max_shield
                        player.seal_cooldown -= round(150 * unused_frac * 0.5)
                        player.shields = [s for s in player.shields if s.name != "broken_seal"]
                        player.seal_no_enemy_ticks = 0
            if player.seal_cooldown > 0 and hf_tick:
                player.seal_cooldown -= 1

        if player.berserk_active:
            self.update_berserk(player)

        if player.combo_count > 0:
            player.combo_timer -= dt * hf_factor
            if player.combo_timer <= 0:
                player.combo_count = 0
                player.combo_timer = 0.0
                player.clobber_used = False
                player.parry_used = False

        if player.berserk_cooldown > 0:
            player.berserk_cooldown -= 1

        # self._apply_hunger_tick(player)  # disabled per request

        if hf_tick:
            player.decay_shields()
        if player.has_fury:
            player.fury_turns_remaining -= 1
            if player.fury_turns_remaining <= 0:
                player.has_fury = False
                player.fury_turns_remaining = 0

        # ChaoticCenser trinket: periodic gas cloud spawning
        from app.engine.entities.trinkets import ChaoticCenser as _CC
        from app.engine.entities.trinkets import trinket_level
        cc_lvl = trinket_level(player, "chaotic_censer")
        if cc_lvl >= 0:
            player._cc_turns = getattr(player, "_cc_turns", 0) + 1
            avg_interval = _CC.average_turns_until_gas(cc_lvl)
            if avg_interval > 0 and player._cc_turns >= avg_interval:
                player._cc_turns = 0
                floor = self._get_or_create_floor(player.floor_id)
                nearby_mobs = [
                    m for m in floor.mobs.values()
                    if m.is_alive and m.faction != Faction.PLAYER
                    and max(abs(m.pos.x - player.pos.x), abs(m.pos.y - player.pos.y)) <= 4
                ]
                if nearby_mobs:
                    target = random.choice(nearby_mobs)
                    gas_type = random.choice(["toxic_gas", "fire", "paralytic_gas"])
                    from app.engine.game.terrain_effects import _create_gas
                    _create_gas(floor, (target.pos.x, target.pos.y), 4, gas_type)
