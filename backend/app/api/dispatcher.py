import logging
from typing import Any, Callable, Dict, Type

from app.engine.game.constants import GAME_MODE_REALTIME, GAME_MODE_TURNBASED
from app.engine.manager import GameInstance
from app.schemas import CLIENT_MESSAGE_ADAPTER, ClientMessage, PongMessage
from app.schemas import messages as msg

logger = logging.getLogger(__name__)

Handler = Callable[[GameInstance, str, Any], None]


class MessageDispatcher:
    """Dispatches validated client messages to registered type handlers."""

    def __init__(self):
        self._handlers: Dict[Type[ClientMessage], Handler] = {}

    def register(self, message_type: Type[ClientMessage]):
        def decorator(func: Handler) -> Handler:
            self._handlers[message_type] = func
            return func

        return decorator

    async def dispatch(
        self, game: GameInstance, player_id: str, message: ClientMessage, websocket: Any
    ) -> None:
        if isinstance(message, msg.Ping):
            await websocket.send_json(PongMessage().model_dump())
            return

        # A turn-based room owns its own action intake: a message becomes a
        # costed TurnAction queued for the player's next turn, or is dropped.
        # Going through the normal handlers instead would let a player act out
        # of turn, and would run the real-time movement plumbing a turn room
        # deliberately ignores. `submit_turn_action` reports False for both
        # "not your turn" and "not an action", so there is nothing else to do.
        if getattr(game, "game_mode", GAME_MODE_REALTIME) == GAME_MODE_TURNBASED:
            game.submit_turn_action(player_id, message)
            return

        handler = self._handlers.get(type(message))
        if handler:
            try:
                handler(game, player_id, message)
            except Exception:
                logger.exception(
                    "game_websocket: error handling message %s from %s",
                    type(message).__name__,
                    player_id,
                )
        else:
            logger.warning(
                "No handler registered for message type %s from %s",
                type(message).__name__,
                player_id,
            )


dispatcher = MessageDispatcher()
