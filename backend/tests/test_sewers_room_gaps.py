"""Regression tests for the previously-stubbed sewers-eligible standard rooms
(MinefieldRoom, PlantsRoom, AquariumRoom, FissureRoom, GrassyGraveRoom,
StudyRoom) and the runtime-only special rooms (SentryRoom, MagicWellRoom,
SacrificeRoom) that were map-layout-correct but functionally inert."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.dungeon.spd_levelgen.standard_rooms import (
    MinefieldRoom, PlantsRoom, AquariumRoom, FissureRoom, GrassyGraveRoom, StudyRoom,
)
from app.engine.dungeon.spd_levelgen.special_rooms import SentryRoom, MagicWellRoom, SacrificeRoom
from app.engine.dungeon.spd_levelgen.room_types import SizeCategory
from app.engine.dungeon.spd_levelgen.room import Door, Room
from app.engine.dungeon.spd_levelgen.level import GenLevel
from app.engine.dungeon.spd_levelgen.generator import init_generator_state
from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_random import SPDRandom
from app.engine.game.spd_adapter import gen_level_to_floor_state, _spawn_mob
from app.engine.entities.mobs import Sentry
from app.engine.manager import GameInstance
from app.engine.entities.base import Position, Faction
from app.engine.entities.player import Player
from app.engine.entities.mobs import Statue
from app.engine.dungeon.constants import TileType


def _make_level(seed=1, depth=3):
    rng = SPDRandom()
    rng.push_generator(seed)
    state = init_generator_state(rng)
    level = GenLevel(depth=depth)
    level.set_size(40, 40)

    class RunState:
        generator_state = state

    level.run_state = RunState()
    return level, rng


def _make_room(cls, left=5, top=5, w=9, h=9, size_cat=SizeCategory.NORMAL):
    room = cls()
    room.size_cat = size_cat
    room.set(left, top, left + w - 1, top + h - 1)
    door = Door(left + w // 2, top)
    neighbour = Room()
    neighbour.set(left + 2, top - 3, left + 4, top)
    room.connected[neighbour] = door
    return room


def test_minefield_room_places_explosive_traps():
    level, rng = _make_level(seed=3)
    room = _make_room(MinefieldRoom, w=11, h=11)
    room.paint(level, rng)
    assert len(level.traps) > 0
    trap_tiles = sum(1 for v in level.map if v in (terrain.TRAP, terrain.SECRET_TRAP))
    assert trap_tiles == len(level.traps)


def test_plants_room_paints_grass_and_seeds():
    level, rng = _make_level(seed=5)
    room = _make_room(PlantsRoom, w=9, h=9)
    room.paint(level, rng)
    assert terrain.HIGH_GRASS in level.map
    assert len(level.plants) >= 1


def test_aquarium_room_spawns_piranha_in_water():
    level, rng = _make_level(seed=7)
    room = _make_room(AquariumRoom, w=9, h=9)
    room.paint(level, rng)
    fish = [m for m in level.mobs if isinstance(m, GenMob) and m.cls_name in ("Piranha", "PhantomPiranha")]
    assert len(fish) >= 1
    for f in fish:
        assert level.map[f.pos] == terrain.WATER


def test_fissure_room_paints_chasm():
    level, rng = _make_level(seed=9)
    room = _make_room(FissureRoom, w=11, h=11)
    room.paint(level, rng)
    assert terrain.CHASM in level.map


def test_grassy_grave_room_drops_tomb_loot():
    level, rng = _make_level(seed=11)
    room = _make_room(GrassyGraveRoom, w=9, h=9)
    room.paint(level, rng)
    tombs = [h for h in level.heaps.values() if getattr(h, 'type', '') == 'TOMB']
    assert len(tombs) >= 1


def test_study_room_drops_pedestal_prize():
    level, rng = _make_level(seed=13)
    room = _make_room(StudyRoom, w=9, h=9)
    room.paint(level, rng)
    assert terrain.PEDESTAL in level.map
    assert len(level.heaps) >= 1


def test_sentry_room_spawns_registered_mob_not_rat_fallback():
    level, rng = _make_level(seed=17)
    room = _make_room(SentryRoom, w=9, h=9)
    room.paint(level, rng)
    gen_mobs = [m for m in level.mobs if isinstance(m, GenMob) and m.cls_name == "Sentry"]
    assert len(gen_mobs) == 1
    entity = _spawn_mob(gen_mobs[0], level.width())
    assert isinstance(entity, Sentry)
    assert entity.take_damage(9999) == 0  # invulnerable, doesn't silently fall back to Rat


def test_magic_well_room_registers_well_metadata():
    level, rng = _make_level(seed=19)
    room = _make_room(MagicWellRoom, w=7, h=7)
    room.paint(level, rng)
    floor = gen_level_to_floor_state(level, depth=3)
    wells = floor.generation_meta.get("magic_wells")
    assert wells and wells[0]["water_type"] in ("health", "awareness")


def test_sacrifice_room_registers_fire_metadata():
    level, rng = _make_level(seed=23)
    room = _make_room(SacrificeRoom, w=9, h=9)
    room.paint(level, rng)
    floor = gen_level_to_floor_state(level, depth=3)
    fires = floor.generation_meta.get("sacrifice_fires")
    assert fires and fires[0]["prize"] == frozenset({"Weapon"})
    assert fires[0]["volume"] == 6 + 3 * 4


def test_drink_from_well_heals_and_consumes_charge():
    game = GameInstance(game_id="t_well", seed="MAB")
    player = Player(id="p1", name="Hero", pos=Position(x=9, y=8), hp=1, max_hp=20,
                     faction=Faction.PLAYER, class_type="warrior")
    game.players["p1"] = player
    floor = game._get_or_create_floor(1)
    floor.generation_meta["magic_wells"] = [{"pos": (10, 8), "water_type": "health", "used": False}]
    floor.grid[8][10] = TileType.WELL

    game._drink_from_well(player, floor, 1, 10, 8)

    assert player.hp == player.get_total_max_hp()
    assert floor.grid[8][10] == TileType.FLOOR
    assert floor.generation_meta["magic_wells"][0]["used"] is True

    # second drink at an already-used well is a no-op
    player.hp = 1
    game._drink_from_well(player, floor, 1, 10, 8)
    assert player.hp == 1


def test_sacrifice_fire_drops_prize_when_volume_exhausted():
    game = GameInstance(game_id="t_sac", seed="MAB")
    floor = game._get_or_create_floor(1)
    floor.generation_meta["sacrifice_fires"] = [
        {"pos": (15, 15), "volume": 1, "max_volume": 18, "prize": frozenset({"Weapon"})}
    ]
    statue = Statue(id="m1", pos=Position(x=15, y=16))
    statue.floor_level = 3
    before = set(floor.items.keys())

    game._process_sacrifice_fire_death(statue, floor, 1)

    assert floor.generation_meta["sacrifice_fires"][0]["volume"] <= 0
    new_items = [floor.items[i] for i in floor.items.keys() - before]
    assert len(new_items) == 1
