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

from app.engine.entities.base import ItemBase
from app.engine.entities.items.equip import Armor, Artifact, Bow, KindOfWeapon, MeleeWeapon, MissileWeapon, Staff
from app.engine.entities.player import Player
from app.engine.entities.armors.armor_glyphs import CURSE_GLYPHS as _ARMOR_CURSES
from app.engine.entities.weapons.weapon_enchants import CURSES


# Types with a `level` field that Scroll of Upgrade can affect.
UPGRADABLE_TYPES = {
    "weapon",
    "wearable",
    "armor",
    "wand",
    "ring",
    "artifact",
}

# Types Scroll of Identify can reveal (excludes seeds).
IDENTIFIABLE_TYPES = {
    "weapon",
    "wearable",
    "armor",
    "wand",
    "ring",
    "artifact",
    "potion",
    "scroll",
}


def player_inventory_items(player: "Player") -> List["ItemBase"]:
    """Flatten everything a player owns: equipped items + backpack contents
    (recursing into nested bags). Thin wrapper over Belongings.all_items()."""
    return list(player.belongings.all_items())


def is_upgradable(item, game) -> bool:
    """True if `item` is a weapon/armor/wand/ring/artifact with a `level`."""
    if item.type not in UPGRADABLE_TYPES:
        return False
    if not hasattr(item, "level"):
        return False
    return True


def is_unidentified_target(item, game) -> bool:
    """True if `item`'s kind is not yet identified and its type is one
    Scroll of Identify can reveal (weapon/armor/wand/ring/artifact/potion/scroll)."""
    if item.type not in IDENTIFIABLE_TYPES:
        return False
    if item.level_known:
        return False
    return item.kind not in game.identified_kinds


def is_cursed_or_suspect(item, game) -> bool:
    """True if `item` is a weapon/armor/wand/ring/artifact that is cursed or
    has a curse enchant/glyph — items that actually need cleansing."""
    if item.type not in UPGRADABLE_TYPES:
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
    if item.type in ("wearable", "armor"):
        return "armor"
    if item.type == "wand":
        return "wand"
    if item.type == "ring":
        return "ring"
    if item.type == "artifact":
        return "artifact"
    if item.type == "potion":
        return "potion"
    if item.type == "scroll":
        return "scroll"
    if item.type == "seed":
        return "seed"
    if item.type in ("throwable", "stone"):
        return "stone"
    if item.type == "runestone":
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
