from app.engine.entities.buffs import get_buff, has_buff, process_buffs
from app.engine.entities.items.consumables import Gold
from app.engine.game.blobs import tick_blob_areas
from app.engine.game.constants import TICK_DURATION
from app.engine.systems.loot import roll_drops

from app.engine.game.spawning import _universal_extra_pool  # noqa: F401


class TickMixin:
    def update_tick(self):
        self._invalidate_fov_cache()

        dt = TICK_DURATION
        active_ids = self.active_floor_ids

        for player in self.players.values():
            removed = process_buffs(player.buffs, dt)
            self._process_removed_buffs(
                player, removed,
                floor=self._get_or_create_floor(player.floor_id),
                floor_id=player.floor_id,
                is_player=True,
            )
            self._apply_bleed(player)
            self._tick_dust_ghost_spawner(player)

        for floor_id in active_ids:
            floor = self.floors[floor_id]
            for mob in floor.mobs.values():
                if not mob.is_alive:
                    continue
                removed = process_buffs(mob.buffs, dt)
                if self._process_removed_buffs(mob, removed, floor=floor, floor_id=floor_id, is_player=False):
                    continue  # mob died to its own buff expiry (e.g. sheep)
                self._apply_bleed(mob)
                self._apply_sungrass_heal(mob, dt, floor_id=floor_id)

        if active_ids:
            active_floors = {fid: self.floors[fid] for fid in active_ids}
            blob_events = tick_blob_areas(active_floors, self.players)
            for ev in blob_events:
                self.add_event(ev["type"], ev["data"],
                               floor_id=ev.get("_floor_id"),
                               source_player_id=ev.get("_source_player_id"))
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
            self._process_item_respawns(floor_id, floor, active_players)
            self._process_boss_respawns(floor_id, floor, active_players)
            self._process_chest_respawns(floor_id, floor, active_players)
            self._update_prison_boss(floor, floor_id)

            time_frozen = any(has_buff(p.buffs, "time_bubble") for p in active_players)
            if not time_frozen:
                for mob in list(floor.mobs.values()):
                    self._tick_mob(mob, floor, floor_id)

        for floor in list(self.floors.values()):
            self._process_pending_unlocks(floor, floor.floor_id)

        self._evict_empty_floors()

    _SHARED_BUFF_EXPIRY_HANDLERS = {
        "invisibility": "_on_invisibility_expired",
        "shadows": "_on_invisibility_expired",
        "frost": "_on_frozen_expired",
        "frozen": "_on_frozen_expired",
    }

    _PLAYER_BUFF_EXPIRY_HANDLERS = {
        **_SHARED_BUFF_EXPIRY_HANDLERS,
        "endure_tracker": "_on_endure_expired",
    }

    _MOB_BUFF_EXPIRY_HANDLERS = {
        "sheep_timer": "_on_sheep_expired",
        **_SHARED_BUFF_EXPIRY_HANDLERS,
        "drowsy": "_on_drowsy_expired",
        "terror": "_on_terror_expired",
    }

    def _process_removed_buffs(self, entity, removed: list[str], *, floor,
                               floor_id: int, is_player: bool) -> bool:
        handlers = self._PLAYER_BUFF_EXPIRY_HANDLERS if is_player \
            else self._MOB_BUFF_EXPIRY_HANDLERS
        ran_handlers = set()
        for buff_id, handler in handlers.items():
            if buff_id not in removed or handler in ran_handlers:
                continue
            ran_handlers.add(handler)
            if getattr(self, handler)(entity, floor, floor_id):
                return True
        return False

    def _on_invisibility_expired(self, entity, floor, floor_id=None) -> bool:
        entity.invisible = max(0, entity.invisible - 1)
        return False

    def _on_frozen_expired(self, entity, floor, floor_id=None) -> bool:
        self._frost_thaw(entity, floor)
        return False

    def _on_endure_expired(self, entity, floor, floor_id=None) -> bool:
        self._finalize_endure(entity)
        return False

    def _on_sheep_expired(self, mob, floor, floor_id=None) -> bool:
        if not mob.is_alive:
            return False
        mob.is_alive = False
        self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)
        self.handle_mob_death(mob, floor, floor_id)
        return True

    def _on_drowsy_expired(self, mob, floor, floor_id=None) -> bool:
        if mob.ai_state in ("idle", "wandering"):
            mob.ai_state = "sleeping"
        return False

    def _on_terror_expired(self, mob, floor, floor_id=None) -> bool:
        if mob.ai_state == "fleeing":
            mob.ai_state = "hunting"
        return False

    def _apply_bleed(self, entity) -> None:
        """Bleeding is presence-keyed (still active), not expiry-keyed, so it
        is applied every tick rather than routed through the expiry dispatch."""
        bleed = get_buff(entity.buffs, "bleeding")
        if bleed:
            dmg = max(1, bleed.level)
            entity.take_damage(dmg)
            self.add_event("DAMAGE", {"target": entity.id, "amount": dmg, "bleed": True})
