import random
import uuid
from typing import Dict, List, Optional

from app.engine.entities.base import (
    ClothArmor,
    DropEntry,
    Gold,
    GooBlob,
    HealthPotion,
    ItemBase,
    Key,
    KingsCrown,
    LeatherArmor,
    MailArmor,
    make_named_melee_weapon,
    Mob,
    MysteryMeat,
    PlateArmor,
    Position,
    Potion,
    ScaleArmor,
    Seed,
    TenguMask,
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
    ClothArmor,
    LeatherArmor,
    MailArmor,
    ScaleArmor,
    PlateArmor,
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

    # Ring of Wealth bonus drops (SPD RingOfWealth.genConsumableDrop)
    if players:
        for p in players:
            from app.engine.entities.rings_tier3 import wealth_drop_multiplier
            mult = wealth_drop_multiplier(p)
            if mult > 1.0:
                bonus = _wealth_bonus_drop(p, death_x, death_y)
                items.extend(bonus)

    return items


def _wealth_bonus_drop(player, x: int, y: int) -> List[ItemBase]:
    """SPD RingOfWealth: accumulated tries → bonus consumable drops."""
    from app.engine.entities.rings import ring_buffed_bonus
    L = ring_buffed_bonus(player, "wealth")
    if L <= 0:
        return []
    player.wealth_tries_to_drop += L
    bonus: List[ItemBase] = []
    while player.wealth_tries_to_drop >= 3:
        player.wealth_tries_to_drop -= 3
        if random.random() < 0.5 + 0.05 * L:
            item = _random_wealth_consumable()
            if item:
                item.id = str(uuid.uuid4())
                item.pos = Position(x=x, y=y)
                bonus.append(item)
    return bonus


def _random_wealth_consumable() -> Optional[ItemBase]:
    kind = random.choice(["seed", "health_potion", "mystery_meat", "potion"])
    return _make_item(kind)


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
        cls = random.choice(RANDOM_ARMORS)
        return cls()
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
