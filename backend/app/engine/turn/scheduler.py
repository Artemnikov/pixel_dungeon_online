import heapq
import itertools
from typing import List, Optional, Tuple

from app.engine.game.constants import TURN_TIME_EPSILON
from app.engine.turn.actors import ActorRef


class TurnScheduler:
    def __init__(self) -> None:
        self.now = 0.0
        self._queue: List[Tuple[float, int, int, ActorRef]] = []
        self._seq = itertools.count()

    @staticmethod
    def _snap(time_value: float) -> float:
        nearest = round(time_value)
        if abs(time_value - nearest) < TURN_TIME_EPSILON:
            return float(nearest)
        return time_value

    def schedule(self, actor: ActorRef, delay: float) -> None:
        actor.scheduled_time = self._snap(self.now + delay)
        self.push_back(actor)

    def reschedule(self, actor: ActorRef, cost: float) -> None:
        self.schedule(actor, cost)

    def push_back(self, actor: ActorRef) -> None:
        heapq.heappush(self._queue, (actor.scheduled_time, -actor.act_priority, next(self._seq), actor))

    def _discard_cancelled_head(self) -> None:
        """Pop cancelled entries off the top.

        An actor that dies, is downed, or leaves is flagged instead of being
        searched for and removed from the middle of the heap, which would be
        O(n) per death on a floor full of mobs. The flag is checked here, the
        one place the queue order is consulted.
        """
        while self._queue and self._queue[0][3].cancelled:
            heapq.heappop(self._queue)

    def peek(self) -> Optional[ActorRef]:
        """The actor whose turn is next, without advancing the clock.

        SPD's game loop asks "whose turn is it?" before committing to one, so
        the turn-based room can park on a hero who owes input instead of
        consuming a turn it can't resolve.
        """
        self._discard_cancelled_head()
        return self._queue[0][3] if self._queue else None

    def preview(self, count: int) -> List[ActorRef]:
        """The next `count` actors in turn order, for the client turn strip.

        Heap order is already (time, -priority, insertion), which is the same
        order pop() would yield, so a straight sort of a copy is exact.
        """
        self._discard_cancelled_head()
        return [
            entry[3]
            for entry in heapq.nsmallest(count, self._queue)
            if not entry[3].cancelled
        ][:count]

    def pop(self) -> ActorRef:
        self._discard_cancelled_head()
        _, _, _, actor = heapq.heappop(self._queue)
        self.now = actor.scheduled_time
        return actor
