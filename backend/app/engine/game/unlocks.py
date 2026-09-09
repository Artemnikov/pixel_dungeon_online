# Copyright (C) 2026 ArtemNikov
#
"""Two-phase door/chest unlocking.

A locked door or locked/crystal chest does not open instantly on bump: the
key is consumed and the input blocked immediately, the hero plays the operate
animation, and only once `KEY_TIME_TO_UNLOCK` passes does the tick resolve the
pending entry — swapping the tile / dropping the contents and playing the
unlock sound. This matches SPD's actUnlock → onOperateComplete flow.
"""

import time

from app.engine.dungeon.constants import TileType
from app.engine.game.constants import KEY_TIME_TO_UNLOCK


class PendingUnlocksMixin:
    def _register_pending_unlock(self, floor, x: int, y: int, kind: str,
                                 player_id: str, chest_id=None) -> None:
        """Record a door/chest unlock that should complete in
        KEY_TIME_TO_UNLOCK seconds (the length of the operate animation)."""
        floor.pending_unlocks[(x, y)] = {
            "ready_at": time.time() + KEY_TIME_TO_UNLOCK,
            "kind": kind,
            "player": player_id,
            "chest_id": chest_id,
        }

    def _process_pending_unlocks(self, floor, floor_id: int) -> None:
        """Resolve any pending unlocks whose animation has finished."""
        if not floor.pending_unlocks:
            return
        now = time.time()
        for (x, y), entry in list(floor.pending_unlocks.items()):
            if entry["ready_at"] > now:
                continue
            kind = entry["kind"]
            if kind == "door":
                self._finish_door_unlock(floor, floor_id, x, y, entry)
            elif kind == "chest":
                self._finish_chest_unlock(floor, floor_id, x, y, entry)
            floor.pending_unlocks.pop((x, y), None)

    def _finish_door_unlock(self, floor, floor_id: int, x: int, y: int, entry) -> None:
        tile = floor.grid[y][x]
        if tile == TileType.LOCKED_EXIT:
            new_tile = TileType.STAIRS_DOWN
        elif tile == TileType.CRYSTAL_DOOR:
            new_tile = TileType.FLOOR
        elif tile == TileType.HERO_LKD_DR:
            new_tile = TileType.DOOR
        else:
            new_tile = TileType.DOOR
        floor.grid[y][x] = new_tile
        floor.locked_doors.pop((x, y), None)
        # Tile mutated from LOCKED_* to an open tile — refresh flag maps so
        # LOS/pathfinding sees it as passable now.
        floor.rebuild_flags()
        self.add_event("MAP_PATCH", {"tiles": [{"x": x, "y": y, "tile": new_tile}]},
                       floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "UNLOCK"}, floor_id=floor_id)

    def _finish_chest_unlock(self, floor, floor_id: int, x: int, y: int, entry) -> None:
        chest = floor.items.pop(entry.get("chest_id"), None)
        if chest is None:
            return
        self._drop_chest_contents(floor, chest, x, y)
        self.add_event("OPEN_CHEST",
                       {"player": entry.get("player"), "x": x, "y": y,
                        "chest_type": chest.chest_type},
                       floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "UNLOCK"}, floor_id=floor_id)
        self._queue_chest_respawn(floor, chest)
