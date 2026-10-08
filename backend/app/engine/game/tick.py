from app.engine.entities.buffs import get_buff, has_buff
from app.engine.game.constants import TICK_DURATION
from app.engine.game.tick_steps import (
    finalize_dead_players,
    run_blob_round_upkeep,
    run_buff_upkeep,
    run_dot_upkeep,
    run_hazard_round_upkeep,
    run_respawn_upkeep,
    run_world_round_upkeep,
    sync_all_effects,
)

from app.engine.game.spawning import _universal_extra_pool  # noqa: F401


class TickMixin:
    def update_tick(self):
        self._invalidate_fov_cache()

        dt = TICK_DURATION
        active_ids = self.active_floor_ids

        for player in self.players.values():
            run_buff_upkeep(
                self, player,
                self._get_or_create_floor(player.floor_id),
                player.floor_id, True, dt,
            )
            self._tick_dust_ghost_spawner(player)

        for floor_id in active_ids:
            floor = self.floors[floor_id]
            for mob in floor.mobs.values():
                if not mob.is_alive:
                    continue
                run_buff_upkeep(self, mob, floor, floor_id, False, dt)

        run_blob_round_upkeep(self, active_ids)

        for floor_id in active_ids:
            run_hazard_round_upkeep(self, floor_id)

        self._emit_state_effects()

        finalize_dead_players(self)
        sync_all_effects(self)

        for player in self.players.values():
            self._tick_player(player, dt)

        for floor_id in active_ids:
            floor = self.floors[floor_id]
            active_players = [p for p in self._players_on_floor(floor_id) if p.is_alive and not p.is_downed]
            if not active_players:
                continue

            run_dot_upkeep(self, floor_id, active_players)
            run_respawn_upkeep(self, floor_id, floor, active_players)
            self._update_prison_boss(floor, floor_id)

            time_frozen = any(has_buff(p.buffs, "time_bubble") for p in active_players)
            if not time_frozen:
                for mob in list(floor.mobs.values()):
                    self._tick_mob(mob, floor, floor_id)

        run_world_round_upkeep(self)

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
