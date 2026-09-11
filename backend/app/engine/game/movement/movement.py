# Copyright (C) 2026 ArtemNikov
#
"""Stepping logic for GameInstance (part of MovementCombatMixin).

Held-direction intent, step resolution (doors, chests, wells, chasms, traps,
grass, stairs) and per-step effects like auto-pickup.
"""

import time

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import is_immune
from app.engine.entities.items.union import Chest
from app.engine.entities.items.bombs import Bomb
from app.engine.entities.items.consumables import Amulet, CorpseDust, Dewdrop, EnergyCrystal, Gold, Key, LostBackpack
from app.engine.entities.player import Player
from app.engine.entities.buffs import add_buff, break_stationary_plant_buffs, has_buff, is_frozen
from app.engine.game.constants import AUTO_MOVE_INTERVAL, MAX_FLOOR_ID, MAX_PLAYER_INPUT_QUEUE
from app.engine.game.terrain_effects import press_cell
from app.engine.talents.registry import registry
from typing import Optional


class MovementMixin:
    def queue_move_step(self, entity_id: str, seq: int, dx: int, dy: int, replaces: Optional[int] = None):
        player = self.players.get(entity_id)
        if player is None or player.is_downed or not player.is_alive:
            return
        # Client-supplied deltas must be unit steps (8-dir); anything larger
        # would teleport through walls since move_entity only validates the
        # final cell. Non-unit steps are dropped, not clamped, so a broken
        # client is visible and a malicious one gains nothing.
        if max(abs(dx), abs(dy)) > 1:
            return
        player.movement.enqueue_step(seq, dx, dy, replaces=replaces)

    def stop_move(self, entity_id: str, last_seq: Optional[int] = None):
        player = self.players.get(entity_id)
        if player is None:
            return
        player.movement.stop(last_seq)

    def _has_enemies_nearby(self, floor, player, radius: int = 3) -> bool:
        return any(
            m.is_alive and m.faction == "dungeon"
            for m in floor.mobs.values()
            if abs(m.pos.x - player.pos.x) + abs(m.pos.y - player.pos.y) <= radius
        )

    def set_move_intent(self, entity_id: str, dx: int, dy: int):
        player = self.players.get(entity_id)
        if player is None:
            return
        # Held-direction intents are single-tile steps; clamp client-supplied
        # values to the unit range so a crafted MOVE_INTENT can't warp the
        # player across the floor one step at a time.
        dx = max(-1, min(1, dx))
        dy = max(-1, min(1, dy))
        if dx == 0 and dy == 0:
            if player.movement.move_intent is not None and player.movement.initial_step_pending:
                step_dx, step_dy = player.movement.move_intent
                player.movement.stop()
                player.movement.last_auto_move_time = time.time()
                self.move_entity(player.id, step_dx, step_dy)
                return
            player.movement.stop()
            return
        player.movement.set_intent(dx, dy, AUTO_MOVE_INTERVAL)

    def attack_mob(self, player_id: str, target_id: str) -> None:
        """Click-to-attack (ATTACK): step the player toward a specific mob
        by one tile; a step onto/into an occupied enemy cell resolves as a
        melee attack in move_entity."""
        player = self.players.get(player_id)
        if not player:
            return
        floor = self._get_or_create_floor(player.floor_id)
        mob = floor.mobs.get(target_id)
        if mob and mob.is_alive:
            dx = mob.pos.x - player.pos.x
            dy = mob.pos.y - player.pos.y
            # Melee only reaches chebyshev-adjacent targets. Without this a
            # crafted ATTACK would feed the full delta to move_entity, which
            # only validates the final cell -- letting the player teleport
            # through walls and hit anything on the floor in one step.
            if max(abs(dx), abs(dy)) > 1:
                return
            self.move_entity(player_id, dx, dy)

    def move_entity(self, entity_id: str, dx: int, dy: int, seq: Optional[int] = None):
        floor_id, entity = self._get_floor_for_entity(entity_id)
        if entity is None or floor_id is None:
            return

        floor = self._get_or_create_floor(floor_id)

        if isinstance(entity, Player) and time.time() < entity.action_until:
            return

        if isinstance(entity, Player) and entity.is_downed:
            return

        # Defense-in-depth: seq'd steps come from the client message path and
        # must be unit moves. Internal multi-tile pushes (knockback, wall-slam)
        # never carry a seq, so they're unaffected.
        if (
            isinstance(entity, Player)
            and seq is not None
            and max(abs(dx), abs(dy)) > 1
        ):
            return

        # Stagger blocks all movement and attacks (bump-attacks route through
        # move_entity).  Applied by Wand of Blast Wave wall-slam.
        if has_buff(entity.buffs, "stagger"):
            return

        # SPD Frost roots the character (paralysed++): a frozen player can't move
        # or attack, and a frozen mob can neither step nor strike (mob attacks are
        # move_entity calls into the target's tile, so this gates those too).
        if is_frozen(entity.buffs):
            return

        new_x = entity.pos.x + dx
        new_y = entity.pos.y + dy

        if not (0 <= new_x < floor.width and 0 <= new_y < floor.height):
            return

        # Any movement attempt cancels a stale chasm-fall confirmation prompt
        # (the player did something else instead of confirming).
        if isinstance(entity, Player):
            entity.pending_chasm_fall = None

        # Diagonal moves past a wall corner are allowed, matching SPD's PathFinder
        # (it only checks the destination cell's passability, not the orthogonal cells).

        target_entity = self._entity_at(floor, floor_id, new_x, new_y, entity_id, active_players_only=True)
        if target_entity:
            self._resolve_bump(entity, target_entity, floor, floor_id)
            if isinstance(entity, Player):
                res_data = {"entity": entity_id, "x": entity.pos.x, "y": entity.pos.y, "ok": False}
                if seq is not None:
                    res_data["seq"] = seq
                self.add_event("MOVE_RESULT", res_data, player_id=entity_id)
            return

        tile = floor.grid[new_y][new_x]
        if tile == TileType.HERO_LKD_DR and isinstance(entity, Player):
            # SPD Hero.actUnlock (HERO_LKD_DR): a door the hero locked with
            # their SkeletonKey refuses to open by bump while a non-cursed
            # key is equipped; otherwise it opens freely, no key/charge.
            if self._player_has_skeleton_key(entity):
                self.add_event("MESSAGE",
                               {"text": "That door was locked by your skeleton key."},
                               floor_id=floor_id, player_id=entity.id)
                return
            floor.grid[new_y][new_x] = TileType.DOOR
            floor.rebuild_flags()
            self.add_event("MAP_PATCH",
                           {"tiles": [{"x": new_x, "y": new_y, "tile": TileType.DOOR}]},
                           floor_id=floor_id)
            return

        if tile in (TileType.LOCKED_DOOR, TileType.CRYSTAL_DOOR, TileType.LOCKED_EXIT):
            if not isinstance(entity, Player):
                return
            self._try_unlock_locked_door(entity, floor, new_x, new_y)
            return

        if isinstance(entity, Player):
            chest = next((item for item in self._items_at(floor, new_x, new_y) if isinstance(item, Chest)), None)
            if chest is not None:
                self._try_open_chest(entity, floor, floor_id, chest)
                return

        if tile == TileType.WELL:
            if isinstance(entity, Player):
                self._drink_from_well(entity, floor, floor_id, new_x, new_y)
            return

        if tile == TileType.CHASM:
            # Mobs never voluntarily step into a chasm (AI pathing already
            # avoids it via AVOID/PIT — see vision.py); this only guards
            # against an entity somehow ending up adjacent regardless.
            if isinstance(entity, Player) and floor_id < MAX_FLOOR_ID:
                entity.pending_chasm_fall = (new_x, new_y)
                self.add_event("CHASM_PROMPT", {"x": new_x, "y": new_y}, floor_id=floor_id, player_id=entity.id)
            return

        if not floor.flags or not (floor.flags.passable[new_y][new_x] or floor.flags.avoid[new_y][new_x]):
            return

        old_x, old_y = entity.pos.x, entity.pos.y
        entity.move(dx, dy)

        self._ignite_if_on_fire(entity, floor, new_x, new_y)
        self._handle_door_transition(entity, floor, floor_id, old_x, old_y)
        break_stationary_plant_buffs(entity)

        # Position changed: door mutation may have changed flags and FOV.
        self._invalidate_fov_cache()

        # Terrain interaction (trample grass, trigger plants, etc.)
        result = press_cell(floor, (entity.pos.x, entity.pos.y), entity)
        if result["tile_changed"]:
            self.add_event("MAP_PATCH", {"tiles": [{"x": entity.pos.x, "y": entity.pos.y, "tile": floor.grid[entity.pos.y][entity.pos.x]}]}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "STEP_GRASS", "x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id, source_player_id=entity.id if isinstance(entity, Player) else None)
        if result.get("grass_trampled"):
            self.add_event("LEAF_BURST", {"x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id)
        if result["triggered_plant"]:
            plant_type = result["triggered_plant"].get("plant_type", "sungrass")
            plant_pos = result["triggered_plant"].get("pos", (new_x, new_y))
            self.add_event("PLANT_TRIGGERED", {
                "plant": plant_type,
                "player": entity.id if isinstance(entity, Player) else None,
                "x": plant_pos[0],
                "y": plant_pos[1],
            }, floor_id=floor_id)

        if isinstance(entity, Player):
            self._player_step_effects(entity, entity_id, floor_id)
            self._auto_pickup_on_step(entity, floor)

        self._trigger_trap_if_needed(floor, entity, floor_id)

        if isinstance(entity, Player):
            if entity.pending_ascend:
                entity.pending_ascend = False
                self._apply_fadeleaf_ascend(entity, entity_id, floor_id)
            self._handle_stairs_tile(entity, entity_id, tile, floor, floor_id)
            res_data = {"entity": entity_id, "x": entity.pos.x, "y": entity.pos.y, "ok": True}
            if seq is not None:
                res_data["seq"] = seq
            self.add_event("MOVE_RESULT", res_data, player_id=entity_id)

    def _apply_fadeleaf_ascend(self, entity: Player, entity_id: str, floor_id: int) -> None:
        """Warden Fadeleaf: move up one depth (SPD Fadeleaf.activate)."""
        if entity.floor_id > 1:
            self._move_player_to_floor(entity, entity.floor_id - 1, TileType.STAIRS_DOWN)
            self.add_event("STAIRS_UP", {"player": entity_id}, player_id=entity_id)

    def _ignite_if_on_fire(self, entity, floor, x: int, y: int) -> None:
        """Fire tiles ignite entities on contact (SPD: Blob checks on movement)."""
        for b in floor.blob_areas.values():
            if b.get("type") == "fire" and (x, y) in b.get("cells", set()):
                if not has_buff(entity.buffs, "burning") and not is_immune(entity, "burning"):
                    add_buff(entity.buffs, "burning", duration=8.0, level=1, stack_mode="extend")

    def _handle_door_transition(self, entity, floor, floor_id: int, old_x: int, old_y: int) -> None:
        """Door enter/leave tile mutation: stepping onto a closed DOOR opens
        it; leaving an open door closes it (if no other entity is on it)."""
        door_changed = False
        door_patches = []
        if floor.grid[entity.pos.y][entity.pos.x] == TileType.DOOR:
            floor.grid[entity.pos.y][entity.pos.x] = TileType.OPEN_DOOR
            door_changed = True
            door_patches.append({"x": entity.pos.x, "y": entity.pos.y, "tile": TileType.OPEN_DOOR})
            if not isinstance(entity, Player):
                # Player door-open sound is inferred client-side from MOVE;
                # mobs never emit MOVE, so broadcast it explicitly here,
                # LOS-filtered by tile position (same as mob HIT_BODY).
                self.add_event("PLAY_SOUND", {"sound": "DOOR_OPEN", "x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id)
        if floor.grid[old_y][old_x] == TileType.OPEN_DOOR:
            has_entity = any(
                p.pos.x == old_x and p.pos.y == old_y
                for p in self._players_on_floor(floor_id)
            )
            if not has_entity:
                has_entity = any(
                    m.is_alive and m.pos.x == old_x and m.pos.y == old_y
                    for m in floor.mobs.values()
                )
            if not has_entity:
                floor.grid[old_y][old_x] = TileType.DOOR
                door_changed = True
                door_patches.append({"x": old_x, "y": old_y, "tile": TileType.DOOR})

        if door_changed:
            floor.rebuild_flags()
            # StateUpdateMessage doesn't carry the grid (only INIT does, on
            # floor change) — clients only learn about this tile flip via a
            # MAP_PATCH event, same mechanism as unlocking/grass-trample.
            self.add_event("MAP_PATCH", {"tiles": door_patches}, floor_id=floor_id)

    def _player_step_effects(self, entity: Player, entity_id: str, floor_id: int) -> None:
        """MOVE event + per-step player-only effects (Freerunner Momentum,
        Rejuvenating Steps healing)."""
        self.add_event("MOVE", {"entity": entity_id, "x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id)
        # Freerunner builds Momentum on each step.
        self.gain_momentum(entity)
        registry.dispatch("on_step", entity, self, payload={"floor_id": floor_id})

    def _auto_pickup_on_step(self, entity: Player, floor) -> None:
        """SPD-style auto-pickup: items under the hero's feet after a step
        (distinct from the explicit PICKUP_FLOOR action -- see
        ItemsMixin.pickup_floor_items)."""
        items_to_pickup = [
            (i_id, i)
            for i_id, i in list(floor.items.items())
            if i.pos and i.pos.x == entity.pos.x and i.pos.y == entity.pos.y
            and i.type != "grave"
            and not getattr(i, 'for_sale', False)
            and (i.pos.x, i.pos.y) not in floor.pending_unlocks
        ]
        for i_id, item in items_to_pickup:
            if i_id in floor.items:
                item.do_pickup(self, entity, floor, i_id)

    def _handle_stairs_tile(self, entity: Player, entity_id: str, tile: int, floor, floor_id: int) -> None:
        """STAIRS_DOWN/STAIRS_UP transitions, including the depth-1 victory
        check when stepping onto the surface exit with the Amulet."""
        if tile == TileType.STAIRS_DOWN and entity.floor_id < MAX_FLOOR_ID:
            first_visit = entity.floor_id + 1 > entity.floors_explored
            self._move_player_to_floor(entity, entity.floor_id + 1, TileType.STAIRS_UP)
            self.add_event("STAIRS_DOWN", {"player": entity_id, "first_visit": first_visit}, player_id=entity_id)

        if tile == TileType.STAIRS_UP and entity.floor_id > 1:
            self._move_player_to_floor(entity, entity.floor_id - 1, TileType.STAIRS_DOWN)
            self.add_event("STAIRS_UP", {"player": entity_id}, player_id=entity_id)

        if tile == TileType.STAIRS_UP and entity.floor_id == 1:
            if any(isinstance(it, Amulet) for it in entity.belongings.all_items()):
                self._complete_victory(entity, floor, floor_id)
            else:
                self.add_event(
                    "MESSAGE",
                    {"text": "You can't leave yet, the rest of the dungeon awaits below!"},
                    player_id=entity_id,
                )
