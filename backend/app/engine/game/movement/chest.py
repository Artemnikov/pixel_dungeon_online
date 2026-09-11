# Copyright (C) 2026 ArtemNikov
#
"""Floor-interaction helpers for GameInstance (part of MovementCombatMixin).

Chests (incl. mimic/crystal-mimic reveal), tombs (wraith spawn), magic wells,
dew drops and small positioning utilities.
"""

import random
import time
import uuid

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction, Position
from app.engine.entities.items.union import Chest
from app.engine.entities.items.consumables import Dewdrop, Waterskin
from app.engine.entities.mobs import CrystalMimic, EbonyMimic, GoldenMimic, Mimic, Wraith
from app.engine.entities.player import Player
from app.engine.entities.scroll_actions import _apply_identify, _apply_remove_curse
from app.engine.game.constants import KEY_TIME_TO_UNLOCK, MAX_FLOOR_ID


class ChestMixin:
    def _spend_unlock_action(self, player: Player) -> None:
        player.action_until = max(player.action_until, time.time() + KEY_TIME_TO_UNLOCK)

    def _player_has_skeleton_key(self, player: Player) -> bool:
        from app.engine.entities.items.artifacts import SkeletonKey
        art = player.belongings.artifact
        return bool(art is not None and isinstance(art, SkeletonKey) and not art.cursed)

    def _items_at(self, floor, x: int, y: int):
        return [item for item in floor.items.values() if item.pos and item.pos.x == x and item.pos.y == y]

    def _entity_at(self, floor, floor_id: int, x: int, y: int, exclude_id: str, active_players_only: bool = False):
        """First living mob or player occupying (x, y), excluding exclude_id.
        Players are checked before mobs. active_players_only additionally
        requires the player be alive and not AFK (used for movement bumps;
        ranged targeting allows hitting any player standing there)."""
        for p in self._players_on_floor(floor_id):
            if p.id == exclude_id or p.pos.x != x or p.pos.y != y:
                continue
            if active_players_only and (not p.is_alive or p.is_afk):
                continue
            return p
        for m in floor.mobs.values():
            if m.id == exclude_id or not m.is_alive or m.pos.x != x or m.pos.y != y:
                continue
            if active_players_only and getattr(m, 'disguised', False):
                continue
            return m
        return None

    def _find_room_containing(self, floor, x: int, y: int):
        for room in floor.rooms:
            if room.x <= x < room.x + room.width and room.y <= y < room.y + room.height:
                return room
        return None

    def _spawn_wraiths_around(self, floor, floor_id: int, player: Player) -> None:
        positions = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                x, y = player.pos.x + dx, player.pos.y + dy
                if not (0 <= x < floor.width and 0 <= y < floor.height):
                    continue
                if not floor.flags or not floor.flags.passable[y][x]:
                    continue
                if any(m.is_alive and m.pos.x == x and m.pos.y == y for m in floor.mobs.values()):
                    continue
                if any(p.is_alive and p.pos.x == x and p.pos.y == y for p in self._players_on_floor(floor_id)):
                    continue
                positions.append((x, y))
        for x, y in positions[:4]:
            wid = str(uuid.uuid4())
            wraith = Wraith(id=wid, type="mob", pos=Position(x=x, y=y), faction=Faction.DUNGEON)
            attack = 10 + floor_id
            wraith.floor_level = floor_id
            wraith.attack_skill = attack
            wraith.defense_skill = attack * 5
            wraith.damage_min = 1 + floor_id // 2
            wraith.damage_max = 2 + floor_id
            floor.mobs[wid] = wraith
            self.add_event("SPAWN_MOB", {"mob": wraith.model_dump()}, floor_id=floor_id)

    def _drop_chest_contents(self, floor, chest: Chest, x: int, y: int) -> None:
        for contained in chest.contents:
            item = contained.model_copy(deep=True)
            item.id = str(uuid.uuid4())
            item.pos = Position(x=x, y=y)
            item.dropped_at = time.time()
            floor.items[item.id] = item

    def _reveal_mimic_for_chest(self, player: Player, floor, floor_id: int, chest_id: str) -> bool:
        """If chest_id is a disguised Mimic's fake chest, reveal the mimic,
        remove the fake chest, and return True.

        Uses Mimic.stop_hiding polymorphism across Mimic, GoldenMimic, EbonyMimic,
        and CrystalMimic subclasses."""
        for mob in list(floor.mobs.values()):
            if not isinstance(mob, Mimic) or not mob.disguised or not mob.is_alive:
                continue
            if mob.fake_chest_id != chest_id:
                continue
            mob.stop_hiding(self, player, floor, floor_id)
            return True
        return False

    def _reveal_crystal_mimic_for_chest(self, player: Player, floor, floor_id: int, chest_id: str) -> bool:
        """Backward-compatible wrapper for _reveal_mimic_for_chest."""
        return self._reveal_mimic_for_chest(player, floor, floor_id, chest_id)

    def _pickup_dewdrop(self, player, floor, floor_id: int, item_id: str, dew) -> bool:
        """SPD Dewdrop.doPickUp: a non-full waterskin collects the drop;
        otherwise it is drunk on the spot (5% max HP per drop, Shielding Dew
        overflow to a shield) and refused entirely when it would do nothing —
        unless standing on an entrance/exit tile, which force-consumes it."""
        waterskin = next(
            (i for i in player.belongings.all_items() if isinstance(i, Waterskin) and not i.is_full()),
            None,
        )
        if waterskin is not None:
            waterskin.volume = min(Waterskin.MAX_VOLUME, waterskin.volume + dew.quantity)
            del floor.items[item_id]
            self.add_event("COLLECT_DEW", {"player": player.id, "item": waterskin.id}, floor_id=floor_id)
            return True

        max_hp = player.get_total_max_hp()
        effect = round(max_hp * 0.05 * dew.quantity)
        heal = min(max_hp - player.hp, effect)

        shield = 0
        shielding_dew = player.talent_info.level("shielding_dew")
        if shielding_dew > 0:
            max_shield = round(max_hp * 0.2 * shielding_dew)
            cur_shield = player.get_shield("dew").amount if player.get_shield("dew") else 0
            shield = min(effect - heal, max_shield - cur_shield)

        tile = floor.grid[player.pos.y][player.pos.x]
        force = tile in (TileType.STAIRS_UP, TileType.STAIRS_DOWN)
        if heal <= 0 and shield <= 0 and not force:
            return False  # already full: leave the drop on the ground

        if heal > 0:
            player.hp += heal
            self.add_event("HEAL", {"target": player.id, "amount": heal, "x": player.pos.x, "y": player.pos.y}, floor_id=floor_id)
        if shield > 0:
            player.add_shield("dew", shield, priority=0)
        del floor.items[item_id]
        self.add_event("PLAY_SOUND", {"sound": "DEWDROP"}, floor_id=floor_id, source_player_id=player.id)
        return True

    def _teleport_entity_to_free_cell(self, entity, floor, floor_id: int) -> None:
        candidates = []
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = entity.pos.x + dx, entity.pos.y + dy
                if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                    continue
                if not floor.flags or not floor.flags.passable[ny][nx]:
                    continue
                if any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values()):
                    continue
                candidates.append((nx, ny))
        if not candidates:
            return
        nx, ny = random.choice(candidates)
        entity.pos = Position(x=nx, y=ny)
        self.add_event("TELEPORT", {"entity": entity.id, "x": nx, "y": ny}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "TELEPORT"}, floor_id=floor_id)

    def _try_open_chest(self, player: Player, floor, floor_id: int, chest: Chest) -> bool:
        if chest.pos is None:
            return False
        x, y = chest.pos.x, chest.pos.y

        if (chest.mimic_hint or chest.chest_type in ("CHEST", "LOCKED_CHEST", "CRYSTAL_CHEST")) and self._reveal_mimic_for_chest(player, floor, floor_id, chest.id):
            self._spend_unlock_action(player)
            return True

        is_locked = chest.chest_type in ("LOCKED_CHEST", "CRYSTAL_CHEST")

        # Already being unlocked by another player — don't double-spend a key.
        if is_locked and (x, y) in floor.pending_unlocks:
            return True

        if is_locked and not player.remove_key(
            "golden" if chest.chest_type == "LOCKED_CHEST" else "crystal", floor_id
        ):
            self.add_event("LOCKED", {"player": player.id, "x": x, "y": y}, floor_id=floor_id)
            return False

        if is_locked:
            # Key consumed + input blocked now; the chest stays closed while the
            # hero plays the operate animation, then the tick resolves the pending
            # unlock (contents drop + sound) once KEY_TIME_TO_UNLOCK passes.
            self._spend_unlock_action(player)
            self.add_event("UNLOCK", {"player": player.id, "x": x, "y": y}, floor_id=floor_id)
            self._register_pending_unlock(floor, x, y, "chest", player.id, chest_id=chest.id)
            return True

        self._spend_unlock_action(player)
        floor.items.pop(chest.id, None)
        if chest.chest_type == "TOMB":
            self.add_event("PLAY_SOUND", {"sound": "TOMB"}, floor_id=floor_id)
            self._spawn_wraiths_around(floor, floor_id, player)
        elif chest.chest_type in ("SKELETON", "REMAINS"):
            self.add_event("PLAY_SOUND", {"sound": "BONES", "x": x, "y": y}, floor_id=floor_id)
        else:
            self.add_event("PLAY_SOUND", {"sound": "UNLOCK"}, floor_id=floor_id)
        self._drop_chest_contents(floor, chest, x, y)
        self.add_event("OPEN_CHEST", {"player": player.id, "x": x, "y": y, "chest_type": chest.chest_type}, floor_id=floor_id)
        self._queue_chest_respawn(floor, chest)
        return True

    def _drink_from_well(self, player: Player, floor, floor_id: int, x: int, y: int) -> None:
        """Port of WellWater.affectCell/affectHero for the two MagicWellRoom
        types (WaterOfHealth/WaterOfAwareness). Simplified to a single-charge
        well (levelgen records which water type this well rolled in
        generation_meta['magic_wells']) rather than SPD's depleting Blob
        volume -- the well empties on first use instead of draining gradually."""
        wells = floor.generation_meta.get("magic_wells", [])
        well = next((w for w in wells if w.get("pos") == (x, y) and not w.get("used")), None)
        if well is None:
            return
        well["used"] = True

        floor.grid[y][x] = TileType.FLOOR
        self.add_event("MAP_PATCH", {"tiles": [{"x": x, "y": y, "tile": TileType.FLOOR}]}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "DRINK"}, floor_id=floor_id, source_player_id=player.id)

        if well["water_type"] == "health":
            player.hp = player.get_total_max_hp()
            player.hunger = 0.0
            for item in player.belongings.equipped_slots():
                if item is not None and getattr(item, "cursed", False):
                    _apply_remove_curse(self, player, item)
            self.add_event("DRINK", {"player": player.id, "type": "well_of_health"}, floor_id=floor_id, source_player_id=player.id)
            self.add_event("HEAL", {"target": player.id, "amount": player.get_total_max_hp()}, floor_id=floor_id)
        else:
            for item in player.belongings.all_items():
                if not item.is_identified():
                    _apply_identify(self, player, item)
            for (tx, ty), actual_tile in list(floor.hidden_doors.items()):
                floor.hidden_doors.pop((tx, ty))
                floor.grid[ty][tx] = actual_tile
                self.add_event("MAP_PATCH", {"tiles": [{"x": tx, "y": ty, "tile": actual_tile}]}, floor_id=floor_id)
            for (tx, ty), trap in floor.traps.items():
                if trap.hidden:
                    trap.hidden = False
                    if floor.grid[ty][tx] == TileType.SECRET_TRAP:
                        floor.grid[ty][tx] = TileType.TRAP
                        self.add_event("MAP_PATCH", {"tiles": [{"x": tx, "y": ty, "tile": TileType.TRAP}]}, floor_id=floor_id)
            self.add_event("DRINK", {"player": player.id, "type": "well_of_awareness"}, floor_id=floor_id, source_player_id=player.id)

        floor.rebuild_flags()
