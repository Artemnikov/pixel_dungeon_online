from typing import TYPE_CHECKING, FrozenSet, Optional, Tuple

from app.engine.game.constants import HERO_PRIO, MOB_PRIO, TIME_TO_WAIT

if TYPE_CHECKING:
    from app.engine.turn.actions import TurnAction


class ActorRef:
    def __init__(self, entity_id: str, act_priority: int) -> None:
        self.entity_id = entity_id
        self.act_priority = act_priority
        self.scheduled_time = 0.0
        # Set when the actor leaves the room (died, downed, disconnected).
        # The scheduler drops flagged entries lazily instead of deleting them
        # from the middle of its heap.
        self.cancelled = False

    def take_turn(self, game) -> float:
        raise NotImplementedError

    def requires_input(self) -> bool:
        return False


class PlayerActor(ActorRef):
    def __init__(self, player) -> None:
        super().__init__(player.id, HERO_PRIO)
        self.player = player
        self.pending_action: Optional["TurnAction"] = None
        # Floor the queued path was computed on. A walk that outlives a change
        # of floor is stale deltas, not a route, so it is dropped rather than
        # replayed against the new layout.
        self.walk_floor_id: Optional[int] = None
        # SPD's `Hero.visibleEnemies`: what the hero could see last time this
        # was refreshed, so a walk can tell a new arrival from a mob that was
        # always in view. See `turn/walk.py`.
        self.visible_enemies: FrozenSet[Tuple[int, int]] = frozenset()

    def is_auto_walking(self) -> bool:
        # Deliberately not a floor check: a path planned on another floor is
        # stale, and `_player_walk_turn` is what notices and drops it. Testing
        # the floor here would let the hero fall back to waiting for input and
        # leave the stale queue in place forever.
        return self.walk_floor_id is not None and self.player.movement.has_path()

    def clear_walk(self) -> None:
        self.walk_floor_id = None
        self.player.movement.path_queue.clear()

    def requires_input(self) -> bool:
        return (
            self.player.is_alive
            and not self.player.is_downed
            and self.pending_action is None
            and not self.is_auto_walking()
        )

    def take_turn(self, game) -> float:
        action = self.pending_action
        if action is not None:
            self.pending_action = None
            return action.execute(game, self.player)
        if self.is_auto_walking():
            return game._player_walk_turn(self)
        return TIME_TO_WAIT


class MobActor(ActorRef):
    def __init__(self, mob) -> None:
        super().__init__(mob.id, MOB_PRIO)
        self.mob = mob

    def take_turn(self, game) -> float:
        return game._mob_take_turn(self.mob)
