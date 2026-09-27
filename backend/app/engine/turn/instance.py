"""Turn-based `GameInstance`: simultaneous player turn and dungeon faction turn.

Real-time rooms run `TickMixin.update_tick` at GAME_LOOP_HZ and let every
entity act continuously. A turn room instead runs in rounds:

1. **Player Phase (Players' Turn)**:
   All active (alive, non-downed) players take their action at the same time.
   Actions are queued as pending and executed during the pump.
   Once every active player has taken their turn (or auto-waited via timer),
   the player phase completes.

2. **Dungeon Faction Phase (Dungeon's Turn)**:
   All dungeon mobs take their turns, world upkeep runs for the elapsed
   turn unit, and the game clock advances to the next player round.

Differences from the real-time path:
* `clock()` returns the turn time, so the engine's existing `action_until` /
  surprise-window / loot-window comparisons read SPD time units instead of
  wall-clock seconds.
* Mob AI is driven per dungeon turn in `_mob_take_turn`.
* World upkeep runs per whole SPD time unit in `turn/world.py`.
* Continuous held-key movement is dropped; discrete actions are processed.
* A far tap is a path request: `path_queue` is drained one tile per turn round.
"""

import time
from typing import Dict, List, Optional, Set

from app.engine.entities.player import Player
from app.engine.game.constants import (
    GAME_MODE_TURNBASED,
    TICKS_PER_TURN,
    TIME_TO_ATTACK,
    TIME_TO_IDLE,
    TIME_TO_MOVE_BASE,
    TIME_TO_WAIT,
    TURN_BASED_WALK_SPEED_MULTIPLIER,
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

        self.sim_unit = 1.0
        self.sim_ticks = TICKS_PER_TURN

        self.scheduler = TurnScheduler()

        # entity_id -> ActorRef.
        self._player_actors: Dict[str, PlayerActor] = {}
        self._mob_actors: Dict[str, MobActor] = {}

        # Set of player IDs who have acted in the current player phase round.
        self._players_acted: Set[str] = set()

        # Whole SPD time units the world has been kept up to.
        self._upkeep_units: int = 0

        # Set while any hero is owed input, so the turn timer knows when to start
        # counting, and None while no input is needed.
        self._turn_deadline: Optional[float] = None
        self._forced_wait_pending: bool = False

        # Wall-clock pacing left over from the real-time mob AI. Zeroed before
        # each mob turn to disable the wall-clock gate inside _tick_mob.
        self._mob_move_times: Dict[str, float] = {}
        self._ally_move_times: Dict[str, float] = {}

        self._broadcast_dirty: bool = True

    # --- clock & movement hooks --------------------------------------------

    def clock(self) -> float:
        return self.scheduler.now

    def action_blocked(self, entity) -> bool:
        return False

    def attack_ready(self, entity, cooldown: float) -> bool:
        return True

    def _gate_steps_on_wall_clock(self) -> bool:
        return False

    def _get_step_duration_multiplier(self) -> float:
        return TURN_BASED_WALK_SPEED_MULTIPLIER

    def add_player(self, *args, **kwargs) -> Player:
        player = super().add_player(*args, **kwargs)
        self._broadcast_dirty = True
        return player

    # --- active player queries ---------------------------------------------

    def _active_players(self) -> Dict[str, Player]:
        return {pid: p for pid, p in self.players.items() if p.is_active}

    def _all_players_have_acted(self) -> bool:
        active = self._active_players()
        return bool(active) and all(pid in self._players_acted for pid in active)

    # --- the 40Hz pump -----------------------------------------------------

    def update_tick(self, dt: float = 0.0) -> None:
        self._invalidate_fov_cache()
        self._reconcile_actors()

        self._process_player_phase()

        if self._turn_deadline is not None and time.monotonic() >= self._turn_deadline:
            self._force_wait_unacted_players()

        if self._all_players_have_acted():
            self._resolve_dungeon_phase()

        if pending_upkeep_units(self) > 0:
            self._run_due_upkeep()

        self._update_turn_timer()
        self._emit_state_effects()

    def _process_player_phase(self) -> None:
        """Execute pending player actions and auto-walks for the current round."""
        for pid, player in list(self._active_players().items()):
            actor = self._player_actors.get(pid)
            if actor is None:
                continue

            if actor.pending_action is not None:
                actor.take_turn(self)
                self._players_acted.add(pid)
                self._broadcast_dirty = True
            elif pid not in self._players_acted and actor.is_auto_walking():
                if actor.walk_floor_id == player.floor_id and not player.movement.is_ready_for_step():
                    continue
                actor.take_turn(self)
                self._players_acted.add(pid)
                self._broadcast_dirty = True

    def _resolve_dungeon_phase(self) -> None:
        """Run dungeon faction turn: all mobs act, upkeep runs, next round begins."""
        self._run_dungeon_mob_turns()
        self.scheduler.now += 1.0
        self._run_due_upkeep()
        self._players_acted.clear()
        self._turn_deadline = None
        self._broadcast_dirty = True

    def _run_dungeon_mob_turns(self) -> None:
        for floor_id in list(self.active_floor_ids):
            floor = self.floors.get(floor_id)
            if floor is None:
                continue
            for mob in list(floor.mobs.values()):
                if mob.is_alive and mob.id in floor.mobs:
                    actor = self._mob_actors.get(mob.id)
                    if actor is not None:
                        actor.take_turn(self)
                    else:
                        self._mob_take_turn(mob)

    def _clear_mob_ai_pacing(self, entity) -> None:
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

    def _update_turn_timer(self) -> None:
        has_waiting_player = any(
            actor.requires_input()
            for pid, actor in self._player_actors.items()
            if pid not in self._players_acted and actor.player.is_active
        )
        if has_waiting_player:
            if self._turn_deadline is None:
                self._turn_deadline = time.monotonic() + self.turn_timer_seconds
        else:
            self._turn_deadline = None

    def _force_wait_unacted_players(self) -> None:
        """Auto-wait all active players who have not yet acted this round."""
        self._turn_deadline = None
        for pid in self._active_players():
            if pid not in self._players_acted:
                actor = self._player_actors.get(pid)
                if actor is not None:
                    actor.clear_walk()
                    actor.pending_action = None
                self.wait(pid)
                self._players_acted.add(pid)
                self._broadcast_dirty = True

    def turn_timer_remaining(self) -> Optional[float]:
        if self._turn_deadline is None:
            return None
        return max(0.0, self._turn_deadline - time.monotonic())

    # --- mob turns ---------------------------------------------------------

    def _mob_take_turn(self, mob) -> float:
        if not mob.is_alive:
            return TIME_TO_WAIT

        floor = self._get_or_create_floor(mob.floor_id)
        if floor is None or mob.id not in floor.mobs:
            return TIME_TO_WAIT

        self._mob_move_times[mob.id] = 0.0
        self._ally_move_times[mob.id] = 0.0

        pre_x, pre_y = mob.pos.x, mob.pos.y
        pre_attack_time = getattr(mob, "last_attack_time", 0.0)
        self._tick_mob(mob, floor, mob.floor_id)
        if not mob.is_alive:
            return TIME_TO_WAIT

        if (mob.pos.x, mob.pos.y) != (pre_x, pre_y):
            return TIME_TO_MOVE_BASE / max(0.1, float(mob.speed))
        if getattr(mob, "last_attack_time", 0.0) != pre_attack_time or self._mob_can_strike(mob, floor, mob.floor_id):
            base_dly = getattr(mob, "attack_delay", TIME_TO_ATTACK)
            if mob.has_buff("slow") or mob.has_buff("chill"):
                base_dly *= 2.0
            if mob.has_buff("haste") or mob.has_buff("fury"):
                base_dly *= 0.5
            return max(0.1, float(base_dly))
        return TIME_TO_IDLE

    def _mob_can_strike(self, mob, floor, floor_id: int) -> bool:
        for other in floor.mobs.values():
            if other.id == mob.id or not other.is_alive:
                continue
            if other.faction == mob.faction:
                continue
            if abs(other.pos.x - mob.pos.x) <= 1 and abs(other.pos.y - mob.pos.y) <= 1:
                return True
        for player in self._players_on_floor(floor_id):
            if not player.is_active or player.invisible > 0 or player.faction == mob.faction:
                continue
            if abs(player.pos.x - mob.pos.x) <= 1 and abs(player.pos.y - mob.pos.y) <= 1:
                return True
        return False

    # --- hero walking -------------------------------------------------------

    def _player_walk_turn(self, actor: PlayerActor) -> float:
        player = actor.player
        if actor.walk_floor_id != player.floor_id or walk_interrupted(self, actor):
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
            actor.walk_floor_id = None
            return TIME_TO_WAIT
        if player.floor_id != actor.walk_floor_id:
            actor.clear_walk()
        else:
            actor.walk_floor_id = None if not player.movement.has_path() else actor.walk_floor_id
        return _move_cost(self, player)

    # --- actor registry ----------------------------------------------------

    def _reconcile_actors(self) -> None:
        live_players = {pid: p for pid, p in self.players.items() if p.is_active}
        for pid, actor in list(self._player_actors.items()):
            if pid not in live_players:
                actor.cancelled = True
                del self._player_actors[pid]
                self._players_acted.discard(pid)
        for pid, player in live_players.items():
            if pid not in self._player_actors:
                player.movement.path_queue.clear()
                actor = PlayerActor(player)
                self._player_actors[pid] = actor
                self.scheduler.push_back(actor)
                self._broadcast_dirty = True

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

        Free actions (0 cost) run immediately and do not consume the turn.
        Costed actions queue as pending for this turn round and mark the
        player as acted. When all active players have acted, the dungeon phase
        resolves.
        """
        player = self.players.get(player_id)
        if player is None or not player.is_active:
            return False

        action = build_turn_action(self, player, message)
        if action is None:
            return False

        if action.cost <= 0.0:
            action.run(self, player, action.message)
            self._broadcast_dirty = True
            return True

        if player_id in self._players_acted:
            return False

        actor = self._player_actors.get(player_id)
        if actor is None or actor.pending_action is not None:
            return False

        if action.label != "PATH_STEPS":
            actor.clear_walk()

        actor.pending_action = action
        self._players_acted.add(player_id)
        self._broadcast_dirty = True
        return True

    # --- per-viewer payload ------------------------------------------------

    def turn_state_for(self, player_id: str) -> Optional[dict]:
        """The `turn` block of this player's STATE_UPDATE view."""
        player = self.players.get(player_id)
        if player is None or not player.is_active:
            return {
                "game_mode": self.game_mode,
                "is_my_turn": False,
                "turn": int(self.scheduler.now),
                "order": [],
                "timer": None,
            }

        has_acted = player_id in self._players_acted
        actor = self._player_actors.get(player_id)
        is_walking = actor is not None and actor.is_auto_walking()
        has_pending = actor is not None and actor.pending_action is not None

        is_my_turn = (not has_acted or is_walking) and not has_pending

        order: List[dict] = []
        for pid, p in self.players.items():
            if p.is_active:
                p_actor = self._player_actors.get(pid)
                needs_input = (pid not in self._players_acted) and p_actor is not None and p_actor.requires_input()
                order.append(
                    {
                        "id": pid,
                        "kind": "player",
                        "name": p.name,
                        "class_type": p.class_type,
                        "needs_input": bool(needs_input),
                        "has_acted": bool(pid in self._players_acted),
                    }
                )

        for floor_id in self.active_floor_ids:
            floor = self.floors.get(floor_id)
            if floor is None:
                continue
            for mob in floor.mobs.values():
                if mob.is_alive:
                    order.append(
                        {
                            "id": mob.id,
                            "kind": "mob",
                            "name": getattr(mob, "name", getattr(mob, "type", "Mob")),
                            "needs_input": False,
                        }
                    )
                    if len(order) >= TURN_ORDER_PREVIEW:
                        break
            if len(order) >= TURN_ORDER_PREVIEW:
                break

        timer = self.turn_timer_remaining() if (actor is not None and actor.requires_input() and not has_acted) else None

        return {
            "game_mode": self.game_mode,
            "is_my_turn": bool(is_my_turn),
            "turn": int(self.scheduler.now),
            "order": order[:TURN_ORDER_PREVIEW],
            "timer": timer,
        }

    def active_actor(self) -> Optional[PlayerActor]:
        for pid, actor in self._player_actors.items():
            if pid not in self._players_acted and actor.requires_input():
                return actor
        return None
