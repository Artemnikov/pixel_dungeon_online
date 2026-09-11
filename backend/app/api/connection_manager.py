"""Lobby layer: rooms, WS connection bookkeeping, and the per-tick broadcast.

Deliberately kept out of GameInstance/engine, which stays a pure
dungeon-simulation concern (see `RoomMeta` below).
"""

import hashlib
import logging
import os
import re
import secrets
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import WebSocket

from pydantic import ValidationError

from app.api.dispatcher import dispatcher
import app.api.ws_handlers  # noqa: F401 - Register handlers
from app.engine.entities.items.consumables import Amulet
from app.engine.manager import GameInstance
from app.engine.game.constants import PARTY_LOOT_MAX_PLAYERS, PUBLIC_ROOM_ID
from app.schemas import CLIENT_MESSAGE_ADAPTER, InitMessage, MoveResultMessage, StateUpdateMessage

logger = logging.getLogger(__name__)

# How long a disconnected player's hero is kept alive in the world so the client
# can reconnect (same session) and resume the same run. After this, the reaper
# removes the orphaned player.
DISCONNECT_GRACE_SECONDS = 60.0

# Dead heroes are kept in game.players after their grace window so a reconnect
# on the same session rebinds to the corpse and shows the death screen. But a
# run that's truly abandoned (the session never returns) would otherwise pin
# its corpse -- and the whole floor it died on -- in memory forever. Cap the
# number of retained corpses per game; past this the oldest ones are dropped
# (their sessions then just start a fresh hero on reconnect).
MAX_RETAINED_CORPSES = 20

# Optional fixed seed for the public room (deploy-time config). When unset the
# room falls back to manager.py's crc32(game_id) deterministic seed. The public
# room deliberately ignores any per-player `seed` query param so its dungeon
# doesn't depend on whichever player happens to connect first.
PUBLIC_ROOM_SEED_ENV = "PUBLIC_ROOM_SEED"

# Rooms: one permanent public room (uncapped) plus player-created private
# groups (name + optional password), capped at the same party size the loot
# scaling tops out at (see engine/game/constants.party_loot_multiplier).
PRIVATE_ROOM_MAX_PLAYERS = PARTY_LOOT_MAX_PLAYERS

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return slug or "group"


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def _strip_transient_player_fields(p_dict: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not p_dict:
        return None
    res = dict(p_dict)
    for key in ("pos", "action_until", "stationary_ticks", "last_auto_move_time", "path_queue", "step_queue", "_cooldown_until", "last_processed_seq", "step_duration_ms"):
        res.pop(key, None)
    return res


class RoomMeta:
    """Lobby-layer room record — deliberately kept out of GameInstance/engine,
    which stays a pure dungeon-simulation concern. `room_id` doubles as the
    `game_id` used to route WS connections and look up GameInstance/
    active_connections/sessions."""

    def __init__(self, room_id: str, name: str, is_public: bool = False,
                 password: Optional[str] = None, max_players: Optional[int] = None):
        self.room_id = room_id
        self.name = name
        self.is_public = is_public
        self.max_players = max_players
        self.created_at = time.monotonic()
        if password:
            self.password_salt: Optional[str] = secrets.token_hex(8)
            self.password_hash: Optional[str] = _hash_password(password, self.password_salt)
        else:
            self.password_salt = None
            self.password_hash = None

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None

    def check_password(self, password: str) -> bool:
        if self.password_hash is None:
            return True
        if self.password_salt is None:
            return False
        return _hash_password(password, self.password_salt) == self.password_hash


class ConnectionManager:
    def __init__(self):
        # game_id -> {websocket: player_id}
        self.active_connections: Dict[str, Dict[WebSocket, str]] = {}
        self.game_instances: Dict[str, GameInstance] = {}
        self.last_sent_floor: Dict[str, Dict[str, Tuple[int, int]]] = {}
        self.last_sent_items: Dict[str, Dict[str, List[Any]]] = {}
        self.last_sent_traps: Dict[str, Dict[str, List[Any]]] = {}
        self.last_sent_plants: Dict[str, Dict[str, List[Any]]] = {}
        self.last_sent_player: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # Per-player FOV diff cache: the frame omits visible_tiles/mapped_tiles
        # when they haven't changed since the last send (see send_to_client).
        self.last_sent_visible: Dict[str, Dict[str, List[Any]]] = {}
        self.last_sent_mapped: Dict[str, Dict[str, List[Any]]] = {}
        # game_id -> {session_id: player_id} — stable identity across reconnects.
        self.sessions: Dict[str, Dict[str, str]] = {}
        # game_id -> {player_id: monotonic deadline} — players awaiting reconnect.
        self.disconnect_deadline: Dict[str, Dict[str, float]] = {}
        # game_id -> [player_id, ...] — reaped corpses in reap order, bounded by
        # MAX_RETAINED_CORPSES (oldest dropped once the cap is exceeded).
        self.retained_corpses: Dict[str, List[str]] = {}
        # room_id -> RoomMeta. Public room is permanent; private groups are
        # added by POST /api/rooms and dropped in cleanup_if_empty.
        self.rooms: Dict[str, RoomMeta] = {
            PUBLIC_ROOM_ID: RoomMeta(PUBLIC_ROOM_ID, "Public", is_public=True),
        }

    def _unique_room(self, requested_name: str) -> Tuple[str, str]:
        """Resolves a user-requested group name to a unique (room_id, name),
        auto-suffixing -1, -2, ... on collision (including against the
        public room's id/name)."""
        base_name = requested_name.strip()[:30] or "Group"
        slug = _slugify(base_name)
        room_id, name = slug, base_name
        n = 1
        while room_id in self.rooms:
            room_id, name = f"{slug}-{n}", f"{base_name}-{n}"
            n += 1
        return room_id, name

    def check_room_join(self, game_id: str, session_id: str, room_password: str) -> Optional[str]:
        """Returns a rejection reason, or None if the join should proceed.
        Unregistered game_ids (not created via POST /api/rooms) are never
        gated, keeping ad-hoc/legacy game_ids working unchanged."""
        room = self.rooms.get(game_id)
        if room is None:
            return None

        existing_player_id = self.sessions.get(game_id, {}).get(session_id)
        game = self.game_instances.get(game_id)
        if existing_player_id and game and existing_player_id in game.players:
            return None  # reconnect: already a member, no re-check

        if not room.check_password(room_password):
            return "wrong password"
        if room.max_players is not None:
            if len(self.active_connections.get(game_id, {})) >= room.max_players:
                return "room full"
        return None

    async def connect(self, game_id: str, websocket: WebSocket, session_id: str, seed: str = "") -> Tuple[str, bool]:
        """Accept a connection and resolve its player identity.

        Returns (player_id, is_new). When the session already maps to a player
        still present in the game, we rebind to that existing hero (preserving
        inventory/HP/depth/position) instead of spawning a fresh one.
        """
        await websocket.accept()
        if game_id not in self.game_instances:
            self.active_connections[game_id] = {}
            self.game_instances[game_id] = GameInstance(
                game_id,
                seed=(os.environ.get(PUBLIC_ROOM_SEED_ENV) if game_id == PUBLIC_ROOM_ID else (seed or None)),
            )
            self.last_sent_floor[game_id] = {}
            self.sessions[game_id] = {}
            self.disconnect_deadline[game_id] = {}

        game = self.game_instances[game_id]
        existing_player_id = self.sessions[game_id].get(session_id)
        if existing_player_id and existing_player_id in game.players:
            # Reconnect: rebind to the live hero and cancel its removal.
            player_id = existing_player_id
            self.disconnect_deadline[game_id].pop(player_id, None)
            game.players[player_id].is_afk = False
            game.players[player_id].movement.stop()
            game.players[player_id].movement.last_processed_seq = 0
            # Re-open any subclass / armor-ability choice window that was up
            # when the player dropped (the choice isn't consumed by wearing
            # the mask/crown, so it survives the reconnect).
            game.reemit_pending_choices(player_id)
            # Force a fresh INIT (full grid/depth) on the next broadcast.
            self.last_sent_floor[game_id].pop(player_id, None)

            # Remove any stale WebSocket connections for this player before
            # registering the new one. If we don't, broadcast_state will try
            # to send state updates on the old socket (which may already be
            # closed or closing), causing RuntimeError: "Unexpected ASGI message
            # 'websocket.send', after sending 'websocket.close'".
            stale = [ws for ws in list(self.active_connections[game_id].keys()) if ws is not websocket and self.active_connections[game_id][ws] == player_id]
            for ws in stale:
                self.active_connections[game_id].pop(ws, None)
                try:
                    await ws.close(code=1000, reason="Replaced by new connection")
                except Exception:
                    pass

            self.active_connections[game_id][websocket] = player_id
            return player_id, False

        player_id = str(uuid.uuid4())
        self.sessions[game_id][session_id] = player_id
        self.active_connections[game_id][websocket] = player_id
        return player_id, True

    async def send_player_init(self, game_id: str, websocket: WebSocket, player_id: str, is_new: bool = True):
        game = self.game_instances[game_id]
        state = game.get_state(player_id)
        player_floor = state.get("depth", 1)
        floor = game._get_or_create_floor(player_floor)
        map_version = getattr(floor, "map_version", 0)
        items = state.get("items", [])
        self_player = state.get("self_player")

        init = InitMessage(
            player_id=player_id,
            is_new=is_new,
            depth=player_floor,
            grid=state["grid"],
            width=state["width"],
            height=state["height"],
            traps=state.get("traps", []),
            plants=state.get("plants", []),
            items=items,
            difficulty=game.difficulty,  # type: ignore[arg-type]
            custom_tiles=state.get("custom_tiles", []),
            custom_walls=state.get("custom_walls", []),
            torches=state.get("torches", []),
            entrance_pos=getattr(floor, 'entrance_pos', None),
            exit_pos=getattr(floor, 'exit_pos', None),
            self_player=self_player,
        )
        try:
            await websocket.send_json(init.model_dump(exclude_none=True))
            self.last_sent_floor.setdefault(game_id, {})[player_id] = (player_floor, map_version)
            self.last_sent_items.setdefault(game_id, {})[player_id] = items
            self.last_sent_traps.setdefault(game_id, {})[player_id] = state.get("traps", [])
            self.last_sent_plants.setdefault(game_id, {})[player_id] = state.get("plants", [])
            # Reset the FOV diff cursors: this INIT resets the client's fog
            # (initFloor wipes `discovered`), so the next STATE_UPDATE must ship
            # a full visible/mapped snapshot regardless of whether the FOV is
            # unchanged since the last connection (reconnect at the same spot).
            self.last_sent_visible.get(game_id, {}).pop(player_id, None)
            self.last_sent_mapped.get(game_id, {}).pop(player_id, None)
            stripped_sp = _strip_transient_player_fields(self_player)
            if stripped_sp is not None:
                self.last_sent_player.setdefault(game_id, {})[player_id] = stripped_sp
        except Exception as e:
            logger.debug("Failed to send init message to player_id=%s: %s", player_id, e)

    async def listen_events(self, game_id: str, websocket: WebSocket, player_id: str):
        game = self.game_instances.get(game_id)
        if not game:
            return

        while True:
            data = await websocket.receive_text()
            try:
                message = CLIENT_MESSAGE_ADAPTER.validate_json(data)
            except ValidationError as e:
                logger.warning("Invalid WS message from %s: %s", player_id, e)
                continue

            await dispatcher.dispatch(game, player_id, message, websocket)


    def _mark_disconnected(self, game_id: str, player_id: str) -> None:
        """Mark a player's hero AFK with a reconnect-grace deadline so
        reap_expired_players eventually removes it. Safe to call from
        disconnect() (normal WebSocketDisconnect) or directly after the
        broadcast loop drops a dead connection that is no longer present in
        active_connections (abnormal close, e.g. a crashed tab)."""
        # A newer connection for this same hero may already be live -- e.g.
        # React StrictMode double-invokes the connect effect once in dev, so
        # a stale first socket's disconnect can arrive after a second socket
        # for the same session already rebound. Don't let that stale close
        # mark a still-connected hero AFK ("stuck as a ghost").
        if player_id in self.active_connections.get(game_id, {}).values():
            return
        # Keep the hero in the world during a grace window so the client can
        # reconnect (same session) and resume. The reaper removes it if not.
        game = self.game_instances.get(game_id)
        if game and player_id in game.players:
            player = game.players[player_id]
            player.movement.stop()
            # Ghost mode: non-solid, un-targetable, "(AFK)" tag client-side.
            player.is_afk = True
            self.disconnect_deadline.setdefault(game_id, {})[player_id] = (
                time.monotonic() + DISCONNECT_GRACE_SECONDS
            )

    def disconnect(self, game_id: str, websocket: WebSocket):
        if game_id not in self.active_connections:
            return
        if websocket in self.active_connections[game_id]:
            player_id = self.active_connections[game_id][websocket]
            del self.active_connections[game_id][websocket]
            self._mark_disconnected(game_id, player_id)

    def reap_expired_players(self, game_id: str):
        """Kill heroes whose reconnect grace window has elapsed."""
        deadlines = self.disconnect_deadline.get(game_id)
        if not deadlines:
            return
        game = self.game_instances.get(game_id)
        connected = set(self.active_connections.get(game_id, {}).values())
        now = time.monotonic()
        for player_id, deadline in list(deadlines.items()):
            if player_id in connected:
                # Reconnected since the deadline was set; clear it.
                deadlines.pop(player_id, None)
                continue
            if now < deadline:
                continue
            deadlines.pop(player_id, None)
            self.last_sent_floor.get(game_id, {}).pop(player_id, None)
            self.last_sent_items.get(game_id, {}).pop(player_id, None)
            self.last_sent_traps.get(game_id, {}).pop(player_id, None)
            self.last_sent_plants.get(game_id, {}).pop(player_id, None)
            self.last_sent_player.get(game_id, {}).pop(player_id, None)
            self.last_sent_visible.get(game_id, {}).pop(player_id, None)
            self.last_sent_mapped.get(game_id, {}).pop(player_id, None)
            if game and player_id in game.players:
                player = game.players[player_id]
                # Didn't reconnect in time -- die for real (gear scatter, grave,
                # DEATH event) via the normal death path: the next update_tick()
                # (called right after this from broadcast_state) picks up
                # is_alive=False and not death_processed and runs _kill_player.
                # Leave the entity in game.players so a later reconnect on this
                # session rebinds to the dead hero and sees the death/score screen.
                if player.is_alive:
                    player.hp = 0
                    player.is_downed = True
                    player.is_alive = False
                # Bound the corpses each game retains; drop the oldest beyond the
                # cap so abandoned runs can't pin their floors in memory forever.
                retained = self.retained_corpses.setdefault(game_id, [])
                retained.append(player_id)
                while len(retained) > MAX_RETAINED_CORPSES:
                    game.players.pop(retained.pop(0), None)

    def cleanup_if_empty(self, game_id: str):
        """Tear down a game once nobody is connected and no hero awaits reconnect."""
        if self.active_connections.get(game_id):
            return
        if self.disconnect_deadline.get(game_id):
            return
        game = self.game_instances.get(game_id)
        # Dead heroes (AFK-reaped or otherwise) no longer get deleted from
        # game.players -- a corpse alone shouldn't keep an abandoned game
        # alive forever, so only a still-living hero blocks teardown here.
        if game and any(p.is_alive for p in game.players.values()):
            return
        self.active_connections.pop(game_id, None)
        self.game_instances.pop(game_id, None)
        self.last_sent_floor.pop(game_id, None)
        self.last_sent_items.pop(game_id, None)
        self.last_sent_traps.pop(game_id, None)
        self.last_sent_plants.pop(game_id, None)
        self.last_sent_player.pop(game_id, None)
        self.last_sent_visible.pop(game_id, None)
        self.last_sent_mapped.pop(game_id, None)
        self.sessions.pop(game_id, None)
        self.disconnect_deadline.pop(game_id, None)
        self.retained_corpses.pop(game_id, None)
        if game_id != PUBLIC_ROOM_ID:
            self.rooms.pop(game_id, None)

    async def broadcast_state(self, game_id: str):
        if game_id in self.active_connections and game_id in self.game_instances:
            game = self.game_instances[game_id]
            game.update_tick()
            events = game.flush_events()

            connections_snapshot = list(self.active_connections[game_id].items())
            if not connections_snapshot:
                return

            import asyncio

            async def send_to_client(connection: WebSocket, player_id: str):
                if player_id not in game.players:
                    return None

                state = game.get_state(player_id)
                player_floor = state.get("depth", 1)
                floor = game._get_or_create_floor(player_floor)
                map_version = getattr(floor, "map_version", 0)
                previous = self.last_sent_floor.setdefault(game_id, {}).get(player_id)

                try:
                    if previous != (player_floor, map_version):
                        floor = game._get_or_create_floor(player_floor)
                        items = state.get("items", [])
                        self_player_init = state.get("self_player")
                        init = InitMessage(
                            depth=player_floor,
                            grid=state["grid"],
                            width=state["width"],
                            height=state["height"],
                            traps=state.get("traps", []),
                            plants=state.get("plants", []),
                            items=items,
                            difficulty=game.difficulty,  # type: ignore[arg-type]
                            custom_tiles=state.get("custom_tiles", []),
                            custom_walls=state.get("custom_walls", []),
                            torches=state.get("torches", []),
                            entrance_pos=getattr(floor, 'entrance_pos', None),
                            exit_pos=getattr(floor, 'exit_pos', None),
                            self_player=self_player_init,
                        )
                        await connection.send_json(init.model_dump(exclude_none=True))
                        self.last_sent_floor[game_id][player_id] = (player_floor, map_version)
                        self.last_sent_items.setdefault(game_id, {})[player_id] = items
                        self.last_sent_traps.setdefault(game_id, {})[player_id] = state.get("traps", [])
                        self.last_sent_plants.setdefault(game_id, {})[player_id] = state.get("plants", [])
                        # Reset the FOV diff cursor so the next frame definitely
                        # ships a fresh visible/mapped snapshot (the client's fog
                        # is reset by initFloor on connect/floor change).
                        self.last_sent_visible.get(game_id, {}).pop(player_id, None)
                        self.last_sent_mapped.get(game_id, {}).pop(player_id, None)
                        stripped_sp_init = _strip_transient_player_fields(self_player_init)
                        if stripped_sp_init is not None:
                            self.last_sent_player.setdefault(game_id, {})[player_id] = stripped_sp_init

                    current_items = state.get("items", [])
                    last_items = self.last_sent_items.setdefault(game_id, {}).get(player_id)
                    if last_items is None or current_items != last_items:
                        items_payload = current_items
                        self.last_sent_items[game_id][player_id] = current_items
                    else:
                        items_payload = None

                    current_traps = state.get("traps", [])
                    last_traps = self.last_sent_traps.setdefault(game_id, {}).get(player_id)
                    if last_traps is None or current_traps != last_traps:
                        traps_payload = current_traps
                        self.last_sent_traps[game_id][player_id] = current_traps
                    else:
                        traps_payload = None

                    current_plants = state.get("plants", [])
                    last_plants = self.last_sent_plants.setdefault(game_id, {}).get(player_id)
                    if last_plants is None or current_plants != last_plants:
                        plants_payload = current_plants
                        self.last_sent_plants[game_id][player_id] = current_plants
                    else:
                        plants_payload = None

                    current_self_player = state.get("self_player")
                    stripped_current_sp = _strip_transient_player_fields(current_self_player)
                    last_sp = self.last_sent_player.setdefault(game_id, {}).get(player_id)

                    if stripped_current_sp is not None and (last_sp is None or stripped_current_sp != last_sp):
                        self_player_payload = current_self_player
                        self.last_sent_player[game_id][player_id] = stripped_current_sp
                    else:
                        self_player_payload = None

                    # Per-player event filter once; movement acks then split out.
                    filtered_events = game.filter_events_for_player(events, player_id)

                    # MOVE_RESULT fast lane: each player's own step confirmations
                    # go out as compact top-level messages ahead of the bulk
                    # frame (and are excluded from the frame's events, so the
                    # client never processes them twice). Step acks are then
                    # bounded by RTT instead of full-frame serialization -- the
                    # client's predictor notches one ack per step in real time
                    # instead of stalling its step buffer on frame latency.
                    move_acks = [e for e in filtered_events if e.get("type") == "MOVE_RESULT"]
                    frame_events = [e for e in filtered_events if e.get("type") != "MOVE_RESULT"]
                    for ack in move_acks:
                        await connection.send_json(MoveResultMessage(data=ack["data"]).model_dump(exclude_none=True))

                    # FOV diff: visible_tiles/mapped_tiles only change when the
                    # player moves (or a scroll/burst affects vision). Omitting
                    # them when unchanged turns a static screen into ~0 FOV bytes
                    # instead of re-serializing ~200 cells at 40Hz.
                    current_visible = state.get("visible_tiles", [])
                    last_visible = self.last_sent_visible.setdefault(game_id, {}).get(player_id)
                    if last_visible is None or current_visible != last_visible:
                        visible_payload = current_visible
                        self.last_sent_visible[game_id][player_id] = current_visible
                    else:
                        visible_payload = None

                    current_mapped = state.get("mapped_tiles", [])
                    last_mapped = self.last_sent_mapped.setdefault(game_id, {}).get(player_id)
                    if last_mapped is None or current_mapped != last_mapped:
                        mapped_payload = current_mapped
                        self.last_sent_mapped[game_id][player_id] = current_mapped
                    else:
                        mapped_payload = None

                    update = StateUpdateMessage(
                        players=state["players"],
                        mobs=state["mobs"],
                        items=items_payload,
                        traps=traps_payload,
                        plants=plants_payload,
                        visible_tiles=visible_payload,
                        mapped_tiles=mapped_payload,
                        events=frame_events,
                        self_player=self_player_payload,
                    )
                    await connection.send_json(update.model_dump(exclude_none=True))
                except (RuntimeError, Exception) as err:
                    # WebSocket is closed, closing, or encountered a transport error.
                    logger.debug("Failed broadcast send to player_id=%s: %s", player_id, err)
                    raise err
                return None

            tasks = [send_to_client(conn, pid) for conn, pid in connections_snapshot]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            dead_connections = []
            for (conn, pid), res in zip(connections_snapshot, results):
                if isinstance(res, Exception):
                    logger.debug("Cleanly dropping closed connection for player_id=%s", pid)
                    dead_connections.append((conn, pid))

            for conn, pid in dead_connections:
                if game_id in self.active_connections and conn in self.active_connections[game_id]:
                    del self.active_connections[game_id][conn]
                # The socket is already gone from active_connections here, so a
                # plain disconnect() call would no-op and the hero would stay
                # alive forever. Mark AFK directly so the normal grace window +
                # reaper apply to abnormal closes too.
                self._mark_disconnected(game_id, pid)


manager = ConnectionManager()
