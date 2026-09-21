import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocket
from app.api.connection_manager import ConnectionManager

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_stale_websocket_cleanup_on_reconnect():
    mgr = ConnectionManager()
    game_id = "test_game"
    session_id = "session_1"
    
    # First connection
    ws1 = MagicMock(spec=WebSocket)
    ws1.accept = AsyncMock()
    ws1.close = AsyncMock()
    
    pid1, is_new1 = await mgr.connect(game_id, ws1, session_id)
    assert is_new1 is True
    assert mgr.active_connections[game_id][ws1] == pid1

    # Add player entity to game instance so reconnect detects live hero in game.players
    game = mgr.game_instances[game_id]
    game.add_player(pid1, "Test Player")
    
    # Second connection (reconnect for same session)
    ws2 = MagicMock(spec=WebSocket)
    ws2.accept = AsyncMock()
    ws2.close = AsyncMock()
    
    pid2, is_new2 = await mgr.connect(game_id, ws2, session_id)
    assert is_new2 is False
    assert pid1 == pid2
    
    # ws1 must have been closed and removed from active_connections
    ws1.close.assert_called_once()
    assert ws1 not in mgr.active_connections[game_id]
    assert mgr.active_connections[game_id][ws2] == pid2

@pytest.mark.anyio
async def test_broadcast_state_handles_closed_websocket_gracefully():
    mgr = ConnectionManager()
    game_id = "test_game"
    session_id = "session_2"
    
    ws = MagicMock(spec=WebSocket)
    ws.accept = AsyncMock()
    # Simulate a closed socket error on send_json
    ws.send_json = AsyncMock(side_effect=RuntimeError("Unexpected ASGI message 'websocket.send'"))
    
    pid, _ = await mgr.connect(game_id, ws, session_id)
    game = mgr.game_instances[game_id]
    game.add_player(pid, "Test Player")
    
    # broadcast_state should catch the error cleanly without raising an unhandled exception
    await mgr.broadcast_state(game_id)
    
    # ws should have been cleanly removed via disconnect
    assert ws not in mgr.active_connections.get(game_id, {})
