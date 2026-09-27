# Copyright (C) 2026 ArtemNikov
#
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


def test_phase1_summon_cooldown_and_damage_acceleration():
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))
    dk.fight_started = True
    dk.summon_cooldown = 0

    _update_dwarf_king(game, dk, floor, 20)

    assert len(dk.pending_summons) == 1
    assert dk.pending_summons[0]["pos"] in PEDESTAL_POSITIONS
    assert dk.summon_cooldown > 0

    # Accelerate cooldown automatically via taking damage
    initial_cd = dk.summon_cooldown
    dk.take_damage(40)
    expected_reduction = (40 / 8.0) * TICKS_PER_TURN
    assert dk.summon_cooldown == initial_cd - expected_reduction


def test_two_way_lifelink_damage_sharing():
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))
    dk.fight_started = True

    minion: DKGhoul = game._spawn_mob_at(DKGhoul, 4, 28)  # type: ignore[assignment]
    floor.mobs[minion.id] = minion

    # Cast LifeLink between King and minion
    from app.engine.game.ai_dwarf_king import _cast_life_link
    success = _cast_life_link(game, dk, [minion], 20)
    assert success is True
    assert dk.linked_mob_id == minion.id
    assert minion.linked_mob_id == dk.id
    assert dk.has_buff("life_link")
    assert minion.has_buff("life_link")

    # 1. Damaging King splits 50% to minion
    minion_initial_hp = minion.hp
    dk_initial_hp = dk.hp
    dk.take_damage(20)
    assert dk.hp == dk_initial_hp - 10
    assert minion.hp == minion_initial_hp - 10

    # 2. Damaging minion splits 50% to King
    minion_prev_hp = minion.hp
    dk_prev_hp = dk.hp
    minion.take_damage(20)
    assert minion.hp == minion_prev_hp - 10
    assert dk.hp == dk_prev_hp - 10

    # 3. Minion death cleans up lifelink on King
    handle_dwarf_king_minion_death(game, minion, floor, 20)
    assert dk.linked_mob_id == ""
    assert not dk.has_buff("life_link")


def test_phase1_hp_clamping_prevents_premature_death():
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))
    dk.fight_started = True

    # Deal massive damage (500) in Phase 1
    dealt = dk.take_damage(500)
    assert dk.hp == 50
    assert dk.is_alive is True


def test_phase1_pedestal_summon_resolution():
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))
    dk.fight_started = True
    dk.summon_cooldown = 100
    dk.ability_cooldown = 100

    pedestal = (4, 28)
    dk.pending_summons = [{
        "pos": pedestal,
        "cls": DKGhoul,
        "ticks_left": 1,
        "particle": "bones",
    }]

    _update_dwarf_king(game, dk, floor, 20)

    assert len(dk.pending_summons) == 0
    minions = [m for m in floor.mobs.values() if isinstance(m, DKGhoul)]
    assert len(minions) == 1
    assert (minions[0].pos.x, minions[0].pos.y) == pedestal


def test_phase1_pedestal_summon_deals_damage_to_occupant():
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))
    dk.fight_started = True

    pedestal = (4, 28)
    player.pos = Position(x=4, y=28)
    initial_hp = player.hp

    dk.pending_summons = [{
        "pos": pedestal,
        "cls": DKGhoul,
        "ticks_left": 1,
        "particle": "bones",
    }]

    _update_dwarf_king(game, dk, floor, 20)

    assert player.hp < initial_hp


def test_transition_to_phase2_on_hp_threshold():
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))
    dk.fight_started = True

    # Drop HP below threshold (<= 50)
    dk.hp = 50
    _update_dwarf_king(game, dk, floor, 20)

    assert dk.phase == 2
    assert (dk.pos.x, dk.pos.y) == THRONE_POS
    assert "IMMOVABLE" in dk.properties
    assert dk.barrier_hp == 300

    # Direct damage dealt in Phase 2 returns 0 (King is invulnerable on throne)
    dealt = dk.take_damage(50)
    assert dealt == 0
    assert dk.hp == 50

    events = game.flush_events()
    assert any(e["type"] == "DWARF_KING_PHASE2" for e in events)
    assert any(e["type"] == "BOSS_YELL" and "slaves" in e["data"]["text"] for e in events)


def test_phase2_waves_and_king_damager_barrier_break():
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))
    dk.fight_started = True
    dk.phase = 2
    dk.hp = 50
    dk.barrier_hp = 300
    dk.barrier_max = 300
    from app.engine.entities.base import Shield
    dk.shields = [Shield(name="dwarf_king_barrier", amount=300, priority=10, decay=0)]

    _update_dwarf_king(game, dk, floor, 20)

    # Wave 1 queues 4 Ghouls
    assert len(dk.pending_summons) == 4

    # Simulate killing a Phase 2 KingDamager minion
    minion = game._spawn_mob_at(DKGhoul, 4, 28)
    minion.king_damager = True
    minion.linked_king_id = dk.id
    floor.mobs[minion.id] = minion

    handle_dwarf_king_minion_death(game, minion, floor, 20)

    # Barrier reduced by 25 (300 / 12)
    assert dk.barrier_hp == 275
    assert len(dk.shields) == 1
    assert dk.shields[0].amount == 275


def test_phase2_pedestal_crush_damages_barrier():
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))
    dk.fight_started = True
    dk.phase = 2
    dk.hp = 50
    dk.barrier_hp = 300
    dk.barrier_max = 300
    from app.engine.entities.base import Shield
    dk.shields = [Shield(name="dwarf_king_barrier", amount=300, priority=10, decay=0)]

    # Player stands on pedestal during summon resolution in Phase 2
    pedestal = (4, 28)
    player.pos = Position(x=4, y=28)
    dk.pending_summons = [{
        "pos": pedestal,
        "cls": DKGhoul,
        "ticks_left": 1,
        "particle": "bones",
    }]

    _update_dwarf_king(game, dk, floor, 20)

    # Player took blast damage AND King's barrier was damaged by 25
    assert dk.barrier_hp == 275
    assert dk.shields[0].amount == 275


def test_phase3_enraged_and_viscosity_deferred_damage():
    game, floor, player = make_boss_game()
    dk = next(m for m in floor.mobs.values() if isinstance(m, DwarfKing))
    dk.fight_started = True
    dk.phase = 2
    dk.hp = 50
    dk.barrier_hp = 25

    # Kill minion to break remaining barrier to 0
    minion = game._spawn_mob_at(DKGhoul, 4, 28)
    minion.king_damager = True
    minion.linked_king_id = dk.id
    floor.mobs[minion.id] = minion

    handle_dwarf_king_minion_death(game, minion, floor, 20)

    assert dk.barrier_hp == 0
    assert len(dk.shields) == 0
    assert dk.phase == 3
    assert "IMMOVABLE" not in dk.properties

    events = game.flush_events()
    assert any(e["type"] == "DWARF_KING_PHASE3" for e in events)
    assert any(e["type"] == "BOSS_YELL" and "IMMORTAL" in e["data"]["text"] for e in events)

    # In Phase 3: damage is deferred (Viscosity)
    dk.take_damage(40)
    assert dk.deferred_damage == 40
    assert dk.hp == 50  # No immediate lump loss

    # Tick deferred damage for 1 full turn (TICKS_PER_TURN)
    for _ in range(TICKS_PER_TURN):
        _update_dwarf_king(game, dk, floor, 20)

    assert dk.deferred_damage < 40
    assert dk.hp < 50


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
