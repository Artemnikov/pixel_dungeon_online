from typing import Tuple

from app.engine.dungeon.constants import TileType
from app.engine.dungeon.models import Room


class CorridorsMixin:
    """Mixin for room painting and corridor carving."""

    def _create_room(self, room: Room):
        for y in range(room.y, room.y + room.height):
            for x in range(room.x, room.x + room.width):
                self.grid[y][x] = TileType.FLOOR

        corners = {
            (room.x - 1, room.y - 1),
            (room.x + room.width, room.y - 1),
            (room.x - 1, room.y + room.height),
            (room.x + room.width, room.y + room.height),
        }
        for y in range(room.y - 1, room.y + room.height + 1):
            for x in range(room.x - 1, room.x + room.width + 1):
                if (x, y) in corners:
                    continue
                if 0 <= x < self.width and 0 <= y < self.height and self.grid[y][x] == TileType.VOID:
                    self.grid[y][x] = TileType.WALL

    def _create_tunnel(self, start: Tuple[int, int], end: Tuple[int, int]):
        x1, y1 = start
        x2, y2 = end

        if self.rng.random() < 0.5:
            self._h_tunnel(x1, x2, y1)
            self._v_tunnel(y1, y2, x2)
        else:
            self._v_tunnel(y1, y2, x1)
            self._h_tunnel(x1, x2, y2)

    def _h_tunnel(self, x1: int, x2: int, y: int):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if self.grid[y][x] == TileType.VOID:
                self.grid[y][x] = TileType.FLOOR
            elif self.grid[y][x] == TileType.WALL:
                self.grid[y][x] = TileType.DOOR

            if y > 0 and self.grid[y - 1][x] == TileType.VOID:
                self.grid[y - 1][x] = TileType.WALL
            if y < self.height - 1 and self.grid[y + 1][x] == TileType.VOID:
                self.grid[y + 1][x] = TileType.WALL

    def _v_tunnel(self, y1: int, y2: int, x: int):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if self.grid[y][x] == TileType.VOID:
                self.grid[y][x] = TileType.FLOOR
            elif self.grid[y][x] == TileType.WALL:
                self.grid[y][x] = TileType.DOOR

            if x > 0 and self.grid[y][x - 1] == TileType.VOID:
                self.grid[y][x - 1] = TileType.WALL
            if x < self.width - 1 and self.grid[y][x + 1] == TileType.VOID:
                self.grid[y][x + 1] = TileType.WALL

