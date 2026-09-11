# Copyright (C) 2026 ArtemNikov
#
import random
import uuid
from typing import Dict, Iterable, List, Optional, Tuple

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position, Entity
from app.engine.entities.buffs import break_stationary_plant_buffs
from app.engine.entities.items.consumables import Berry, Dewdrop, FrozenCarpaccio, MysteryMeat, Seed
from app.engine.entities.player import Player
from app.engine.game.floor_state import FloorState
from app.engine.game.terrain_primitives import GRASS_TILES, plant_grass, _plant_seed_at, _create_gas


def _drop_seed(floor: FloorState, pos: Tuple[int, int], plant_type: Optional[str] = None):
    if plant_type is None:
        # SPD Generator.Category.SEED excludes Rotberry: it is a unique quest
        # seed and can never be dropped from trampling regular high grass.
        plant_type = random.choice([
            "sungrass", "earthroot", "firebloom", "icecap",
            "sorrowmoss", "fadeleaf",
            "starflower", "stormvine", "blindweed", "swiftthistle",
            "mageroyal",
        ])
    if plant_type == "dreamfoil":
        plant_type = "mageroyal"

    seed = Seed(
        id=str(uuid.uuid4()),
        name=plant_type.capitalize() + " Seed",
        pos=Position(x=pos[0], y=pos[1]),
        plant_type=plant_type,
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


def _trinket_grass_loot_mult(player: Player) -> float:
    from app.engine.entities.trinkets import PetrifiedSeed as _PS
    from app.engine.entities.trinkets import trinket_level
    lvl = trinket_level(player, "petrified_seed")
    if lvl < 0:
        return 1.0
    return _PS.grass_loot_multiplier(lvl)


def _trinket_stone_instead_of_seed(player: Player) -> bool:
    from app.engine.entities.trinkets import PetrifiedSeed as _PS
    from app.engine.entities.trinkets import trinket_level
    lvl = trinket_level(player, "petrified_seed")
    if lvl < 0:
        return False
    return random.random() < _PS.stone_instead_of_seed_chance(lvl)


def _naturalism_level(trampler: Entity) -> int:
    """SPD SandalsOfNature.Naturalism: equipped sandals grant +1..+4 loot
    levels; a cursed pair means no grass loot at all (-1). A bagged pair
    grants nothing (the buff only exists while equipped)."""
    if not isinstance(trampler, Player):
        return 0
    sandals = trampler.belongings.artifact
    if sandals is None or getattr(sandals, "kind", "") != "sandals_of_nature":
        return 0
    if sandals.cursed:
        return -1
    # SPD sandals cap at +3; the remake levels artifacts to +10, so clamp to
    # keep the SPD loot ranges (seeds 1/25..1/9, dew 1/6..1/4).
    return min(getattr(sandals, "level", 0), 3) + 1


def roll_grass_loot(floor: FloorState, trampler: Entity) -> list:
    drops: list = []

    # SPD: no loot in mining level or vault
    region = getattr(floor, "region", "")
    if region in ("mining", "vault"):
        return drops

    naturalism = _naturalism_level(trampler)
    if naturalism < 0:
        return drops  # cursed Sandals of Nature suppress all grass loot

    # PetrifiedSeed trinket: grass loot multiplier
    loot_mult = 1.0
    if isinstance(trampler, Player):
        loot_mult = _trinket_grass_loot_mult(trampler)

    # Seeds: 1/(25 - naturalism*4) chance
    seed_chance = 1.0 / max(1, 25 - naturalism * 4) * loot_mult
    if isinstance(trampler, Player) and _trinket_stone_instead_of_seed(trampler):
        from app.engine.entities.items.consumables import Stone as StoneItem
        stone = StoneItem(
            id=str(uuid.uuid4()),
            pos=Position(x=trampler.pos.x, y=trampler.pos.y),
            damage=1, range=5,
        )
        floor.items[stone.id] = stone
    elif random.random() < seed_chance:
        _drop_seed(floor, (trampler.pos.x, trampler.pos.y))

    # Dewdrops: 1/(6 - naturalism/2) chance
    dew_chance = 1.0 / max(1, 6 - naturalism / 2) * loot_mult
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
            if berry_rate > 0 and random.random() < berry_rate * 0.01 * loot_mult:
                _drop_berry(floor, (trampler.pos.x, trampler.pos.y))

    return drops


def press_cell(floor: FloorState, pos: Tuple[int, int], trampler: Optional[Entity] = None, players: Optional[Iterable[Entity]] = None) -> dict:
    result = {
        "tile_changed": False,
        "grass_trampled": False,
        "drops": [],
        "triggered_plant": None,
    }

    tile = floor.grid[pos[1]][pos[0]]

    # --- Trample grass ------------------------------------------------------
    # SPD HighGrass.trample keys off the huntress *class* (any subclass): she
    # furrows high grass instead of flattening it, and furrowed grass survives
    # her steps. Everyone else tramples both down to short grass.
    if tile in (TileType.HIGH_GRASS, TileType.FURROWED_GRASS):
        result["grass_trampled"] = True
        is_huntress = isinstance(trampler, Player) and trampler.class_type == "huntress"

        if tile == TileType.FURROWED_GRASS:
            if not is_huntress:
                floor.grid[pos[1]][pos[0]] = TileType.FLOOR_GRASS
                result["tile_changed"] = True
        else:
            if is_huntress:
                floor.grid[pos[1]][pos[0]] = TileType.FURROWED_GRASS
            else:
                floor.grid[pos[1]][pos[0]] = TileType.FLOOR_GRASS
            result["tile_changed"] = True

        if result["tile_changed"]:
            floor.rebuild_flags()

        # Loot and the Camouflage glyph only trigger on HIGH_GRASS (SPD rolls
        # them in the non-furrowed branch, even when the huntress furrows).
        if tile == TileType.HIGH_GRASS and trampler is not None:
            result["drops"] = roll_grass_loot(floor, trampler)
            _trigger_camouflage(trampler)
            _trigger_rejuvenating_steps(floor, pos, trampler)

    # --- Trigger plant at this cell -----------------------------------------
    # Plant values are runtime dicts ({"pos","plant_type","triggered"}); guard
    # defensively so a stray non-dict value can never crash the game loop.
    plant = floor.plants.get(pos)
    if isinstance(plant, dict) and not plant.get("triggered", False):
        plant["triggered"] = True
        result["triggered_plant"] = plant
        plant_type = plant.get("plant_type", "sungrass")
        if trampler is not None:
            _trigger_plant_effect(floor, pos, plant, trampler, players=players)
        else:
            if plant_type in ("firebloom", "icecap", "sorrowmoss", "blindweed", "stormvine", "rotberry", "blandfruit_bush", "seedpod", "dewcatcher"):
                dummy = type("_PlantDummy", (Entity,), {
                    "pos": Position(x=pos[0], y=pos[1]), "buffs": [], "id": "",
                    "take_damage": lambda self, d: 0, "has_buff": lambda self, b: False,
                    "add_buff": lambda self, *a, **kw: None, "get_total_max_hp": lambda self: 1, "hp": 1,
                })()
                _trigger_plant_effect(floor, pos, plant, dummy, players=players)

        # Uproot/wither plant
        if pos in floor.plants:
            del floor.plants[pos]

        # Lotus aura seed preservation check
        if plant_type not in ("rotberry", "blandfruit_bush", "seedpod", "dewcatcher"):
            for mob in list(getattr(floor, "mobs", {}).values()):
                if getattr(mob, "mob_type", "") == "lotus" and getattr(mob, "is_alive", True):
                    dist = max(abs(pos[0] - mob.pos.x), abs(pos[1] - mob.pos.y))
                    range_val = getattr(mob, "view_distance", 2)
                    if dist <= range_val:
                        wand_lvl = getattr(mob, "_wand_level", 0)
                        seed_chance = min(1.0, 0.20 + 0.08 * wand_lvl)
                        if random.random() < seed_chance:
                            _drop_seed(floor, pos, plant_type)
                        break

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


class PlantEffect:
    """Base strategy for plant activation effects."""
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        pass


class SungrassPlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        is_warden = _is_warden(activator)
        ht = activator.get_total_max_hp() if isinstance(activator, Player) else getattr(activator, "max_hp", getattr(activator, "HT", 20))
        activator.add_buff(
            "sungrass_health",
            duration=999999.0,
            level=ht,
            source_id=None if is_warden else f"{pos[0]},{pos[1]}",
        )


class EarthrootPlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        is_warden = _is_warden(activator)
        if is_warden:
            lvl = getattr(activator, "level", getattr(activator, "lvl", 1))
            activator.add_buff("barkskin", duration=5.0, level=lvl + 5)
        else:
            ht = getattr(activator, "HT", getattr(activator, "max_hp", 20))
            activator.add_buff(
                "earthroot_armor",
                duration=100.0,
                level=ht,
                source_id=f"{pos[0]},{pos[1]}",
            )


class FirebloomPlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        if _is_warden(activator):
            activator.add_buff("fire_imbue", duration=4.5)
        else:
            _explode_fire(floor, pos)


class IcecapPlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        if _is_warden(activator):
            activator.add_buff("frost_imbue", duration=4.5)
        _freeze_area(floor, pos, activator, players=kwargs.get("players"))


class SorrowmossPlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        if _is_warden(activator):
            activator.add_buff("toxic_imbue", duration=4.5)
        else:
            depth = getattr(floor, "floor_id", 1)
            duration = 5.0 + round(2.0 * depth / 3.0)
            activator.add_buff("poison", duration=duration, level=1)


class MageroyalPlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        if _is_warden(activator):
            activator.add_buff("blob_immunity", duration=5.0)
        _cure_debuffs(activator)


class FadeleafPlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        if _is_warden(activator) and getattr(floor, "floor_id", 1) > 1:
            # SPD Fadeleaf warden path: the Warden returns up one depth.
            # The actual floor transition happens in movement.py after the
            # step resolves (player.pending_ascend flag).
            activator.pending_ascend = True
        else:
            _teleport_activator(floor, activator)


class SwiftthistlePlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        if _is_warden(activator):
            activator.add_buff("haste", duration=6.0, level=1)
        activator.add_buff("time_bubble", duration=6.0, level=1)


class BlindweedPlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        if _is_warden(activator):
            activator.add_buff("invisibility", duration=10.0, level=1)
        else:
            activator.add_buff("blindness", duration=10.0, level=1)
            activator.add_buff("cripple", duration=10.0, level=1)


class StormvinePlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        if _is_warden(activator):
            activator.add_buff("levitation", duration=10.0, level=1)
        else:
            activator.add_buff("vertigo", duration=10.0, level=1)


class StarflowerPlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        activator.add_buff("bless", duration=20.0, level=1)
        if _is_warden(activator):
            activator.add_buff("recharging", duration=20.0, level=1)


class RotberryPlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        if _is_warden(activator):
            activator.add_buff("adrenaline_surge", duration=30.0, level=1)
        else:
            _create_gas(floor, pos, 100, "toxic_gas")
        _drop_seed(floor, pos, "rotberry")


class BlandfruitBushPlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        _drop_blandfruit(floor, pos)


class SeedpodPlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        _spawn_seedpod(floor, pos)


class DewcatcherPlantEffect(PlantEffect):
    def activate(self, floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs) -> None:
        _spawn_dewcatcher(floor, pos)


PLANT_REGISTRY: Dict[str, PlantEffect] = {
    "sungrass": SungrassPlantEffect(),
    "earthroot": EarthrootPlantEffect(),
    "firebloom": FirebloomPlantEffect(),
    "icecap": IcecapPlantEffect(),
    "sorrowmoss": SorrowmossPlantEffect(),
    "mageroyal": MageroyalPlantEffect(),
    "dreamfoil": MageroyalPlantEffect(),
    "fadeleaf": FadeleafPlantEffect(),
    "swiftthistle": SwiftthistlePlantEffect(),
    "blindweed": BlindweedPlantEffect(),
    "stormvine": StormvinePlantEffect(),
    "starflower": StarflowerPlantEffect(),
    "rotberry": RotberryPlantEffect(),
    "blandfruit_bush": BlandfruitBushPlantEffect(),
    "seedpod": SeedpodPlantEffect(),
    "dewcatcher": DewcatcherPlantEffect(),
}


def _trigger_plant_effect(floor: FloorState, pos: Tuple[int, int], plant: dict, activator: Entity, **kwargs):
    plant_type = plant.get("plant_type", "sungrass")
    is_warden = _is_warden(activator)

    if is_warden:
        talent_info = getattr(activator, "talent_info", None)
        if talent_info and talent_info.talents.get("natures_aid", 0) > 0:
            pts = talent_info.talents.get("natures_aid", 0)
            duration = (1 + 2 * pts) * 1.0
            activator.add_buff("barkskin", duration=duration, level=2)

    if not isinstance(activator, Player) and plant_type not in ("blandfruit_bush", "seedpod", "dewcatcher"):
        activator.add_buff("hazard_assist_tracker", duration=10.0, level=1)

    effect = PLANT_REGISTRY.get(plant_type)
    if effect is not None:
        effect.activate(floor, pos, plant, activator, **kwargs)


def _drop_blandfruit(floor: FloorState, pos: Tuple[int, int]):
    from app.engine.entities.items.consumables import Blandfruit
    bf = Blandfruit(
        id=str(uuid.uuid4()),
        pos=Position(x=pos[0], y=pos[1]),
    )
    floor.items[bf.id] = bf
    return bf.id


def _plant_adjacent_cells(floor: FloorState, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
    """Passable 8-neighbour cells excluding the level entrance/exit, per
    WandOfRegrowth.Seedpod/Dewcatcher.activate (NEIGHBOURS8 scan)."""
    candidates: List[Tuple[int, int]] = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = pos[0] + dx, pos[1] + dy
            if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                continue
            if floor.flags and not floor.flags.passable[ny][nx]:
                continue
            if (nx, ny) in (floor.entrance_pos, floor.exit_pos):
                continue
            candidates.append((nx, ny))
    return candidates


def _spawn_seedpod(floor: FloorState, pos: Tuple[int, int]):
    """WandOfRegrowth.Seedpod.activate: drop 2-4 random seeds on adjacent
    cells, each candidate used at most once."""
    candidates = _plant_adjacent_cells(floor, pos)
    random.shuffle(candidates)
    for _ in range(min(random.randint(2, 4), len(candidates))):
        _drop_seed(floor, candidates.pop())


def _spawn_dewcatcher(floor: FloorState, pos: Tuple[int, int]):
    """WandOfRegrowth.Dewcatcher.activate: drop 3-6 dewdrops on adjacent
    cells, each candidate used at most once."""
    candidates = _plant_adjacent_cells(floor, pos)
    random.shuffle(candidates)
    for _ in range(min(random.randint(3, 6), len(candidates))):
        _drop_dewdrop(floor, candidates.pop())


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


def _freeze_area(floor: FloorState, pos: Tuple[int, int], activator: Optional[Entity] = None, players: Optional[Iterable[Entity]] = None):
    """Icecap: SPD Freezing blob cellEffect over the plant's 3x3 non-solid area."""
    cells: set = set()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                if floor.flags and floor.flags.solid[ny][nx]:
                    continue
                cells.add((nx, ny))
                tile = floor.grid[ny][nx]
                if tile in (TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.FURROWED_GRASS):
                    floor.grid[ny][nx] = TileType.FLOOR

    def _freeze_duration(ex: int, ey: int) -> float:
        if 0 <= ey < floor.height and 0 <= ex < floor.width:
            if floor.grid[ey][ex] == TileType.FLOOR_WATER:
                return 30.0
        return 10.0

    seen_keys: set = set()
    targets = []
    for m in getattr(floor, "mobs", {}).values():
        if m.is_alive and (m.pos.x, m.pos.y) in cells:
            key = getattr(m, "id", None) or id(m)
            if key not in seen_keys:
                seen_keys.add(key)
                targets.append(m)
    if activator is not None and getattr(activator, "is_alive", True) and (activator.pos.x, activator.pos.y) in cells:
        key = getattr(activator, "id", None) or id(activator)
        if key not in seen_keys:
            seen_keys.add(key)
            targets.append(activator)
    if players is not None:
        for p in players:
            if getattr(p, "is_alive", True) and (p.pos.x, p.pos.y) in cells:
                key = getattr(p, "id", None) or id(p)
                if key not in seen_keys:
                    seen_keys.add(key)
                    targets.append(p)

    for entity in targets:
        dur = _freeze_duration(entity.pos.x, entity.pos.y)
        entity.add_buff("frost", duration=dur, level=1)
        if not isinstance(entity, Player):
            entity.add_buff("hazard_assist_tracker", duration=10.0, level=1)

    for bid in list(floor.blob_areas.keys()):
        b = floor.blob_areas[bid]
        if b.get("type") == "fire":
            b["cells"] = set(b["cells"]) - cells
            for c in list(b.get("volume", {})):
                if c in cells:
                    del b["volume"][c]
            if not b["cells"]:
                del floor.blob_areas[bid]

    for item_id, item in list(floor.items.items()):
        if isinstance(item, MysteryMeat) and (item.pos.x, item.pos.y) in cells:
            floor.items[item_id] = FrozenCarpaccio(
                id=item.id,
                name="Frozen Carpaccio",
                pos=Position(x=item.pos.x, y=item.pos.y),
                quantity=getattr(item, "quantity", 1),
            )

    floor.rebuild_flags()


def _cure_debuffs(entity: Entity):
    entity.cleanse(("poison", "blindness", "bleeding", "weakness", "slow", "cripple", "burning", "chill", "frost"))


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
        break_stationary_plant_buffs(entity)
