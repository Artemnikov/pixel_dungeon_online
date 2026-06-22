import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.dungeon.constants import TileType
from app.engine.dungeon.terrain_flags import build_flag_maps
from app.engine.manager import GameInstance


def test_chasm_tile_is_avoid_and_pit_not_passable():
    grid = [[TileType.CHASM for _ in range(3)] for _ in range(3)]
    flags = build_flag_maps(grid)
    # Border cells are forced solid/impassable regardless of tile id (see
    # build_flag_maps Pass 2), so only the center cell reflects CHASM's own
    # flags.
    assert flags.avoid[1][1] is True
    assert flags.pit[1][1] is True
    assert flags.passable[1][1] is False
    assert flags.solid[1][1] is False
    assert flags.los_blocking[1][1] is False


def test_floor_10_post_tengu_reveal_has_real_chasm_not_wall():
    from app.engine.entities.base import Position
    from app.engine.entities.mobs import Tengu
    from app.engine.dungeon.spd_levelgen import prison_boss_layout as layout

    game = GameInstance("test-chasm-floor10")
    game.players = {}
    floor = game.generate_floor(10)
    player = game.add_player("p1", "Hero")
    player.floor_id = 10
    player.pos = Position(x=layout.TENGU_CELL_CENTER.x, y=layout.TENGU_CELL.top + 2)

    game._update_prison_boss(floor, 10)  # -> FIGHT_START
    tengu = next(m for m in floor.mobs.values() if isinstance(m, Tengu))
    tengu.hp = tengu.max_hp // 2
    game._update_prison_boss(floor, 10)  # -> FIGHT_PAUSE
    player.pos = Position(x=layout.START_HALLWAY.left + 2, y=layout.START_HALLWAY.top)
    game._update_prison_boss(floor, 10)  # -> FIGHT_ARENA
    del floor.mobs[tengu.id]  # simulate Tengu's death/removal
    game._update_prison_boss(floor, 10)  # -> WON

    assert floor.tengu_state == "WON"
    chasm_cells = sum(1 for row in floor.grid for cell in row if cell == TileType.CHASM)
    assert chasm_cells > 0, "endMap's C cells must render as real chasm, not WALL"


def test_player_has_pending_chasm_fall_field_defaulting_to_none():
    from app.engine.entities.base import Player, Position, Faction
    player = Player(id="p1", name="Hero", pos=Position(x=0, y=0), hp=20, max_hp=20, faction=Faction.PLAYER)
    assert player.pending_chasm_fall is None


def test_chasm_prompt_event_is_registered():
    from app.schemas.events import EVENT_MODELS
    assert "CHASM_PROMPT" in EVENT_MODELS
    model = EVENT_MODELS["CHASM_PROMPT"](x=5, y=7)
    assert model.x == 5 and model.y == 7


def test_player_step_onto_chasm_prompts_instead_of_moving():
    game = GameInstance("test-chasm-prompt")
    floor = game._get_or_create_floor(game.depth)
    floor.grid = [[TileType.FLOOR for _ in range(5)] for _ in range(5)]
    floor.grid[2][3] = TileType.CHASM
    floor.rebuild_flags()
    player = game.add_player("p1", "Hero")
    player.pos.x, player.pos.y = 2, 2

    game.move_entity(player.id, 1, 0)

    assert (player.pos.x, player.pos.y) == (2, 2), "player must not move onto the chasm tile"
    assert player.pending_chasm_fall == (3, 2)
    events = game.flush_events()
    prompts = [e for e in events if e["type"] == "CHASM_PROMPT"]
    assert len(prompts) == 1
    assert prompts[0]["data"] == {"x": 3, "y": 2}


def test_mob_step_onto_chasm_is_a_no_op():
    from app.engine.entities.base import Mob as MobEntity, Faction, Position
    game = GameInstance("test-chasm-mob-noop")
    floor = game._get_or_create_floor(game.depth)
    floor.grid = [[TileType.FLOOR for _ in range(5)] for _ in range(5)]
    floor.grid[2][3] = TileType.CHASM
    floor.rebuild_flags()
    floor.mobs = {}
    mob = MobEntity(id="m1", name="Rat", pos=Position(x=2, y=2), hp=10, max_hp=10, faction=Faction.DUNGEON)
    floor.mobs[mob.id] = mob

    game.move_entity(mob.id, 1, 0)

    assert (mob.pos.x, mob.pos.y) == (2, 2)
    assert game.flush_events() == []


def test_any_other_move_clears_a_stale_pending_chasm_fall():
    game = GameInstance("test-chasm-clear-stale")
    floor = game._get_or_create_floor(game.depth)
    floor.grid = [[TileType.FLOOR for _ in range(5)] for _ in range(5)]
    floor.rebuild_flags()
    player = game.add_player("p1", "Hero")
    player.pos.x, player.pos.y = 2, 2
    player.pending_chasm_fall = (99, 99)

    game.move_entity(player.id, 1, 0)

    assert player.pending_chasm_fall is None


def test_chasm_step_at_max_floor_id_is_a_silent_no_op():
    from app.engine.game.constants import MAX_FLOOR_ID
    game = GameInstance("test-chasm-last-floor")
    floor = game._get_or_create_floor(game.depth)
    floor.grid = [[TileType.FLOOR for _ in range(5)] for _ in range(5)]
    floor.grid[2][3] = TileType.CHASM
    floor.rebuild_flags()
    player = game.add_player("p1", "Hero")
    player.pos.x, player.pos.y = 2, 2
    player.floor_id = MAX_FLOOR_ID

    game.move_entity(player.id, 1, 0)

    assert (player.pos.x, player.pos.y) == (2, 2)
    assert player.pending_chasm_fall is None
    assert game.flush_events() == []


def test_get_next_step_to_routes_around_chasm():
    from app.engine.entities.base import Position
    game = GameInstance("test-chasm-pathfind-mob")
    floor = game._get_or_create_floor(game.depth)
    # 7x7 so the detour gap (y=1) is an interior row, not the border row
    # (y=0) that build_flag_maps always forces impassable.
    floor.grid = [[TileType.FLOOR for _ in range(7)] for _ in range(7)]
    for y in range(2, 5):
        floor.grid[y][3] = TileType.CHASM
    floor.rebuild_flags()

    step = game._get_next_step_to(Position(x=1, y=3), Position(x=5, y=3), floor_id=floor.floor_id)

    # The chasm column blocks a direct eastward step; a path must exist via
    # the y=1 gap, so some step is returned, but never the naive direct one.
    assert step is not None
    assert step != (1, 0)


def test_get_next_step_to_allows_flying_entity_through_chasm():
    from app.engine.entities.base import Position
    game = GameInstance("test-chasm-pathfind-flying")
    floor = game._get_or_create_floor(game.depth)
    floor.grid = [[TileType.FLOOR for _ in range(7)] for _ in range(7)]
    for y in range(2, 5):
        floor.grid[y][3] = TileType.CHASM
    floor.rebuild_flags()

    step = game._get_next_step_to(Position(x=1, y=3), Position(x=5, y=3), floor_id=floor.floor_id, flying=True)

    assert step == (1, 0), "a flying entity should path straight through the chasm column"


def test_bfs_full_path_can_end_exactly_on_an_adjacent_chasm_tile():
    from app.engine.entities.base import Position
    game = GameInstance("test-chasm-bfs-target")
    floor = game._get_or_create_floor(game.depth)
    floor.grid = [[TileType.FLOOR for _ in range(5)] for _ in range(5)]
    floor.grid[2][3] = TileType.CHASM
    floor.rebuild_flags()

    path = game._bfs_full_path(Position(x=2, y=2), Position(x=3, y=2), floor.floor_id)

    assert path == [(1, 0)]


def test_bfs_full_path_never_routes_through_a_non_target_chasm_cell():
    from app.engine.entities.base import Position
    game = GameInstance("test-chasm-bfs-detour")
    floor = game._get_or_create_floor(game.depth)
    floor.grid = [[TileType.FLOOR for _ in range(7)] for _ in range(7)]
    for y in range(2, 5):
        floor.grid[y][3] = TileType.CHASM
    floor.rebuild_flags()

    path = game._bfs_full_path(Position(x=1, y=3), Position(x=5, y=3), floor.floor_id)
    assert path, "a detour path must exist via the y=1 gap"

    visited_x = 1
    visited_y = 3
    for dx, dy in path:
        visited_x += dx
        visited_y += dy
        if (visited_x, visited_y) != (5, 3):
            assert floor.grid[visited_y][visited_x] != TileType.CHASM


def make_chasm_fall_game():
    game = GameInstance("test-chasm-fall")
    floor = game._get_or_create_floor(game.depth)
    floor.grid = [[TileType.FLOOR for _ in range(5)] for _ in range(5)]
    floor.grid[2][3] = TileType.CHASM
    floor.rebuild_flags()
    below = game._get_or_create_floor(game.depth + 1)
    below.grid = [[TileType.FLOOR for _ in range(5)] for _ in range(5)]
    below.rebuild_flags()
    player = game.add_player("p1", "Hero")
    player.pos.x, player.pos.y = 2, 2
    player.hp = player.get_total_max_hp()
    return game, floor, player


def test_confirm_chasm_fall_rejected_without_a_matching_pending_state():
    game, floor, player = make_chasm_fall_game()
    start_floor = player.floor_id

    game.confirm_chasm_fall(player.id, 3, 2)

    assert player.floor_id == start_floor
    assert (player.pos.x, player.pos.y) == (2, 2)


def test_confirm_chasm_fall_moves_player_down_one_floor_and_clears_pending():
    game, floor, player = make_chasm_fall_game()
    player.pending_chasm_fall = (3, 2)
    start_floor = player.floor_id

    game.confirm_chasm_fall(player.id, 3, 2)

    assert player.floor_id == start_floor + 1
    assert player.pending_chasm_fall is None
    assert player.floors_explored >= start_floor + 1


def test_confirm_chasm_fall_applies_damage_cripple_and_bleed():
    from app.engine.entities.buffs import get_buff
    game, floor, player = make_chasm_fall_game()
    player.pending_chasm_fall = (3, 2)
    full_hp = player.hp

    game.confirm_chasm_fall(player.id, 3, 2)

    assert player.hp < full_hp
    assert get_buff(player.buffs, "cripple") is not None
    assert player.bleed_amount > 0
    assert player.bleed_turns > 0


def test_confirm_chasm_fall_emits_damage_and_screen_shake_events():
    game, floor, player = make_chasm_fall_game()
    player.pending_chasm_fall = (3, 2)

    game.confirm_chasm_fall(player.id, 3, 2)

    events = [e["type"] for e in game.flush_events()]
    assert "DAMAGE" in events
    assert "SCREEN_SHAKE" in events
    assert "PLAY_SOUND" in events


def test_confirm_chasm_fall_rejected_at_max_floor_id():
    from app.engine.game.constants import MAX_FLOOR_ID
    game, floor, player = make_chasm_fall_game()
    player.floor_id = MAX_FLOOR_ID
    player.pending_chasm_fall = (3, 2)

    game.confirm_chasm_fall(player.id, 3, 2)

    assert player.floor_id == MAX_FLOOR_ID
    assert player.pending_chasm_fall is None
