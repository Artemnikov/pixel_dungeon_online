# Copyright (C) 2026 ArtemNikov
#
import pytest
from app.engine.entities.base import Position
from app.engine.entities.items.consumables import Blandfruit, Seed
from app.engine.entities.player import Player, Mob as MobEntity
from app.engine.game.floor_state import FloorState
from app.engine.game.terrain_effects import press_cell, _trigger_plant_effect
from app.engine.alchemy.recipes import CookBlandfruitRecipe


def create_test_floor():
    grid = [[1 for _ in range(10)] for _ in range(10)]  # TileType.FLOOR = 1
    return FloorState(floor_id=1, grid=grid, rooms=[], mobs={}, items={})


def create_test_player(is_warden=False):
    player = Player(
        id="player_1",
        name="Hero",
        pos=Position(x=1, y=1),
        hp=20,
        max_hp=20,
        floor_id=1,
    )
    if is_warden:
        player.subclass_info.subclass = "warden"
    return player


def test_sungrass_trigger():
    floor = create_test_floor()
    player = create_test_player(is_warden=False)
    player.hp = 10
    plant = {"pos": (1, 1), "plant_type": "sungrass", "triggered": False}
    _trigger_plant_effect(floor, (1, 1), plant, player)

    assert any(b.type == "sungrass_health" for b in player.buffs)


def test_sungrass_warden_trigger():
    floor = create_test_floor()
    player = create_test_player(is_warden=True)
    player.hp = 10
    plant = {"pos": (1, 1), "plant_type": "sungrass", "triggered": False}
    _trigger_plant_effect(floor, (1, 1), plant, player)

    buff = player.get_buff("sungrass_health")
    assert buff is not None
    assert buff.source_id is None
    assert buff.level == player.get_total_max_hp()


def test_earthroot_warden_trigger():
    floor = create_test_floor()
    player = create_test_player(is_warden=True)
    plant = {"pos": (1, 1), "plant_type": "earthroot", "triggered": False}
    _trigger_plant_effect(floor, (1, 1), plant, player)

    assert any(b.type == "barkskin" for b in player.buffs)


def test_swiftthistle_trigger():
    floor = create_test_floor()
    player = create_test_player(is_warden=False)
    plant = {"pos": (1, 1), "plant_type": "swiftthistle", "triggered": False}
    _trigger_plant_effect(floor, (1, 1), plant, player)

    assert any(b.type == "time_bubble" for b in player.buffs)


def test_rotberry_seed_drop():
    floor = create_test_floor()
    player = create_test_player(is_warden=False)
    plant = {"pos": (1, 1), "plant_type": "rotberry", "triggered": False}
    _trigger_plant_effect(floor, (1, 1), plant, player)

    seeds = [i for i in floor.items.values() if isinstance(i, Seed) and i.plant_type == "rotberry"]
    assert len(seeds) == 1


def test_cook_blandfruit_recipe():
    recipe = CookBlandfruitRecipe()
    fruit = Blandfruit(name="Blandfruit")
    seed = Seed(name="Rotberry Seed", plant_type="rotberry")

    assert recipe.test_ingredients(None, [fruit, seed]) is True
    out = recipe.brew(None, [fruit, seed])
    assert out is not None
    assert out.potion_type == "strength"
    assert out.name == "Rotfruit"


def test_lotus_seed_preservation():
    floor = create_test_floor()
    player = create_test_player(is_warden=False)
    lotus = MobEntity(
        id="lotus_1",
        type="mob",
        mob_type="lotus",
        name="Lotus",
        pos=Position(x=1, y=2),
        hp=25,
        max_hp=25,
        attack=0,
        defense=999,
        damage_min=0,
        damage_max=0,
        view_distance=3,
    )
    lotus._wand_level = 10  # 100% preservation rate
    floor.mobs[lotus.id] = lotus

    floor.plants[(1, 1)] = {"pos": (1, 1), "plant_type": "firebloom", "triggered": False}
    press_cell(floor, (1, 1), player)

    seeds = [i for i in floor.items.values() if isinstance(i, Seed) and i.plant_type == "firebloom"]
    assert len(seeds) == 1


def test_seed_actions_and_default():
    seed = Seed(plant_type="sungrass")
    actions = seed.actions()
    assert "PLANT" in actions
    assert "THROW" in actions
    assert "DROP" in actions
    assert seed.default_action() == "THROW"


def test_action_plant_seed_on_hero_tile():
    from app.engine.manager import GameInstance
    from app.engine.dungeon.constants import TileType
    from app.engine.entities.items.actions import action_plant_seed

    game = GameInstance("test-plant-seed")
    player = list(game.players.values())[0] if game.players else game.add_player("p1", "Hero", "warrior")
    floor = game._get_or_create_floor(player.floor_id)

    px, py = player.pos.x, player.pos.y
    floor.grid[py][px] = TileType.FLOOR

    seed = Seed(plant_type="firebloom")
    player.belongings.backpack.collect(seed)

    action_plant_seed(game, player, seed)

    assert (px, py) in floor.plants
    assert floor.plants[(px, py)]["plant_type"] == "firebloom"
    assert floor.grid[py][px] == TileType.FLOOR_GRASS
    assert player.belongings.get_item(seed.id) is None


def test_action_plant_seed_warden_furrowed_grass():
    from app.engine.manager import GameInstance
    from app.engine.dungeon.constants import TileType
    from app.engine.entities.items.actions import action_plant_seed

    game = GameInstance("test-warden-plant")
    player = list(game.players.values())[0] if game.players else game.add_player("p1", "Huntress", "huntress")
    player.subclass_info.subclass = "warden"
    floor = game._get_or_create_floor(player.floor_id)

    px, py = player.pos.x, player.pos.y
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if 0 <= px + dx < floor.width and 0 <= py + dy < floor.height:
                floor.grid[py + dy][px + dx] = TileType.FLOOR

    seed = Seed(plant_type="earthroot")
    player.belongings.backpack.collect(seed)

    action_plant_seed(game, player, seed)

    assert (px, py) in floor.plants
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = px + dx, py + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                assert floor.grid[ny][nx] == TileType.FURROWED_GRASS


def test_action_throw_seed_plants_at_target():
    from app.engine.manager import GameInstance
    from app.engine.dungeon.constants import TileType
    from app.engine.entities.items.actions import action_throw

    game = GameInstance("test-throw-seed")
    player = list(game.players.values())[0] if game.players else game.add_player("p1", "Hero", "warrior")
    floor = game._get_or_create_floor(player.floor_id)

    px, py = player.pos.x, player.pos.y
    tx, ty = px + 2, py
    if tx >= floor.width:
        tx = px - 2
    floor.grid[ty][tx] = TileType.FLOOR
    if floor.flags:
        floor.flags.solid[ty][tx] = False

    seed = Seed(plant_type="sungrass")
    player.belongings.backpack.collect(seed)

    action_throw(game, player, seed, tx, ty)

    assert (tx, ty) in floor.plants
    assert floor.plants[(tx, ty)]["plant_type"] == "sungrass"
    assert floor.grid[ty][tx] == TileType.FLOOR_GRASS


def test_action_throw_seed_into_alchemy_pot():
    from app.engine.manager import GameInstance
    from app.engine.dungeon.constants import TileType
    from app.engine.entities.items.actions import action_throw

    game = GameInstance("test-throw-alchemy")
    player = list(game.players.values())[0] if game.players else game.add_player("p1", "Hero", "warrior")
    floor = game._get_or_create_floor(player.floor_id)

    px, py = player.pos.x, player.pos.y
    tx, ty = px + 1, py
    floor.grid[ty][tx] = TileType.ALCHEMY
    if floor.flags:
        floor.flags.solid[ty][tx] = False

    seed = Seed(plant_type="icecap")
    player.belongings.backpack.collect(seed)

    action_throw(game, player, seed, tx, ty)

    assert (tx, ty) not in floor.plants
    alchemy_items = [i for i in floor.items.values() if i.pos and i.pos.x == tx and i.pos.y == ty]
    assert len(alchemy_items) == 1
    assert getattr(alchemy_items[0], "plant_type", "") == "icecap"


def test_seed_descriptions():
    from app.engine.entities.items.consumables import _PLANT_TYPE_NAMES, PLANT_DESCS, WARDEN_PLANT_DESCS
    from app.engine.entities.wands.wandmaker_quest_items import RotberrySeed

    for pt in _PLANT_TYPE_NAMES:
        seed = Seed(plant_type=pt)
        desc = seed.description()
        assert desc.startswith("Throw this seed to the place where you want to grow a plant.\n\n")
        assert PLANT_DESCS[pt] in desc

    sungrass = Seed(plant_type="sungrass")
    warrior = create_test_player(is_warden=False)
    desc_warrior = sungrass.description(warrior)
    assert "Sungrass is renowned for its sap's slow but effective healing properties." in desc_warrior
    assert "_The Warden_" not in desc_warrior

    warden = create_test_player(is_warden=True)
    desc_warden = sungrass.description(warden)
    assert "Sungrass is renowned for its sap's slow but effective healing properties." in desc_warden
    assert "_The Warden_ can receive healing from trampled sungrass even if she moves away from it." in desc_warden

    rot_seed = RotberrySeed()
    assert "The berries of a young rotberry shrub taste like sweet, sweet death." in rot_seed.description()
    assert "sweet, sweet death" in rot_seed.description(warden)
    assert "_the Warden_ is able to harness energy" in rot_seed.description(warden)

    dreamfoil_seed = Seed(plant_type="dreamfoil")
    assert "The mageroyal's prickly flowers contain a chemical" in dreamfoil_seed.description()

    unknown_seed = Seed(plant_type="unknown_plant")
    assert unknown_seed.description() == "Throw this seed to the place where you want to grow a plant."


def test_mageroyal_alchemy_recipe():
    from app.engine.alchemy.recipes import SEED_TO_POTION, PotionOfPurity

    assert SEED_TO_POTION["mageroyal"] is PotionOfPurity


def test_rotberry_not_in_grass_loot_pool():
    from unittest import mock
    from app.engine.game import terrain_effects

    floor = create_test_floor()
    captured = {}

    def fake_choice(seq):
        captured["seq"] = list(seq)
        return seq[0]

    with mock.patch.object(terrain_effects.random, "choice", side_effect=fake_choice):
        terrain_effects._drop_seed(floor, (5, 5))

    assert "rotberry" not in captured["seq"]


def test_icecap_freezes_and_clears_grass():
    from app.engine.dungeon.constants import TileType

    floor = create_test_floor()
    player = create_test_player(is_warden=False)
    mob = MobEntity(
        id="mob_1",
        type="mob",
        mob_type="rat",
        name="Rat",
        pos=Position(x=2, y=2),
        hp=20, max_hp=20, attack=1, defense=0, damage_min=1, damage_max=3,
    )
    floor.mobs[mob.id] = mob
    floor.grid[1][2] = TileType.HIGH_GRASS
    floor.grid[2][2] = TileType.FLOOR_GRASS

    plant = {"pos": (1, 1), "plant_type": "icecap", "triggered": False}
    _trigger_plant_effect(floor, (1, 1), plant, player)

    # Both the trampler and a mob in the 3x3 area are frozen.
    assert player.has_buff("frost")
    assert mob.has_buff("frost")
    # Grass inside the area is cleared to plain floor.
    assert floor.grid[1][2] == TileType.FLOOR
    assert floor.grid[2][2] == TileType.FLOOR


def test_icecap_douses_fire_and_freezes_meat():
    from app.engine.entities.items.consumables import FrozenCarpaccio, MysteryMeat

    floor = create_test_floor()
    player = create_test_player(is_warden=False)

    floor.blob_areas["fire_test"] = {
        "type": "fire",
        "cells": {(2, 2), (10, 10)},
        "volume": {(2, 2): 10, (10, 10): 10},
    }
    meat = MysteryMeat(id="meat_1", pos=Position(x=2, y=2), quantity=2)
    floor.items[meat.id] = meat

    plant = {"pos": (1, 1), "plant_type": "icecap", "triggered": False}
    _trigger_plant_effect(floor, (1, 1), plant, player)

    # Fire blob overlapping the 3x3 area is doused; out-of-area cells survive.
    blob = floor.blob_areas["fire_test"]
    assert (2, 2) not in blob["cells"]
    assert (10, 10) in blob["cells"]
    assert blob["volume"].get((2, 2)) is None

    # Ground Mystery Meat is converted to Frozen Carpaccio.
    assert isinstance(floor.items[meat.id], FrozenCarpaccio)
    assert floor.items[meat.id].quantity == 2


def test_sungrass_heals_while_standing():
    from app.engine.manager import GameInstance

    game = GameInstance("test-sungrass-heal")
    player = list(game.players.values())[0] if game.players else game.add_player("p1", "Hero", "warrior")
    floor = game._get_or_create_floor(player.floor_id)
    px, py = player.pos.x, player.pos.y

    floor.plants[(px, py)] = {"pos": (px, py), "plant_type": "sungrass", "triggered": False}
    press_cell(floor, (px, py), player)

    heal_buff = player.get_buff("sungrass_health")
    assert heal_buff is not None
    assert heal_buff.source_id == f"{px},{py}"

    player.hp = player.get_total_max_hp() - 5
    for _ in range(10):
        game._apply_sungrass_heal(player, 3.0)
    assert player.hp == player.get_total_max_hp()


def test_sungrass_healing_depletes_reservoir():
    from app.engine.manager import GameInstance

    game = GameInstance("test-sungrass-deplete")
    player = list(game.players.values())[0] if game.players else game.add_player("p1", "Hero", "warrior")
    floor = game._get_or_create_floor(player.floor_id)
    px, py = player.pos.x, player.pos.y

    # Give player a small reservoir of 3 HP on a damaged hero
    player.hp = 5
    player.add_buff("sungrass_health", duration=100.0, level=3, source_id=f"{px},{py}")

    for _ in range(3):
        game._apply_sungrass_heal(player, 3.0)
    assert player.hp == 8
    assert player.get_buff("sungrass_health") is None


def test_earthroot_sets_buff_source_id():
    floor = create_test_floor()
    player = create_test_player(is_warden=False)
    plant = {"pos": (3, 3), "plant_type": "earthroot", "triggered": False}
    _trigger_plant_effect(floor, (3, 3), plant, player)

    armor = player.get_buff("earthroot_armor")
    assert armor is not None
    assert armor.source_id == "3,3"


def test_earthroot_armor_absorbs_damage():
    from app.engine.systems.combat import _apply_earthroot_armor

    player = create_test_player()
    player.add_buff("earthroot_armor", duration=100.0, level=20, source_id="1,1")

    # Depth 1 absorbs (1+5)//2 = 3 per hit from the 20-point pool.
    assert _apply_earthroot_armor(player, 30, depth=1) == 27
    armor = player.get_buff("earthroot_armor")
    assert armor is not None and armor.level == 17
    assert _apply_earthroot_armor(player, 30, depth=1) == 27
    armor = player.get_buff("earthroot_armor")
    assert armor is not None and armor.level == 14

    # Depleting the pool removes the buff and lets the rest through.
    armor = player.get_buff("earthroot_armor")
    assert armor is not None
    armor.level = 2
    assert _apply_earthroot_armor(player, 10, depth=1) == 8
    assert player.get_buff("earthroot_armor") is None

    # No armor buff: damage passes through unchanged.
    assert _apply_earthroot_armor(player, 10, depth=1) == 10

    # Entanglement-glyph armor (no source_id) drains its reservoir 1:1 per
    # hit instead of the per-hit plant cap (plant cap at depth 1 would
    # only ever block 3 per hit).
    glyph_player = create_test_player()
    glyph_player.add_buff("earthroot_armor", duration=20.0, level=10)
    assert _apply_earthroot_armor(glyph_player, 6, depth=1) == 0
    glyph_armor = glyph_player.get_buff("earthroot_armor")
    assert glyph_armor is not None and glyph_armor.level == 4
    assert _apply_earthroot_armor(glyph_player, 6, depth=1) == 2
    assert glyph_player.get_buff("earthroot_armor") is None


def test_sungrass_breaks_on_movement():
    from app.engine.manager import GameInstance
    from app.engine.dungeon.constants import TileType

    game = GameInstance("test-sungrass-break")
    player = list(game.players.values())[0] if game.players else game.add_player("p1", "Hero", "warrior")
    floor = game._get_or_create_floor(player.floor_id)
    px, py = player.pos.x, player.pos.y

    floor.plants[(px, py)] = {"pos": (px, py), "plant_type": "sungrass", "triggered": False}
    press_cell(floor, (px, py), player)
    assert player.has_buff("sungrass_health")

    # Step onto a guaranteed-passable carved neighbor.
    nx, ny = px + 1, py
    if nx >= floor.width:
        nx, ny = px, py + 1
    for mid in list(floor.mobs.keys()):
        if (floor.mobs[mid].pos.x, floor.mobs[mid].pos.y) == (nx, ny):
            del floor.mobs[mid]
    floor.grid[ny][nx] = TileType.FLOOR
    floor.rebuild_flags()

    game.move_entity(player.id, nx - px, ny - py)
    assert not player.has_buff("sungrass_health")


def test_earthroot_breaks_on_movement():
    from app.engine.manager import GameInstance
    from app.engine.dungeon.constants import TileType

    game = GameInstance("test-earthroot-break")
    player = list(game.players.values())[0] if game.players else game.add_player("p1", "Hero", "warrior")
    floor = game._get_or_create_floor(player.floor_id)
    px, py = player.pos.x, player.pos.y

    floor.plants[(px, py)] = {"pos": (px, py), "plant_type": "earthroot", "triggered": False}
    press_cell(floor, (px, py), player)
    assert player.has_buff("earthroot_armor")

    nx, ny = px + 1, py
    if nx >= floor.width:
        nx, ny = px, py + 1
    for mid in list(floor.mobs.keys()):
        if (floor.mobs[mid].pos.x, floor.mobs[mid].pos.y) == (nx, ny):
            del floor.mobs[mid]
    floor.grid[ny][nx] = TileType.FLOOR
    floor.rebuild_flags()

    game.move_entity(player.id, nx - px, ny - py)
    assert not player.has_buff("earthroot_armor")


def test_fadeleaf_warden_sets_pending_ascend():
    from app.engine.game.floor_state import FloorState

    grid = [[1 for _ in range(10)] for _ in range(10)]
    floor = FloorState(floor_id=2, grid=grid, rooms=[], mobs={}, items={})
    player = create_test_player(is_warden=True)
    plant = {"pos": (1, 1), "plant_type": "fadeleaf", "triggered": False}

    _trigger_plant_effect(floor, (1, 1), plant, player)
    assert player.pending_ascend is True


def test_fadeleaf_non_warden_stays_and_teleports():
    from app.engine.game.floor_state import FloorState

    grid = [[1 for _ in range(10)] for _ in range(10)]
    floor = FloorState(floor_id=2, grid=grid, rooms=[], mobs={}, items={})
    player = create_test_player(is_warden=False)
    plant = {"pos": (1, 1), "plant_type": "fadeleaf", "triggered": False}

    _trigger_plant_effect(floor, (1, 1), plant, player)
    assert player.pending_ascend is False


def test_fadeleaf_warden_ascends_on_step():
    from app.engine.manager import GameInstance
    from app.engine.dungeon.constants import TileType

    game = GameInstance("test-fadeleaf-warden")
    player = list(game.players.values())[0] if game.players else game.add_player("p1", "Huntress", "huntress")
    player.subclass_info.subclass = "warden"
    player.floor_id = 2
    floor = game._get_or_create_floor(player.floor_id)
    px, py = player.pos.x, player.pos.y

    tx, ty = px + 1, py
    if tx >= floor.width:
        tx, ty = px, py + 1
    for mid in list(floor.mobs.keys()):
        if (floor.mobs[mid].pos.x, floor.mobs[mid].pos.y) == (tx, ty):
            del floor.mobs[mid]
    floor.grid[ty][tx] = TileType.FLOOR
    floor.rebuild_flags()
    floor.plants[(tx, ty)] = {"pos": (tx, ty), "plant_type": "fadeleaf", "triggered": False}

    game.move_entity(player.id, tx - px, ty - py)

    # The Warden ascended one depth by stepping on the fadeleaf.
    assert player.floor_id == 1
    assert player.pending_ascend is False


def test_earthroot_armor_rejects_damage_if_moved_off_tile():
    from app.engine.systems.combat import _apply_earthroot_armor

    player = create_test_player()
    player.pos = Position(x=5, y=5)
    player.add_buff("earthroot_armor", duration=100.0, level=20, source_id="1,1")

    # Defender is at (5,5) but buff was stamped at (1,1) -> buff detaches immediately
    # and blocks 0 damage.
    assert _apply_earthroot_armor(player, 10, depth=1) == 10
    assert player.get_buff("earthroot_armor") is None


def test_knockback_breaks_stationary_plant_buffs():
    from app.engine.entities.wands.base import knockback_char
    from app.engine.game.floor_state import FloorState
    from app.engine.dungeon.terrain_flags import build_flag_maps
    from app.engine.dungeon.constants import TileType

    grid = [[TileType.FLOOR for _ in range(10)] for _ in range(10)]
    floor = FloorState(floor_id=1, grid=grid, rooms=[], mobs={}, items={})
    floor.flags = build_flag_maps(grid)

    player = create_test_player()
    player.pos = Position(x=2, y=2)
    player.add_buff("earthroot_armor", duration=100.0, level=20, source_id="2,2")
    player.add_buff("sungrass_health", duration=100.0, level=20, source_id="2,2")

    knockback_char(floor, player, 1, 0, power=1, floor_id=1)
    assert player.pos.x == 3 and player.pos.y == 2
    assert not player.has_buff("earthroot_armor")
    assert not player.has_buff("sungrass_health")


def test_teleport_breaks_stationary_plant_buffs():
    from app.engine.game.terrain_effects import _teleport_activator
    from app.engine.game.floor_state import FloorState
    from app.engine.dungeon.terrain_flags import build_flag_maps
    from app.engine.dungeon.constants import TileType

    grid = [[TileType.FLOOR for _ in range(10)] for _ in range(10)]
    floor = FloorState(floor_id=1, grid=grid, rooms=[], mobs={}, items={})
    floor.flags = build_flag_maps(grid)

    player = create_test_player()
    player.pos = Position(x=2, y=2)
    player.add_buff("earthroot_armor", duration=100.0, level=20, source_id="2,2")
    player.add_buff("sungrass_health", duration=100.0, level=20, source_id="2,2")

    _teleport_activator(floor, player)
    assert not player.has_buff("earthroot_armor")
    assert not player.has_buff("sungrass_health")


def test_seed_plant_sound_emission_and_los_filter():
    from app.engine.manager import GameInstance
    from app.engine.dungeon.constants import TileType
    from app.engine.entities.base import Action

    g = GameInstance("test-plant-sound-los")
    grid = [[TileType.FLOOR for _ in range(11)] for _ in range(11)]
    for y in range(11):
        grid[y][5] = TileType.WALL

    floor = FloorState(floor_id=1, grid=grid, rooms=[], mobs={}, items={})
    floor.rebuild_flags()
    g.floors[1] = floor

    p1 = g.add_player("p1", "Planter")
    p1.pos = Position(x=2, y=2)
    p2_los = g.add_player("p2", "WatcherInLOS")
    p2_los.pos = Position(x=3, y=2)
    p3_no_los = g.add_player("p3", "BehindWall")
    p3_no_los.pos = Position(x=8, y=2)

    seed = Seed(plant_type="sungrass")
    p1.add_to_inventory(seed)

    g.flush_events()
    g.execute_item_action("p1", seed.id, Action.PLANT)

    events = g.flush_events()
    plant_sounds = [e for e in events if e.get("type") == "PLAY_SOUND" and e.get("data", {}).get("sound") == "PLANT"]
    assert len(plant_sounds) == 1
    sound_ev = plant_sounds[0]
    assert sound_ev["data"]["x"] == 2 and sound_ev["data"]["y"] == 2

    p1_filtered = g.filter_events_for_player(events, "p1")
    p2_filtered = g.filter_events_for_player(events, "p2")
    p3_filtered = g.filter_events_for_player(events, "p3")

    assert any(e.get("type") == "PLAY_SOUND" and e.get("data", {}).get("sound") == "PLANT" for e in p1_filtered)
    assert any(e.get("type") == "PLAY_SOUND" and e.get("data", {}).get("sound") == "PLANT" for e in p2_filtered)
    assert not any(e.get("type") == "PLAY_SOUND" and e.get("data", {}).get("sound") == "PLANT" for e in p3_filtered)


def test_sungrass_warden_mobile_healing():
    from app.engine.manager import GameInstance
    from app.engine.dungeon.constants import TileType

    game = GameInstance("test-warden-sungrass-mobile")
    player = game.add_player("p_warden", "Huntress", "huntress")
    player.subclass_info.subclass = "warden"
    floor = game._get_or_create_floor(player.floor_id)
    px, py = player.pos.x, player.pos.y

    floor.plants[(px, py)] = {"pos": (px, py), "plant_type": "sungrass", "triggered": False}
    press_cell(floor, (px, py), player)

    buff = player.get_buff("sungrass_health")
    assert buff is not None
    assert buff.source_id is None

    # Step off tile
    nx, ny = px + 1, py
    if nx >= floor.width:
        nx, ny = px, py + 1
    floor.grid[ny][nx] = TileType.FLOOR
    floor.rebuild_flags()
    game.move_entity(player.id, nx - px, ny - py)

    # Buff is preserved because it is mobile (source_id is None)
    assert player.has_buff("sungrass_health")

    # Healing ticks while moving/standing away from original plant tile
    player.hp = player.get_total_max_hp() - 5
    for _ in range(15):
        game._apply_sungrass_heal(player, 1.0)
    assert player.hp == player.get_total_max_hp()


def test_sungrass_reservoir_preserved_at_full_hp():
    from app.engine.manager import GameInstance

    game = GameInstance("test-sungrass-full-hp")
    player = game.add_player("p_full", "Hero", "warrior")
    px, py = player.pos.x, player.pos.y
    max_hp = player.get_total_max_hp()
    player.hp = max_hp

    player.add_buff("sungrass_health", duration=999999.0, level=20, source_id=f"{px},{py}")

    # Standing at full health: accumulator doesn't advance and reservoir doesn't drain
    for _ in range(10):
        game._apply_sungrass_heal(player, 1.0)
    buff = player.get_buff("sungrass_health")
    assert buff is not None
    assert buff.level == 20

    # Take damage while staying on tile
    player.hp = max_hp - 5
    for _ in range(15):
        game._apply_sungrass_heal(player, 1.0)
    assert player.hp == max_hp
    buff = player.get_buff("sungrass_health")
    assert buff is not None
    assert buff.level == 15


def test_sungrass_mob_healing():
    from app.engine.manager import GameInstance
    from app.engine.entities.player import Mob as MobEntity

    game = GameInstance("test-sungrass-mob")
    floor = game._get_or_create_floor(1)
    mob = MobEntity(id="mob_rat", name="Marsupial Rat", pos=Position(x=3, y=3), hp=4, max_hp=10)
    floor.mobs[mob.id] = mob

    plant = {"pos": (3, 3), "plant_type": "sungrass", "triggered": False}
    _trigger_plant_effect(floor, (3, 3), plant, mob)

    buff = mob.get_buff("sungrass_health")
    assert buff is not None
    assert buff.source_id == "3,3"
    assert buff.level == 10

    # Mob heals while on tile
    for _ in range(15):
        game._apply_sungrass_heal(mob, 1.0, floor_id=1)
    assert mob.hp > 4

    # When mob moves off tile, stationary buff breaks
    mob.pos = Position(x=4, y=3)
    game._apply_sungrass_heal(mob, 1.0, floor_id=1)
    assert not mob.has_buff("sungrass_health")


def test_staff_of_regrowth_sungrass_boost():
    from app.engine.entities.wands.regrowth import WandOfRegrowth
    from app.engine.dungeon.constants import TileType

    floor = create_test_floor()
    floor.grid[1][1] = TileType.FLOOR_GRASS
    attacker = create_test_player()
    attacker.pos = Position(x=1, y=1)
    defender = MobEntity(id="mob_1", name="Rat", pos=Position(x=1, y=2), hp=10, max_hp=10)

    staff = WandOfRegrowth(level=2)
    # damage 12 with level 2: round(12 * 4 / 8 / 2) = round(3) = 3
    staff.on_hit(attacker, defender, damage=12, floor=floor)

    buff = attacker.get_buff("sungrass_health")
    assert buff is not None
    assert buff.level == 3
    assert buff.source_id == "1,1"

    # Second melee strike on grass boosts the reservoir
    staff.on_hit(attacker, defender, damage=12, floor=floor)
    buff = attacker.get_buff("sungrass_health")
    assert buff is not None
    assert buff.level == 6


def test_sunfruit_cleanses_and_heals():
    from app.engine.manager import GameInstance
    from app.engine.entities.items.actions import action_eat_handler

    game = GameInstance("test-sunfruit-eat")
    player = game.add_player("p_eater", "Hero", "warrior")
    player.hp = 10
    player.add_buff("poison", duration=10.0, level=1)
    player.add_buff("bleeding", duration=10.0, level=1)
    player.add_buff("cripple", duration=10.0, level=1)
    player.add_buff("ooze", duration=10.0, level=1)
    player.bleed_amount = 5
    player.ooze_amount = 3

    sunfruit = Blandfruit(potion_type="health")
    player.add_to_inventory(sunfruit)

    action_eat_handler(game, player, sunfruit)

    # Debuffs and DoT counters cleansed
    assert not player.has_buff("poison")
    assert not player.has_buff("bleeding")
    assert not player.has_buff("cripple")
    assert not player.has_buff("ooze")
    assert player.bleed_amount == 0
    assert player.ooze_amount == 0

    # Potion of healing over time applied
    assert player.heal_left > 0


def test_sungrass_hud_active_effect_sync():
    from app.engine.game.status_effects_tick import DEFAULT_STATUS_EFFECT_REGISTRY

    player = create_test_player()
    player.add_buff("sungrass_health", duration=999999.0, level=15, source_id="1,1")

    effects = DEFAULT_STATUS_EFFECT_REGISTRY.collect(player)
    sungrass_eff = next((e for e in effects if e.key == "sungrass_health"), None)

    assert sungrass_eff is not None
    assert sungrass_eff.name == "Herbal Healing"
    assert sungrass_eff.icon == 19
    assert sungrass_eff.remaining == 15.0
    assert sungrass_eff.duration == float(player.get_total_max_hp())


def test_earthroot_hud_active_effect_sync():
    from app.engine.game.status_effects_tick import DEFAULT_STATUS_EFFECT_REGISTRY

    player = create_test_player()
    max_hp = player.get_total_max_hp()
    player.add_buff("earthroot_armor", duration=100.0, level=max_hp, source_id="1,1")

    effects = DEFAULT_STATUS_EFFECT_REGISTRY.collect(player)
    earthroot_eff = next((e for e in effects if e.key == "earthroot_armor"), None)

    assert earthroot_eff is not None
    assert earthroot_eff.name == "Earthroot"
    assert earthroot_eff.icon == 20
    assert earthroot_eff.remaining == float(max_hp)
    assert earthroot_eff.duration == float(max_hp)


def test_staff_of_regrowth_warden_keeps_mobile_buff():
    from app.engine.entities.wands.regrowth import WandOfRegrowth
    from app.engine.dungeon.constants import TileType

    floor = create_test_floor()
    floor.grid[1][1] = TileType.FLOOR_GRASS
    attacker = create_test_player(is_warden=True)
    attacker.pos = Position(x=1, y=1)
    defender = MobEntity(id="mob_1", name="Rat", pos=Position(x=1, y=2), hp=10, max_hp=10)

    staff = WandOfRegrowth(level=2)
    staff.on_hit(attacker, defender, damage=12, floor=floor)

    buff = attacker.get_buff("sungrass_health")
    assert buff is not None
    assert buff.source_id is None


def test_invisibility_refresh_does_not_leak_stealth():
    player = create_test_player()
    assert player.invisible == 0

    player.add_buff("invisibility", duration=20.0)
    assert player.invisible == 1

    # Refreshing the buff should not increment stealth counter again
    player.add_buff("invisibility", duration=20.0)
    assert player.invisible == 1

    player.remove_buff("invisibility")
    assert player.invisible == 0


def test_movement_onto_plant_emits_plant_triggered_event():
    from app.engine.manager import GameInstance
    from app.engine.dungeon.constants import TileType

    game = GameInstance("test-plant-trigger-event")
    player = game.add_player("p1", "Hero", "warrior")
    floor = game._get_or_create_floor(player.floor_id)
    px, py = player.pos.x, player.pos.y

    nx, ny = px + 1, py
    if nx >= floor.width:
        nx, ny = px, py + 1
    floor.grid[ny][nx] = TileType.FLOOR
    floor.rebuild_flags()
    floor.plants[(nx, ny)] = {"pos": (nx, ny), "plant_type": "sungrass", "triggered": False}

    game.flush_events()
    game.move_entity(player.id, nx - px, ny - py)

    events = game.flush_events()
    triggered_events = [e for e in events if e.get("type") == "PLANT_TRIGGERED"]
    assert len(triggered_events) == 1
    ev = triggered_events[0]
    assert ev["data"]["plant"] == "sungrass"
    assert ev["data"]["player"] == "p1"
    assert ev["data"]["x"] == nx
    assert ev["data"]["y"] == ny


def test_icecap_warden_gains_frost_imbue_and_triggers_area_freeze():
    from app.engine.dungeon.constants import TileType
    from app.engine.entities.items.consumables import FrozenCarpaccio, MysteryMeat

    floor = create_test_floor()
    warden = create_test_player(is_warden=True)
    warden.pos = Position(x=1, y=1)

    mob = MobEntity(
        id="mob_ice",
        type="mob",
        mob_type="rat",
        name="Rat",
        pos=Position(x=2, y=1),
        hp=20, max_hp=20, attack=1, defense=0, damage_min=1, damage_max=3,
    )
    floor.mobs[mob.id] = mob
    floor.grid[1][2] = TileType.HIGH_GRASS

    meat = MysteryMeat(id="meat_ice", pos=Position(x=1, y=2), quantity=1)
    floor.items[meat.id] = meat

    plant = {"pos": (1, 1), "plant_type": "icecap", "triggered": False}
    _trigger_plant_effect(floor, (1, 1), plant, warden)

    # Warden gains FrostImbue and is immune to frost
    assert warden.has_buff("frost_imbue")
    assert not warden.has_buff("frost")

    # Adjacent mob is frozen and tagged with hazard assist tracker
    assert mob.has_buff("frost")
    assert mob.has_buff("hazard_assist_tracker")

    # Adjacent grass is cleared and meat is frozen to carpaccio
    assert floor.grid[1][2] == TileType.FLOOR
    assert isinstance(floor.items[meat.id], FrozenCarpaccio)


def test_icecap_water_triples_freeze_duration():
    from app.engine.dungeon.constants import TileType

    floor = create_test_floor()
    # Put water under dry mob pos (2, 1) and keep water under water mob pos (1, 2)
    floor.grid[2][1] = TileType.FLOOR_WATER
    floor.grid[1][2] = TileType.FLOOR

    mob_water = MobEntity(
        id="mob_water",
        type="mob",
        mob_type="rat",
        name="Water Rat",
        pos=Position(x=1, y=2),
        hp=20, max_hp=20, attack=1, defense=0, damage_min=1, damage_max=3,
    )
    mob_dry = MobEntity(
        id="mob_dry",
        type="mob",
        mob_type="rat",
        name="Dry Rat",
        pos=Position(x=2, y=1),
        hp=20, max_hp=20, attack=1, defense=0, damage_min=1, damage_max=3,
    )

    floor.mobs[mob_water.id] = mob_water
    floor.mobs[mob_dry.id] = mob_dry

    player = create_test_player(is_warden=False)
    player.pos = Position(x=1, y=1)

    plant = {"pos": (1, 1), "plant_type": "icecap", "triggered": False}
    _trigger_plant_effect(floor, (1, 1), plant, player)

    buff_water = mob_water.get_buff("frost")
    buff_dry = mob_dry.get_buff("frost")

    assert buff_water is not None and buff_water.remaining == 30.0  # 3x in water
    assert buff_dry is not None and buff_dry.remaining == 10.0      # standard on dry floor


def test_icecap_solid_wall_blocks_freeze():
    from app.engine.dungeon.constants import TileType
    from app.engine.dungeon.terrain_flags import build_flag_maps

    floor = create_test_floor()
    # Make tile (2, 1) a solid wall
    floor.grid[1][2] = TileType.WALL
    floor.flags = build_flag_maps(floor.grid)

    mob_behind_wall = MobEntity(
        id="mob_wall",
        type="mob",
        mob_type="rat",
        name="Wall Rat",
        pos=Position(x=2, y=1),
        hp=20, max_hp=20, attack=1, defense=0, damage_min=1, damage_max=3,
    )
    floor.mobs[mob_behind_wall.id] = mob_behind_wall

    player = create_test_player(is_warden=False)
    player.pos = Position(x=1, y=1)

    plant = {"pos": (1, 1), "plant_type": "icecap", "triggered": False}
    _trigger_plant_effect(floor, (1, 1), plant, player)

    # Mob in solid wall is not frozen
    assert not mob_behind_wall.has_buff("frost")


