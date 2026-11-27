import random
import time
import uuid
from typing import Dict, List, Optional

from app.engine.entities.base import ItemBase, Position
from app.engine.game.constants import party_loot_multiplier
from app.engine.entities.items.consumables import Gold, GooBlob, Key, KingsCrown, MysteryMeat, PhantomMeat, Seed, TenguMask
from app.engine.entities.items.equip import ClothArmor, LeatherArmor, MailArmor, make_named_melee_weapon, PlateArmor, ScaleArmor
from app.engine.entities.items.potions import HealthPotion, Potion
from app.engine.entities.player import DropEntry, Mob
from app.engine.entities.weapons.weapon_enchants import roll_weapon_level, roll_weapon_enchant
from app.engine.entities.armors.armor_glyphs import roll_armor_glyph

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

# Party-size loot scaling applies only to potion/scroll kinds (see
# party_loot_multiplier) -- other loot (gold, weapons, armor, quest items)
# is left at its solo rate.
_PARTY_SCALED_KINDS = {"potion", "health_potion", "scroll", "scorpio_potion"}

# SPD Generator.Category SEED / STONE classes with their defaultProbs, for
# Generator.randomUsingDefaults(category).
_SEED_DEFAULTS = (
    ("rotberry_seed", 0), ("sungrass_seed", 2), ("fadeleaf_seed", 2), ("icecap_seed", 2),
    ("firebloom_seed", 2), ("sorrowmoss_seed", 2), ("swiftthistle_seed", 2),
    ("blindweed_seed", 2), ("stormvine_seed", 2), ("earthroot_seed", 2),
    ("mageroyal_seed", 2), ("starflower_seed", 1),
)
_STONE_DEFAULTS = (
    ("stone_enchantment", 0), ("stone_intuition", 2), ("stone_detect_magic", 2),
    ("stone_flock", 2), ("stone_shock", 2), ("stone_blink", 2), ("stone_deep_sleep", 2),
    ("stone_clairvoyance", 2), ("stone_aggression", 2), ("stone_blast", 2),
    ("stone_fear", 2), ("stone_augmentation", 0),
)


def _random_using_defaults(table) -> Optional[ItemBase]:
    from app.engine.entities.items.catalog import make_catalog_item
    kinds = [k for k, _ in table]
    weights = [w for _, w in table]
    return make_catalog_item(kinds[_weighted_choice(weights)])


def _make_items(item_kind: str) -> List[ItemBase]:
    """Kinds whose SPD createLoot() yields something other than one item."""
    if item_kind == "eye_loot":
        # Eye.createLoot: Random.Int(4) -> 0/1 a dewdrop plus a second one
        # dropped beside it, 2 a seed, 3 a runestone (randomUsingDefaults).
        roll = random.randint(0, 3)
        if roll <= 1:
            from app.engine.entities.items.consumables import Dewdrop
            return [Dewdrop(), Dewdrop()]
        item = _random_using_defaults(_SEED_DEFAULTS if roll == 2 else _STONE_DEFAULTS)
        return [item] if item is not None else []
    item = _make_item(item_kind)
    return [item] if item is not None else []


def roll_drops(
    mob: Mob,
    drop_counters: Dict[str, int],
    death_x: int,
    death_y: int,
    players: Optional[List] = None,
) -> List[ItemBase]:
    items: List[ItemBase] = []
    party_mult = 1.0
    if players:
        alive_n = sum(1 for p in players if getattr(p, "is_alive", True))
        party_mult = party_loot_multiplier(alive_n)

    for entry in mob.loot_table:
        if entry.max_global > 0 and drop_counters.get(entry.item_kind, 0) >= entry.max_global:
            continue
        # chance can exceed 1.0 once party-scaled; each whole point is a
        # guaranteed copy and the remainder is one more Bernoulli trial (same
        # accumulator idiom as the CrackedSpyglass bonus below).
        chance = entry.chance * party_mult if entry.item_kind in _PARTY_SCALED_KINDS else entry.chance
        if entry.decay_key is not None:
            chance *= (1.0 / 3.0) ** drop_counters.get(entry.decay_key, 0)
        count = 0
        while chance > 0:
            if random.random() < min(chance, 1.0):
                count += 1
            chance -= 1.0
        if count == 0:
            continue
        if entry.item_kind == "tengu_mask" and players:
            if not any(p.subclass_info.subclass is None for p in players):
                continue
        for _ in range(count):
            for item in _make_items(entry.item_kind):
                item.id = str(uuid.uuid4())
                item.pos = Position(x=death_x, y=death_y)
                items.append(item)
        if entry.max_global > 0:
            drop_counters[entry.item_kind] = drop_counters.get(entry.item_kind, 0) + count
        if entry.decay_key is not None:
            drop_counters[entry.decay_key] = drop_counters.get(entry.decay_key, 0) + 1

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
            from app.engine.entities.rings.ring_mechanics import wealth_drop_multiplier
            mult = wealth_drop_multiplier(p)
            if mult > 1.0:
                bonus = _wealth_bonus_drop(p, death_x, death_y)
                items.extend(bonus)

    # CrackedSpyglass trinket: extra loot chance from defeated enemies
    if players:
        for p in players:
            from app.engine.entities.trinkets import CrackedSpyglass as _CS
            from app.engine.entities.trinkets import trinket_level
            cs_lvl = trinket_level(p, "cracked_spyglass")
            if cs_lvl >= 0:
                chance = _CS.extra_loot_chance(cs_lvl)
                while chance > 0:
                    if random.random() < min(chance, 1.0):
                        bonus_item = _random_wealth_consumable()
                        if bonus_item:
                            bonus_item.id = str(uuid.uuid4())
                            bonus_item.pos = Position(x=death_x, y=death_y)
                            items.append(bonus_item)
                    chance -= 1.0

    # ShardOfOblivion trinket: loot multiplier based on worn unidentified items
    if players:
        for p in players:
            from app.engine.entities.trinkets import ShardOfOblivion as _SO
            from app.engine.entities.trinkets import trinket_level
            so_lvl = trinket_level(p, "shard_of_oblivion")
            if so_lvl >= 0:
                worn_un_id = p.count_worn_unidentified()
                mult = _SO.loot_chance_multiplier(so_lvl, worn_un_id)
                if mult > 1.0:
                    for existing in items[:]:
                        if random.random() < mult - 1.0:
                            dup = _make_item(getattr(existing, "kind", "gold"))
                            if dup:
                                dup.id = str(uuid.uuid4())
                                dup.pos = Position(x=death_x, y=death_y)
                                items.append(dup)

    now = time.time()
    for it in items:
        it.dropped_at = now
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
        return Seed(plant_type="sungrass")
    elif item_kind == "gold":
        return Gold(name="Gold", quantity=random.randint(5, 20))
    elif item_kind == "health_potion":
        return HealthPotion()
    elif item_kind == "mystery_meat":
        return MysteryMeat()
    elif item_kind == "phantom_meat":
        return PhantomMeat()
    elif item_kind == "tier2_weapon":
        return _random_dungeon_weapon(random.choice(TIER2_WEAPONS))
    elif item_kind == "weapon":
        return _random_dungeon_weapon(random.choice(RANDOM_WEAPONS))
    elif item_kind == "armor":
        cls = random.choice(RANDOM_ARMORS)
        a = cls()
        glyph, cursed = roll_armor_glyph()
        if glyph:
            a.enchantment.type = glyph
        a.cursed = cursed
        return a
    elif item_kind == "potion":
        effect = random.choice(RANDOM_POTIONS)
        return Potion(name="Potion", effect=effect)
    elif item_kind == "scorpio_potion":
        # Scorpio.createLoot: Random.oneOf(POTION.classes), never Healing or Strength.
        from app.engine.game.spd_adapter import POTION_CLASS_BY_INDEX
        from app.engine.entities.items.potions import HealthPotion as _Heal
        pool = [c for c in POTION_CLASS_BY_INDEX if c is not _Heal and c.__name__ != "PotionOfStrength"]
        return random.choice(pool)()
    elif item_kind == "goo_blob":
        return GooBlob()
    elif item_kind == "tengu_mask":
        return TenguMask(name="Tengu's Mask")
    elif item_kind == "kings_crown":
        return KingsCrown(name="King's Crown")
    elif item_kind == "metal_shard":
        from app.engine.entities.items.bombs import MetalShard
        return MetalShard()
    return None


def _random_dungeon_weapon(name: str) -> ItemBase:
    weapon = make_named_melee_weapon(name)
    weapon.level = roll_weapon_level()
    enchant, cursed = roll_weapon_enchant()
    weapon.enchantment = enchant
    weapon.cursed = cursed
    return weapon
