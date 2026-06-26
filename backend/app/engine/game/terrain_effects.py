# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
import random
import uuid
from typing import List, Optional, Tuple

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import (
    Berry,
    Dewdrop,
    Position,
    Seed,
    Player,
    Entity,
)
from app.engine.game.floor_state import FloorState


def _plant_seed_at(floor: FloorState, pos: Tuple[int, int], plant_type: str):
    plant = {
        "pos": pos,
        "plant_type": plant_type,
        "triggered": False,
    }
    floor.plants[pos] = plant


def _drop_seed(floor: FloorState, pos: Tuple[int, int]):
    seed_type = random.choice([
        "sungrass", "earthroot", "firebloom", "icecap",
        "sorrowmoss", "dreamfoil", "fadeleaf", "rotberry",
        "starflower", "stormvine", "blindweed", "swiftthistle",
    ])
    seed = Seed(
        id=str(uuid.uuid4()),
        name=seed_type.capitalize() + " Seed",
        pos=Position(x=pos[0], y=pos[1]),
        plant_type=seed_type,
    )
    floor.items[seed.id] = seed
    return seed.id


def _drop_dewdrop(floor: FloorState, pos: Tuple[int, int]):
    dew = Dewdrop(
        id=str(uuid.uuid4()),
        name="Dewdrop",
        pos=Position(x=pos[0], y=pos[1]),
    )
    floor.items[dew.id] = dew
    return dew.id


def _drop_berry(floor: FloorState, pos: Tuple[int, int]):
    berry = Berry(
        id=str(uuid.uuid4()),
        name="Berry",
        pos=Position(x=pos[0], y=pos[1]),
        quantity=random.randint(1, 2),
    )
    floor.items[berry.id] = berry
    return berry.id


def roll_grass_loot(floor: FloorState, trampler: Entity) -> list:
    drops: list = []

    # SPD: no loot in mining level or vault
    region = getattr(floor, "region", "")
    if region in ("mining", "vault"):
        return drops

    # Naturalism bonus from Sandals of Nature
    naturalism = 0
    if isinstance(trampler, Player):
        for item in trampler.belongings.all_items():
            if getattr(item, "artifact_type", None) == "sandals_of_nature":
                naturalism = getattr(item, "naturalism_level", 0)
                break

    # Seeds: 1/(25 - naturalism*4) chance
    seed_chance = 1.0 / max(1, 25 - naturalism * 4)
    if random.random() < seed_chance:
        _drop_seed(floor, (trampler.pos.x, trampler.pos.y))

    # Dewdrops: 1/(6 - naturalism/2) chance
    dew_chance = 1.0 / max(1, 6 - naturalism / 2)
    if region == "sewers":
        dew_chance /= 2  # GRASS-feeling floors in sewers
    if random.random() < dew_chance:
        _drop_dewdrop(floor, (trampler.pos.x, trampler.pos.y))

    # Berries: Nature's Bounty talent check
    if isinstance(trampler, Player):
        talent_level = 0
        talent_info = getattr(trampler, "talent_info", None)
        if talent_info:
            talent_level = talent_info.talents.get("natures_bounty", 0)
        if talent_level > 0:
            berry_floor = getattr(floor, "floor_id", 1)
            berry_rate = max(0.0, 1.0 - (berry_floor - 2) * 0.02 * talent_level)
            if berry_rate > 0 and random.random() < berry_rate * 0.01:
                _drop_berry(floor, (trampler.pos.x, trampler.pos.y))

    return drops


def press_cell(floor: FloorState, pos: Tuple[int, int], trampler: Entity) -> dict:
    result = {
        "tile_changed": False,
        "drops": [],
        "triggered_plant": None,
    }

    tile = floor.grid[pos[1]][pos[0]]

    # --- Trample grass ------------------------------------------------------
    if tile in (TileType.HIGH_GRASS, TileType.FURROWED_GRASS):
        is_warden = _is_warden(trampler)
        is_huntress = isinstance(trampler, Player) and trampler.class_type == "huntress"

        if tile == TileType.FURROWED_GRASS:
            if not is_warden:
                floor.grid[pos[1]][pos[0]] = TileType.FLOOR_GRASS
                result["tile_changed"] = True
        elif tile == TileType.HIGH_GRASS:
            if is_warden:
                floor.grid[pos[1]][pos[0]] = TileType.FURROWED_GRASS
            elif is_huntress:
                floor.grid[pos[1]][pos[0]] = TileType.FURROWED_GRASS
            else:
                floor.grid[pos[1]][pos[0]] = TileType.FLOOR_GRASS
            result["tile_changed"] = True

        if result["tile_changed"]:
            floor.rebuild_flags()

        # Roll loot from trampled grass (not from FURROWED_GRASS stepped by Warden)
        if tile == TileType.HIGH_GRASS:
            result["drops"] = roll_grass_loot(floor, trampler)

        # Camouflage glyph check
        _trigger_camouflage(trampler)

        # Rejuvenating Steps check
        _trigger_rejuvenating_steps(floor, pos, trampler)

    # --- Trigger plant at this cell -----------------------------------------
    plant = floor.plants.get(pos)
    if plant and not plant.get("triggered", False):
        plant["triggered"] = True
        result["triggered_plant"] = plant
        _trigger_plant_effect(floor, pos, plant, trampler)

    return result


def _is_warden(entity: Entity) -> bool:
    if isinstance(entity, Player):
        subclass_info = getattr(entity, "subclass_info", None)
        if subclass_info and subclass_info.subclass == "warden":
            return True
    return False


def _trigger_camouflage(trampler: Entity):
    if not isinstance(trampler, Player):
        return
    armor = trampler.belongings.armor
    if armor and getattr(armor, "enchantment", None) and armor.enchantment.type == "camouflage":
        level = armor.enchantment.level
        duration = 3.0 + level * 0.5
        trampler.add_buff("invisibility", duration=duration)


def _trigger_rejuvenating_steps(floor: FloorState, pos: Tuple[int, int], trampler: Entity):
    if not isinstance(trampler, Player):
        return
    talent_info = getattr(trampler, "talent_info", None)
    talent_level = talent_info.talents.get("rejuvenating_steps", 0) if talent_info else 0
    if talent_level <= 0:
        return

    cooldown = max(5, 15 - talent_level * 5)
    if trampler.has_buff("rejuvenating_steps_cooldown"):
        return

    tile = floor.grid[pos[1]][pos[0]]
    if tile == TileType.FLOOR_GRASS or tile == 14:  # EMBERS (when added)
        floor.grid[pos[1]][pos[0]] = TileType.HIGH_GRASS
        floor.rebuild_flags()
        trampler.add_buff("rejuvenating_steps_cooldown", duration=cooldown)


def _trigger_plant_effect(floor: FloorState, pos: Tuple[int, int], plant, activator: Entity):
    plant_type = plant.get("plant_type", "sungrass")

    # Nature's Aid: Warden gets Barkskin on plant trigger
    if _is_warden(activator):
        talent_info = getattr(activator, "talent_info", None)
        if talent_info and talent_info.talents.get("natures_aid", 0) > 0:
            activator.add_buff("barkskin", duration=30.0, level=2)

    effects = {
        "sungrass": lambda: _heal_activator(activator, 10.0),
        "earthroot": lambda: activator.add_buff("barkskin", duration=6.0, level=3),
        "firebloom": lambda: _explode_fire(floor, pos),
        "icecap": lambda: _freeze_area(floor, pos),
        "sorrowmoss": lambda: _create_gas(floor, pos, 4, "toxic_gas"),
        "dreamfoil": lambda: _cure_debuffs(activator),
        "fadeleaf": lambda: _teleport_activator(floor, activator),
        "rotberry": lambda: activator.add_buff("bless", duration=20.0, level=1),
        "starflower": lambda: activator.add_buff("well_fed", duration=50.0, level=1),
        "stormvine": lambda: _teleport_activator(floor, activator),
        "blindweed": lambda: activator.add_buff("blindness", duration=10.0, level=1),
        "swiftthistle": lambda: activator.add_buff("haste", duration=3.0, level=1),
    }

    effect = effects.get(plant_type)
    if effect:
        effect()


def _heal_activator(entity: Entity, duration: float):
    if isinstance(entity, Player):
        entity.set_heal(10.0, 0.1, 1.0)


def _explode_fire(floor: FloorState, pos: Tuple[int, int]):
    blob_id = f"firebloom_{pos[0]}_{pos[1]}"
    cells = set()
    volume = {}
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                tile = floor.grid[ny][nx]
                flamable = floor.flags.flamable[ny][nx] if floor.flags else False
                if flamable or tile == TileType.FLOOR or tile == TileType.EMPTY_DECO:
                    cells.add((nx, ny))
                    volume[(nx, ny)] = 2
    if cells:
        floor.blob_areas[blob_id] = {"type": "fire", "cells": cells, "volume": volume}


def _freeze_area(floor: FloorState, pos: Tuple[int, int]):
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                tile = floor.grid[ny][nx]
                if tile == TileType.FLOOR_GRASS or tile == TileType.HIGH_GRASS or tile == TileType.FURROWED_GRASS:
                    floor.grid[ny][nx] = TileType.FLOOR
    floor.rebuild_flags()


def _create_gas(floor: FloorState, pos: Tuple[int, int], strength: int, gas_type: str = "toxic_gas"):
    blob_id = f"{gas_type}_{pos[0]}_{pos[1]}"
    cells = set()
    volume = {}
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                if floor.flags and not floor.flags.solid[ny][nx]:
                    cells.add((nx, ny))
                    volume[(nx, ny)] = strength
    if cells:
        for bid in list(floor.blob_areas.keys()):
            b = floor.blob_areas[bid]
            if b.get("type") == gas_type and b.get("cells", set()) & cells:
                del floor.blob_areas[bid]
        floor.blob_areas[blob_id] = {"type": gas_type, "cells": cells, "volume": volume}


def _cure_debuffs(entity: Entity):
    for debuff in ("poison", "blindness", "bleeding", "weakness", "slow", "cripple", "burning", "chill", "frost"):
        entity.remove_buff(debuff)


def _teleport_activator(floor: FloorState, entity: Entity):
    candidates = []
    for y in range(floor.height):
        for x in range(floor.width):
            if floor.flags and floor.flags.passable[y][x] and not floor.flags.solid[y][x]:
                candidates.append((x, y))
    if candidates:
        tx, ty = random.choice(candidates)
        entity.pos.x = tx
        entity.pos.y = ty
