import random
from collections import deque
from typing import List, Optional, Tuple

from app.engine.dungeon.constants import TileType  # noqa: F401 — re-exported (many callers import it from here)
from app.engine.dungeon.models import Room, TrapInfo  # noqa: F401 — TrapInfo re-exported, same reason
from app.engine.dungeon.corridors import CorridorsMixin


class DungeonGenerator(CorridorsMixin):
    def __init__(self, width: int, height: int, seed: Optional[int] = None):
        self.width = width
        self.height = height
        self.grid = [[TileType.VOID for _ in range(width)] for _ in range(height)]
        self.rooms: List[Room] = []
        # Per-instance RNG — SPD equivalent of Random.pushGenerator(Dungeon.seedCurDepth()).
        # When seed is None, falls back to a random seed so generation stays varied
        # in contexts that don't thread seeds yet.
        self.seed = seed if seed is not None else random.Random().getrandbits(32)
        self.rng = random.Random(self.seed)

    def generate(
        self, max_rooms: int, min_room_size: int, max_room_size: int
    ) -> Tuple[List[List[int]], List[Room]]:
        self.rooms = []

        max_retries = 10
        for _ in range(max_retries):
            self.grid = [[TileType.VOID for _ in range(self.width)] for _ in range(self.height)]
            self.rooms = []

            for _ in range(max_rooms):
                w = self.rng.randint(min_room_size, max_room_size)
                h = self.rng.randint(min_room_size, max_room_size)
                x = self.rng.randint(1, self.width - w - 1)
                y = self.rng.randint(1, self.height - h - 1)

                new_room = Room(x, y, w, h)

                if any(new_room.intersects(other) for other in self.rooms):
                    continue

                self._create_room(new_room)

                if self.rooms:
                    prev_center = self.rooms[-1].center
                    new_center = new_room.center
                    self._create_tunnel(prev_center, new_center)

                self.rooms.append(new_room)

            if self.is_connected() and len(self.rooms) > 1:
                break

        if self.rooms:
            up_x, up_y = self.rooms[0].center
            down_x, down_y = self.rooms[-1].center
            self.grid[up_y][up_x] = TileType.STAIRS_UP
            self.grid[down_y][down_x] = TileType.STAIRS_DOWN

        return self.grid, self.rooms

    def is_connected(self) -> bool:
        if not self.rooms:
            return True

        start_x, start_y = self.rooms[0].center
        if self.grid[start_y][start_x] == TileType.WALL:
            return False

        q = deque([(start_x, start_y)])
        visited = {(start_x, start_y)}

        while q:
            cx, cy = q.popleft()
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.width and 0 <= ny < self.height and (nx, ny) not in visited:
                    tile = self.grid[ny][nx]
                    if tile != TileType.WALL and tile != TileType.VOID:
                        visited.add((nx, ny))
                        q.append((nx, ny))

        for room in self.rooms:
            if room.center not in visited:
                return False
        return True
