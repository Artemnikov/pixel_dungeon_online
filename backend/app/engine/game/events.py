"""Event queue for GameInstance.

Events are buffered each tick, then filtered per-player (by floor, target, and
line-of-sight to the source) before being flushed to clients.
"""

import logging
import os
from typing import List, Optional

from app.engine.entities.base import Position
from app.engine.entities.items.potions import ELIXIR_BREW_KINDS
from app.schemas.events import EVENT_MODELS

logger = logging.getLogger(__name__)

# Event payload fields that carry an item's display name, keyed by event type.
# These are masked per-recipient so an undiscovered potion/scroll never leaks
# its real type (SPD shows the scrambled label for unknown consumables).
_MASKED_NAME_FIELDS = {"PICKUP": "item", "DROP": "item_name"}

# Opt-in: when set, validate each event's payload against its schema and warn on
# drift. Off in production (zero overhead, no wire change); on in tests.
_VALIDATE_EVENTS = bool(os.environ.get("PXD_VALIDATE_EVENTS"))


def _validate_event_payload(event_type: str, data: dict) -> None:
    model = EVENT_MODELS.get(event_type)
    if model is None:
        logger.warning("Unknown event type %r (no schema in EVENT_MODELS)", event_type)
        return
    try:
        model.model_validate(data)
    except Exception as exc:  # pydantic.ValidationError
        logger.warning("Event %r payload failed validation: %s", event_type, exc)


class EventsMixin:
    def add_event(self, event_type: str, data: dict = None, floor_id: Optional[int] = None, player_id: Optional[str] = None, source_player_id: Optional[str] = None, echo_to_source: bool = False):
        data = data or {}
        if _VALIDATE_EVENTS:
            _validate_event_payload(event_type, data)
        event = {
            "type": event_type,
            "data": data,
        }
        if floor_id is not None:
            event["_floor_id"] = floor_id
        if player_id is not None:
            event["_player_id"] = player_id
        if source_player_id is not None:
            event["_source_player_id"] = source_player_id
            if echo_to_source:
                event["_echo_to_source"] = True
        self.events.append(event)

    def _mask_name_for(self, event: dict, player) -> dict:
        # Per-recipient masking of potion/scroll/ring info in events: if the
        # recipient hasn't personally discovered the kind, swap the raw name for
        # the scrambled per-run label (PICKUP/DROP), or re-mask an embedded item
        # dict (RANGED_ATTACK thrown items). Copies the event so the shared
        # payload isn't mutated for other recipients.
        data = event.get("data", {})
        etype = event.get("type")

        if etype == "RANGED_ATTACK":
            item_dict = data.get("item")
            if not isinstance(item_dict, dict):
                return event
            kind = item_dict.get("kind")
            typ = item_dict.get("type")
            # Already-masked dicts keep their scrambled appearance — re-running
            # the mask would recompute a wrong sprite index, so leave them alone.
            if (not kind or kind == typ
                    or typ not in ("potion", "scroll", "ring")
                    or kind in ELIXIR_BREW_KINDS
                    or kind in player.discovered_kinds):
                return event
            new_data = dict(data)
            new_data["item"] = self._mask_item_dict(dict(item_dict), player.discovered_kinds)
            new_event = dict(event)
            new_event["data"] = new_data
            return new_event

        field = _MASKED_NAME_FIELDS.get(etype)
        if field is None:
            return event
        kind = data.get("item_kind")
        item_type = data.get("item_type")
        if not kind or item_type not in ("potion", "scroll", "ring"):
            return event
        if kind in ELIXIR_BREW_KINDS or kind in player.discovered_kinds:
            return event
        new_data = dict(data)
        new_data[field] = self._label_for(kind, item_type)
        new_event = dict(event)
        new_event["data"] = new_data
        return new_event

    def filter_events_for_player(self, events: List[dict], player_id: str) -> List[dict]:
        player = self.players.get(player_id)
        if not player:
            return []

        filtered = []
        for event in events:
            event_player = event.get("_player_id")
            event_floor = event.get("_floor_id")
            source_player_id = event.get("_source_player_id")

            if event_player is not None and event_player != player_id:
                continue

            # Never echo events back to the player who emitted/originated them,
            # unless the server is the only source of that feedback
            # (echo_to_source) and the client predicts nothing for it.
            if source_player_id is not None and source_player_id == player_id and not event.get("_echo_to_source"):
                continue

            if event_floor is not None and event_floor != player.floor_id:
                continue

            # LOS scoping uses one of two anchors:
            #   _source_player_id — action feedback tied to a player (attacks,
            #     drinks, chat). Scoped to that player's current position.
            #   data.x/data.y     — world/effect events without a source player
            #     (mob steps, blob evolution). Scoped to the effect's cell.
            # _source_player_id wins when both are present; its x/y in data is
            # then ignored for filtering.
            if source_player_id is not None:
                source_player = self.players.get(source_player_id)
                if source_player and source_player.floor_id == player.floor_id:
                    if not self._is_in_los(player.pos, source_player.pos, floor_id=player.floor_id):
                        continue

            # LOS check: events with explicit x/y position (e.g. mob-step sounds)
            # are only audible to players who can see that cell
            if source_player_id is None:
                ev_data = event.get("data", {})
                sx, sy = ev_data.get("x"), ev_data.get("y")
                if sx is not None and sy is not None:
                    if not self._is_in_los(player.pos, Position(x=sx, y=sy), floor_id=player.floor_id):
                        continue

            out = {k: v for k, v in event.items() if not k.startswith("_")}
            filtered.append(self._mask_name_for(out, player))

        return filtered

    def flush_events(self):
        events = self.events
        self.events = []
        return events
