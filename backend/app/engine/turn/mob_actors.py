"""Turn-based mob brains: one dungeon turn for one mob.

Real-time rooms let a mob act continuously at `GAME_LOOP_HZ` and rate-limit it
with wall-clock timestamps (`mob.last_attack_time` against
`mob.attack_cooldown`). A turn room has no such clock to measure against: a
dungeon phase resolves as fast as the heroes played, which for a fast player
is a few milliseconds. Boss and special-mob AI in `app/engine/game/ai_*.py` is
written against that wall clock, so left alone in a turn room those abilities
are gated shut for the whole fight -- a Shaman's zap is hard-capped at one per
1.5 real seconds, and Goo's pumped charge at one per `attack_cooldown` real
seconds, neither of which a turn room can ever reach.

This module is the turn-room half of that pacing, expressed as a class
hierarchy rather than mode checks scattered through the AI:

* `TurnMobActor` owns the turn algorithm every mob shares (SPD `Char.move()` /
  `Char.attackDelay()` / idle costs) as a template method, with hooks for the
  parts that differ per mob.
* `WallClockGatedMobActor` adds a turn-denominated cadence ledger. When the
  ledger says the mob's signature ability is due, the actor presents the
  wall clock as already elapsed, so the untouched real-time AI in `ai_*.py`
  sees its gate open exactly on the turn it is owed. It never rewrites the AI
  and never runs a second copy of it -- the AI still decides *whether* to
  attack; the actor only decides *when it is allowed to ask*.
* `TickCounterMobActor` advances mobs whose ability cooldowns are denominated
  in real-time ticks by one turn's worth of ticks per turn, so a threshold
  written as `5 * GAME_TURN_TICKS` stays five turns long instead of stretching
  to two hundred.

The real-time path in `app/engine/game/` is untouched: these classes are only
ever constructed by `create_mob_actor`, which only the turn room calls.
"""

import time

from app.engine.entities.mobs import (
    DM100,
    DM200,
    DM300,
    BlueShaman,
    DwarfKing,
    Eye,
    FireElemental,
    Goo,
    PurpleShaman,
    RedShaman,
    Spinner,
    Tengu,
    Warlock,
    YogDzewa,
)
from app.engine.game.constants import (
    GAME_TURN_TICKS,
    TIME_TO_ATTACK,
    TIME_TO_IDLE,
    TIME_TO_MOVE_BASE,
    TIME_TO_WAIT,
    TIME_TO_ZAP,
)


class TurnMobActor:
    """One mob's turn brain. Subclasses tune pacing; none of them re-run AI."""

    def __init__(self, mob, floor_id: int) -> None:
        self.mob = mob
        # Floor the scheduler last saw this mob on. The floor iteration that
        # owns the mob is the authority here, not `mob.floor_id`: a mob that
        # was summoned, re-parented, or spawned by a path that never stamped
        # the field would otherwise be looked up on the wrong floor and have
        # its turn dropped before the AI ran.
        self.floor_id = floor_id

    # --- SPD time costs (what the scheduler charges the actor) --------------

    def move_cost(self) -> float:
        """SPD `Char.move()`: `spend(1 / speed())` -- Char.java:298."""
        return TIME_TO_MOVE_BASE / max(0.1, float(self.mob.speed))

    def attack_cost(self) -> float:
        """SPD `Char.attackDelay()`: `spend(attackDelay())` -- Char.java:775."""
        base_dly = getattr(self.mob, "attack_delay", TIME_TO_ATTACK)
        if self.mob.has_buff("slow") or self.mob.has_buff("chill"):
            base_dly *= 2.0
        if self.mob.has_buff("haste") or self.mob.has_buff("fury"):
            base_dly *= 0.5
        return max(0.1, float(base_dly))

    def idle_cost(self) -> float:
        return TIME_TO_IDLE

    # --- the turn algorithm -------------------------------------------------

    def take_turn(self, game) -> float:
        """Run one dungeon turn and return the SPD time it charges.

        The body is the shared turn algorithm; the hooks below are the whole
        extension surface, so a new mob paces itself by subclassing rather
        than by adding a mode check to the real-time AI.
        """
        mob = self.mob
        if not mob.is_alive:
            return TIME_TO_WAIT

        floor = game._get_or_create_floor(self.floor_id)
        if floor is None or mob.id not in floor.mobs:
            return TIME_TO_WAIT

        # Neutralise the real-time movement gate; in a turn room the scheduler,
        # not the wall clock, decides how often a mob is allowed to step.
        game._clear_mob_ai_pacing(mob)

        pre_pos = (mob.pos.x, mob.pos.y)
        pre_attack_time = getattr(mob, "last_attack_time", 0.0)

        self.begin_turn(game, floor)
        game._tick_mob(mob, floor, self.floor_id)

        if not mob.is_alive:
            return TIME_TO_WAIT

        acted = getattr(mob, "last_attack_time", 0.0) != pre_attack_time

        if (mob.pos.x, mob.pos.y) != pre_pos:
            return self.move_cost()
        if acted or game._mob_can_strike(mob, floor, self.floor_id):
            return self.attack_cost()
        return self.idle_cost()

    # --- hooks --------------------------------------------------------------

    def begin_turn(self, game, floor) -> None:
        """Runs before the mob's AI, to set up what it is allowed to do."""


class WallClockGatedMobActor(TurnMobActor):
    """A mob whose signature ability is gated on the real-time wall clock.

    `ai_goo.py`, `ai_shaman.py` and friends compare `time.time()` against
    `mob.last_attack_time` with a hard-coded interval. In a turn room that
    interval is measured in real seconds while rounds advance in turns, so the
    gate stays shut for the whole fight: a Shaman zaps once and then never
    again, and Goo's charge never comes round. The actor keeps the interval in
    SPD turns instead and, on a turn the ability is due, backdates the timestamp
    by the AI's own interval so the untouched AI reads it as elapsed.

    The cadence is a plain turn counter rather than something inferred from
    the mob's state, because the real-time AI cannot be observed reliably from
    outside: `mob_ai_movement` also stamps `last_attack_time` to arm a mob's
    first-strike windup, so a timestamp delta does not mean the ability fired.
    A turn counter is the stat the mode actually needs.

    Deviation from SPD: SPD does not `spend` a delay when `canAttack` is false,
    so a caster that is out of range retries next turn. Here the delay is spent
    whenever the cadence comes round, so an out-of-range caster can miss a beat.
    """

    def __init__(self, mob, floor_id: int) -> None:
        super().__init__(mob, floor_id)
        # SPD turns until the ability is next permitted. Starts due, so a mob
        # that walks into range acts on the turn it gets there.
        self.turns_until_ability: float = 0.0

    def ability_cadence(self) -> float:
        """SPD turns between uses of the signature ability."""
        return 1.0

    def _gate_seconds(self) -> float:
        """The interval the real-time AI compares against, in real seconds."""
        return float(getattr(self.mob, "attack_cooldown", 0.0) or 0.0)

    def begin_turn(self, game, floor) -> None:
        if self.turns_until_ability > 0:
            self.turns_until_ability -= 1.0
        else:
            self.turns_until_ability = self.ability_cadence()
            gate = self._gate_seconds()
            if gate > 0:
                # Due this turn: satisfy the AI's wall-clock gate. Same idiom
                # the real-time ally path already uses in `mob_ai_dispatch.py`.
                self.mob.last_attack_time = time.time() - gate
        super().begin_turn(game, floor)


class TickCounterMobActor(TurnMobActor):
    """A mob whose ability cooldowns are denominated in real-time ticks.

    `ai_dm300.py` and friends express cooldowns as turns times
    `GAME_TURN_TICKS` and compare them against a counter the AI bumps once per
    call. In real time one call is one tick, so the units agree. A turn room
    calls the AI once per turn, so the same counter needs a whole turn's worth
    of ticks per call for the cooldown to stay the length it was written as.
    """

    # Entity fields that count *elapsed* time in real-time ticks. Only these
    # are advanced: a field holding a *threshold* (a cooldown length) is set
    # by the AI and must not be pushed further out on every turn.
    elapsed_tick_counters: tuple = ()

    def begin_turn(self, game, floor) -> None:
        for name in self.elapsed_tick_counters:
            value = getattr(self.mob, name, None)
            if isinstance(value, int) and not isinstance(value, bool):
                setattr(self.mob, name, value + GAME_TURN_TICKS)
        super().begin_turn(game, floor)


class GooActor(WallClockGatedMobActor):
    """Goo's pumped charge.

    SPD `Goo.doAttack()` spends `attackDelay()` on each of the three beats
    (pump, pump, release), so the charge is paced by the mob's own attack
    delay rather than by a flat interval.
    """

    def ability_cadence(self) -> float:
        return self.attack_cost()


class DM300Actor(WallClockGatedMobActor, TickCounterMobActor):
    """DM-300: wall-clock-gated melee, tick-denominated gas/rock cooldowns.

    `ai_dm300.py` compares `turns_since_last_ability` against a threshold of
    `5..9 * GAME_TURN_TICKS`. The counter is bumped once per `_update_dm300`
    call, which is once per tick in a real-time room and once per turn here, so
    without the tick conversion below the gas/rock ability would need two
    hundred turns to come round.
    """

    elapsed_tick_counters = ("turns_since_last_ability",)

    def ability_cadence(self) -> float:
        return self.attack_cost()


class TenguActor(TickCounterMobActor):
    """Tengu's bomb and shocker, both already tick-denominated.

    `ai_tengu.py` gates its abilities on `turn_tick` against `TURN_TICKS` and
    counts the bomb down one unit per call, so both need a turn's worth of
    ticks per call to keep the cadence the code was written against.
    """

    elapsed_tick_counters = ("turn_tick", "bomb_timer")


class DwarfKingActor(TickCounterMobActor):
    """Dwarf King's summon and life-link cooldowns, tick-denominated.

    `ai_dwarf_king.py` sets `summon_cooldown`/`ability_cooldown` to
    `8..14 * TICKS_PER_TURN` and decrements them once per call, so they are
    elapsed counters here too.
    """

    elapsed_tick_counters = ("summon_cooldown", "ability_cooldown")


class YogDzewaActor(TickCounterMobActor):
    """Yog-Dzewa's death-ray telegraph and fist cooldowns, tick-denominated.

    `ability_telegraph_timer` is deliberately left alone: SPD telegraphs the
    death ray for a turn or two, so scaling it by a turn's worth of ticks would
    collapse the telegraph into the same turn it was raised. It is one of the
    cooldowns that still needs a balance pass against real play.
    """

    elapsed_tick_counters = ("summon_cooldown",)


class RangedMobActor(WallClockGatedMobActor):
    """Zap-and-bolt casters: Shaman, Warlock, DM-100, Eye, Spinner, DM-200.

    SPD spends `TICK` on a zap (`Eye.act()`, Warlock.act()), so the cadence is
    one zap per `TIME_TO_ZAP` turns.
    """

    def ability_cadence(self) -> float:
        return TIME_TO_ZAP


# Bosses and casters resolve most-specific-first, mirroring the isinstance
# ladder in `app/engine/game/mob_ai_dispatch.py`.
_ACTOR_TYPES = (
    (GooActor, (Goo,)),
    (DM300Actor, (DM300,)),
    (TenguActor, (Tengu,)),
    (DwarfKingActor, (DwarfKing,)),
    (YogDzewaActor, (YogDzewa,)),
    (
        RangedMobActor,
        (
            RedShaman,
            BlueShaman,
            PurpleShaman,
            Warlock,
            DM100,
            Eye,
            Spinner,
            DM200,
            FireElemental,
        ),
    ),
)


def create_mob_actor(mob, floor_id: int) -> TurnMobActor:
    """Build the turn brain for `mob` -- the turn room's one construction site."""
    for actor_cls, mob_types in _ACTOR_TYPES:
        if isinstance(mob, mob_types):
            return actor_cls(mob, floor_id)
    return TurnMobActor(mob, floor_id)
