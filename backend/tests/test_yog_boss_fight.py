# Copyright (C) 2026 ArtemNikov
#
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction, Position
from app.engine.entities.buffs import has_buff
from app.engine.entities.mobs import (
    BurningFist, DemonSpawner, Larva, RipperDemon, RottingFist, RustedFist,
    SoiledFist, BrightFist, DarkFist, YogDzewa, YogRipper,
)
from app.engine.entities.player import Player
from app.engine.game.ai_yog_dzewa import (
    _charge_yog_death_ray,
    _fire_yog_death_ray,
    _get_spawners_alive,
    _summon_yog_minion,
    _update_yog_dzewa,
    _yog_maybe_seal_arena,
    _yog_unseal_arena,
    build_fist_schedule,
    build_regular_summons,
)
from app.engine.game.constants import TICKS_PER_TURN
from app.engine.game.floor_state import FloorState
from app.engine.manager import GameInstance


def make_floor_25():
    game = GameInstance("test-yog-boss-fight")
    floor = game.generate_floor(25)
    player = game.add_player("p1", "Hero")
    player.floor_id = 25
    ent = floor.entrance_pos or (16, 26)
    player.pos = Position(x=ent[0], y=ent[1])
    return game, floor, player


def test_walking_from_entrance_seals_arena_and_starts_fight():
    game, floor, player = make_floor_25()
    yog = next(m for m in floor.mobs.values() if isinstance(m, YogDzewa))
    ent = floor.entrance_pos or (16, 26)

    assert not yog.fight_started
    assert not floor.generation_meta.get("yog_sealed", False)
    assert floor.grid[ent[1]][ent[0]] == TileType.STAIRS_UP

    # Player takes 2 steps north into the arena
    player.pos = Position(x=ent[0], y=ent[1] - 2)
    _yog_maybe_seal_arena(game, player, floor, 25)

    assert yog.fight_started
    assert yog.phase == 1
    assert floor.generation_meta.get("yog_sealed", True)
    assert floor.grid[ent[1]][ent[0]] == TileType.FLOOR_WOOD
    assert player.locked_floor_left == 0.0

    events = game.flush_events()
    assert any(e["type"] == "YOG_FIGHT_STARTED" for e in events)
    assert any(e["type"] == "BOSS_YELL" for e in events)


def test_spawner_count_affects_regular_summons():
    game = GameInstance("test-spawners")
    # No spawners on floors 21..24 -> all Larva
    summons_0 = build_regular_summons(spawners_alive=0, challenged=False)
    assert all(cls == Larva for cls in summons_0)
    assert len(summons_0) == 4

    # 2 spawners alive -> 2 Rippers, 2 Larvae
    summons_2 = build_regular_summons(spawners_alive=2, challenged=False)
    assert summons_2.count(YogRipper) == 2
    assert summons_2.count(Larva) == 2


def test_yog_phase_progression_and_invulnerability_gates():
    game, floor, player = make_floor_25()
    yog = next(m for m in floor.mobs.values() if isinstance(m, YogDzewa))
    player.pos = Position(x=16, y=20)
    _yog_maybe_seal_arena(game, player, floor, 25)

    assert yog.phase == 1
    assert yog.hp == 1000

    # Phase 1: Damage Yog down to 700 HP
    yog.take_damage(200)
    assert yog.hp == 800
    assert yog.phase == 1

    # Clamped at 700 HP
    yog.take_damage(200)
    assert yog.hp == 700

    # Tick Yog -> triggers Phase 2 and spawns Fist 1
    _update_yog_dzewa(game, yog, floor, 25)
    assert yog.phase == 2
    assert len(yog.fist_ids) == 1
    fist1 = floor.mobs[yog.fist_ids[0]]
    assert fist1.is_alive
    assert floor.view_distance == 3

    # Yog is invulnerable while fist 1 is alive
    raw_dmg = yog.defense_proc(50, player, floor.mobs, yog.pos.x, yog.pos.y)
    assert raw_dmg == 0

    # Fist 1 is near Yog -> Fist is invulnerable
    fist1.pos = Position(x=yog.pos.x + 1, y=yog.pos.y)
    fist_dmg = getattr(fist1, "defense_proc")(50, player, floor.mobs, fist1.pos.x, fist1.pos.y)
    assert fist_dmg == 0

    # Move Fist 1 far from Yog -> Fist takes damage
    fist1.pos = Position(x=yog.pos.x, y=yog.pos.y + 6)
    fist_dmg = getattr(fist1, "defense_proc")(50, player, floor.mobs, fist1.pos.x, fist1.pos.y)
    assert fist_dmg == 50

    # Kill Fist 1
    fist1.hp = 0
    fist1.is_alive = False

    # Yog becomes vulnerable again
    raw_dmg = yog.defense_proc(50, player, floor.mobs, yog.pos.x, yog.pos.y)
    assert raw_dmg == 50

    # Phase 2: Damage Yog down to 400 HP
    yog.take_damage(300)
    assert yog.hp == 400
    _update_yog_dzewa(game, yog, floor, 25)
    assert yog.phase == 3
    assert len(yog.fist_ids) == 2
    fist2 = floor.mobs[yog.fist_ids[1]]
    assert fist2.is_alive
    assert floor.view_distance == 2

    # Kill Fist 2
    fist2.hp = 0
    fist2.is_alive = False

    # Phase 3: Damage Yog down to 100 HP
    yog.take_damage(300)
    assert yog.hp == 100
    _update_yog_dzewa(game, yog, floor, 25)
    assert yog.phase == 4
    assert len(yog.fist_ids) == 3
    fist3 = floor.mobs[yog.fist_ids[2]]
    assert fist3.is_alive
    assert floor.view_distance == 1

    # Kill Fist 3 -> triggers Final Phase 5
    fist3.hp = 0
    fist3.is_alive = False
    _update_yog_dzewa(game, yog, floor, 25)
    assert yog.phase == 5

    # Phase 5: Yog can now be reduced to 0 HP
    yog.take_damage(100)
    assert yog.hp == 0
    assert not yog.is_alive


def test_death_ray_telegraph_and_fire():
    game, floor, player = make_floor_25()
    yog = next(m for m in floor.mobs.values() if isinstance(m, YogDzewa))
    player.pos = Position(x=16, y=20)
    yog.fight_started = True
    yog.phase = 1

    # Charge Death Ray
    _charge_yog_death_ray(game, yog, player, floor, 25)
    assert len(yog.targeted_cells) > 0
    assert (16, 20) in yog.targeted_cells
    assert yog.ability_telegraph_timer > 0

    events = game.flush_events()
    assert any(e["type"] == "TARGETED_CELLS" for e in events)

    # Fire Death Ray
    initial_hp = player.hp
    _fire_yog_death_ray(game, yog, floor, 25)
    assert player.hp < initial_hp
    assert yog.targeted_cells == []

    events = game.flush_events()
    assert any(e["type"] == "YOG_DEATH_RAY" for e in events)


def test_minion_summoning():
    game, floor, player = make_floor_25()
    yog = next(m for m in floor.mobs.values() if isinstance(m, YogDzewa))
    player.pos = Position(x=16, y=20)
    yog.fight_started = True
    yog.phase = 1

    initial_mobs_count = len(floor.mobs)
    _summon_yog_minion(game, yog, player, floor, 25, alive_fists=[])
    assert len(floor.mobs) == initial_mobs_count + 1

    larva = next(m for m in floor.mobs.values() if isinstance(m, Larva))
    assert larva.is_alive
    assert abs(larva.pos.x - yog.pos.x) <= 1
    assert abs(larva.pos.y - yog.pos.y) <= 1


def test_yog_defeat_and_arena_unseal():
    game, floor, player = make_floor_25()
    yog = next(m for m in floor.mobs.values() if isinstance(m, YogDzewa))
    ent = floor.entrance_pos or (16, 26)

    # Spawn a minion
    _summon_yog_minion(game, yog, player, floor, 25, alive_fists=[])
    larva = next(m for m in floor.mobs.values() if isinstance(m, Larva))

    # Unseal arena upon death
    _yog_unseal_arena(game, floor, 25)

    # Minions killed
    assert not larva.is_alive

    # Entrance and exit restored
    assert floor.grid[ent[1]][ent[0]] == TileType.STAIRS_UP
    assert floor.grid[9][16] == TileType.STAIRS_DOWN
    assert floor.view_distance is None

    # Custom tilemaps updated
    vis = next(l for l in floor.custom_tiles if l["texture"] == "halls_special")
    assert vis["tiles"][0][4] == 19
    walls = next(l for l in floor.custom_walls if l["texture"] == "halls_special")
    assert walls["tiles"][0][4] == 0
