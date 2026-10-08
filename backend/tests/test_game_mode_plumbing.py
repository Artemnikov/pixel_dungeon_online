import asyncio

from app.api.connection_manager import ConnectionManager, RoomMeta, manager
from app.api.routes import CreateRoomRequest, create_room
from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.game.constants import (
    DEFAULT_TURN_TIMER_SECONDS,
    GAME_MODE_REALTIME,
    GAME_MODE_TURNBASED,
    TICK_DURATION,
    TICKS_PER_TURN,
)
from app.engine.manager import GameInstance
from app.engine.turn.instance import TurnBasedGameInstance


def _pop_room(res) -> None:
    manager.rooms.pop(res["room_id"], None)


def test_create_room_stores_turnbased_mode():
    res = asyncio.run(create_room(CreateRoomRequest(
        name="tb-room", game_mode="turnbased", turn_timer_seconds=30.0,
    )))
    try:
        room = manager.rooms[res["room_id"]]
        assert room.game_mode == GAME_MODE_TURNBASED
        assert room.turn_timer_seconds == 30.0
        assert res["game_mode"] == "turnbased"
    finally:
        _pop_room(res)


def test_create_room_defaults_to_realtime():
    res = asyncio.run(create_room(CreateRoomRequest(name="rt-room")))
    try:
        room = manager.rooms[res["room_id"]]
        assert room.game_mode == GAME_MODE_REALTIME
        assert room.turn_timer_seconds == DEFAULT_TURN_TIMER_SECONDS
        assert res["game_mode"] == "realtime"
    finally:
        _pop_room(res)


def test_create_game_instance_selects_by_room_mode():
    cm = ConnectionManager()
    cm.rooms["rt"] = RoomMeta("rt", "RT")
    cm.rooms["tb"] = RoomMeta("tb", "TB", game_mode=GAME_MODE_TURNBASED)

    assert type(cm._create_game_instance("rt", None)) is GameInstance
    assert type(cm._create_game_instance("tb", None)) is TurnBasedGameInstance


def test_create_game_instance_passes_room_turn_timer():
    cm = ConnectionManager()
    cm.rooms["tb"] = RoomMeta(
        "tb", "TB", game_mode=GAME_MODE_TURNBASED, turn_timer_seconds=17.5
    )

    game = cm._create_game_instance("tb", None)
    assert game.turn_timer_seconds == 17.5


def test_realtime_game_instance_has_no_scheduler():
    game = GameInstance("rt-only")
    assert game.sim_unit == TICK_DURATION
    assert game.sim_ticks == 1
    assert game.turn_state_for("nobody") is None
    # The real-time dispatcher path answers "no scheduler to charge".
    assert game.submit_turn_action("nobody", None) is False


def test_turnbased_game_instance_uses_spd_time_units():
    game = TurnBasedGameInstance("tb-units")
    assert game.game_mode == GAME_MODE_TURNBASED
    assert game.sim_unit == 1.0
    assert game.sim_ticks == TICKS_PER_TURN
    assert game.clock() == 0.0


def test_create_game_instance_legacy_id_defaults_to_realtime():
    cm = ConnectionManager()
    assert type(cm._create_game_instance("legacy-id", None)) is GameInstance


def test_base_broadcast_hooks_and_wait(game):
    assert game.should_broadcast() is True
    game.on_broadcast_complete()
    game.wait("anyone")


def test_step_player_move_moves_once_per_ready_step(open_game_factory):
    game = open_game_factory(width=20, height=20)
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=3, y=3)

    game.step_player_move(player.id, 1, 0)
    game.step_player_move(player.id, 1, 0)

    assert (player.pos.x, player.pos.y) == (4, 3)


def test_step_player_move_blocked_step_keeps_position(open_game_factory):
    game = open_game_factory(width=20, height=20)
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=3, y=3)
    floor = game._get_or_create_floor(1)
    floor.grid[3][4] = TileType.WALL
    floor.rebuild_flags()

    game.step_player_move(player.id, 1, 0)

    assert (player.pos.x, player.pos.y) == (3, 3)
