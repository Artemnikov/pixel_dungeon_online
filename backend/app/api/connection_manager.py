"""Lobby layer: rooms, WS connection bookkeeping, and the per-tick broadcast.

Deliberately kept out of GameInstance/engine, which stays a pure
dungeon-simulation concern (see `RoomMeta` below).
"""

import hashlib
import logging
import re
import secrets
import time
import uuid
from typing import Dict, Optional, Tuple

from fastapi import WebSocket

from app.engine.entities.items_consumable import Amulet
from app.engine.manager import GameInstance
from app.engine.game.constants import PARTY_LOOT_MAX_PLAYERS
from app.schemas import InitMessage, StateUpdateMessage

logger = logging.getLogger(__name__)

# How long a disconnected player's hero is kept alive in the world so the client
# can reconnect (same session) and resume the same run. After this, the reaper
# removes the orphaned player.
DISCONNECT_GRACE_SECONDS = 60.0

# Rooms: one permanent public room (uncapped) plus player-created private
# groups (name + optional password), capped at the same party size the loot
# scaling tops out at (see engine/game/constants.party_loot_multiplier).
PUBLIC_ROOM_ID = "public"
PRIVATE_ROOM_MAX_PLAYERS = PARTY_LOOT_MAX_PLAYERS

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return slug or "group"


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


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
        # game_id -> {session_id: player_id} — stable identity across reconnects.
        self.sessions: Dict[str, Dict[str, str]] = {}
        # game_id -> {player_id: monotonic deadline} — players awaiting reconnect.
        self.disconnect_deadline: Dict[str, Dict[str, float]] = {}
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
            self.game_instances[game_id] = GameInstance(game_id, seed=seed or None)
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
            # Force a fresh INIT (full grid/depth) on the next broadcast.
            self.last_sent_floor[game_id].pop(player_id, None)
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

        floor = game._get_or_create_floor(player_floor)
        init = InitMessage(
            player_id=player_id,
            is_new=is_new,
            depth=player_floor,
            grid=state["grid"],
            width=state["width"],
            height=state["height"],
            traps=state.get("traps", []),
            custom_tiles=state.get("custom_tiles", []),
            custom_walls=state.get("custom_walls", []),
            torches=state.get("torches", []),
            entrance_pos=getattr(floor, 'entrance_pos', None),
            exit_pos=getattr(floor, 'exit_pos', None),
        )
        await websocket.send_json(init.model_dump(exclude_none=True))
        self.last_sent_floor.setdefault(game_id, {})[player_id] = (player_floor, map_version)


    def disconnect(self, game_id: str, websocket: WebSocket):
        if game_id not in self.active_connections:
            return
        if websocket in self.active_connections[game_id]:
            player_id = self.active_connections[game_id][websocket]
            del self.active_connections[game_id][websocket]
            # A newer connection for this same hero may already be live -- e.g.
            # React StrictMode double-invokes the connect effect once in dev, so
            # a stale first socket's disconnect can arrive after a second socket
            # for the same session already rebound. Don't let that stale close
            # mark a still-connected hero AFK ("stuck as a ghost").
            if player_id in self.active_connections[game_id].values():
                return
            # Keep the hero in the world during a grace window so the client can
            # reconnect (same session) and resume. The reaper removes it if not.
            game = self.game_instances.get(game_id)
            if game and player_id in game.players:
                player = game.players[player_id]
                # Stop any in-progress walking so a disconnected hero stands still.
                player.move_intent = None
                player.path_queue = []
                # Ghost mode: non-solid, un-targetable, "(AFK)" tag client-side.
                player.is_afk = True
                self.disconnect_deadline.setdefault(game_id, {})[player_id] = (
                    time.monotonic() + DISCONNECT_GRACE_SECONDS
                )

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
        self.sessions.pop(game_id, None)
        self.disconnect_deadline.pop(game_id, None)
        if game_id != PUBLIC_ROOM_ID:
            self.rooms.pop(game_id, None)

    async def broadcast_state(self, game_id: str):
        if game_id in self.active_connections and game_id in self.game_instances:
            game = self.game_instances[game_id]
            game.update_tick()
            events = game.flush_events()
            dead_connections = []

            # Snapshot before iterating: connect/disconnect can mutate this dict
            # from another coroutine while `await connection.send_json(...)`
            # below yields control, which raised "dictionary changed size during
            # iteration" and crashed the single global_game_loop task -- since
            # that loop has no per-game exception isolation, one game's mutation
            # race silently froze broadcast_state for every game on the server.
            for connection, player_id in list(self.active_connections[game_id].items()):
                try:
                    if player_id not in game.players:
                        continue

                    state = game.get_state(player_id)
                    player_floor = state.get("depth", 1)
                    floor = game._get_or_create_floor(player_floor)
                    map_version = getattr(floor, "map_version", 0)
                    previous = self.last_sent_floor.setdefault(game_id, {}).get(player_id)

                    if previous != (player_floor, map_version):
                        floor = game._get_or_create_floor(player_floor)
                        init = InitMessage(
                            depth=player_floor,
                            grid=state["grid"],
                            width=state["width"],
                            height=state["height"],
                            traps=state.get("traps", []),
                            custom_tiles=state.get("custom_tiles", []),
                            custom_walls=state.get("custom_walls", []),
                            torches=state.get("torches", []),
                            entrance_pos=getattr(floor, 'entrance_pos', None),
                            exit_pos=getattr(floor, 'exit_pos', None),
                        )
                        await connection.send_json(init.model_dump(exclude_none=True))
                        self.last_sent_floor[game_id][player_id] = (player_floor, map_version)

                    player_obj = game.players.get(player_id)
                    gold = player_obj.gold if player_obj else 0
                    energy = player_obj.energy if player_obj else 0
                    has_amulet = (
                        any(isinstance(it, Amulet) for it in player_obj.belongings.all_items())
                        if player_obj else False
                    )
                    boss_lurking = game._boss_lurking_on_floor(player_floor)

                    update = StateUpdateMessage(
                        depth=player_floor,
                        difficulty=game.difficulty,
                        players=state["players"],
                        mobs=state["mobs"],
                        items=state.get("items", []),
                        visible_tiles=state.get("visible_tiles", []),
                        traps=state.get("traps", []),
                        gold=gold,
                        energy=energy,
                        has_amulet=has_amulet,
                        boss_lurking=boss_lurking,
                        mapped_tiles=state.get("mapped_tiles", []),
                        events=game.filter_events_for_player(events, player_id),
                    )
                    await connection.send_json(update.model_dump(exclude_none=True))
                except Exception:
                    logger.exception("Error broadcasting to player_id=%s", player_id)
                    dead_connections.append(connection)

            for conn in dead_connections:
                self.disconnect(game_id, conn)


manager = ConnectionManager()
