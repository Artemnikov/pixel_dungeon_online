"""Outgoing server -> client message envelopes: INIT, STATE_UPDATE, PONG.

These wrap the per-tick frames that main.py used to build as bare dicts. The nested
entity / item / event payloads are deliberately left loose (`list[Any]` /
`dict[str, Any]`, `extra="allow"`): they're already serialized, unidentified-masked
and augmented with computed fields (actions/description/appearance) in
engine/game/serialization.py, so re-validating them strictly here would drop keys
the client relies on.

Build a model, then `model_dump(exclude_none=True)` for `send_json` — this produces
byte-identical keys to the old hand-built dicts (e.g. INIT only carries `player_id`
on first connect, where it's set; floor-change INIT leaves it None -> excluded).
"""

from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from .common import Difficulty


class _Envelope(BaseModel):
    model_config = ConfigDict(extra="allow")


class PongMessage(_Envelope):
    type: Literal["PONG"] = "PONG"


class InitMessage(_Envelope):
    type: Literal["INIT"] = "INIT"
    depth: int
    grid: List[List[int]]
    width: int
    height: int
    traps: List[Dict[str, Any]]
    items: List[Any] = []
    difficulty: Difficulty = "normal"
    custom_tiles: List[Dict[str, Any]] = []
    custom_walls: List[Dict[str, Any]] = []
    torches: List[Tuple[int, int]] = []
    # Only set on the very first INIT after connecting; omitted on floor change.
    player_id: Optional[str] = None
    # True only when this connect spawned a brand-new hero, False when it
    # rebound to an existing one (reconnect/resume) -- player_id alone can't
    # tell the two apart, since it's set on both. Omitted on floor change.
    is_new: Optional[bool] = None
    entrance_pos: Optional[Tuple[int, int]] = None
    exit_pos: Optional[Tuple[int, int]] = None
    self_player: Optional[Dict[str, Any]] = None


class MoveResultMessage(_Envelope):
    """Compact movement-ack fast lane sent ahead of the bulk STATE_UPDATE.

    broadcast_state splits each player's MOVE_RESULT events out of the frame and
    ships them as dedicated top-level messages (one per step), so step
    confirmation is bounded by RTT instead of frame serialization + payload.
    """

    type: Literal["MOVE_RESULT"] = "MOVE_RESULT"
    data: Dict[str, Any]


class StateUpdateMessage(_Envelope):
    type: Literal["STATE_UPDATE"] = "STATE_UPDATE"
    players: List[Any]
    mobs: List[Any]
    # Optional on purpose: broadcast_state diffs the per-player FOV and omits
    # the field when it hasn't changed (a static screen sends zero FOV bytes).
    visible_tiles: Optional[List[Any]] = None
    events: List[Any]
    items: Optional[List[Any]] = None
    depth: Optional[int] = None
    traps: Optional[List[Dict[str, Any]]] = None
    mapped_tiles: Optional[List[Tuple[int, int]]] = None
    gold: Optional[int] = None
    energy: Optional[int] = None
    has_amulet: Optional[Dict[str, Any]] = None
    self_player: Optional[Dict[str, Any]] = None
