from app.engine.dungeon.constants import TileType
from app.engine.entities.items.consumables import Key
from app.engine.manager import GameInstance


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
    TileType.PEDESTAL,
}


def _find_adjacent_walkable(floor, x, y):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if not (0 <= ny < len(floor.grid) and 0 <= nx < len(floor.grid[0])):
            continue
        if floor.grid[ny][nx] in WALKABLE_TILES:
            return nx, ny
    return None


def _find_floor_with_locked_door(max_tries=60):
    # Filter to "iron" locks specifically: a CRYSTAL_DOOR (Vault room) or
    # LOCKED_EXIT (goo_door) unlock to a different tile (FLOOR / STAIRS_DOWN,
    # see World._try_unlock_locked_door) than the LOCKED_DOOR -> OPEN_DOOR
    # path this test exercises.
    for idx in range(max_tries):
        game = GameInstance(f"locked-sewers-{idx}")
        floor = game._get_or_create_floor(1)
        if any(key_id == "iron" for key_id in floor.locked_doors.values()):
            return game, floor
    return None, None


def _find_floor_with_hidden_door(max_tries=60):
    for idx in range(max_tries):
        game = GameInstance(f"search-sewers-{idx}")
        for fid in (2, 3, 4, 1):
            floor = game._get_or_create_floor(fid)
            if floor.hidden_doors:
                return game, floor
    return None, None


def test_search_reveals_hidden_door_and_emits_map_patch():
    game, floor = _find_floor_with_hidden_door()
    assert game is not None and floor is not None
    floor.mobs = {}

    assert floor.hidden_doors
    hidden_pos = next(iter(floor.hidden_doors.keys()))

    player = game.add_player("p-search", "Searcher")
    player.floor_id = floor.floor_id

    neighbor = _find_adjacent_walkable(floor, hidden_pos[0], hidden_pos[1])
    assert neighbor is not None
    player.pos.x, player.pos.y = neighbor

    game.flush_events()
    game.search(player.id)

    assert hidden_pos not in floor.hidden_doors
    assert floor.grid[hidden_pos[1]][hidden_pos[0]] in {TileType.DOOR, TileType.LOCKED_DOOR}

    events = game.flush_events()
    map_patches = [e for e in events if e["type"] == "MAP_PATCH"]
    assert map_patches

    revealed_positions = {
        (tile_patch["x"], tile_patch["y"])
        for event in map_patches
        for tile_patch in event["data"].get("tiles", [])
    }
    assert hidden_pos in revealed_positions


def test_locked_door_requires_matching_key_and_unlocks_with_patch():
    game, floor = _find_floor_with_locked_door()
    assert game is not None and floor is not None

    floor.mobs = {}

    (door_x, door_y), key_id = next(
        (pos, k) for pos, k in floor.locked_doors.items() if k == "iron"
    )

    player = game.add_player("p-lock", "Unlocker")

    neighbor = _find_adjacent_walkable(floor, door_x, door_y)
    assert neighbor is not None
    player.pos.x, player.pos.y = neighbor

    assert player.key_count(key_id, floor.floor_id) == 0

    game.flush_events()
    game.move_entity(player.id, door_x - player.pos.x, door_y - player.pos.y)

    assert (player.pos.x, player.pos.y) == neighbor
    assert floor.grid[door_y][door_x] == TileType.LOCKED_DOOR

    player.add_key(key_id, floor.floor_id, "Rusty Key")

    game.move_entity(player.id, door_x - player.pos.x, door_y - player.pos.y)

    # Bumping a locked door with the matching key spends the action
    # unlocking it (move_entity._try_unlock_locked_door always `return`s
    # without calling entity.move) -- the player steps through on a
    # separate, later move, same as the original's two-turn unlock+walk.
    assert (player.pos.x, player.pos.y) == neighbor
    # Two-phase unlock: the key is consumed immediately but the door stays
    # locked until the operate animation (KEY_TIME_TO_UNLOCK) completes.
    assert floor.grid[door_y][door_x] == TileType.LOCKED_DOOR
    assert player.key_count(key_id, floor.floor_id) == 0
    assert (door_x, door_y) in floor.pending_unlocks

    # Drive the completion the tick would perform once the animation elapsed.
    floor.pending_unlocks[(door_x, door_y)]["ready_at"] = 0
    game._process_pending_unlocks(floor, floor.floor_id)

    assert floor.grid[door_y][door_x] == TileType.DOOR
    assert (door_x, door_y) not in floor.locked_doors

    events = game.flush_events()
    map_patches = [e for e in events if e["type"] == "MAP_PATCH"]
    assert map_patches
    assert any(
        tile_patch["x"] == door_x and tile_patch["y"] == door_y and tile_patch["tile"] == TileType.DOOR
        for event in map_patches
        for tile_patch in event["data"].get("tiles", [])
    )


def _place_locked_door(floor, tile, key_id):
    """Set a locked-door tile (with its lock registry entry) on the first cell
    that has a walkable neighbour, so a player can bump it."""
    for y in range(len(floor.grid)):
        for x in range(len(floor.grid[y])):
            if _find_adjacent_walkable(floor, x, y) is not None:
                floor.grid[y][x] = tile
                floor.locked_doors[(x, y)] = key_id
                floor.rebuild_flags()
                return x, y
    raise AssertionError("no cell with a walkable neighbour")


def _crystal_door_fixture(seed_suffix):
    game = GameInstance(f"crystal-lock-{seed_suffix}")
    floor = game._get_or_create_floor(1)
    floor.mobs = {}
    door_x, door_y = _place_locked_door(floor, TileType.CRYSTAL_DOOR, "crystal")
    player = game.add_player(f"p-{seed_suffix}", "CrystalBumper")
    nb = _find_adjacent_walkable(floor, door_x, door_y)
    assert nb is not None, "crystal door needs a walkable neighbour"
    player.pos.x, player.pos.y = nb
    player.floor_id = floor.floor_id
    return game, floor, player, door_x, door_y


def test_crystal_door_no_key_emits_locked_sound():
    """Bumping a crystal door without the matching key must emit the LOCKED
    event (locked-sound jingle on the client) and deliver it to the bumper."""
    game, floor, player, door_x, door_y = _crystal_door_fixture("nokey")
    assert player.key_count("crystal", floor.floor_id) == 0

    game.flush_events()
    game.move_entity(player.id, door_x - player.pos.x, door_y - player.pos.y)

    raw = game.flush_events()
    locked = [e for e in raw if e["type"] == "LOCKED"]
    assert locked, "LOCKED event must be emitted for a crystal door without a key"
    assert locked[0]["data"] == {"player": player.id, "x": door_x, "y": door_y}

    delivered = game.filter_events_for_player(raw, player.id)
    assert any(e["type"] == "LOCKED" for e in delivered), \
        "LOCKED event must survive per-player LOS filtering for the bumper"
    assert floor.grid[door_y][door_x] == TileType.CRYSTAL_DOOR, "door stays locked"


def test_crystal_door_unlock_completes_with_unlock_sound():
    """Unlocking a crystal door must complete with the UNLOCK sample (SPD
    parity with iron doors), not the old TELEPORT sound."""
    game, floor, player, door_x, door_y = _crystal_door_fixture("inok")
    player.add_key("crystal", floor.floor_id, "Crystal Key")

    game.flush_events()
    game.move_entity(player.id, door_x - player.pos.x, door_y - player.pos.y)
    assert (door_x, door_y) in floor.pending_unlocks

    floor.pending_unlocks[(door_x, door_y)]["ready_at"] = 0
    game._process_pending_unlocks(floor, floor.floor_id)

    events = game.flush_events()
    sounds = [e["data"]["sound"] for e in events if e["type"] == "PLAY_SOUND"]
    assert "UNLOCK" in sounds, "crystal door unlock must play UNLOCK"
    assert "TELEPORT" not in sounds, "crystal door unlock must not play TELEPORT"
    assert floor.grid[door_y][door_x] == TileType.FLOOR


def test_worn_dart_trap_triggers_once_and_deals_low_damage():
    game = GameInstance("trap-sewers")
    floor = game._get_or_create_floor(1)
    floor.mobs = {}

    assert floor.traps
    (trap_x, trap_y), trap = next(iter(floor.traps.items()))

    player = game.add_player("p-trap", "Trapper")
    neighbor = _find_adjacent_walkable(floor, trap_x, trap_y)
    assert neighbor is not None

    player.pos.x, player.pos.y = neighbor

    game.flush_events()
    hp_before = player.hp
    game.move_entity(player.id, trap_x - player.pos.x, trap_y - player.pos.y)

    assert (player.pos.x, player.pos.y) == (trap_x, trap_y)
    assert trap.active is False
    assert player.hp < hp_before

    events = game.flush_events()
    assert any(event["type"] == "TRAP_TRIGGERED" for event in events)

    hp_after = player.hp
    game._trigger_trap_if_needed(floor, player, floor.floor_id)
    assert player.hp == hp_after
