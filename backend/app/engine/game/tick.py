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
"""The per-tick game loop for GameInstance.

Advances death processing, buff sync, player auto-movement, healing/regen,
status effects (bleed/ooze), mob respawns, and delegates boss AI to sub-mixins.

This module is the orchestrator: per-entity heavy lifting lives in sibling
mixins (player_tick.py, mob_ai_dispatch.py, mob_ai_movement.py,
damage_over_time.py, spawning.py, status_effects_tick.py, player_regen.py),
all composed onto GameInstance alongside TickMixin in manager.py.
"""

from app.engine.entities.buffs import get_buff, process_buffs
from app.engine.entities.items_consumable import Gold
from app.engine.game.blobs import tick_blob_areas
from app.engine.systems.loot import roll_drops

# Re-exported for backward-compatible `from app.engine.game.tick import
# _universal_extra_pool` (used directly by tests/test_universal_spawns.py).
from app.engine.game.spawning import _universal_extra_pool  # noqa: F401


class TickMixin:
    def update_tick(self):
        self._invalidate_fov_cache()

        dt = 0.05
        active_ids = self.active_floor_ids

        for player in self.players.values():
            removed = process_buffs(player.buffs, dt)
            if "invisibility" in removed or "shadows" in removed:
                player.invisible = max(0, player.invisible - 1)
            if "frost" in removed or "frozen" in removed:
                self._frost_thaw(player, self._get_or_create_floor(player.floor_id))
            if "endure_tracker" in removed:
                self._finalize_endure(player)
            bleed = get_buff(player.buffs, "bleeding")
            if bleed:
                dmg = max(1, bleed.level)
                player.take_damage(dmg)
                self.add_event("DAMAGE", {"target": player.id, "amount": dmg, "bleed": True})
            self._tick_dust_ghost_spawner(player)

        for floor_id in active_ids:
            floor = self.floors[floor_id]
            for mob in floor.mobs.values():
                if mob.is_alive:
                    removed = process_buffs(mob.buffs, dt)
                    if "sheep_timer" in removed and mob.is_alive:
                        mob.is_alive = False
                        self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)
                        self.handle_mob_death(mob, floor, floor_id)
                        continue
                    if "invisibility" in removed or "shadows" in removed:
                        mob.invisible = max(0, mob.invisible - 1)
                    if "frost" in removed or "frozen" in removed:
                        self._frost_thaw(mob, floor)
                    if "drowsy" in removed and mob.ai_state in ("idle", "wandering"):
                        mob.ai_state = "sleeping"
                    if "terror" in removed and mob.ai_state == "fleeing":
                        mob.ai_state = "hunting"
                    bleed = get_buff(mob.buffs, "bleeding")
                    if bleed:
                        dmg = max(1, bleed.level)
                        mob.take_damage(dmg)
                        self.add_event("DAMAGE", {"target": mob.id, "amount": dmg, "bleed": True})

        if active_ids:
            active_floors = {fid: self.floors[fid] for fid in active_ids}
            blob_events = tick_blob_areas(active_floors, self.players)
            for ev in blob_events:
                self.add_event(ev["type"], ev["data"])
            for ev in blob_events:
                if ev["type"] == "DEATH" and "target" in ev.get("data", {}):
                    target_id = ev["data"]["target"]
                    for fid in active_ids:
                        f = self.floors[fid]
                        mob = f.mobs.get(target_id)
                        if mob is not None and not mob.is_alive:
                            self.handle_mob_death(mob, f, fid)
                            drops = roll_drops(mob, self.drop_counters,
                                               mob.pos.x, mob.pos.y,
                                               players=list(self._players_on_floor(fid)))
                            for item in drops:
                                f.items[item.id] = item
                            if any(isinstance(d, Gold) for d in drops):
                                self.add_event("GOLD_DROP",
                                               {"x": mob.pos.x, "y": mob.pos.y},
                                               floor_id=fid)
                            break

        for floor_id in active_ids:
            self._tick_tengu_blobs(self.floors[floor_id], floor_id)
            self.tick_bombs(self.floors[floor_id], floor_id)

        self._emit_state_effects()

        for player in self.players.values():
            if not player.is_alive and not player.death_processed:
                self._kill_player(player, self._get_or_create_floor(player.floor_id), player.floor_id)

        for player in self.players.values():
            self._sync_effects(player)

        for player in self.players.values():
            self._tick_player(player, dt)

        for floor_id in active_ids:
            floor = self.floors[floor_id]
            active_players = [p for p in self._players_on_floor(floor_id) if p.is_alive and not p.is_downed]
            if not active_players:
                continue

            self._process_bleed_ooze(floor_id, active_players)
            self._process_burning(floor_id, active_players)
            self._process_poison_corrosion(floor_id, active_players)
            self._process_respawns(floor_id, floor, active_players)
            self._update_prison_boss(floor, floor_id)

            for mob in list(floor.mobs.values()):
                self._tick_mob(mob, floor, floor_id)

        self._evict_empty_floors()
