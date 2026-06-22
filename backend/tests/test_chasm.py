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
