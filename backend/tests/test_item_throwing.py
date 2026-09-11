# Copyright (C) 2026 ArtemNikov
import pytest

from app.engine.manager import GameInstance
from app.engine.dungeon.constants import TileType
from app.engine.dungeon.models import TrapInfo
from app.engine.entities.base import Action, Position
from app.engine.entities.items.consumables import Food, Ration, Seed, Stone, ThrowableDagger
from app.engine.entities.items.potions import (
    HealthPotion, PotionOfFrost, PotionOfLevitation, PotionOfLiquidFlame,
    PotionOfPurity, PotionOfStrength,
)
from app.engine.entities.items.equip import Armor, MeleeWeapon, MissileWeapon
from app.engine.entities.items.actions import action_throw
from app.engine.entities.runestones import StoneOfBlast
from app.engine.entities.items.bombs import Bomb
from app.engine.entities.talent_enum import Talent


def _setup_test_scene(game_id: str, char_class: str = "warrior"):
    game = GameInstance(game_id)
    player = game.add_player("p1", "Hero", char_class)
    floor = game._get_or_create_floor(player.floor_id)
    player.belongings.backpack.items.clear()
    for y in range(0, 12):
        for x in range(0, 12):
            floor.grid[y][x] = TileType.FLOOR
    floor.rebuild_flags()
    player.pos = Position(x=5, y=5)
    return game, player, floor


def test_item_classification_keys():
    """Verify is_throwable and throw_behavior defaults and subclass overrides."""
    food = Ration()
    assert food.is_throwable is False
    assert food.throw_behavior == "regular"

    armor = Armor(name="Cloth Armor")
    assert armor.is_throwable is False
    assert armor.throw_behavior == "regular"

    weapon = MeleeWeapon(name="Shortsword", damage=4)
    assert weapon.is_throwable is False
    assert weapon.throw_behavior == "regular"

    stone = Stone()
    assert stone.is_throwable is True
    assert stone.throw_behavior == "missile"

    dagger = ThrowableDagger()
    assert dagger.is_throwable is True
    assert dagger.throw_behavior == "missile"

    missile_wep = MissileWeapon(name="Dart")
    assert missile_wep.is_throwable is True
    assert missile_wep.throw_behavior == "missile"

    seed = Seed(plant_type="sungrass")
    assert seed.is_throwable is False
    assert seed.throw_behavior == "seed"

    potion = HealthPotion()
    assert potion.is_throwable is False
    assert potion.throw_behavior == "potion"

    bomb = Bomb()
    assert bomb.is_throwable is False
    assert bomb.throw_behavior == "bomb"

    runestone = StoneOfBlast()
    assert runestone.is_throwable is False
    assert runestone.throw_behavior == "runestone"


def test_throw_regular_item_drops_on_floor_and_opens_door():
    """Throwing food or regular items traces ballistica, opens doors, and drops on floor."""
    game, player, floor = _setup_test_scene("test-throw-regular")

    door_x, door_y = 7, 5
    floor.grid[door_y][door_x] = TileType.DOOR
    floor.rebuild_flags()

    food = Ration(id="food_1")
    player.belongings.backpack.collect(food)

    action_throw(game, player, food, 8, 5)

    assert floor.grid[door_y][door_x] == TileType.OPEN_DOOR
    dropped = [item for item in floor.items.values() if item.pos and item.pos.x == door_x and item.pos.y == door_y]
    assert len(dropped) == 1
    assert dropped[0].name == food.name
    assert player.belongings.get_item("food_1") is None


def test_throw_regular_item_triggers_trap_at_destination():
    """Throwing regular items onto traps triggers the trap at the impact cell."""
    game, player, floor = _setup_test_scene("test-throw-trap")

    tx, ty = 7, 5
    floor.grid[ty][tx] = TileType.TRAP
    floor.traps[(tx, ty)] = TrapInfo(x=tx, y=ty, trap_type="burning_trap", hidden=False, active=True)
    floor.rebuild_flags()

    food = Ration(id="food_1")
    player.belongings.backpack.collect(food)

    action_throw(game, player, food, tx, ty)

    assert (tx, ty) in floor.traps
    assert floor.traps[(tx, ty)].active is False
    assert floor.grid[ty][tx] == TileType.INACTIVE_TRAP
    dropped = [item for item in floor.items.values() if item.pos and item.pos.x == tx and item.pos.y == ty]
    assert len(dropped) == 1


def test_throw_regular_item_into_chasm_falls_to_next_floor():
    """Throwing items into a chasm drops them to the floor below."""
    game, player, floor = _setup_test_scene("test-throw-chasm")

    cx, cy = 6, 5
    floor.grid[cy][cx] = TileType.CHASM
    floor.rebuild_flags()

    food = Ration(id="food_1")
    player.belongings.backpack.collect(food)

    action_throw(game, player, food, cx, cy)

    next_floor = game._get_or_create_floor(player.floor_id + 1)
    assert "food_1" in next_floor.items
    item_in_next = next_floor.items["food_1"]
    assert item_in_next.pos is not None
    assert item_in_next.pos.x == cx
    assert item_in_next.pos.y == cy
    assert "food_1" not in floor.items


def test_throw_regular_item_procs_improvised_projectiles():
    """Warrior Tier 2 Improvised Projectiles blinds enemy on hit with regular item."""
    game, player, floor = _setup_test_scene("test-throw-ip")
    player.talent_info.talents["improvised_projectiles"] = 2

    from app.engine.entities.mobs.sewers import Rat
    rat = Rat(id="rat_1", name="Marsupial Rat", pos=Position(x=7, y=5), hp=10, max_hp=10)
    floor.mobs["rat_1"] = rat
    floor.rebuild_flags()

    food = Ration(id="food_1")
    player.belongings.backpack.collect(food)

    action_throw(game, player, food, 7, 5)

    assert rat.has_buff("blindness")
    assert player.has_buff("improvised_projectile_cooldown")


def test_throw_equipped_gear_unequips_and_throws():
    """Throwing equipped uncursed gear unequips it and drops it on impact."""
    game, player, floor = _setup_test_scene("test-throw-equipped")

    armor = Armor(id="armor_1", name="Cloth Armor", tier=1)
    player.belongings.armor = armor

    action_throw(game, player, armor, 7, 5)

    assert player.belongings.armor is None
    dropped = [item for item in floor.items.values() if item.pos and item.pos.x == 7 and item.pos.y == 5]
    assert len(dropped) == 1
    assert dropped[0].id == "armor_1"


def test_throw_cursed_equipped_gear_fails():
    """Throwing cursed equipped gear is prevented."""
    game, player, floor = _setup_test_scene("test-throw-cursed-equipped")

    armor = Armor(id="armor_1", name="Cursed Armor", tier=1, cursed=True, cursed_known=True)
    player.belongings.armor = armor

    action_throw(game, player, armor, 7, 5)

    assert player.belongings.armor is not None
    assert "armor_1" not in floor.items


def test_throw_seed_plants_and_updates_map():
    """Throwing a seed plants on valid ground and updates map."""
    game, player, floor = _setup_test_scene("test-throw-seed-map", "huntress")

    seed = Seed(plant_type="sungrass", id="seed_1")
    player.belongings.backpack.collect(seed)

    action_throw(game, player, seed, 7, 5)

    assert (7, 5) in floor.plants
    assert floor.plants[(7, 5)]["plant_type"] == "sungrass"
    assert floor.grid[5][7] == TileType.FLOOR_GRASS


def test_throw_seed_warden_creates_furrowed_grass():
    """Warden throwing a seed converts surrounding tiles to furrowed grass."""
    game, player, floor = _setup_test_scene("test-throw-seed-warden", "huntress")
    player.subclass_info.subclass = "warden"

    seed = Seed(plant_type="earthroot", id="seed_1")
    player.belongings.backpack.collect(seed)

    action_throw(game, player, seed, 7, 5)

    assert (7, 5) in floor.plants
    assert floor.grid[5][7] == TileType.FLOOR_GRASS
    assert floor.grid[4][7] == TileType.FURROWED_GRASS
    assert floor.grid[6][7] == TileType.FURROWED_GRASS
    assert floor.grid[5][6] == TileType.FURROWED_GRASS
    assert floor.grid[5][8] == TileType.FURROWED_GRASS


def test_throw_potion_liquid_flame_creates_fire_blob():
    """Throwing liquid flame creates fire blob at impact."""
    game, player, floor = _setup_test_scene("test-throw-flame", "mage")

    pot = PotionOfLiquidFlame(id="pot_1")
    player.belongings.backpack.collect(pot)

    action_throw(game, player, pot, 7, 5)

    assert any(b.get("type") == "fire" and (7, 5) in b.get("cells", set()) for b in floor.blob_areas.values())


def test_throw_potion_frost_creates_frost_gas():
    """Throwing potion of frost creates frost gas blob."""
    game, player, floor = _setup_test_scene("test-throw-frost", "mage")

    pot = PotionOfFrost(id="pot_1")
    player.belongings.backpack.collect(pot)

    action_throw(game, player, pot, 7, 5)

    assert any(b.get("type") == "frost_gas" and (7, 5) in b.get("cells", []) for b in floor.blob_areas.values())


def test_throw_potion_levitation_creates_confusion_gas():
    """Throwing potion of levitation creates confusion gas blob."""
    game, player, floor = _setup_test_scene("test-throw-lev", "mage")

    pot = PotionOfLevitation(id="pot_1")
    player.belongings.backpack.collect(pot)

    action_throw(game, player, pot, 7, 5)

    assert any(b.get("type") == "confusion_gas" and (7, 5) in b.get("cells", []) for b in floor.blob_areas.values())


def test_throw_potion_purity_clears_harmful_blobs():
    """Throwing potion of purity clears harmful gas/fire blobs within radius 3."""
    game, player, floor = _setup_test_scene("test-throw-purity", "mage")

    floor.blob_areas["toxic_blob"] = {"type": "toxic_gas", "cells": [(7, 5), (8, 5)], "volume": 100}

    pot = PotionOfPurity(id="pot_1")
    player.belongings.backpack.collect(pot)

    action_throw(game, player, pot, 7, 5)

    assert "toxic_blob" not in floor.blob_areas or len(floor.blob_areas["toxic_blob"].get("cells", [])) == 0


def test_throw_beneficial_potion_shatters_without_error():
    """Throwing beneficial potions like Strength or Health shatters safely without exception."""
    game, player, floor = _setup_test_scene("test-throw-beneficial", "warrior")

    pot = PotionOfStrength(id="pot_str")
    player.belongings.backpack.collect(pot)

    action_throw(game, player, pot, 7, 5)

    assert player.belongings.get_item("pot_str") is None


def test_throw_potion_triggers_liquid_willpower_shield():
    """Throwing any potion grants shield when Warrior has Liquid Willpower talent."""
    game, player, floor = _setup_test_scene("test-throw-liquid-willpower", "warrior")
    player.talent_info.talents["liquid_willpower"] = 2

    pot = HealthPotion(id="pot_hp")
    player.belongings.backpack.collect(pot)

    assert len(player.shields) == 0

    action_throw(game, player, pot, 7, 5)

    assert any(s.name == "liquid_willpower" for s in player.shields)


def test_throw_potion_into_chasm_or_well_drops_intact():
    """Throwing a potion into a chasm or well drops intact without shattering."""
    game, player, floor = _setup_test_scene("test-throw-well-chasm", "warrior")

    floor.grid[5][7] = TileType.WELL
    floor.rebuild_flags()

    pot = PotionOfStrength(id="pot_str")
    player.belongings.backpack.collect(pot)

    action_throw(game, player, pot, 7, 5)

    dropped = [item for item in floor.items.values() if item.pos and item.pos.x == 7 and item.pos.y == 5]
    assert len(dropped) == 1
    assert dropped[0].id == "pot_str"


def test_throw_seed_onto_closed_door_plants_without_changing_tile():
    """Throwing a seed onto a door plants on the door cell while preserving TileType.DOOR."""
    game, player, floor = _setup_test_scene("test-throw-seed-door", "warrior")

    floor.grid[5][7] = TileType.DOOR
    floor.rebuild_flags()

    seed = Seed(plant_type="sungrass", id="seed_door")
    player.belongings.backpack.collect(seed)

    action_throw(game, player, seed, 7, 5)

    assert (7, 5) in floor.plants
    assert floor.plants[(7, 5)]["plant_type"] == "sungrass"
    assert floor.grid[5][7] == TileType.DOOR


def test_perform_ranged_attack_delegates_non_missile_to_action_throw():
    """perform_ranged_attack routes seeds, potions, and items through action_throw."""
    game, player, floor = _setup_test_scene("test-pra-delegate", "warrior")

    seed = Seed(plant_type="sungrass", id="seed_pra")
    player.belongings.backpack.collect(seed)

    game.perform_ranged_attack("p1", "seed_pra", 7, 5)

    assert (7, 5) in floor.plants
    assert floor.plants[(7, 5)]["plant_type"] == "sungrass"
    assert floor.grid[5][7] == TileType.FLOOR_GRASS
