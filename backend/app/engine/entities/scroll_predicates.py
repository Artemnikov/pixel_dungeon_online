"""Target-selection predicates for selector-based scrolls.

Each predicate has the signature ``(item, game) -> bool`` and decides whether
``item`` (one of the player's owned items) is a valid target for a given
scroll kind. ``PREDICATE`` maps a scroll's ``kind`` string to its predicate,
used by ``action_read``/``apply_scroll_target`` (item_actions.py) and
``ItemsMixin.select_scroll_target`` (game/items.py) to build/validate
candidate lists.

``is_transmutable`` (Scroll of Transmutation) classifies items into "transmute
groups" via ``transmute_group``; the other predicates (Upgrade, Identify,
Remove Curse) are also implemented.
"""

from typing import List, Optional

from app.engine.entities.base import ItemCategory, ItemBase
from app.engine.entities.items_consumable import Seed, Stone
from app.engine.entities.items_equip import Armor, Artifact, Bow, KindOfWeapon, MeleeWeapon, MissileWeapon, Staff
from app.engine.entities.player import Player
from app.engine.entities.armor_glyphs import CURSE_GLYPHS as _ARMOR_CURSES
from app.engine.entities.weapon_enchants import CURSES


# Categories with a `level` field that Scroll of Upgrade can affect.
UPGRADABLE_CATEGORIES = {
    ItemCategory.WEAPON,
    ItemCategory.ARMOR,
    ItemCategory.WAND,
    ItemCategory.RING,
    ItemCategory.ARTIFACT,
}

# Categories Scroll of Identify can reveal (excludes seeds).
IDENTIFIABLE_CATEGORIES = {
    ItemCategory.WEAPON,
    ItemCategory.ARMOR,
    ItemCategory.WAND,
    ItemCategory.RING,
    ItemCategory.ARTIFACT,
    ItemCategory.POTION,
    ItemCategory.SCROLL,
}


def player_inventory_items(player: "Player") -> List["ItemBase"]:
    """Flatten everything a player owns: equipped items + backpack contents
    (recursing into nested bags). Thin wrapper over Belongings.all_items()."""
    return list(player.belongings.all_items())


def is_upgradable(item, game) -> bool:
    """True if `item` is a weapon/armor/wand/ring/artifact with a `level`."""
    if item.category not in UPGRADABLE_CATEGORIES:
        return False
    if not hasattr(item, "level"):
        return False
    return True


def is_unidentified_target(item, game) -> bool:
    """True if `item`'s kind is not yet identified and its category is one
    Scroll of Identify can reveal (weapon/armor/wand/ring/artifact/potion/scroll)."""
    if item.category not in IDENTIFIABLE_CATEGORIES:
        return False
    if item.level_known:
        return False
    return item.kind not in game.identified_kinds


def is_cursed_or_suspect(item, game) -> bool:
    """True if `item` is a weapon/armor/wand/ring/artifact that is cursed or
    has a curse enchant/glyph — items that actually need cleansing."""
    if item.category not in UPGRADABLE_CATEGORIES:
        return False
    if item.cursed:
        return True
    enchantment = getattr(item, "enchantment", None)
    curse_pool = CURSES + _ARMOR_CURSES
    if isinstance(enchantment, str) and enchantment in curse_pool:
        return True
    if hasattr(enchantment, "type") and enchantment.type in curse_pool:
        return True
    return False


def transmute_group(item) -> Optional[str]:
    """Classifies `item` into one of Scroll of Transmutation's broad groups,
    or None if it isn't transmutable. See TRANSMUTE_GROUPS in item_catalog.py
    for the catalog kinds belonging to each group."""
    # Staff is grouped with melee weapons: there's no separate "magic weapon"
    # transmute pool in this codebase.
    if isinstance(item, (MeleeWeapon, Staff)):
        return "weapon_melee"
    if isinstance(item, (Bow, MissileWeapon)):
        return "weapon_missile"
    if item.category == ItemCategory.ARMOR:
        return "armor"
    if item.category == ItemCategory.WAND:
        return "wand"
    if item.category == ItemCategory.RING:
        return "ring"
    if item.category == ItemCategory.ARTIFACT:
        return "artifact"
    if item.category == ItemCategory.POTION:
        return "potion"
    if item.category == ItemCategory.SCROLL:
        return "scroll"
    if item.category == ItemCategory.SEED:
        return "seed"
    if item.category == ItemCategory.STONE:
        return "stone"
    if item.category == ItemCategory.RUNESTONE:
        return "runestone"
    return None


def is_transmutable(item, game) -> bool:
    """True if `item` can be transmuted by Scroll of Transmutation: not the
    transmutation scroll itself, and belongs to a known transmute group."""
    if item.kind == "scroll_of_transmutation":
        return False
    return transmute_group(item) is not None


def _is_enchantable(item, game) -> bool:
    """True if `item` is a weapon or armor that can receive an enchant/glyph."""
    return isinstance(item, (KindOfWeapon, Armor))


# scroll `kind` -> predicate. Extended by later tasks.
PREDICATE = {
    "scroll_of_upgrade": is_upgradable,
    "scroll_of_identify": is_unidentified_target,
    "scroll_of_remove_curse": is_cursed_or_suspect,
    "scroll_of_transmutation": is_transmutable,
    "scroll_of_enchantment": _is_enchantable,
    "scroll_of_exotic_enchantment": _is_enchantable,
}
