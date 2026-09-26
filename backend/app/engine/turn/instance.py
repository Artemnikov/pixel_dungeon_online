"""Turn-based `GameInstance`: the SPD actor-energy scheduler over a real room.

Real-time rooms run `TickMixin.update_tick` at GAME_LOOP_HZ and let every
entity act continuously. A turn room instead keeps one SPD time cursor
(`TurnScheduler`) shared by every player and mob on the floor, and advances it
one actor at a time, exactly as `NoosaPixelGame.update` does:

    while (!isGamePaused() && now >= nextTurn) {
        turn(now); nextTurn = now + turn();
    }

The 40Hz server tick is only a *pump* here. It asks the scheduler for as many
actor turns as are due, stops the moment a hero is owed input, and otherwise
does nothing. That is what keeps a paused turn room from flooding the socket:
`should_broadcast` reports dirty only after an action or a turn boundary.

Differences from the real-time path, all deliberate:

* `clock()` returns the scheduler's time, so the engine's existing
  `action_until` / surprise-window / loot-window comparisons read SPD time
  units instead of wall-clock seconds, and a room can be paused indefinitely
  without any of them expiring.
* Mob AI is driven per mob turn, not per tick -- see `_mob_take_turn`.
* World upkeep runs per whole SPD time unit, not per tick -- see
  `turn/world.py`.
* Player movement is action-driven, so no held-key input is read at all.
* A far tap is a path request rather than a step: the client's deltas sit in
  `path_queue` and the hero's own following turns drain one per turn, since
  the real-time path pump never runs here -- see `turn/walk.py`.
"""

import time
from typing import Dict, List, Optional

from app.engine.game.constants import (
    GAME_MODE_TURNBASED,
    MAX_TURN_STEPS_PER_TICK,
    TICKS_PER_TURN,
    TIME_TO_ATTACK,
    TIME_TO_IDLE,
    TIME_TO_MOVE_BASE,
    TIME_TO_WAIT,
    TURN_ORDER_PREVIEW,
)
from app.engine.manager import GameInstance
from app.engine.turn.actions import _move_cost, build_turn_action
from app.engine.turn.actors import MobActor, PlayerActor
from app.engine.turn.scheduler import TurnScheduler
from app.engine.turn.walk import refresh_visible_enemies, walk_interrupted
from app.engine.turn.world import pending_upkeep_units, run_turn_upkeep


class TurnBasedGameInstance(GameInstance):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game_mode = GAME_MODE_TURNBASED

        # One whole SPD time unit per world-step, and one game turn's worth of
        # engine ticks. Every dt-driven and tick-counted system in the engine
        # reads these instead of hardcoded real-time values.
        self.sim_unit = 1.0
        self.sim_ticks = TICKS_PER_TURN

        self.scheduler = TurnScheduler()

        # entity_id -> ActorRef. Reconciled every pump rather than hooked into
        # the many places players join/leave, change floor, and mobs spawn or
        # die, so no lifecycle path can leave a stale actor in the queue.
        self._player_actors: Dict[str, PlayerActor] = {}
        self._mob_actors: Dict[str, MobActor] = {}

        # Whole SPD time units the world has been kept up to.
        self._upkeep_units: int = 0

        # Set while a hero is owed input, so the turn timer knows when to start
        # counting, and None while the room is running free.
        self._turn_deadline: Optional[float] = None
        self._forced_wait_pending: bool = False

        # Wall-clock pacing left over from the real-time mob AI. The scheduler
        # owns mob timing in this mode, so `_mob_take_turn` zeroes these before
        # each call to disable the wall-clock gate inside _tick_mob.
        self._mob_move_times: Dict[str, float] = {}
        self._ally_move_times: Dict[str, float] = {}

        # Set by the dispatcher when a turn action arrives; consumed and run by
        # the scheduler on the actor's next turn.
        self._broadcast_dirty: bool = True

    # --- clock -------------------------------------------------------------

    def clock(self) -> float:
        return self.scheduler.now

    def action_blocked(self, entity) -> bool:
        """Never block: the scheduler is the `spend()` in this mode.

        The real-time default gates movement and item use on `action_until`.
        Here the actor was dequeued only because it was due, and its action has
        already been charged `TurnAction.cost` SPD time units, so the wall-clock
        gate would stall the turn it exists to pace.
        """
        return False

    def attack_ready(self, entity, cooldown: float) -> bool:
        """Never block: `attackDelay` is charged as the turn's time cost.

        This also matters for a mob's first strike after it engages, which the
        real-time path deliberately delays by `aggro_windup`; SPD's `Mob.act()`
        has no such windup and attacks on the turn it decides to.
        """
        return True

    # --- the 40Hz pump -----------------------------------------------------

    def step_player_move(self, player_id: str, dx: int, dy: int) -> None:
        """Move one tile as a single discrete step.

        The base implementation is the real-time pacer: it refuses a step
        until the previous hop's wall-clock `step_duration` has elapsed, which
        would silently swallow every second move in a turn room. Turn pacing
        comes from the scheduler instead, so the step is unconditional -- only
        the same `on_step_executed` bookkeeping the client animates against.
        """
        player = self.players.get(player_id)
        if player is None or player.is_downed or not player.is_alive:
            return
        player.movement.stop()
        pre_x, pre_y = player.pos.x, player.pos.y
        self.move_entity(player_id, dx, dy)
        if (player.pos.x, player.pos.y) != (pre_x, pre_y):
            player.movement.on_step_executed(None, 0.0, dx, dy)
        else:
            player.movement.on_step_failed(None)

    def update_tick(self, dt: float = 0.0) -> None:
        self._invalidate_fov_cache()
        self._reconcile_actors()

        if self._consume_forced_wait():
            return

        if self._drain_actor_turns():
            self._broadcast_dirty = True
        if pending_upkeep_units(self) > 0:
            self._run_due_upkeep()
        if self._expire_turn_timer():
            return

        self._emit_state_effects()

    def _drain_actor_turns(self, budget: int = MAX_TURN_STEPS_PER_TICK) -> int:
        """Run every actor turn that is due, stopping at the first hero input.

        This is the `while (now >= nextTurn) turn()` loop from SPD's
        NoosaPixelGame.update, bounded per pump so a long mob cascade can't
        starve the event loop.
        """
        steps = 0
        while steps < budget:
            head = self.scheduler.peek()
            if head is None:
                self._turn_deadline = None
                break

            if head.scheduled_time > self.scheduler.now:
                # Nobody is due yet, so time passes to the next scheduled turn.
                # The head is by definition the earliest actor, so skipping
                # forward to it steps over nobody. SPD's game reaches the same
                # state from the other side: it is blocked inside hero.act(),
                # having already advanced nextTurn past every mob turn.
                self.scheduler.now = head.scheduled_time
                self._hold_for_input(head)
                break

            if head.requires_input():
                self._hold_for_input(head)
                break

            actor = self.scheduler.pop()
            cost = self._run_actor_turn(actor)
            self.scheduler.reschedule(actor, cost)
            steps += 1

        return steps

    def _hold_for_input(self, actor) -> None:
        """Room is waiting on a hero: (re)arm the turn timer if needed."""
        if self._turn_deadline is None:
            self._turn_deadline = time.monotonic() + self.turn_timer_seconds

    def _run_actor_turn(self, actor) -> float:
        self._turn_deadline = None
        entity = actor.player if isinstance(actor, PlayerActor) else actor.mob
        self._clear_mob_ai_pacing(entity)
        if not isinstance(actor, PlayerActor):
            return actor.take_turn(self)
        pre = (actor.player.pos.x, actor.player.pos.y)
        actor.player._moved_this_turn = False
        try:
            return actor.take_turn(self)
        finally:
            actor.player._moved_this_turn = (
                actor.player.pos.x, actor.player.pos.y
            ) != pre
            # Keeps the "newly visible enemy" comparison honest between turns:
            # a mob that walks into the FOV while the hero is mid-trip has to
            # read as new on the step that follows it.
            refresh_visible_enemies(self, actor)

    def _clear_mob_ai_pacing(self, entity) -> None:
        """Hand mob AI timing to the scheduler for one turn.

        The mob AI in this engine gates movement on wall-clock via the
        `_mob_move_times` / `_ally_move_times` dictionaries (shadow allies pace
        through the second). Zeroing this turn's entry makes `can_move` true, so
        the mob's SPD act() cost -- 1/speed for a step, attackDelay for a strike
        -- is what decides how often it moves.

        This is only the AI's own pacing. The per-entity action limiters are
        handled by the `action_blocked` / `attack_ready` overrides below.
        """
        if hasattr(entity, "id"):
            self._mob_move_times[entity.id] = 0.0
            self._ally_move_times[entity.id] = 0.0

    def _run_due_upkeep(self) -> None:
        units = pending_upkeep_units(self)
        if units <= 0:
            return
        self._broadcast_dirty = True
        for _ in range(units):
            self._upkeep_units += 1
            run_turn_upkeep(self)

    # --- turn timer --------------------------------------------------------

    def _expire_turn_timer(self) -> bool:
        """Auto-Wait the hero who ran out the clock.

        SPD has no such timer, but a multiplayer room has to keep moving when a
        player walks away from the keyboard, so an expired deadline is turned
        into the wait the player would have sent themselves.

        The deadline is wall-clock on purpose: it measures how long a human sat
        on their turn, not simulated game time, so it must not be read off the
        scheduler cursor.
        """
        if self._turn_deadline is None:
            return False
        if time.monotonic() < self._turn_deadline:
            return False
        self._turn_deadline = None
        self._forced_wait_pending = True
        return True

    def _consume_forced_wait(self) -> bool:
        if not self._forced_wait_pending:
            return False
        self._forced_wait_pending = False
        head = self.scheduler.peek()
        if head is not None and head.requires_input():
            if isinstance(head, PlayerActor):
                self._broadcast_dirty = True
                self.scheduler.reschedule(head, TIME_TO_WAIT)
        return True

    def turn_timer_remaining(self) -> Optional[float]:
        if self._turn_deadline is None:
            return None
        return max(0.0, self._turn_deadline - time.monotonic())

    # --- mob turns ---------------------------------------------------------

    def _mob_take_turn(self, mob) -> float:
        """One SPD mob turn: run the AI, then charge what it did.

        The cost mirrors `Mob.act()` -- 1/speed() for a step, attackDelay() for
        a strike, TIME_TO_IDLE when it had nothing to do. Mob AI in this engine
        is written for the real-time loop and gates movement on wall-clock via
        `_mob_move_times` / `_ally_move_times`; zeroing those first hands timing
        to the scheduler, which is what this mode is for.
        """
        if not mob.is_alive:
            return TIME_TO_WAIT

        floor = self._get_or_create_floor(mob.floor_id)
        if floor is None or mob.id not in floor.mobs:
            return TIME_TO_WAIT

        self._mob_move_times[mob.id] = 0.0
        self._ally_move_times[mob.id] = 0.0
        if not mob.is_alive:
            return TIME_TO_WAIT

        pre_x, pre_y = mob.pos.x, mob.pos.y
        self._tick_mob(mob, floor, mob.floor_id)
        if not mob.is_alive:
            return TIME_TO_WAIT

        if (mob.pos.x, mob.pos.y) != (pre_x, pre_y):
            return TIME_TO_MOVE_BASE / max(0.1, float(mob.speed))
        if self._mob_can_strike(mob, floor, mob.floor_id):
            return TIME_TO_ATTACK
        return TIME_TO_IDLE

    def _mob_can_strike(self, mob, floor, floor_id: int) -> bool:
        """Whether the mob is in melee reach, i.e. its turn was an attack.

        A mob attack in this engine is a bump into the target's tile, so it
        leaves the mob's own position unchanged -- indistinguishable from idling
        by position alone. Reach is the thing that separates them.
        """
        for other in floor.mobs.values():
            if other.id == mob.id or not other.is_alive:
                continue
            if other.faction == mob.faction:
                continue
            if abs(other.pos.x - mob.pos.x) <= 1 and abs(other.pos.y - mob.pos.y) <= 1:
                return True
        for player in self._players_on_floor(floor_id):
            if not player.is_alive or player.faction == mob.faction:
                continue
            if abs(player.pos.x - mob.pos.x) <= 1 and abs(player.pos.y - mob.pos.y) <= 1:
                return True
        return False

    # --- hero walking -------------------------------------------------------

    def _player_walk_turn(self, actor) -> float:
        """One tile of a tap-to-travel path, charged as that hero's turn.

        The turn-mode stand-in for the real-time path pump in
        `PlayerTickMixin._process_player_movement`, which a turn room never
        runs. The head of the queue is validated before it is spent, so the trip
        ends rather than turning into something the player did not ask for:

        * a change of floor leaves stale deltas, not a route;
        * a hostile that came into view interrupts, as in SPD's
          `Hero.checkVisibleMobs` -- a walk never bump-attacks, because
          attacking is an explicit action there too;
        * an occupied next tile is the same interruption one tile earlier.

        Everything else is handed to `step_player_move`, whose own
        `on_step_failed` bookkeeping clears the queue when a step turns out not
        to move anybody -- a wall, a closed door, a mob that was not there when
        the tile was checked.
        """
        player = actor.player
        if actor.walk_floor_id != player.floor_id:
            actor.clear_walk()
            return TIME_TO_WAIT
        if walk_interrupted(self, actor):
            actor.clear_walk()
            return TIME_TO_WAIT

        floor = self._get_or_create_floor(player.floor_id)
        if floor is None or not player.movement.has_path():
            actor.clear_walk()
            return TIME_TO_WAIT

        dx, dy = player.movement.path_queue[0]
        nx, ny = player.pos.x + dx, player.pos.y + dy
        if any(
            mob.is_alive and mob.pos.x == nx and mob.pos.y == ny
            for mob in floor.mobs.values()
        ):
            actor.clear_walk()
            return TIME_TO_WAIT

        player.movement.path_queue.popleft()
        pre_x, pre_y = player.pos.x, player.pos.y
        self.step_player_move(player.id, dx, dy)
        if (player.pos.x, player.pos.y) == (pre_x, pre_y):
            # The step didn't move anybody, so `on_step_failed` already dropped
            # the rest of the route; there was no turn's worth of walking.
            actor.walk_floor_id = None
            return TIME_TO_WAIT
        if player.floor_id != actor.walk_floor_id:
            # Descending resolves inside `move_entity`, and the deltas left were
            # planned for the floor just left behind.
            actor.clear_walk()
        else:
            actor.walk_floor_id = None if not player.movement.has_path() else actor.walk_floor_id
        return _move_cost(self, player)

    # --- actor registry ----------------------------------------------------

    def _reconcile_actors(self) -> None:
        """Sync the scheduler's actors with the live players and mobs.

        Reconciliation rather than lifecycle hooks: players join, leave, change
        floor and die through a dozen call sites, and mobs are spawned, killed
        and respawned by the level generator. Walking the live sets every pump
        is the one approach that cannot miss a path.
        """
        live_players = {
            pid: p for pid, p in self.players.items() if p.is_alive and not p.is_downed
        }
        for pid, actor in list(self._player_actors.items()):
            if pid not in live_players:
                # Flagged, not spliced: the scheduler drops it when it reaches
                # the top, so a corpse never holds the room and never burns a
                # step out of the per-pump budget.
                actor.cancelled = True
                del self._player_actors[pid]
        for pid, player in live_players.items():
            if pid not in self._player_actors:
                # A queue left over from a real-time room (or a previous life)
                # is not a route this hero planned, and its actor has no walk
                # state to own it.
                player.movement.path_queue.clear()
                actor = PlayerActor(player)
                self._player_actors[pid] = actor
                self.scheduler.push_back(actor)

        live_mobs: Dict[str, object] = {}
        for floor_id in self.active_floor_ids:
            floor = self.floors.get(floor_id)
            if floor is None:
                continue
            for mob in floor.mobs.values():
                if mob.is_alive:
                    live_mobs[mob.id] = mob
        for mob_id, actor in list(self._mob_actors.items()):
            if mob_id not in live_mobs:
                actor.cancelled = True
                del self._mob_actors[mob_id]
        for mob_id, mob in live_mobs.items():
            if mob_id not in self._mob_actors:
                actor = MobActor(mob)
                self._mob_actors[mob_id] = actor
                self.scheduler.push_back(actor)

    # --- broadcast gating --------------------------------------------------

    def should_broadcast(self) -> bool:
        """Dirty only after an action or a turn boundary.

        A paused turn room must not send 40 state updates a second, so the pump
        is silent until something actually happened.
        """
        if not self._broadcast_dirty:
            return False
        self._broadcast_dirty = False
        return True

    def mark_dirty(self) -> None:
        self._broadcast_dirty = True

    def on_broadcast_complete(self) -> None:
        return None

    # --- client action intake ---------------------------------------------

    def submit_turn_action(self, player_id: str, message) -> bool:
        """Apply `message` as the given player's action.

        Returns False without spending time when the message isn't something
        this player may do right now, which is also how a non-active player's
        input is ignored.

        A zero-cost call -- chat, a menu, picking something up off the ground
        into a hand -- is not a turn, so it runs immediately and is allowed
        even when the room is waiting on somebody else. Only costed actions
        queue behind the scheduler, which is what releases the room.
        """
        player = self.players.get(player_id)
        if player is None or not player.is_alive or player.is_downed:
            return False

        action = build_turn_action(self, player, message)
        if action is None:
            return False

        if action.cost <= 0.0:
            action.run(self, player, action.message)
            self._broadcast_dirty = True
            return True

        head = self.scheduler.peek()
        if not isinstance(head, PlayerActor) or head.player.id != player_id:
            return False
        if head.pending_action is not None:
            return False

        # A costed action replaces a trip in progress, as it does in SPD where a
        # new `curAction` overwrites the walk -- including a new tap, which is
        # how a second far click retargets the first. Free calls (a menu, an
        # equip) are not turns and so leave the walk alone; they can't disturb
        # it either, since turn mode never gates on `action_until`.
        head.clear_walk()
        head.pending_action = action
        self._broadcast_dirty = True
        return True

    # --- per-viewer payload ------------------------------------------------

    def turn_state_for(self, player_id: str) -> Optional[dict]:
        """The `turn` block of this player's STATE_UPDATE view."""
        head = self.scheduler.peek()
        if head is None:
            return {
                "game_mode": self.game_mode,
                "is_my_turn": False,
                "turn": 0,
                "order": [],
                "timer": None,
            }

        waiting = head.requires_input()
        mine = isinstance(head, PlayerActor) and head.player.id == player_id
        order: List[dict] = []
        for actor in self.scheduler.preview(TURN_ORDER_PREVIEW):
            kind = "player" if isinstance(actor, PlayerActor) else "mob"
            entity_id = actor.player.id if isinstance(actor, PlayerActor) else actor.entity_id
            order.append(
                {
                    "id": entity_id,
                    "kind": kind,
                    "needs_input": actor.requires_input(),
                }
            )

        return {
            "game_mode": self.game_mode,
            # `mine`, not `mine and waiting`: a hero walking a path is not owed
            # input, but its owner must still be able to interrupt the walk, and
            # the client gates every action on this flag (`canActNow`). Outside a
            # walk the two are the same condition.
            "is_my_turn": bool(mine),
            "turn": int(self.scheduler.now),
            "order": order,
            "timer": self.turn_timer_remaining() if mine and waiting else None,
        }

    def active_actor(self):
        head = self.scheduler.peek()
        if head is not None and head.requires_input():
            return head
        return None
