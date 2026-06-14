import random
import uuid
from typing import Dict, List, Optional

from app.engine.entities.base import (
    DropEntry,
    ItemBase,
    Mob,
    Position,
    Seed,
    Gold,
    HealthPotion,
    MysteryMeat,
    make_named_melee_weapon,
    Armor,
    Potion,
    Key,
    TenguMask,
    KingsCrown,
    GooBlob,
)
from app.engine.entities.weapon_enchants import roll_weapon_level, roll_weapon_enchant

TIER2_WEAPONS = [
    "Sword",
    "War Hammer",
    "Battle Axe",
]

RANDOM_WEAPONS = [
    "Worn Shortsword",
    "Dagger",
    "Gloves",
    "Rapier",
    "Cudgel",
    "Shortsword",
]

RANDOM_ARMORS = [
    ("Cloth Armor", 1, 10),
    ("Leather Armor", 2, 12),
    ("Mail Armor", 3, 14),
    ("Scale Armor", 4, 16),
    ("Plate Armor", 5, 18),
]

RANDOM_POTIONS = [
    "regen",
    "heal",
]


def roll_drops(
    mob: Mob,
    drop_counters: Dict[str, int],
    death_x: int,
    death_y: int,
    players: Optional[List] = None,
) -> List[ItemBase]:
    items: List[ItemBase] = []
    for entry in mob.loot_table:
        if entry.max_global > 0 and drop_counters.get(entry.item_kind, 0) >= entry.max_global:
            continue
        if random.random() >= entry.chance:
            continue
        if entry.item_kind == "tengu_mask" and players:
            if not any(p.subclass_info.subclass is None for p in players):
                continue
        item = _make_item(entry.item_kind)
        if item is None:
            continue
        item.id = str(uuid.uuid4())
        item.pos = Position(x=death_x, y=death_y)
        items.append(item)
        if entry.max_global > 0:
            drop_counters[entry.item_kind] = drop_counters.get(entry.item_kind, 0) + 1

    for wd in mob.weighted_drops:
        if wd.max_global > 0 and drop_counters.get(wd.item_kind, 0) >= wd.max_global:
            continue
        count = wd.base_count + _weighted_choice(wd.weights)
        for _ in range(count):
            item = _make_item(wd.item_kind)
            if item is None:
                continue
            item.id = str(uuid.uuid4())
            item.pos = Position(x=death_x, y=death_y)
            items.append(item)
        if wd.max_global > 0:
            drop_counters[wd.item_kind] = drop_counters.get(wd.item_kind, 0) + count

    return items


def _weighted_choice(weights: List[float]) -> int:
    # Mirrors SPD's Random.chances(): pick index i with probability
    # weights[i] / sum(weights).
    total = sum(weights)
    r = random.random() * total
    acc = 0.0
    for i, w in enumerate(weights):
        acc += w
        if r < acc:
            return i
    return len(weights) - 1


def _make_item(item_kind: str) -> Optional[ItemBase]:
    if item_kind == "seed":
        return Seed(name="Seed of Sunlight")
    elif item_kind == "gold":
        return Gold(name="Gold", quantity=random.randint(5, 20))
    elif item_kind == "health_potion":
        return HealthPotion()
    elif item_kind == "mystery_meat":
        return MysteryMeat()
    elif item_kind == "tier2_weapon":
        return _random_dungeon_weapon(random.choice(TIER2_WEAPONS))
    elif item_kind == "weapon":
        return _random_dungeon_weapon(random.choice(RANDOM_WEAPONS))
    elif item_kind == "armor":
        name, tier, str_req = random.choice(RANDOM_ARMORS)
        return Armor(name=name, tier=tier, strength_requirement=str_req)
    elif item_kind == "potion":
        effect = random.choice(RANDOM_POTIONS)
        return Potion(name="Potion", effect=effect)
    elif item_kind == "goo_blob":
        return GooBlob()
    elif item_kind == "tengu_mask":
        return TenguMask(name="Tengu's Mask")
    elif item_kind == "kings_crown":
        return KingsCrown(name="King's Crown")
    return None


def _random_dungeon_weapon(name: str) -> ItemBase:
    weapon = make_named_melee_weapon(name)
    weapon.level = roll_weapon_level()
    enchant, cursed = roll_weapon_enchant()
    weapon.enchantment = enchant
    weapon.cursed = cursed
    return weapon
