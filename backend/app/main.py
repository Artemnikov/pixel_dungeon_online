import asyncio, logging, time, uuid, os, sys
from typing import Optional

from pathlib import Path
from dotenv import load_dotenv

root_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(root_dir / ".env")
load_dotenv(backend_dir / ".env")

sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.connection_manager import manager
from app.api.routes import router
from app.engine.game.constants import GAME_LOOP_HZ, TARGET_TICK_INTERVAL

logger = logging.getLogger(__name__)

app = FastAPI(title="Online Pixel Dungeon API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.websocket("/ws/game/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: str, class_type: str = "warrior", difficulty: str = "normal", name: Optional[str] = None, admin_secret: str = "", session: Optional[str] = None, seed: str = "", challenges: str = "", room_password: str = "", faction: str = "player"):
    session_id = session or str(uuid.uuid4())

    rejection = manager.check_room_join(game_id, session_id, room_password, faction=faction)
    if rejection is not None:
        await websocket.accept()
        close_code = 4001 if rejection == "wrong password" else (4003 if rejection == "dungeon faction disabled" else 4002)
        await websocket.close(code=close_code, reason=rejection)
        return

    player_id, is_new = await manager.connect(game_id, websocket, session_id, seed=seed)

    game = manager.game_instances[game_id]
    if is_new:
        if game.player_count == 0: # First player sets difficulty
            game.change_difficulty(difficulty)
            game.set_challenges(challenges)

        is_admin = bool(admin_secret and admin_secret == os.environ.get("ADMIN_SECRET", "admin"))
        player_name = "admin" if is_admin else (name.strip()[:20] if name and name.strip() else f"Player_{player_id[:4]}")
        game.add_player(player_id, player_name, class_type, is_admin=is_admin, faction=faction)
        if faction == "dungeon":
            game.add_event("MESSAGE", {"text": f"{player_name} joined the Dungeon faction."})
        else:
            game.add_event("MESSAGE", {"text": f"{player_name} joined the game."})
    await manager.send_player_init(game_id, websocket, player_id, is_new=is_new)

    try:
        await manager.listen_events(game_id, websocket, player_id)
    except WebSocketDisconnect:
        if player_id in game.players:
            game.add_event(
                "MESSAGE",
                {"text": f"{game.players[player_id].name} left the game."},
                source_player_id=player_id,
            )
        manager.disconnect(game_id, websocket)


async def global_game_loop():
    while True:
        start_time = time.monotonic()
        for game_id in list(manager.game_instances.keys()):
            try:
                manager.reap_expired_players(game_id)
                await manager.broadcast_state(game_id)
                manager.cleanup_if_empty(game_id)
            except Exception:
                # One game's bug must never freeze broadcast_state for every
                # connected player. Log and continue ticking other games.
                logger.exception("global_game_loop: error ticking game_id=%s", game_id)
        elapsed = time.monotonic() - start_time
        sleep_dur = max(0.001, TARGET_TICK_INTERVAL - elapsed)
        await asyncio.sleep(sleep_dur)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(global_game_loop())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
