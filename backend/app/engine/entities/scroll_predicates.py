"""Target-selection predicates for selector-based scrolls.

Each predicate has the signature ``(item, game) -> bool`` and decides whether
``item`` (one of the player's owned items) is a valid target for a given
scroll kind. ``PREDICATE`` maps a scroll's ``kind`` string to its predicate,
used by ``action_read``/``apply_scroll_target`` (item_actions.py) and
``ItemsMixin.select_scroll_target`` (game/items.py) to build/validate
candidate lists.

Only ``is_upgradable`` (Scroll of Upgrade) is implemented so far. The other
three predicates below are placeholders for later tasks (Identify, Remove
Curse, Transmutation).
"""

from typing import List

from app.engine.entities.base import ItemCategory, ItemBase, Player


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
    """Placeholder for Scroll of Remove Curse (Task 8)."""
    raise NotImplementedError


def is_transmutable(item, game) -> bool:
    """Placeholder for Scroll of Transmutation (Task 9)."""
    raise NotImplementedError


# scroll `kind` -> predicate. Extended by later tasks.
PREDICATE = {
    "scroll_of_upgrade": is_upgradable,
    "scroll_of_identify": is_unidentified_target,
}
