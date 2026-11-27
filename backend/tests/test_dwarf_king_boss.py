# Copyright (C) 2026 ArtemNikov
#
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.items.consumables import KingsCrown
from app.engine.entities.mobs import DKGhoul, DKGolem, DKMonk, DKWarlock, DwarfKing
from app.engine.game.ai_dwarf_king import (
    BOTTOM_DOOR_POS,
    PEDESTAL_POSITIONS,
    THRONE_POS,
    TOP_DOOR_POS,
    _dwarf_king_maybe_seal_arena,
    _dwarf_king_seal_arena,
    _dwarf_king_unseal_arena,
    _update_dwarf_king,
    handle_dwarf_king_minion_death,
)
from app.engine.game.constants import TICKS_PER_TURN
from app.engine.manager import GameInstance


def make_boss_game(challenges=None):
    game = GameInstance("test-dwarf-king")
    if challenges:
        game.challenges = set(challenges)
    floor = game._get_or_create_floor(20)
    player = game.add_player("p1", "Hero")
    player.floor_id = 20
    player.pos = Position(x=7, y=40)
    return game, floor, player


def test_walking_in_entrance_library_does_not_trigger_shout_or_sealing():
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))

    # Player starts at entrance (7, 44) and walks north up the hallway to (7, 38)
    for y in range(44, 37, -1):
        player.pos = Position(x=7, y=y)
        _update_dwarf_king(game, dk, floor, 20)
        _dwarf_king_maybe_seal_arena(game, player, floor, 20)

        assert not dk.fight_started
        assert not floor.generation_meta.get("dwarf_king_sealed", False)
        assert floor.grid[37][7] == TileType.DOOR
        events = game.flush_events()
        assert not any(e["type"] == "BOSS_YELL" for e in events)
        assert not any(e["type"] == "DWARF_KING_FIGHT_STARTED" for e in events)


def test_bumping_locked_door_sends_move_result_ok_false_with_seq():
    game, floor, player = make_boss_game()
    floor.grid[37][7] = TileType.LOCKED_DOOR
    floor.locked_doors[(7, 37)] = "some_key"
    player.pos = Position(x=7, y=38)

    # Move north into the locked door with sequence number 42
    game.move_entity("p1", 0, -1, seq=42)

    assert (player.pos.x, player.pos.y) == (7, 38)
    events = game.flush_events()
    move_results = [e for e in events if e["type"] == "MOVE_RESULT"]
    assert len(move_results) == 1
    assert move_results[0]["data"]["seq"] == 42
    assert move_results[0]["data"]["ok"] is False


def test_dwarf_king_arena_sealing_only_past_door():
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))

    assert not floor.generation_meta.get("dwarf_king_sealed", False)
    assert not dk.fight_started
    assert floor.grid[37][7] == TileType.DOOR

    # 1. Stepping ON the door tile (7, 37) does NOT seal the arena
    player.pos = Position(x=7, y=37)
    _dwarf_king_maybe_seal_arena(game, player, floor, 20)

    assert not floor.generation_meta.get("dwarf_king_sealed", False)
    assert not dk.fight_started
    assert floor.grid[37][7] == TileType.DOOR

    # 2. Stepping PAST the door into the arena at (7, 36) seals the room
    player.pos = Position(x=7, y=36)
    _dwarf_king_maybe_seal_arena(game, player, floor, 20)

    assert floor.generation_meta.get("dwarf_king_sealed") is True
    assert floor.grid[37][7] == TileType.LOCKED_DOOR
    assert floor.locked_doors.get((7, 37)) == "dwarf_king_arena"
    assert dk.fight_started is True
    assert player.locked_floor_left == 50.0
    assert (player.pos.x, player.pos.y) == (7, 36)

    events = game.flush_events()
    assert any(e["type"] == "DWARF_KING_FIGHT_STARTED" for e in events)
    assert any(e["type"] == "BOSS_YELL" and "interfering" in e["data"]["text"] for e in events)
    assert any(e["type"] == "MAP_PATCH" and e["data"]["tiles"][0]["tile"] == TileType.LOCKED_DOOR for e in events)

    # 3. Player remains fully mobile inside the arena
    game.move_entity("p1", 0, -1)  # (7, 36) -> (7, 35)
    assert (player.pos.x, player.pos.y) == (7, 35)

    game.move_entity("p1", 1, 0)   # (7, 35) -> (8, 35)
    assert (player.pos.x, player.pos.y) == (8, 35)


def _king(floor):
    return next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))


def act(game, dk, floor):
    """Advance exactly one DwarfKing.act() (one game turn)."""
    dk.act_ticks = TICKS_PER_TURN - 1
    return _update_dwarf_king(game, dk, floor, 20)


def run_ticks(game, dk, floor, n):
    for _ in range(n):
        _update_dwarf_king(game, dk, floor, 20)


def summon(cls, pos, delay=1):
    return {"pos": pos, "cls": cls.__name__, "delay": delay, "particle": "bones"}


def fight(challenges=None):
    game, floor, player = make_boss_game(challenges)
    dk = _king(floor)
    dk.fight_started = True
    return game, floor, player, dk


def phase2(game, dk, barrier=300):
    dk.phase = 2
    dk.hp = 50
    dk.properties.append("IMMOVABLE")
    from app.engine.game.ai_dwarf_king import _set_barrier
    _set_barrier(dk, barrier)


def test_act_runs_once_per_turn():
    game, floor, player, dk = fight()
    dk.summon_cooldown = 5
    dk.ability_cooldown = 5
    run_ticks(game, dk, floor, TICKS_PER_TURN - 1)
    assert dk.summon_cooldown == 5
    run_ticks(game, dk, floor, 1)
    assert dk.summon_cooldown == 4


def test_phase1_summon_cooldown_and_damage_acceleration(monkeypatch):
    import app.engine.game.ai_dwarf_king as ai
    monkeypatch.setattr(ai, "normal_int_range", lambda lo, hi: lo)
    game, floor, player, dk = fight()

    act(game, dk, floor)
    assert len(dk.pending_summons) == 1
    assert tuple(dk.pending_summons[0]["pos"]) in PEDESTAL_POSITIONS
    assert dk.summon_cooldown == 10
    assert dk.summons_made == 1

    dk.take_damage(40)
    assert dk.summon_cooldown == 5
    dk.take_damage(80)
    assert dk.summon_cooldown == -5

    act(game, dk, floor)
    assert dk.summon_cooldown == 5


def test_lifelink_splits_damage_across_every_link():
    from app.engine.game.ai_dwarf_king import _cast_life_link
    game, floor, player, dk = fight()
    a = game._spawn_mob_at(DKGhoul, 4, 28, 20)
    b = game._spawn_mob_at(DKGhoul, 10, 28, 20)
    floor.mobs[a.id] = a
    floor.mobs[b.id] = b

    assert _cast_life_link(game, dk, floor, 20) is True
    assert _cast_life_link(game, dk, floor, 20) is True
    assert _cast_life_link(game, dk, floor, 20) is False
    assert dk.has_buff("life_link") and a.has_buff("life_link") and b.has_buff("life_link")
    events = game.flush_events()
    assert sum(e["type"] == "HEALTH_RAY" for e in events) == 2

    hp_dk, hp_a, hp_b = dk.hp, a.hp, b.hp
    dk.take_damage(20)
    assert dk.hp == hp_dk - 7
    assert a.hp == hp_a - 7
    assert b.hp == hp_b - 7

    hp_dk, hp_a = dk.hp, a.hp
    a.take_damage(20)
    assert a.hp == hp_a - 10
    assert dk.hp == hp_dk - 10

    a.is_alive = False
    handle_dwarf_king_minion_death(game, a, floor, 20)
    b.is_alive = False
    handle_dwarf_king_minion_death(game, b, floor, 20)
    assert not dk.has_buff("life_link")


def test_phase1_hp_clamping_prevents_premature_death():
    game, floor, player, dk = fight()
    dk.take_damage(500)
    assert dk.hp == 50
    assert dk.is_alive is True


def test_phase1_pedestal_summon_resolution():
    game, floor, player, dk = fight()
    dk.summon_cooldown = 100
    dk.ability_cooldown = 100
    dk.pending_summons = [summon(DKGhoul, (4, 28))]

    act(game, dk, floor)

    assert dk.pending_summons == []
    minions = [m for m in floor.mobs.values() if isinstance(m, DKGhoul)]
    assert len(minions) == 1
    assert (minions[0].pos.x, minions[0].pos.y) == (4, 28)
    assert minions[0].ai_state == "hunting"
    assert not minions[0].king_damager


def test_summon_delay_counts_turns_including_the_summoning_turn():
    game, floor, player, dk = fight()
    dk.ability_cooldown = 100
    act(game, dk, floor)
    assert dk.pending_summons[0]["delay"] == 2
    act(game, dk, floor)
    assert dk.pending_summons[0]["delay"] == 1
    act(game, dk, floor)
    assert dk.pending_summons == []
    assert any(isinstance(m, DKGhoul) for m in floor.mobs.values())


def test_phase1_pedestal_summon_relocates_when_pedestal_occupied():
    game, floor, player, dk = fight()
    dk.summon_cooldown = 100
    dk.ability_cooldown = 100
    player.pos = Position(x=4, y=28)
    initial_hp = player.hp
    dk.pending_summons = [summon(DKGhoul, (4, 28))]

    act(game, dk, floor)

    assert player.hp == initial_hp
    minions = [m for m in floor.mobs.values() if isinstance(m, DKGhoul)]
    assert len(minions) == 1
    assert (minions[0].pos.x, minions[0].pos.y) != (4, 28)
    assert abs(minions[0].pos.x - 4) <= 1 and abs(minions[0].pos.y - 28) <= 1


def _surround(game, floor, pos):
    for ndx in (-1, 0, 1):
        for ndy in (-1, 0, 1):
            if ndx or ndy:
                blocker = game._spawn_mob_at(DKGhoul, pos[0] + ndx, pos[1] + ndy, 20)
                floor.mobs[blocker.id] = blocker


def test_phase1_pedestal_summon_deals_damage_to_occupant():
    game, floor, player, dk = fight()
    dk.summon_cooldown = 100
    dk.ability_cooldown = 100
    player.pos = Position(x=4, y=28)
    initial_hp = player.hp
    _surround(game, floor, (4, 28))
    dk.pending_summons = [summon(DKGhoul, (4, 28))]

    act(game, dk, floor)

    assert 20 <= initial_hp - player.hp <= 40
    assert len([m for m in floor.mobs.values() if isinstance(m, DKGhoul)]) == 8


def test_paralysed_king_still_summons_but_uses_no_ability():
    game, floor, player, dk = fight()
    player.pos = Position(x=7, y=34)
    gh = game._spawn_mob_at(DKGhoul, 4, 28, 20)
    floor.mobs[gh.id] = gh
    dk.add_buff("paralysis", duration=10.0)

    assert act(game, dk, floor) is True
    assert len(dk.pending_summons) == 1
    assert dk.ability_cooldown == 0
    assert dk.last_ability == 0


def test_ability_spends_the_kings_turn(monkeypatch):
    import app.engine.game.ai_dwarf_king as ai
    monkeypatch.setattr(ai, "_cast_teleport_subject", lambda *a: True)
    monkeypatch.setattr(ai, "_cast_life_link", lambda *a: True)
    game, floor, player, dk = fight()
    dk.summon_cooldown = 100
    assert act(game, dk, floor) is True
    assert dk.ability_cooldown > 0
    assert _update_dwarf_king(game, dk, floor, 20) is True
    act(game, dk, floor)
    assert _update_dwarf_king(game, dk, floor, 20) is False


def test_failed_ability_keeps_cooldown_ready_and_retries_next_turn():
    game, floor, player, dk = fight()
    dk.summon_cooldown = 100
    act(game, dk, floor)
    assert dk.ability_cooldown == 0
    assert dk.last_ability in (1, 2)


def test_teleport_subject_falls_back_to_furthest_open_neighbour():
    from app.engine.game.ai_dwarf_king import _cast_teleport_subject
    game, floor, player, dk = fight()
    dk.pos = Position(x=7, y=32)
    player.pos = Position(x=7, y=35)
    gh = game._spawn_mob_at(DKGhoul, 4, 28, 20)
    floor.mobs[gh.id] = gh

    assert _cast_teleport_subject(game, dk, floor, 20) is True
    assert (dk.pos.x, dk.pos.y) == (6, 31)
    assert (gh.pos.x, gh.pos.y) == (6, 34)
    events = game.flush_events()
    assert any(e["type"] == "TELEPORT" and e["data"]["player"] == gh.id for e in events)
    assert any(e["type"] == "BOSS_YELL" and "slave" in e["data"]["text"] for e in events)


def test_teleport_subject_steps_along_hero_line_when_open():
    from app.engine.game.ai_dwarf_king import _cast_teleport_subject
    game, floor, player, dk = fight()
    dk.pos = Position(x=7, y=33)
    player.pos = Position(x=7, y=35)
    gh = game._spawn_mob_at(DKGhoul, 4, 28, 20)
    floor.mobs[gh.id] = gh

    _cast_teleport_subject(game, dk, floor, 20)
    assert (dk.pos.x, dk.pos.y) == (7, 32)
    assert (gh.pos.x, gh.pos.y) == (7, 34)


def test_transition_to_phase2_on_hp_threshold():
    game, floor, player, dk = fight()
    dk.pos = Position(x=7, y=34)
    gh = game._spawn_mob_at(DKGhoul, 4, 28, 20)
    floor.mobs[gh.id] = gh
    dk.pending_summons = [summon(DKGhoul, (10, 28), delay=3)]
    dk.hp = 50
    _update_dwarf_king(game, dk, floor, 20)

    assert dk.phase == 2
    assert (dk.pos.x, dk.pos.y) == THRONE_POS
    assert "IMMOVABLE" in dk.properties
    assert dk.barrier_hp == 300
    assert dk.pending_summons == []
    assert not gh.is_alive

    assert dk.take_damage(50) == 0
    assert dk.hp == 50

    events = game.flush_events()
    phase = next(e for e in events if e["type"] == "DWARF_KING_PHASE2")
    assert (phase["data"]["x"], phase["data"]["y"]) == THRONE_POS
    assert any(e["type"] == "TELEPORT" and e["data"]["player"] == dk.id for e in events)

    act(game, dk, floor)
    events = game.flush_events()
    assert any(e["type"] == "BOSS_YELL" and "Arise" in e["data"]["text"] for e in events)


def _clear_spawned(floor, dk):
    dk.king_damager_ids.clear()
    for m in list(floor.mobs.values()):
        if isinstance(m, (DKGhoul, DKMonk, DKWarlock, DKGolem)):
            del floor.mobs[m.id]


def test_phase2_wave_pacing_matches_spd():
    game, floor, player, dk = fight()
    phase2(game, dk)
    player.pos = Position(x=7, y=36)

    created = []
    for turn in range(40):
        act(game, dk, floor)
        created.append(dk.summons_made)
        _clear_spawned(floor, dk)
        if turn == 15:
            phase2(game, dk, barrier=200)
        if turn == 25:
            phase2(game, dk, barrier=100)

    assert created[0] == 1 and created[2] == 1 and created[3] == 2
    assert created[9] == 4 and created[15] == 4
    assert created[16:20] == [5, 6, 7, 8]
    assert created[25] == 8
    assert created[26] == 12


def test_phase2_wave2_last_summon_is_monk_or_warlock():
    game, floor, player, dk = fight()
    phase2(game, dk, barrier=200)
    dk.summons_made = 7
    act(game, dk, floor)
    assert dk.pending_summons[0]["cls"] in ("DKMonk", "DKWarlock")


def test_phase2_summons_carry_king_damager():
    game, floor, player, dk = fight()
    phase2(game, dk)
    dk.pending_summons = [summon(DKGhoul, (4, 28))]
    dk.wave_wait = 5
    act(game, dk, floor)
    gh = next(m for m in floor.mobs.values() if isinstance(m, DKGhoul))
    assert gh.king_damager is True


def king_damager(game, floor, dk, x=4, y=28):
    minion = game._spawn_mob_at(DKGhoul, x, y, 20)
    minion.king_damager = True
    floor.mobs[minion.id] = minion
    dk.king_damager_ids.append(minion.id)
    return minion


def test_king_damager_death_breaks_barrier():
    game, floor, player, dk = fight()
    phase2(game, dk)
    minion = king_damager(game, floor, dk)

    minion.is_alive = False
    handle_dwarf_king_minion_death(game, minion, floor, 20)

    assert dk.barrier_hp == 275
    assert dk.shields[0].amount == 275
    assert minion.king_damager is False


def test_king_damager_overflow_hits_hp_and_starts_phase3():
    game, floor, player, dk = fight()
    phase2(game, dk, barrier=10)
    minion = king_damager(game, floor, dk)

    minion.is_alive = False
    handle_dwarf_king_minion_death(game, minion, floor, 20)

    assert dk.barrier_hp == 0
    assert dk.hp == 35
    assert dk.phase == 3
    assert "IMMOVABLE" not in dk.properties
    events = game.flush_events()
    assert any(e["type"] == "DWARF_KING_PHASE3" for e in events)
    assert any(e["type"] == "BOSS_YELL" and "IMMORTAL" in e["data"]["text"] for e in events)


def test_corrupted_king_damager_detaches_and_hurts_barrier():
    game, floor, player, dk = fight()
    phase2(game, dk)
    dk.wave_wait = 5
    minion = king_damager(game, floor, dk)
    minion.faction = "player"

    act(game, dk, floor)
    assert dk.barrier_hp == 275
    assert minion.king_damager is False
    act(game, dk, floor)
    assert dk.barrier_hp == 275


def test_dk_barrier_regenerates_only_below_20():
    game, floor, player, dk = fight()
    phase2(game, dk, barrier=5)
    dk.wave_wait = 50
    act(game, dk, floor)
    assert dk.barrier_hp == 6
    phase2(game, dk, barrier=19)
    act(game, dk, floor)
    assert dk.barrier_hp == 19
    phase2(game, dk, barrier=150)
    act(game, dk, floor)
    assert dk.barrier_hp == 150


def test_king_damager_counts_kills_that_skip_death_hooks():
    game, floor, player, dk = fight()
    phase2(game, dk)
    killed = king_damager(game, floor, dk)
    removed = king_damager(game, floor, dk, 10, 28)

    killed.is_alive = False
    del floor.mobs[removed.id]
    _update_dwarf_king(game, dk, floor, 20)

    assert dk.barrier_hp == 250
    assert dk.king_damager_ids == []
    _update_dwarf_king(game, dk, floor, 20)
    assert dk.barrier_hp == 250


def test_phase2_spawned_summons_are_tracked():
    game, floor, player, dk = fight()
    phase2(game, dk)
    dk.pending_summons = [summon(DKGhoul, (4, 28))]
    dk.wave_wait = 5
    act(game, dk, floor)
    gh = next(m for m in floor.mobs.values() if isinstance(m, DKGhoul))
    assert dk.king_damager_ids == [gh.id]


def test_shielded_king_clock_runs_faster_only_while_no_minion_is_alive():
    from app.engine.game.constants import DK_IDLE_CLOCK_MULTIPLIER
    game, floor, player, dk = fight()
    phase2(game, dk)
    dk.wave_wait = 50
    run_ticks(game, dk, floor, TICKS_PER_TURN // DK_IDLE_CLOCK_MULTIPLIER)
    assert dk.wave_wait == 49

    king_damager(game, floor, dk)
    run_ticks(game, dk, floor, TICKS_PER_TURN // DK_IDLE_CLOCK_MULTIPLIER)
    assert dk.wave_wait == 49
    run_ticks(game, dk, floor, TICKS_PER_TURN)
    assert dk.wave_wait == 48


def test_unshielded_king_clock_is_not_accelerated():
    game, floor, player, dk = fight()
    dk.summon_cooldown = 5
    dk.ability_cooldown = 5
    run_ticks(game, dk, floor, TICKS_PER_TURN - 1)
    assert dk.summon_cooldown == 5


def test_phase2_pedestal_crush_damages_barrier():
    game, floor, player, dk = fight()
    phase2(game, dk)
    dk.summons_made = 4
    player.pos = Position(x=4, y=28)
    _surround(game, floor, (4, 28))
    dk.pending_summons = [summon(DKGhoul, (4, 28))]

    act(game, dk, floor)

    assert dk.barrier_hp == 275
    assert dk.shields[0].amount == 275


def test_phase3_viscosity_deferred_damage():
    game, floor, player, dk = fight()
    dk.phase = 3
    dk.hp = 50
    player.locked_floor_left = 10.0

    assert dk.take_damage(40) == 0
    assert dk.deferred_damage == 40
    assert dk.hp == 50

    _update_dwarf_king(game, dk, floor, 20)
    events = game.flush_events()
    assert any(e["type"] == "DWARF_KING_DEFERRED" and e["data"]["amount"] == 40 for e in events)

    run_ticks(game, dk, floor, TICKS_PER_TURN - 2)
    assert dk.hp == 50
    run_ticks(game, dk, floor, 1)
    assert dk.hp == 46
    assert dk.deferred_damage == 36
    assert player.locked_floor_left > 10.0


def test_phase3_losing_yell_and_bleed_death_awards_xp():
    game, floor, player, dk = fight()
    dk.phase = 3
    dk.hp = 22
    dk.take_damage(30)
    dk.phase3_ticks = TICKS_PER_TURN - 1
    _update_dwarf_king(game, dk, floor, 20)
    assert dk.hp == 19
    assert any(e["type"] == "BOSS_YELL" and "lies below" in e["data"]["text"] for e in game.flush_events())

    exp_before = player.experience
    level_before = player.level
    dk.hp = 1
    dk.phase3_ticks = TICKS_PER_TURN - 1
    _update_dwarf_king(game, dk, floor, 20)
    assert not dk.is_alive
    assert player.experience != exp_before or player.level != level_before
    crowns = [i for i in floor.items.values() if isinstance(i, KingsCrown)]
    assert len(crowns) == 1


def test_phase3_leftover_king_damager_adds_deferred_damage():
    game, floor, player, dk = fight()
    dk.phase = 3
    minion = king_damager(game, floor, dk)
    minion.is_alive = False
    handle_dwarf_king_minion_death(game, minion, floor, 20)
    assert dk.deferred_damage == 25


def test_phase3_summons_every_turn_up_to_four_inbound():
    game, floor, player, dk = fight()
    dk.phase = 3
    dk.summons_made = 1
    player.pos = Position(x=7, y=36)
    act(game, dk, floor)
    assert len(dk.pending_summons) == 1
    act(game, dk, floor)
    assert len(dk.pending_summons) == 2
    assert dk.summons_made == 3
def test_dwarf_king_weapons_free_challenge_qualification():
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))
    dk.fight_started = True

    # Arena sealed -> initially qualified
    game.qualified_for_boss_challenge = True

    # 1. Unarmed attack does not disqualify
    from app.engine.systems.combat import resolve_melee_attack
    player.belongings.weapon = None
    resolve_melee_attack(
        player, dk, floor.mobs, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: True, floor=floor, game=game,
    )
    assert game.qualified_for_boss_challenge is True

    # 2. Attack with a weapon disqualifies
    from app.engine.entities.items.equip import MeleeWeapon
    player.belongings.weapon = MeleeWeapon(name="Dagger")
    resolve_melee_attack(
        player, dk, floor.mobs, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: True, floor=floor, game=game,
    )
    assert game.qualified_for_boss_challenge is False


def test_dwarf_king_death_and_unsealing():
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))
    dk.fight_started = True
    dk.phase = 3
    dk.pos = Position(x=7, y=31)

    # Spawn minion on floor
    minion = game._spawn_mob_at(DKMonk, 5, 30)
    floor.mobs[minion.id] = minion

    # Player has degrade debuff
    player.add_buff("degrade", duration=10.0)
    assert player.has_buff("degrade")

    # King dies
    dk.is_alive = False
    game.handle_mob_death(dk, floor, 20)

    # King's Crown dropped at (7, 32)
    crown = next((i for i in floor.items.values() if isinstance(i, KingsCrown)), None)
    assert crown is not None
    assert crown.pos is not None
    assert (crown.pos.x, crown.pos.y) == (7, 32)

    # Arena doors unsealed
    assert floor.grid[37][7] == TileType.DOOR
    assert floor.grid[25][7] == TileType.DOOR
    assert (7, 37) not in floor.locked_doors
    assert (7, 25) not in floor.locked_doors

    # Minions killed
    assert not minion.is_alive

    # Player degrade cleansed
    assert not player.has_buff("degrade")

    # Boss score updated
    assert game.boss_scores[3] == 4000

    events = game.flush_events()
    assert any(e["type"] == "BOSS_SLAIN" and e["data"]["depth"] == 20 for e in events)
    assert any(e["type"] == "BOSS_YELL" and "Doomed" in e["data"]["text"] for e in events)


def test_stronger_bosses_challenge():
    game, floor, player = make_boss_game(challenges=["stronger_bosses"])
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))

    # Higher HP with challenge
    assert dk.max_hp == 450
    dk.hp = 450
    dk.fight_started = True

    # Triggers Phase 2 at <= 100 HP
    dk.hp = 100
    _update_dwarf_king(game, dk, floor, 20)

    assert dk.phase == 2
    assert dk.barrier_hp == 450


def test_dwarf_king_state_json_serializable_when_entering_boss_hall():
    """Entering the boss hall starts the fight and immediately queues a pedestal summon.
    The game state must remain strictly JSON-serializable so WebSocket broadcasts do not crash."""
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))

    # Step past door into arena
    player.pos = Position(x=7, y=36)
    _dwarf_king_maybe_seal_arena(game, player, floor, 20)
    assert dk.fight_started is True

    # Boss AI acts on its first turn and queues a pending summon
    act(game, dk, floor)
    assert len(dk.pending_summons) > 0

    # Serialization must succeed without TypeError (e.g. ModelMetaclass not JSON serializable)
    state = game.get_state("p1")
    serialized = json.dumps(state)
    assert isinstance(serialized, str)
    assert len(serialized) > 0

    dk_dump = dk.model_dump()
    assert dk_dump["pending_summons"][0]["particle"] in ("bones", "fire", "shadow", "spark")

    # Tick down pending summon until the minion spawns
    while dk.pending_summons:
        act(game, dk, floor)

    # State must still serialize cleanly after minion appears
    state_after_spawn = game.get_state("p1")
    serialized_after = json.dumps(state_after_spawn)
    assert isinstance(serialized_after, str)


def test_phase2_waves_state_json_serializable():
    """Phase 2 waves queue scripted pending summons, which must also be JSON-serializable."""
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))
    dk.fight_started = True
    dk.hp = 50
    # First tick transitions to phase 2
    _update_dwarf_king(game, dk, floor, 20)
    assert dk.phase == 2

    # Next turn runs the first phase 2 wave step and queues a summon
    act(game, dk, floor)
    assert len(dk.pending_summons) > 0

    state = game.get_state("p1")
    serialized = json.dumps(state)
    assert isinstance(serialized, str)


def test_dwarf_king_multiplayer_party_prompt_and_teleport():
    game = GameInstance("test-dk-party")
    floor = game._get_or_create_floor(20)
    p1 = game.add_player("p1", "Alice")
    p1.floor_id = 20
    p1.pos = Position(x=7, y=38)

    p2 = game.add_player("p2", "Bob")
    p2.floor_id = 20
    p2.pos = Position(x=7, y=42)

    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))
    assert not dk.fight_started
    assert not floor.generation_meta.get("dwarf_king_sealed", False)

    # 1. Alice steps into the door / arena: with 2 players on floor 20, party prompt initiates
    game.move_entity("p1", 0, -1)  # step towards (7, 37) / past door
    events = game.flush_events()

    assert not floor.generation_meta.get("dwarf_king_sealed", False)
    assert floor.dwarf_king_prompt is not None
    assert floor.dwarf_king_prompt["initiator_id"] == "p1"
    assert "p2" in floor.dwarf_king_prompt["pending"]
    assert any(e["type"] == "DWARF_KING_JOIN_PROMPT" and e.get("_player_id") == "p2" for e in events)
    assert any(e["type"] == "DWARF_KING_PARTY_STATUS" and e.get("_player_id") == "p1" for e in events)

    # 2. Bob approves
    game.respond_dwarf_king_join("p2", True)
    assert floor.generation_meta.get("dwarf_king_sealed") is True
    assert dk.fight_started is True
    assert floor.dwarf_king_prompt is None

    # Both players teleported inside arena (y <= 36) on distinct positions
    assert p1.pos.y in (36, 35) and 1 <= p1.pos.x <= 13
    assert p2.pos.y in (36, 35) and 1 <= p2.pos.x <= 13
    assert (p1.pos.x, p1.pos.y) != (p2.pos.x, p2.pos.y)


def test_dwarf_king_party_prompt_decline_and_start_without():
    game = GameInstance("test-dk-decline")
    floor = game._get_or_create_floor(20)
    p1 = game.add_player("p1", "Alice")
    p1.floor_id = 20
    p1.pos = Position(x=7, y=38)

    p2 = game.add_player("p2", "Bob")
    p2.floor_id = 20
    p2.pos = Position(x=7, y=42)

    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))

    # Alice steps towards arena
    game.move_entity("p1", 0, -1)
    game.flush_events()

    # Bob declines
    game.respond_dwarf_king_join("p2", False)
    assert not floor.generation_meta.get("dwarf_king_sealed", False)
    assert floor.dwarf_king_prompt is not None
    assert "p2" in floor.dwarf_king_prompt["declined"]

    # Alice decides to start without Bob
    game.decide_dwarf_king_start("p1", "start_without")
    assert floor.generation_meta.get("dwarf_king_sealed") is True
    assert dk.fight_started is True

    # Alice is inside the arena, Bob remains outside
    assert p1.pos.y in (36, 35) and 1 <= p1.pos.x <= 13
    assert p2.pos.y == 42


def test_dwarf_king_seal_gathers_allies():
    game = GameInstance("test-dk-allies")
    floor = game._get_or_create_floor(20)
    player = game.add_player("p1", "Hero")
    player.floor_id = 20
    player.pos = Position(x=7, y=38)

    # Spawn an ally in the entrance library (outside arena)
    ally = game._spawn_mob_at(DKGhoul, 7, 43)
    ally.faction = "player"
    floor.mobs[ally.id] = ally

    # Trigger fight seal
    _dwarf_king_seal_arena(game, floor, 20)

    # Ally was gathered inside the arena
    assert 25 <= ally.pos.y <= 36 and 1 <= ally.pos.x <= 13


def test_dwarf_king_throne_throws_items_and_unseal_clears_locked_floor():
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))
    player.pos = Position(x=7, y=36)
    _dwarf_king_maybe_seal_arena(game, player, floor, 20)
    assert player.locked_floor_left == 50.0

    # Place an item on the throne (7, 31) while DK is standing on (7, 31)
    from app.engine.entities.items.consumables import Gold
    gold = Gold(id="g-throne", name="Gold", quantity=10, pos=Position(x=7, y=31))
    floor.items[gold.id] = gold

    act(game, dk, floor)
    assert gold.pos is not None
    assert (gold.pos.x, gold.pos.y) != (7, 31)
    assert abs(gold.pos.x - 7) <= 1 and abs(gold.pos.y - 31) <= 1

    # Unsealing clears player.locked_floor_left
    _dwarf_king_unseal_arena(game, floor, 20)
    assert player.locked_floor_left is None


def test_dk_warlock_zap_reduces_boss_score():
    game, floor, player = make_boss_game()
    game.boss_scores[3] = 4000
    warlock = game._spawn_mob_at(DKWarlock, 7, 35, 20)
    floor.mobs[warlock.id] = warlock
    player.pos = Position(x=7, y=36)

    from app.engine.game.ai_warlock import _warlock_zap
    _warlock_zap(game, warlock, player, floor, 20)
    assert game.boss_scores[3] == 3600


def test_reentering_arena_after_victory_does_not_reseal():
    game, floor, player = make_boss_game()
    dk = _king(floor)
    player.pos = Position(x=7, y=36)
    _dwarf_king_maybe_seal_arena(game, player, floor, 20)
    dk.is_alive = False
    game.handle_mob_death(dk, floor, 20)
    assert floor.grid[37][7] == TileType.DOOR

    player.pos = Position(x=7, y=38)
    _dwarf_king_maybe_seal_arena(game, player, floor, 20)
    player.pos = Position(x=7, y=36)
    _dwarf_king_maybe_seal_arena(game, player, floor, 20)

    assert floor.grid[37][7] == TileType.DOOR
    assert (7, 37) not in floor.locked_doors


def test_king_drops_exactly_one_crown_through_the_kill_path():
    from app.engine.systems.loot import roll_drops
    game, floor, player, dk = fight()
    dk.phase = 3
    dk.is_alive = False
    game.handle_mob_death(dk, floor, 20)
    for drop in roll_drops(dk, game.drop_counters, dk.pos.x, dk.pos.y, players=[player]):
        floor.items[drop.id] = drop
    assert sum(isinstance(i, KingsCrown) for i in floor.items.values()) == 1


def test_dk_minions_give_no_xp_or_loot():
    from app.engine.systems.loot import roll_drops
    for cls in (DKGhoul, DKMonk, DKWarlock, DKGolem):
        m = cls(id="m", pos=Position(x=1, y=1))
        assert m.exp == 0
        assert all(not roll_drops(m, {}, 1, 1) for _ in range(50))


def test_turn_mode_actor_runs_one_act_per_turn():
    from app.engine.turn.mob_actors import DwarfKingActor
    game, floor, player, dk = fight()
    dk.ability_cooldown = 100
    actor = DwarfKingActor(dk, 20)

    actor.begin_turn(game, floor)
    _update_dwarf_king(game, dk, floor, 20)
    assert len(dk.pending_summons) == 1
    assert dk.pending_summons[0]["delay"] == 2

    for _ in range(2):
        actor.begin_turn(game, floor)
        _update_dwarf_king(game, dk, floor, 20)
    assert dk.pending_summons == []
    assert any(isinstance(m, DKGhoul) for m in floor.mobs.values())


def test_turn_mode_actor_bleeds_deferred_damage_each_turn():
    from app.engine.turn.mob_actors import DwarfKingActor
    game, floor, player, dk = fight()
    dk.phase = 3
    dk.hp = 50
    dk.take_damage(40)
    actor = DwarfKingActor(dk, 20)
    actor.begin_turn(game, floor)
    _update_dwarf_king(game, dk, floor, 20)
    assert dk.hp == 46
