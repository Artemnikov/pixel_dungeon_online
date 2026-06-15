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

from app.engine.entities.base import (
    Bow, ItemCategory, ItemBase, MeleeWeapon, MissileWeapon, Player, Staff,
)
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
    return item.kind not in game.identified_kinds


def is_cursed_or_suspect(item, game) -> bool:
    """True if `item` is a weapon/armor/wand/ring/artifact that is known to be
    cursed, has a curse enchant/glyph, or whose curse status is unknown."""
    if item.category not in UPGRADABLE_CATEGORIES:
        return False
    if item.cursed:
        return True
    if not item.cursed_known:
        return True
    enchantment = getattr(item, "enchantment", None)
    if isinstance(enchantment, str) and enchantment in CURSES:
        return True
    # Armor curse-enchant generation isn't implemented yet (enchantment.type
    # is always "none"), but this stays forward-compatible once it lands.
    if hasattr(enchantment, "type") and enchantment.type in CURSES:
        return True
    return False


def transmute_group(item) -> Optional[str]:
    """Classifies `item` into one of Scroll of Transmutation's broad groups,
    or None if it isn't transmutable. See TRANSMUTE_GROUPS in item_catalog.py
    for the catalog kinds belonging to each group."""
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
    if item.category == ItemCategory.POTION:
        return "potion"
    if item.category == ItemCategory.SCROLL:
        return "scroll"
    return None


def is_transmutable(item, game) -> bool:
    """True if `item` can be transmuted by Scroll of Transmutation: not the
    transmutation scroll itself, and belongs to a known transmute group."""
    if item.kind == "scroll_of_transmutation":
        return False
    return transmute_group(item) is not None


# scroll `kind` -> predicate. Extended by later tasks.
PREDICATE = {
    "scroll_of_upgrade": is_upgradable,
    "scroll_of_identify": is_unidentified_target,
    "scroll_of_remove_curse": is_cursed_or_suspect,
    "scroll_of_transmutation": is_transmutable,
}
