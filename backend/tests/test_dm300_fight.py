# Copyright (C) 2026 ArtemNikov
#
import pytest

from app.engine.dungeon.constants import TileType
from app.engine.dungeon.terrain_flags import build_flag_maps
from app.engine.entities.base import Faction, Position
from app.engine.entities.mobs import DM300, Pylon, Rat
from app.engine.game.ai_dm300 import (
    _dm300_drop_rocks,
    _dm300_maybe_seal_arena,
    _dm300_unseal_arena,
    _dm300_vent_gas,
    _dm300_wall_smash,
    _tick_dm300_pending_rockfall,
    _update_dm300,
    DIGGABLE_AREA,
    GATE,
    MAIN_ARENA,
    PYLON_COORDS,
)
from app.engine.game.ai_pylon import _activate_pylon
from app.engine.game.constants import GAME_TURN_TICKS
from app.engine.game.floor_state import FloorState
from app.engine.manager import GameInstance


def make_floor(floor_id: int = 15, width: int = 33, height: int = 42) -> FloorState:
    grid = [[TileType.FLOOR for _ in range(width)] for _ in range(height)]
    # Place gate at y=13, x=14..18
    for gx in range(GATE.left, GATE.right):
        grid[GATE.top][gx] = TileType.WALL_DECO
    floor = FloorState(
        floor_id=floor_id,
        grid=grid,
        rooms=[],
        mobs={},
        items={},
        region="caves",
        entrance_pos=(16, 25),
        exit_pos=(16, 2),
    )
    floor.flags = build_flag_maps(floor.grid, region="caves")
    return floor


def make_game(floor: FloorState) -> GameInstance:
    game = GameInstance(game_id="test_dm300")
    game.floors[floor.floor_id] = floor
    return game


def test_dm300_stats_and_properties():
    dm = DM300(id="dm1", pos=Position(x=10, y=10))
    assert dm.hp == 300
    assert dm.max_hp == 300
    assert dm.attack_skill == 20
    assert dm.defense_skill == 15
    assert dm.damage_min == 15
    assert dm.damage_max == 25
    assert dm.dr_min == 0
    assert dm.dr_max == 10
    assert "BOSS" in dm.properties
    assert "LARGE" in dm.properties
    assert "INORGANIC" in dm.properties
    assert "sleep" in dm.immunities


def test_dm300_gas_vent_creates_toxic_gas_blob():
    floor = make_floor()
    game = make_game(floor)

    dm = DM300(id="dm1", pos=Position(x=10, y=10), faction=Faction.DUNGEON)
    floor.mobs[dm.id] = dm

    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=10, y=15)

    _dm300_vent_gas(game, dm, player, floor, floor.floor_id)

    # A toxic gas blob was registered
    gas_blobs = [b for b in floor.blob_areas.values() if b.get("type") == "toxic_gas"]
    assert len(gas_blobs) == 1
    blob = gas_blobs[0]
    # Collision cell (10, 15) has at least 100 gas
    assert blob["volume"].get((10, 15), 0) >= 100
    # Total volume is at least 250
    assert sum(blob["volume"].values()) >= 250

    events = game.flush_events()
    assert any(e["type"] == "DM300_GAS" for e in events)


def test_dm300_rockfall_knockback_telegraph_and_delayed_damage():
    floor = make_floor()
    game = make_game(floor)

    dm = DM300(id="dm1", pos=Position(x=10, y=10), faction=Faction.DUNGEON)
    floor.mobs[dm.id] = dm

    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=10, y=11)  # Adjacent to DM300
    player.hp = player.get_total_max_hp()

    rat = Rat(id="rat1", pos=Position(x=15, y=15), faction=Faction.DUNGEON)
    floor.mobs[rat.id] = rat

    pylon = Pylon(id="pylon1", pos=Position(x=4, y=13), faction=Faction.DUNGEON)
    floor.mobs[pylon.id] = pylon

    # Trigger boulder drops
    _dm300_drop_rocks(game, dm, player, floor, floor.floor_id)

    # Target player knocked back 2 tiles south (to 10, 13)
    assert player.pos.y > 11
    assert dm.pending_rockfall is not None
    assert len(dm.pending_rockfall["cells"]) > 0

    events = game.flush_events()
    assert any(e["type"] == "DM300_ROCKFALL_WARN" for e in events)

    # Force the player and rat and pylon onto a rock cell
    rock_cell = dm.pending_rockfall["cells"][0]
    player.pos = Position(x=rock_cell[0], y=rock_cell[1])
    rat.pos = Position(x=rock_cell[0], y=rock_cell[1])
    pylon.pos = Position(x=rock_cell[0], y=rock_cell[1])
    dm.pos = Position(x=rock_cell[0], y=rock_cell[1])
    pylon_hp_before = pylon.hp
    dm_hp_before = dm.hp
    rat_hp_before = rat.hp

    # Tick rockfall countdown to 0
    dm.pending_rockfall["ticks_left"] = 1
    _tick_dm300_pending_rockfall(game, dm, floor, floor.floor_id)

    # Player took damage and gained paralysis
    assert player.hp < player.get_total_max_hp()
    assert player.has_buff("paralysis")

    # Status effect registry maps paralysis to buff icon 4 on HUD
    from app.engine.game.status_effects_tick import DEFAULT_STATUS_EFFECT_REGISTRY
    effects = DEFAULT_STATUS_EFFECT_REGISTRY.collect(player)
    paralysis_fx = next(e for e in effects if e.key == "paralysis")
    assert paralysis_fx.icon == 4
    assert paralysis_fx.name == "Paralyzed"

    # Regular mob took damage and paralysis
    assert rat.hp < rat_hp_before
    assert rat.has_buff("paralysis")

    # Pylon and DM300 are immune to falling rocks
    assert pylon.hp == pylon_hp_before
    assert dm.hp == dm_hp_before

    events = game.flush_events()
    assert any(e["type"] == "DM300_ROCKFALL" for e in events)
    assert any(e["type"] == "MESSAGE" and e["data"]["text"] == "You are paralyzed!" for e in events)


def test_pylon_energy_damages_entities_and_skips_dm300():
    floor = make_floor()
    game = make_game(floor)

    # Set wire tile under player and rat and DM300
    floor.grid[15][10] = TileType.INACTIVE_TRAP
    floor.grid[15][11] = TileType.INACTIVE_TRAP
    floor.grid[15][12] = TileType.INACTIVE_TRAP

    pylon = Pylon(id="pylon1", pos=Position(x=4, y=13), faction=Faction.DUNGEON)
    floor.mobs[pylon.id] = pylon

    dm = DM300(id="dm1", pos=Position(x=12, y=15), faction=Faction.DUNGEON)
    floor.mobs[dm.id] = dm

    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=10, y=15)
    player.hp = player.get_total_max_hp()

    rat = Rat(id="rat1", pos=Position(x=11, y=15), faction=Faction.DUNGEON)
    floor.mobs[rat.id] = rat

    # Activate pylon -> seeds pylon_energy blob
    _activate_pylon(game, floor, floor.floor_id, near_pos=player.pos)

    assert "dm300_pylon_energy" in floor.blob_areas
    energy_blob = floor.blob_areas["dm300_pylon_energy"]
    assert (10, 15) in energy_blob["cells"]
    assert (11, 15) in energy_blob["cells"]
    assert (12, 15) in energy_blob["cells"]

    # Trigger blob upkeep tick
    from app.engine.game.blobs import tick_blob_areas
    energy_blob["tick_counter"] = GAME_TURN_TICKS - 1  # will trigger on next tick
    tick_blob_areas({floor.floor_id: floor}, game.players)

    # Player and rat took electricity damage
    assert player.hp < player.get_total_max_hp()
    assert rat.hp < rat.max_hp
    # DM300 is immune to pylon energy
    assert dm.hp == dm.max_hp


def test_dm300_trap_step_no_shield_when_energized():
    floor = make_floor()
    game = make_game(floor)

    floor.grid[15][10] = TileType.INACTIVE_TRAP
    dm = DM300(id="dm1", pos=Position(x=10, y=15), faction=Faction.DUNGEON)
    floor.mobs[dm.id] = dm

    # 1. Normal un-energized step: gains barrier
    from app.engine.game.ai_dm300 import _check_dm300_trap_step
    _check_dm300_trap_step(game, dm, floor, floor.floor_id)
    assert len(dm.shields) == 1
    assert dm.shields[0].name == "dm300_barrier"

    # 2. Energized step: no new barrier
    dm.shields = []
    floor.blob_areas["dm300_pylon_energy"] = {
        "type": "pylon_energy",
        "cells": {(10, 15)},
        "volume": {(10, 15): 1},
    }
    _check_dm300_trap_step(game, dm, floor, floor.floor_id)
    assert len(dm.shields) == 0


def test_arena_seal_on_pylon_approach_and_unseal_on_death():
    floor = make_floor()
    game = make_game(floor)

    dm = DM300(id="dm1", pos=Position(x=16, y=20), faction=Faction.DUNGEON)
    floor.mobs[dm.id] = dm
    pylons = [Pylon(id=f"p{i}", pos=Position(x=px, y=py)) for i, (px, py) in enumerate(PYLON_COORDS)]
    for p in pylons:
        floor.mobs[p.id] = p

    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=16, y=25)  # Entrance cell

    # Entrance is STAIRS_UP initially
    floor.grid[25][16] = TileType.STAIRS_UP
    floor.flags = build_flag_maps(floor.grid, region="caves")

    # Step near top-left pylon (4, 13)
    player.pos = Position(x=5, y=13)
    _dm300_maybe_seal_arena(game, player, floor, floor.floor_id)

    # Arena is sealed: entrance is now WALL
    assert floor.generation_meta.get("dm300_sealed") is True
    assert floor.grid[25][16] == TileType.WALL
    assert player.locked_floor_left == 50.0
    assert dm.fight_started is True
    assert dm.ai_state == "hunting"

    # Unseal when DM300 dies
    _dm300_unseal_arena(game, floor, floor.floor_id)

    # Entrance restored to STAIRS_UP, gate row (14..18, y=13) opened to FLOOR
    assert floor.generation_meta.get("dm300_sealed") is False
    assert floor.grid[25][16] == TileType.STAIRS_UP
    for gx in range(14, 19):
        assert floor.grid[13][gx] == TileType.FLOOR
    assert player.locked_floor_left is None


def test_supercharged_dm300_wall_smash():
    floor = make_floor()
    game = make_game(floor)

    # Place wall between DM300 and player inside diggable area
    floor.grid[20][15] = TileType.WALL
    floor.grid[20][16] = TileType.WALL
    floor.grid[20][17] = TileType.WALL
    floor.flags = build_flag_maps(floor.grid, region="caves")

    dm = DM300(id="dm1", pos=Position(x=16, y=21), faction=Faction.DUNGEON)
    dm.supercharged = True
    dm.ai_state = "hunting"
    floor.mobs[dm.id] = dm

    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=16, y=18)

    # Trigger wall smash
    smashed = _dm300_wall_smash(game, dm, player, floor, floor.floor_id)
    assert smashed is True
    # Walls in 3x3 became EMPTY_DECO
    assert floor.grid[20][16] == TileType.EMPTY_DECO
    assert dm.has_buff("stagger")


def test_dm300_ability_scheduler_and_aggressive_usage():
    floor = make_floor()
    game = make_game(floor)

    # Place chasm at y=22 to make target unreachable while keeping LOS open
    for x in range(33):
        floor.grid[22][x] = TileType.CHASM
    floor.flags = build_flag_maps(floor.grid, region="caves")

    dm = DM300(id="dm1", pos=Position(x=10, y=20), faction=Faction.DUNGEON)
    dm.ai_state = "hunting"
    dm.fight_started = True
    dm.turns_since_last_ability = 5 * GAME_TURN_TICKS
    floor.mobs[dm.id] = dm

    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=10, y=25)  # Across chasm with open LOS

    # Unreachable target with LOS triggers gas vent aggressively at 5 turns
    _update_dm300(game, dm, floor, floor.floor_id)
    assert dm.last_ability == "gas"
    assert dm.turns_since_last_ability == 0

    # Without LOS (wall instead of chasm), unreachable target drops rocks
    for x in range(33):
        floor.grid[22][x] = TileType.WALL
    floor.flags = build_flag_maps(floor.grid, region="caves")
    game._invalidate_fov_cache()
    dm.turns_since_last_ability = 5 * GAME_TURN_TICKS

    _update_dm300(game, dm, floor, floor.floor_id)
    assert dm.last_ability == "rocks"
    assert dm.turns_since_last_ability == 0


def test_supercharge_triggers_from_indirect_damage_in_dispatch():
    floor = make_floor()
    game = make_game(floor)

    dm = DM300(id="dm1", pos=Position(x=10, y=20), faction=Faction.DUNGEON)
    floor.mobs[dm.id] = dm
    pylons = [Pylon(id=f"p{i}", pos=Position(x=px, y=py)) for i, (px, py) in enumerate(PYLON_COORDS)]
    for p in pylons:
        floor.mobs[p.id] = p

    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id
    player.pos = Position(x=10, y=25)

    # Indirect damage (e.g. DoT / bomb) crosses 200 HP threshold
    dm.take_damage(120)
    assert dm.hp == 200
    assert dm.supercharged is True
    assert dm.pending_pylon_activation is True

    # Next mob dispatch tick consumes pending_pylon_activation and activates a pylon
    game._tick_mob(dm, floor, floor.floor_id)
    assert dm.pending_pylon_activation is False
    assert any(p.activated for p in pylons)
    assert dm.has_buff("stagger")


def test_pylon_elimination_clears_energy_on_first_and_retains_on_second():
    floor = make_floor()
    game = make_game(floor)

    dm = DM300(id="dm1", pos=Position(x=16, y=20), faction=Faction.DUNGEON)
    dm.supercharged = True
    dm.pylons_activated = 1
    floor.mobs[dm.id] = dm

    pylons = [Pylon(id=f"p{i}", pos=Position(x=px, y=py)) for i, (px, py) in enumerate(PYLON_COORDS)]
    for p in pylons:
        floor.mobs[p.id] = p

    pylons[0].activated = True
    floor.blob_areas["dm300_pylon_energy"] = {"type": "pylon_energy", "cells": {(10, 10)}}

    # Kill first pylon (3 remain > 2) -> energy cleared, DM300 de-supercharged
    pylons[0].is_alive = False
    game.handle_mob_death(pylons[0], floor, floor.floor_id)
    assert dm.supercharged is False
    assert "dm300_pylon_energy" not in floor.blob_areas

    # Second supercharge -> activate pylon 1
    dm.supercharged = True
    dm.pylons_activated = 2
    pylons[1].activated = True
    floor.blob_areas["dm300_pylon_energy"] = {"type": "pylon_energy", "cells": {(10, 10)}}

    # Kill second pylon (2 remain <= 2) -> DM300 de-supercharged, final phase, energy blob retained
    pylons[1].is_alive = False
    game.handle_mob_death(pylons[1], floor, floor.floor_id)
    assert dm.supercharged is False
    assert "dm300_pylon_energy" in floor.blob_areas

