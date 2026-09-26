"""World upkeep for turn-based rooms, one SPD time unit at a time.

`TickMixin.update_tick` runs the real-time loop's upkeep every 25ms and lets
each system's own accumulator decide what a "turn" means. A turn room instead
calls `run_turn_upkeep` once per whole SPD time unit the scheduler has advanced
through, with `game.sim_unit == 1.0` and `game.sim_ticks == TICKS_PER_TURN`, so
the tick-counted systems (respawns, blob lifetimes, fuses) advance by exactly
one game turn -- the same amount the real-time loop would have needed a full
second to deliver.

Two things are deliberately absent compared with the real-time tick:

* `_tick_player` is not called. In turn mode a player only ever moves as the
  result of one of their own actions (see `turn/actions.py`), never from held
  keyboard input. The per-turn player mechanics that `_tick_player` shares with
  movement -- heal ticks, armor charge, class upkeep, shield decay, the
  per-class tickers -- are run here instead, with `is_turn` unconditionally
  true because one unit is one game turn.
* `_tick_mob` is not called. Mob AI is driven by the scheduler, once per mob
  turn, in `TurnBasedGameInstance._mob_take_turn`.
"""

import math

from app.engine.game.tick_steps import (
    finalize_dead_players,
    roll_hold_fast,
    run_armor_charge_upkeep,
    run_blob_round_upkeep,
    run_buff_upkeep,
    run_chaotic_censer_upkeep,
    run_class_tick_upkeep,
    run_dot_upkeep,
    run_hazard_round_upkeep,
    run_player_heal_upkeep,
    run_respawn_upkeep,
    run_shield_decay_upkeep,
    run_stationary_upkeep,
    run_world_round_upkeep,
    sync_all_effects,
)


def run_turn_upkeep(game) -> None:
    """Advance the world by one SPD time unit."""
    game._invalidate_fov_cache()

    dt = game.sim_unit
    active_ids = game.active_floor_ids

    for player in game.players.values():
        if not player.is_alive:
            continue
        floor = game._get_or_create_floor(player.floor_id)
        run_buff_upkeep(game, player, floor, player.floor_id, True, dt)
        game._tick_dust_ghost_spawner(player)
        _tick_player_turn(game, player, dt)

    for floor_id in active_ids:
        floor = game.floors[floor_id]
        for mob in floor.mobs.values():
            if mob.is_alive:
                run_buff_upkeep(game, mob, floor, floor_id, False, dt)

    run_blob_round_upkeep(game, active_ids)

    for floor_id in active_ids:
        run_hazard_round_upkeep(game, floor_id)

    finalize_dead_players(game)
    sync_all_effects(game)

    for floor_id in active_ids:
        floor = game.floors[floor_id]
        active_players = [
            p for p in game._players_on_floor(floor_id) if p.is_alive and not p.is_downed
        ]
        if not active_players:
            continue
        run_dot_upkeep(game, floor_id, active_players)
        run_respawn_upkeep(game, floor_id, floor, active_players)
        game._update_prison_boss(floor, floor_id)

    run_world_round_upkeep(game)


def _tick_player_turn(game, player, dt: float) -> None:
    """The per-game-turn half of `PlayerTickMixin._tick_player`.

    Mirrors the real-time ordering (heal ticks, armor charge, class upkeep,
    shield decay, then the class tickers) minus movement, so a hero standing
    still in a turn room keeps regenerating, recharging and counting down
    exactly as they would in real time.
    """
    if player.is_downed:
        return

    run_player_heal_upkeep(game, player, dt)

    # One upkeep unit is one game turn, so the real-time accumulator has
    # nothing to do here: the gate is simply always open.
    is_turn = True
    run_armor_charge_upkeep(player, is_turn)

    # Movement is action-driven, so "moved" is decided by whether the player's
    # own turn just stepped them. Stationary_upkeep owns the Hold Fast
    # no-enemy counters, which read the same signal here.
    moved = player._moved_this_turn
    run_class_tick_upkeep(game, player, dt, moved)
    run_stationary_upkeep(player, moved, ticks=game.sim_ticks)

    hf_factor, hf_tick = roll_hold_fast(player)

    run_shield_decay_upkeep(player, hf_tick)
    run_chaotic_censer_upkeep(game, player, is_turn)

    game._tick_player_by_class_type(player, dt, is_turn, hf_factor)


def pending_upkeep_units(game) -> int:
    """Whole SPD time units the scheduler has advanced past the last upkeep.

    Fractional time is deliberately not floored away mid-turn: mobs acting at
    0.77 per step means the scheduler passes a whole unit mid-cascade, and the
    world must tick at that boundary rather than when the cascade finishes.
    """
    return int(math.floor(game.scheduler.now + 1e-9)) - game._upkeep_units
