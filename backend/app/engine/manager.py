"""Central game state for a single multiplayer session.

`GameInstance` owns all game state and coordinates the engine subsystems. The
implementation is split into per-concern mixins under ``app.engine.game`` so each
area stays small and editable in isolation; this module composes them and holds
the shared constructor.

Re-exports below (``FloorState``, ``TileType``, ``Position``, ``CharacterClass``,
the module constants) keep the historical ``from app.engine.manager import ...``
import paths working for callers and tests.
"""

import time
from typing import Dict, List, Optional, Tuple

# Re-exported for backward-compatible imports (main.py, tests).
from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.player import CharacterClass, Difficulty, Player

from app.engine.game.constants import (
    AUTO_MOVE_INTERVAL,
    DEFAULT_TURN_TIMER_SECONDS,
    GAME_MODE_REALTIME,
    HEAL_TICK_INTERVAL,
    MAP_HEIGHT,
    MAP_WIDTH,
    MAX_FLOOR_ID,
    NO_RESPAWN_FLOORS,
    PASSIVE_REGEN_INTERVAL,
    RESPAWN_TURNS,
    SEWERS_MAX_FLOOR,
    TICK_DURATION,
)
from app.engine.game.floor_state import FloorState
from app.engine.game.alchemy import AlchemyMixin
from app.engine.game.bombs import BombsMixin
from app.engine.game.armor_abilities import ArmorAbilitiesMixin
from app.engine.game.chat import ChatMixin
from app.engine.game.events import EventsMixin
from app.engine.game.floors import FloorAccessMixin
from app.engine.game.generation import GenerationMixin
from app.engine.game.items import ItemsMixin
from app.engine.game.movement import MovementCombatMixin
from app.engine.game.players import PlayersMixin
from app.engine.game.rogue import RogueMixin
from app.engine.game.serialization import SerializationMixin
from app.engine.game.talents import TalentsMixin
from app.engine.game.tengu_arena import PrisonBossMixin
from app.engine.game.ai_tengu import TenguAIMixin
from app.engine.game.player_tick import PlayerTickMixin
from app.engine.game.mob_ai_dispatch import MobAIDispatchMixin
from app.engine.game.mob_ai_movement import MobAIMovementMixin
from app.engine.game.damage_over_time import DamageOverTimeMixin
from app.engine.game.spawning import SpawnTickMixin
from app.engine.game.status_effects_tick import StatusEffectsTickMixin
from app.engine.game.player_regen import PlayerRegenMixin
from app.engine.game.tick import TickMixin
from app.engine.game.vision import VisionMixin
from app.engine.game.world import WorldInteractionMixin
from app.engine.game.unlocks import PendingUnlocksMixin
from app.engine.game.mob_death import MobDeathMixin
from app.engine.game.npc_economy import NpcEconomyMixin
from app.engine.game.artifacts import ArtifactsMixin
from app.engine.game.duelist import DuelistMixin
from app.engine.game.cleric import ClericMixin
from app.engine.game.public_room import PublicRoomMixin


class GameInstance(
    FloorAccessMixin,
    EventsMixin,
    ChatMixin,
    GenerationMixin,
    PlayersMixin,
    WorldInteractionMixin,
    PendingUnlocksMixin,
    MobDeathMixin,
    NpcEconomyMixin,
    MovementCombatMixin,
    ItemsMixin,
    AlchemyMixin,
    BombsMixin,
    PrisonBossMixin,
    TenguAIMixin,
    PlayerTickMixin,
    MobAIDispatchMixin,
    MobAIMovementMixin,
    DamageOverTimeMixin,
    SpawnTickMixin,
    StatusEffectsTickMixin,
    PlayerRegenMixin,
    TickMixin,
    ArmorAbilitiesMixin,
    TalentsMixin,
    RogueMixin,
    ArtifactsMixin,
    DuelistMixin,
    ClericMixin,
    VisionMixin,
    SerializationMixin,
    PublicRoomMixin,
):
    def __init__(self, game_id: str, seed: Optional[str] = None,
                 turn_timer_seconds: float = DEFAULT_TURN_TIMER_SECONDS):
        self.game_id = game_id
        self.depth = 1  # Compatibility view for single-floor tests/legacy callers.

        # Which GameInstance subclass runs this room. The lobby layer reads it
        # from RoomMeta; the WebSocket envelopes advertise it to clients.
        self.game_mode = GAME_MODE_REALTIME
        self.turn_timer_seconds = turn_timer_seconds

        # Simulated seconds advanced by one world-step. Real-time rooms step
        # every 25ms; turn-based rooms step one whole SPD time unit (TICK) per
        # completed turn. Every dt-driven system in the engine (buff durations,
        # regen, blob lifetimes, wand recharge) is authored in these units, so
        # this single value is all that separates the two modes.
        self.sim_unit: float = TICK_DURATION

        # Engine ticks charged by one world-step, for the systems that count in
        # ticks rather than seconds (fuse counters, respawn counters, mob
        # ability cooldowns). Real-time charges 1; turn-based charges a whole
        # game turn so tick-counted constants stay correct in both modes.
        self.sim_ticks: int = 1

        self.players: Dict[str, Player] = {}
        self.floors: Dict[int, FloorState] = {}
        self.floor_cache: Dict[int, bytes] = {}
        self.events: List[dict] = []

        # Per-tick shadowcasting caches. Open doors depend on occupancy, which
        # changes as entities move, so both are invalidated every tick (and on
        # any movement) via _invalidate_fov_cache().
        self._fov_cache: Dict[Tuple[int, int, int, int], List[bool]] = {}
        self._blocking_cache: Dict[int, List[bool]] = {}

        self.difficulty = Difficulty.NORMAL
        self.player_count = 0

        # Lobby challenge flags (SPD Challenges), comma-separated set parsed
        # via set_challenges(). Currently only "stronger_bosses" is supported.
        self.challenges: set = set()

        # Shared per-run identification knowledge (co-op semantics, mirrors SPD's
        # per-Dungeon catalog): once any player IDs a potion/scroll kind, the whole
        # party knows it. `kind_labels` holds the scrambled per-run display names
        # for still-unidentified kinds.
        self.identified_kinds: set = set()
        self.kind_labels: Dict[str, str] = {}
        self.kind_appearance: Dict[str, int] = {}
        self._appearance_used: Dict[str, set] = {"potion": set(), "scroll": set()}

        # Global drop limiters
        self.drop_counters: Dict[str, int] = {}

        # Player chat rate-limit windows: player_id -> channel -> deque of
        # monotonic timestamps (see engine/game/chat.py).
        self.chat_windows: Dict[str, Dict[str, object]] = {}

        # Per-run boss score tracking (SPD Statistics.bossScores)
        # Indices: 0=Goo, 1=Tengu, 2=DM300, 3=Dwarf King, 4=Yog
        self.boss_scores: Dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
        # Badge eligibility — set when entering a boss floor, cleared on
        # avoidable damage (SPD Statistics.qualifiedForBossChallengeBadge)
        self.qualified_for_boss_challenge: bool = False

        # DimensionalSundial day/night cycle start (unix timestamp).
        self.game_start_time = time.time()

        # Seed + RunState for SPD-parity level generation.
        if seed:
            from app.engine.dungeon.dungeon_seed import convert_from_text
            self.master_seed = convert_from_text(seed)
        else:
            import zlib
            self.master_seed = zlib.crc32(game_id.encode("utf-8")) % 5_429_503_678_976

        from app.engine.dungeon.spd_levelgen.run_state import RunState
        from app.engine.dungeon.spd_random import SPDRandom

        self.run_state = RunState()
        init_rng = SPDRandom()
        init_rng.push_generator(self.master_seed + 1)
        self.run_state.init_for_run(init_rng)
        init_rng.pop_generator()

        self.generate_floor(1)

    def clock(self) -> float:
        """Monotonic simulated-seconds used by every gameplay timing check.

        Real-time rooms return the wall clock. Turn-based rooms override this
        to return the turn scheduler's current time, so the same `action_until`
        / surprise-window / loot-window comparisons read turn units instead.
        """
        return time.monotonic()

    def action_blocked(self, entity) -> bool:
        """Whether a wall-clock action cooldown still blocks `entity`.

        The engine paces real-time actions with `action_until`, the port's
        stand-in for SPD's `Actor.spend()`. Turn-based rooms override this to
        always return False: the scheduler charges the SPD cost itself, and it
        only dequeues an actor when that actor is actually due.
        """
        return time.time() < getattr(entity, "action_until", 0.0)

    def attack_ready(self, entity, cooldown: float) -> bool:
        """Whether `entity`'s attack-rate cooldown has elapsed.

        As with `action_blocked`, this is a real-time rate limit standing in for
        SPD's `spend(attackDelay())`; turn-based rooms let the scheduler charge
        the delay instead and always report ready.
        """
        return time.time() - entity.last_attack_time >= cooldown

    def turn_state_for(self, player_id: str) -> Optional[dict]:
        """Per-viewer turn payload for the STATE_UPDATE envelope, or None."""
        return None

    def wait(self, player_id: str) -> None:
        return None

    def submit_turn_action(self, player_id: str, message) -> bool:
        """Turn-room action intake; real-time rooms have no scheduler.

        The dispatcher routes every client message here when the room's
        game_mode is turnbased, and falls through to the normal ws_handlers
        otherwise. Returning False is the real-time answer: there is no
        scheduler to charge the action to.
        """
        return False

    def should_broadcast(self) -> bool:
        return True

    def on_broadcast_complete(self) -> None:
        return None

    def _gate_steps_on_wall_clock(self) -> bool:
        """Whether `step_player_move` refuses a step until the step clock expires.

        Real-time rooms: yes, that gate *is* the pacer. A turn room says no,
        because its input arrives as fast as a player can click and a click must
        never be swallowed -- the scheduler holds a *walking* hero on the same
        clock instead (`ActorRef.turn_ready`), which is what keeps a
        tap-to-travel hop on the same cadence as a held real-time key.
        """
        return True

    def step_player_move(self, player_id: str, dx: int, dy: int) -> None:
        """Move one tile: the single movement path for both game modes.

        The step is paced and recorded identically wherever it runs -- the same
        `get_step_duration` clock, the same `on_step_executed` / `on_step_failed`
        bookkeeping the client animates against, and the same `move_entity`
        validation of the destination. Turn rooms share all of it and differ
        only in who enforces the wait (see `_gate_steps_on_wall_clock`).
        """
        player = self.players.get(player_id)
        if player is None or player.is_downed or not player.is_alive:
            return
        player.movement.stop()
        if self._gate_steps_on_wall_clock() and not player.movement.is_ready_for_step():
            return
        floor = self._get_or_create_floor(player.floor_id)
        pre_x, pre_y = player.pos.x, player.pos.y
        self.move_entity(player_id, dx, dy)
        if (player.pos.x, player.pos.y) != (pre_x, pre_y):
            step_duration = player.get_step_duration(
                enemies_nearby=self._has_enemies_nearby(floor, player, radius=3)
            )
            player.movement.on_step_executed(None, step_duration, dx, dy)
        else:
            player.movement.on_step_failed(None)
