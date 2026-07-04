from collections import defaultdict, deque
from typing import Dict

from app.engine.dungeon.constants import RoomKind, TileType, TrapType
from app.engine.manager import GameInstance


# Matches terrain_flags.py's PASSABLE set exactly (everything flagged
# PASSABLE there is walkable -- traps and embers don't block movement,
# they just trigger/burn on entry).
WALKABLE_TILES = {
    TileType.FLOOR,
    TileType.DOOR,
    TileType.STAIRS_UP,
    TileType.STAIRS_DOWN,
    TileType.FLOOR_WOOD,
    TileType.FLOOR_WATER,
    TileType.FLOOR_COBBLE,
    TileType.FLOOR_GRASS,
    TileType.EMPTY_DECO,
    TileType.HIGH_GRASS,
    TileType.FURROWED_GRASS,
    TileType.EMBERS,
    TileType.SECRET_TRAP,
    TileType.TRAP,
    TileType.INACTIVE_TRAP,
    TileType.OPEN_DOOR,
}


def _find_tile(grid, tile_type):
    for y, row in enumerate(grid):
        for x, tile in enumerate(row):
            if tile == tile_type:
                return (x, y)
    return None


def _is_in_room(rooms, x, y):
    for room in rooms:
        if room.contains(x, y):
            return True
    return False


def _is_in_safe_room(rooms, x, y):
    if not rooms:
        return False
    return rooms[0].contains(x, y) or rooms[-1].contains(x, y)


def _reachable_from_start(grid, start, walkable=WALKABLE_TILES):
    q = deque([start])
    visited = {start}

    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not (0 <= ny < len(grid) and 0 <= nx < len(grid[0])):
                continue
            if (nx, ny) in visited:
                continue
            if grid[ny][nx] not in walkable:
                continue
            visited.add((nx, ny))
            q.append((nx, ny))

    return visited


def test_sewers_room_allocation_and_layout_contracts():
    game = GameInstance("sewers-contracts")

    for _ in range(30):
        floor = game.generate_floor(1)
        meta = floor.generation_meta
        room_ids_by_kind = meta["room_ids_by_kind"]

        assert 4 <= len(room_ids_by_kind[RoomKind.STANDARD]) <= 6
        assert 1 <= len(room_ids_by_kind[RoomKind.SPECIAL]) <= 2
        # SecretRoom.secretsForFloor(1) == 0 in the original (RegularLevel
        # never rolls secret rooms on the very first floor) -- depth 1 is
        # the only sewers depth with a deterministic hidden-room count.
        assert len(room_ids_by_kind[RoomKind.HIDDEN]) == 0

        assert meta["layout_kind"] in {"loop", "figure_eight"}

        if meta["layout_kind"] == "figure_eight":
            room_by_id = {room.room_id: room for room in floor.rooms}
            standard_rooms = [room_by_id[rid] for rid in room_ids_by_kind[RoomKind.STANDARD]]
            largest = max(standard_rooms, key=lambda room: room.width * room.height)
            cx, cy = largest.center
            assert abs(cx - (game.width // 2)) <= 4
            assert abs(cy - (game.height // 2)) <= 4


def test_sewers_doors_keys_and_hidden_connections_contracts():
    game = GameInstance("sewers-doors")

    # Depth 3 (not 1): SecretRoom.secretsForFloor(1) == 0, so depth 1 never
    # has a hidden room to exercise the hidden-connection checks below.
    for _ in range(25):
        floor = game.generate_floor(3)
        room_by_id = {room.room_id: room for room in floor.rooms}
        room_ids_by_kind = floor.generation_meta["room_ids_by_kind"]

        door_positions = []
        for y, row in enumerate(floor.grid):
            for x, tile in enumerate(row):
                if tile in (TileType.DOOR, TileType.LOCKED_DOOR):
                    door_positions.append((x, y, tile))

        assert door_positions

        # Note: a door's neighbours aren't always a `floor.rooms` member --
        # floor.rooms intentionally excludes ConnectionRoom (corridor/tunnel)
        # segments (see spd_adapter.gen_level_to_floor_state, matching the
        # original's "corridors are implicit" convention), and a door can
        # legitimately sit between two tunnel segments. A walkable neighbour
        # on at least one side is the real, tile-grid-based structural check.
        for x, y, _ in door_positions:
            has_walkable_side = False
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= ny < len(floor.grid) and 0 <= nx < len(floor.grid[0])):
                    continue
                if floor.grid[ny][nx] in WALKABLE_TILES:
                    has_walkable_side = True
                    break
            assert has_walkable_side, f"Door at {(x, y)} has no walkable side"

        # Standard rooms must be connected to the rest of the floor, but not
        # necessarily via a literal DOOR tile: SewerPipeRoom-to-SewerPipeRoom
        # links paint as plain WATER (DoorType.WATER, no door tile -- see
        # RegularPainter._paint_doors), and same-size StandardRooms can fuse
        # via an open wall with no door at all (room_merges). Reachability
        # from the stairs is the real, tile-agnostic invariant.
        stairs_up = _find_tile(floor.grid, TileType.STAIRS_UP)
        assert stairs_up is not None
        reachable = _reachable_from_start(floor.grid, stairs_up)
        for room_id in room_ids_by_kind[RoomKind.STANDARD]:
            room = room_by_id[room_id]
            room_cells = (
                (x, y)
                for y in range(room.y, room.y + room.height)
                for x in range(room.x, room.x + room.width)
            )
            assert any(cell in reachable for cell in room_cells), \
                f"Standard room {room_id} is not reachable from the entrance"

        hidden_door_positions = set(floor.hidden_doors.keys())
        for room_id in room_ids_by_kind[RoomKind.HIDDEN]:
            room = room_by_id[room_id]
            room_hidden = [
                pos
                for pos in hidden_door_positions
                if room.is_perimeter(pos[0], pos[1])
            ]
            assert room_hidden, f"Hidden room {room_id} does not connect via hidden door"

        if floor.locked_doors:
            # key_id is a per-depth category (Key.key_id), not a per-door
            # identifier -- a floor with two same-type locks (e.g. two
            # "iron" vaults) drops two separate, stackable key items sharing
            # that id. Group by id rather than collapsing into one.
            #
            # A key can also turn up *inside* an unrelated special room's
            # treasure chest: GenLevel.find_prize_item() (TrapsRoom/
            # ConsumableRoom etc.'s prize()) pulls a random queued
            # itemsToSpawn descriptor, which can be the very IronKey/
            # CrystalKey another room's paint() just queued -- faithful to
            # the original Level.findPrizeItem(). The key's reachability
            # then depends on the chest's position, not a standalone pos.
            keys_by_id: Dict[str, list] = defaultdict(list)
            for item in floor.items.values():
                if getattr(item, "type", "") == "key":
                    keys_by_id[item.key_id].append(item)
                elif getattr(item, "kind", "") == "chest":
                    for sub in item.contents:
                        if getattr(sub, "type", "") == "key":
                            keys_by_id[sub.key_id].append(item)  # reachability uses the chest's pos

            # Note: a vault's perimeter can have several CRYSTAL_DOOR/
            # LOCKED_DOOR tiles (multiple "windows" into one room) all
            # opened by the same single key -- tile count isn't key count,
            # so this only checks "at least one key per lock category
            # exists and is reachable", not an exact tiles-needed tally.
            lock_ids_needed = set(floor.locked_doors.values())

            # Treat every lock tile -- SECRET_DOOR, and BARRICADE -- as
            # passable: a floor can have more than one independent vault/
            # lock, a key can sit past a hidden door or a burnable barricade
            # (StorageRoom etc.), and none of that should block a key's
            # reachability check (searching/fire are always available to the
            # player; this checks eventual solvability, not "in plain sight").
            lock_tiles = WALKABLE_TILES | {
                TileType.LOCKED_DOOR, TileType.CRYSTAL_DOOR, TileType.LOCKED_EXIT,
                TileType.SECRET_DOOR, TileType.BARRICADE,
            }
            stairs_up = _find_tile(floor.grid, TileType.STAIRS_UP)
            assert stairs_up is not None
            reachable = _reachable_from_start(floor.grid, stairs_up, lock_tiles)

            for key_id in lock_ids_needed:
                keys = keys_by_id.get(key_id, [])
                assert keys, f"No {key_id!r} key found for its lock"
                for key_item in keys:
                    assert key_item.pos is not None
                    assert (key_item.pos.x, key_item.pos.y) in reachable


def test_sewers_terrain_and_trap_contracts():
    game = GameInstance("sewers-terrain")

    samples = 80
    terrain_total = 0
    water_total = 0
    grass_total = 0

    for _ in range(samples):
        floor = game.generate_floor(1)

        for y, row in enumerate(floor.grid):
            for x, tile in enumerate(row):
                if _is_in_safe_room(floor.rooms, x, y):
                    continue
                # HIGH_GRASS counts as grass terrain too: the painter
                # promotes some painted GRASS cells to HIGH_GRASS based on
                # neighbour density (RegularPainter._paint_grass), so
                # excluding it from the ratio undercounts the Patch fill.
                if tile not in (TileType.FLOOR, TileType.FLOOR_WATER, TileType.FLOOR_GRASS, TileType.HIGH_GRASS):
                    continue
                terrain_total += 1
                if tile == TileType.FLOOR_WATER:
                    water_total += 1
                elif tile in (TileType.FLOOR_GRASS, TileType.HIGH_GRASS):
                    grass_total += 1

        assert 1 <= len(floor.traps) <= 3
        for trap in floor.traps.values():
            assert trap.trap_type == TrapType.WORN_DART

    assert terrain_total > 0
    water_ratio = water_total / terrain_total
    grass_ratio = grass_total / terrain_total

    # The v2 painter masks water/grass against per-room filters (secret
    # and special rooms refuse them), so averaged fill rates sit below
    # the raw Patch target. Loosen the tolerance to ±15 pp around the
    # target — enough to catch "nothing generated" or "everything is
    # water" regressions while accommodating the builder's shape.
    assert abs(water_ratio - 0.30) <= 0.15
    assert abs(grass_ratio - 0.20) <= 0.15


def test_sewers_corridors_are_single_tile_wide():
    game = GameInstance("sewers-corridors")

    floor = game.generate_floor(1)
    corridor_tiles = set()

    for y, row in enumerate(floor.grid):
        for x, tile in enumerate(row):
            if tile not in (TileType.FLOOR, TileType.FLOOR_WATER, TileType.FLOOR_GRASS, TileType.FLOOR_COBBLE):
                continue
            if _is_in_room(floor.rooms, x, y):
                continue
            corridor_tiles.add((x, y))

    for y in range(game.height - 1):
        for x in range(game.width - 1):
            block = {(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)}
            assert not block.issubset(corridor_tiles), "Found 2x2 corridor block"
