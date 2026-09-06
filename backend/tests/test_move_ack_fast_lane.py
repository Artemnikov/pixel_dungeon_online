# Copyright (C) 2026 ArtemNikov
#
"""Movement-ack fast lane and FOV diff in broadcast_state.

Guards the live-feel improvements:
- every MOVE_RESULT ack is sent as a compact top-level message ahead of the
  bulk STATE_UPDATE frame (and excluded from the frame's events, so the client
  never processes a step confirmation twice);
- visible_tiles / mapped_tiles are omitted from the frame when unchanged
  (server-side FOV diffing turns a static screen into ~0 FOV bytes).
"""

from app.api.connection_manager import ConnectionManager
from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position


class DummyWebSocket:
    def __init__(self):
        self.accepted = False
        self.messages = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, payload):
        self.messages.append(payload)


def _open_floor(game):
    floor = game._get_or_create_floor(1)
    floor.grid = [[TileType.FLOOR for _ in range(20)] for _ in range(20)]
    floor.rebuild_flags()
    return floor


async def _connected_player():
    manager = ConnectionManager()
    game_id, session_id = "g", "sess-1"
    ws = DummyWebSocket()
    pid, _ = await manager.connect(game_id, ws, session_id)
    game = manager.game_instances[game_id]
    _open_floor(game)
    player = game.add_player(pid, "Hero")
    player.pos = Position(x=3, y=3)
    return manager, game_id, ws, game, pid, player


def _frames(ws):
    return [m for m in ws.messages if m.get("type") == "STATE_UPDATE"]


def _last_frame(ws):
    return _frames(ws)[-1]


def test_move_result_acks_ride_the_fast_lane_and_not_the_frame():
    async def scenario():
        manager, game_id, ws, game, pid, player = await _connected_player()

        game.queue_move_step(pid, 1, 1, 0)
        await manager.broadcast_state(game_id)

        # The step was actually executed.
        assert (player.pos.x, player.pos.y) == (4, 3)

        # One compact MOVE_RESULT ack arrived as its own top-level message.
        move_acks = [m for m in ws.messages if m.get("type") == "MOVE_RESULT"]
        assert len(move_acks) == 1, f"expected exactly one ack, got {len(move_acks)}"
        ack = move_acks[0]
        assert ack["data"] == {"entity": pid, "seq": 1, "x": 4, "y": 3, "ok": True}

        # The bulk frames carry the acks' data only as top-level messages.
        frames = _frames(ws)
        assert len(frames) == 1
        frame_events = [e.get("type") for e in frames[0].get("events", [])]
        assert "MOVE_RESULT" not in frame_events, "ack must not be duplicated inside the frame"

        # Managed-broadcast order: the ack precedes the frame.
        assert ws.messages.index(ack) < ws.messages.index(frames[0])

    import asyncio
    asyncio.run(scenario())


def test_first_frame_ships_fov_then_unchanged_fov_is_omitted():
    async def scenario():
        manager, game_id, ws, game, pid, player = await _connected_player()

        await manager.broadcast_state(game_id)

        # The first frame after INIT must include the initial FOV (the client's
        # fog is reset on floor entry -- without this the screen starts dark).
        first_frame = _last_frame(ws)
        assert "visible_tiles" in first_frame

        # Steady state: the player hasn't moved, so the next frame omits both
        # the FOV and the (still-empty) mapped tiles.
        await manager.broadcast_state(game_id)
        second_frame = _last_frame(ws)
        assert "visible_tiles" not in second_frame, "unchanged FOV must be omitted"
        assert "mapped_tiles" not in second_frame, "unchanged mapped tiles must be omitted"

        # A vision-affecting change (magic mapping) ships the new mapped set
        # even though the FOV is still unchanged.
        floor = game._get_or_create_floor(1)
        floor.mapped = True
        floor.mapped_tiles = [(9, 9)]
        await manager.broadcast_state(game_id)
        third_frame = _last_frame(ws)
        assert third_frame.get("mapped_tiles") == [(9, 9)]
        assert "visible_tiles" not in third_frame

    import asyncio
    asyncio.run(scenario())


def test_reconnect_same_spot_still_ships_fov():
    async def scenario():
        manager, game_id, ws, game, pid, player = await _connected_player()

        await manager.broadcast_state(game_id)
        first_frame = _last_frame(ws)
        assert "visible_tiles" in first_frame, "first frame carries FOV"
        assert "mapped_tiles" in first_frame, "first frame carries mapped tiles"

        # Drop the connection (FOV diff cursors are retained) and reconnect to
        # the same hero on the same floor at the same position.
        manager.disconnect(game_id, ws)
        ws2 = DummyWebSocket()
        rejoin_id, is_new = await manager.connect(game_id, ws2, "sess-1")
        assert rejoin_id == pid
        assert is_new is False

        # The real flow runs send_player_init on (re)connect; it re-sets
        # last_sent_floor so broadcast's INIT branch is skipped. The FOV cursors
        # must still reset so the next frame ships a full snapshot -- otherwise
        # the first STATE_UPDATE after reconnect omits visible_tiles and the
        # client's fog (wiped by initFloor) never gets repopulated.
        await manager.send_player_init(game_id, ws2, rejoin_id, is_new=False)
        await manager.broadcast_state(game_id)

        frames_after = _frames(ws2)
        assert len(frames_after) == 1, "reconnect frame must carry FOV"
        assert "visible_tiles" in frames_after[0]
        assert "mapped_tiles" in frames_after[0]

    import asyncio
    asyncio.run(scenario())