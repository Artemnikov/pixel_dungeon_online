"""Real-time game-tick steps, decomposed out of TickMixin.update_tick.

These are the per-tick world/actor upkeep functions for the *real-time* game
mode, where the server ticks at GAME_LOOP_HZ and each call advances the
simulation by GameInstance.sim_unit seconds.

The turn-based mode does not use these entry points: it drives the same
mechanics from app/engine/turn/world.py, once per completed SPD time unit.
"""

import random
from typing import List, Tuple

from app.engine.entities.base import chebyshev_distance
from app.engine.entities.buffs import get_buff, process_buffs
from app.engine.entities.items.consumables import Gold
from app.engine.entities.player import CharacterClass, Player
from app.engine.entities.talent_enum import Talent
from app.engine.game.blobs import tick_blob_areas
from app.engine.game.constants import TICKS_PER_TURN
from app.engine.systems.loot import roll_drops

_TURN_ACCUM_ATTR = '_turn_accum'


def run_buff_upkeep(game, entity, floor, floor_id: int, is_player: bool, dt: float) -> bool:
    removed = process_buffs(entity.buffs, dt)
    if game._process_removed_buffs(entity, removed, floor=floor, floor_id=floor_id, is_player=is_player):
        return False
    game._apply_bleed(entity)
    if not is_player:
        game._apply_sungrass_heal(entity, dt, floor_id=floor_id)
    return True


def run_blob_round_upkeep(game, active_ids) -> None:
    if not active_ids:
        return
    active_floors = {fid: game.floors[fid] for fid in active_ids}
    blob_events = tick_blob_areas(active_floors, game.players)
    for ev in blob_events:
        game.add_event(ev["type"], ev["data"],
                       floor_id=ev.get("_floor_id"),
                       source_player_id=ev.get("_source_player_id"))
    for ev in blob_events:
        if ev["type"] == "DEATH" and "target" in ev.get("data", {}):
            target_id = ev["data"]["target"]
            for fid in active_ids:
                f = game.floors[fid]
                mob = f.mobs.get(target_id)
                if mob is not None and not mob.is_alive:
                    game.handle_mob_death(mob, f, fid)
                    drops = roll_drops(mob, game.drop_counters,
                                       mob.pos.x, mob.pos.y,
                                       players=list(game._players_on_floor(fid)))
                    for item in drops:
                        f.items[item.id] = item
                    if any(isinstance(d, Gold) for d in drops):
                        game.add_event("GOLD_DROP",
                                       {"x": mob.pos.x, "y": mob.pos.y},
                                       floor_id=fid)
                    break


def run_hazard_round_upkeep(game, floor_id: int) -> None:
    game._tick_tengu_blobs(game.floors[floor_id], floor_id)
    game.tick_bombs(game.floors[floor_id], floor_id)


def finalize_dead_players(game) -> None:
    for player in game.players.values():
        if not player.is_alive and not player.death_processed:
            game._kill_player(player, game._get_or_create_floor(player.floor_id), player.floor_id)


def sync_all_effects(game) -> None:
    for player in game.players.values():
        game._sync_effects(player)


def run_dot_upkeep(game, floor_id: int, active_players: List[Player]) -> None:
    game._process_bleed_ooze(floor_id, active_players)
    game._process_burning(floor_id, active_players)
    game._process_poison_corrosion(floor_id, active_players)


def run_respawn_upkeep(game, floor_id: int, floor, active_players: List[Player]) -> None:
    game._process_respawns(floor_id, floor, active_players)
    game._process_item_respawns(floor_id, floor, active_players)
    game._process_boss_respawns(floor_id, floor, active_players)
    game._process_chest_respawns(floor_id, floor, active_players)


def run_world_round_upkeep(game) -> None:
    for floor in list(game.floors.values()):
        game._process_pending_unlocks(floor, floor.floor_id)
    game._evict_empty_floors()


def run_player_heal_upkeep(game, player: Player, dt: float) -> None:
    game._apply_heal_tick(player)
    game._apply_aqua_heal_tick(player)
    game._apply_rest_regen(player, dt)
    game._apply_passive_regen(player, dt)
    game._apply_sungrass_heal(player, dt)
    heal_buff = get_buff(player.buffs, "healing")
    if heal_buff and player.hp < player.get_total_max_hp():
        player.set_heal(float(heal_buff.level * 2), 0.1, 1.0)
    game._tick_passive_wand_recharge(player, dt)


def advance_turn_accumulator(player: Player, ticks: float = 1.0) -> bool:
    turn_accum = getattr(player, _TURN_ACCUM_ATTR, 0.0) + ticks
    is_turn = turn_accum >= TICKS_PER_TURN
    if is_turn:
        turn_accum -= TICKS_PER_TURN
    setattr(player, _TURN_ACCUM_ATTR, turn_accum)
    return is_turn


def run_armor_charge_upkeep(player: Player, is_turn: bool) -> None:
    if is_turn and player.armor_charge < 100:
        player.armor_charge = min(100, player.armor_charge + 2)


def run_class_tick_upkeep(game, player: Player, dt: float, moved: bool) -> None:
    game.tick_rogue(player, dt, moved=moved)
    game.tick_artifacts(player, dt)
    game.tick_duelist(player, dt)
    game.tick_cleric(player, dt)


def run_stationary_upkeep(player: Player, moved: bool, ticks: int = 1) -> None:
    if moved:
        player.stationary_ticks = 0
        if getattr(player, "patient_strike_tile", None) != (player.pos.x, player.pos.y):
            player.patient_strike_ready = False
    else:
        player.stationary_ticks += ticks
        if player.class_type == CharacterClass.DUELIST and player.talent_info.level(Talent.PATIENT_STRIKE) > 0:
            player.patient_strike_tile = (player.pos.x, player.pos.y)
            player.patient_strike_ready = True


def roll_hold_fast(player: Player) -> Tuple[float, bool]:
    hf_factor = player.get_hold_fast_decay_factor()
    return hf_factor, hf_factor >= 1.0 or random.random() < hf_factor


def run_shield_decay_upkeep(player: Player, hf_tick: bool) -> None:
    if hf_tick:
        player.decay_shields()


def run_chaotic_censer_upkeep(game, player: Player, is_turn: bool) -> None:
    from app.engine.entities.trinkets import ChaoticCenser as _CC
    from app.engine.entities.trinkets import trinket_level
    cc_lvl = trinket_level(player, "chaotic_censer")
    if not (is_turn and cc_lvl >= 0):
        return
    player._cc_turns = getattr(player, "_cc_turns", 0) + 1
    avg_interval = _CC.average_turns_until_gas(cc_lvl)
    if avg_interval <= 0 or player._cc_turns < avg_interval:
        return
    player._cc_turns = 0
    floor = game._get_or_create_floor(player.floor_id)
    nearby_mobs = [
        m for m in floor.mobs.values()
        if m.is_alive and m.faction != player.faction
        and chebyshev_distance(m.pos.x, m.pos.y, player.pos.x, player.pos.y) <= 4
    ]
    if not nearby_mobs:
        return
    target = random.choice(nearby_mobs)
    gas_type = random.choice(["toxic_gas", "fire", "paralytic_gas"])
    from app.engine.game.terrain_effects import _create_gas
    _create_gas(floor, (target.pos.x, target.pos.y), 4, gas_type)


def run_class_ability_upkeep(game, player: Player, dt: float, is_turn: bool, hf_factor: float) -> None:
    game._tick_player_by_class_type(player, dt, is_turn, hf_factor)
