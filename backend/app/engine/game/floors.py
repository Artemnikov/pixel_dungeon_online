"""Floor access and lookup helpers for GameInstance.

The legacy single-floor API (``grid``, ``rooms``, ``mobs``, ``items``, ``width``,
``height``) is exposed here as compatibility properties that proxy to the current
depth's FloorState, alongside the multi-floor lookup helpers and the
eviction/cache layer that keeps only active-player floors in hot memory.
"""

import pickle
from typing import Dict, List, Optional, Set, Tuple

from app.engine.entities.base import Item, Mob as MobEntity, Player
from app.engine.game.constants import MAP_HEIGHT, MAP_WIDTH, MAX_FLOOR_ID
from app.engine.game.floor_state import FloorState


class FloorAccessMixin:
    @property
    def width(self) -> int:
        """Current-depth floor width. Read-only compatibility view for the
        generator seed, the client snapshot, and single-floor tests — never use
        for per-floor logic (use the floor's own width). Falls back to the seed
        constant before the current floor exists."""
        f = self.floors.get(self.depth)
        return f.width if f else MAP_WIDTH

    @property
    def height(self) -> int:
        f = self.floors.get(self.depth)
        return f.height if f else MAP_HEIGHT

    @property
    def grid(self) -> List[List[int]]:
        return self._get_or_create_floor(self.depth).grid

    @grid.setter
    def grid(self, value: List[List[int]]):
        self._get_or_create_floor(self.depth).grid = value

    @property
    def rooms(self) -> List[object]:
        return self._get_or_create_floor(self.depth).rooms

    @rooms.setter
    def rooms(self, value: List[object]):
        self._get_or_create_floor(self.depth).rooms = value

    @property
    def mobs(self) -> Dict[str, MobEntity]:
        return self._get_or_create_floor(self.depth).mobs

    @mobs.setter
    def mobs(self, value: Dict[str, MobEntity]):
        self._get_or_create_floor(self.depth).mobs = value

    @property
    def items(self) -> Dict[str, Item]:
        return self._get_or_create_floor(self.depth).items

    @items.setter
    def items(self, value: Dict[str, Item]):
        self._get_or_create_floor(self.depth).items = value

    @property
    def active_floor_ids(self) -> Set[int]:
        """Floor IDs that have at least one alive, non-downed player.

        Used by the tick loop to restrict processing to floors where
        gameplay actually matters (mob AI, blobs, state effects)."""
        return {
            p.floor_id
            for p in self.players.values()
            if p.is_alive and not p.is_downed
        }

    def _get_or_create_floor(self, floor_id: int) -> FloorState:
        floor_id = max(1, min(MAX_FLOOR_ID, floor_id))
        if floor_id in self.floors:
            return self.floors[floor_id]
        if floor_id in self.floor_cache:
            floor = pickle.loads(self.floor_cache.pop(floor_id))
            self.floors[floor_id] = floor
            return floor
        return self.generate_floor(floor_id)

    def _evict_floor(self, floor_id: int) -> None:
        """Pickle and remove *floor_id* from hot memory.

        Only evicts when **zero** players remain on the floor.  The pickled
        blob is stored in ``self.floor_cache`` so the floor can be restored
        verbatim on re-entry (preserving mob UIDs, boss state, blob areas,
        opened doors, …)."""
        if floor_id not in self.floors:
            return
        if self._players_on_floor(floor_id):
            return
        floor = self.floors.pop(floor_id)
        self.floor_cache[floor_id] = pickle.dumps(floor)

    def _evict_empty_floors(self) -> None:
        """Post-tick sweep — evict every floor that no player references.

        Catches edge-cases such as players that disconnected mid-tick (and
        have since been reaped) or dynamic player removal."""
        occupied = {p.floor_id for p in self.players.values()}
        for fid in list(self.floors.keys()):
            if fid not in occupied:
                self._evict_floor(fid)

    def _find_mob_floor(self, mob_id: str) -> Optional[int]:
        for floor_id, floor in self.floors.items():
            if mob_id in floor.mobs:
                return floor_id
        return None

    def _get_floor_for_entity(self, entity_id: str) -> Tuple[Optional[int], Optional[object]]:
        if entity_id in self.players:
            player = self.players[entity_id]
            return player.floor_id, player

        mob_floor = self._find_mob_floor(entity_id)
        if mob_floor is None:
            return None, None

        floor = self._get_or_create_floor(mob_floor)
        return mob_floor, floor.mobs.get(entity_id)

    def _players_on_floor(self, floor_id: int) -> List[Player]:
        return [p for p in self.players.values() if p.floor_id == floor_id]

    def _boss_lurking_on_floor(self, floor_id: int) -> bool:
        """True while a sealed-arena boss (Goo, DM300, Dwarf King, Yog-Dzewa)
        is alive on the floor but hasn't been engaged yet (SPD
        SewerBossLevel.playLevelMusic(): ambient track silenced while the
        boss lives, even before notice())."""
        floor = self.floors.get(floor_id)
        if floor is None:
            return False
        return any(
            m.is_alive and getattr(m, "fight_started", True) is False
            for m in floor.mobs.values()
        )
