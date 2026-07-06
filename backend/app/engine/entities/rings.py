# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
"""Ring subclasses and bonus helpers, ported from SPD's items/rings/.

SPD uses a RingBuff actor attached to the Char. This codebase has no buff-actor
system, so instead we scan the player's `ring` + `misc` equip slots directly
via `ring_bonus()` / `ring_buffed_bonus()`.

Each ring subclass sets `buff_class` to a unique string (e.g. "accuracy").
The helper functions sum `solo_bonus()` across both slots for rings whose
`buff_class` matches.

Reference: docs/spd_items/03-rings-artifacts.md §1-2
"""
from __future__ import annotations

import random as _random
from typing import TYPE_CHECKING, ClassVar, Literal, Optional

from app.engine.entities.items_equip import Ring

if TYPE_CHECKING:
    from app.engine.entities.player import Player


# --- core bonus helpers (SPD Ring.java:357-404) ------------------------------

def solo_bonus(ring: Ring) -> int:
    """SPD Ring.soloBonus(): cursed -> min(0, level-2), else level+1."""
    if ring.cursed:
        return min(0, ring.level - 2)
    return ring.level + 1


def solo_buffed_bonus(ring: Ring) -> int:
    """SPD Ring.soloBuffedBonus(): same as solo_bonus but using buffedLvl.
    Currently buffedLvl == level (EnhancedRings buff not yet implemented)."""
    lvl = ring.level  # future: +1 if EnhancedRings buff
    if ring.cursed:
        return min(0, lvl - 2)
    return lvl + 1


def ring_bonus(player: "Player", buff_class: str) -> int:
    """SPD Ring.getBonus(target, RingBuffClass): sum of solo_bonus() across
    all equipped rings with matching buff_class. Returns 0 if MagicImmune."""
    if player.has_buff("magic_immune"):
        return 0
    total = 0
    for slot in ("ring", "misc"):
        ring = getattr(player.belongings, slot, None)
        if isinstance(ring, Ring) and ring.buff_class == buff_class:
            total += solo_bonus(ring)
    return total


def ring_buffed_bonus(player: "Player", buff_class: str) -> int:
    """SPD Ring.getBuffedBonus(target, RingBuffClass): sum of solo_buffed_bonus()
    across all equipped rings with matching buff_class. Returns 0 if MagicImmune."""
    if player.has_buff("magic_immune"):
        return 0
    total = 0
    for slot in ("ring", "misc"):
        ring = getattr(player.belongings, slot, None)
        if isinstance(ring, Ring) and ring.buff_class == buff_class:
            total += solo_buffed_bonus(ring)
    return total


def random_ring() -> Ring:
    """SPD Ring.random(): +0=66.67%, +1=26.67%, +2=6.67%; 30% cursed."""
    ring = Ring(name="Ring")
    n = 0
    if _random.randint(0, 2) == 0:
        n += 1
        if _random.randint(0, 4) == 0:
            n += 1
    ring.level = n
    if _random.random() < 0.3:
        ring.cursed = True
    return ring


# --- ring subclasses ---------------------------------------------------------

class RingOfAccuracy(Ring):
    kind: Literal["ring_accuracy"] = "ring_accuracy"
    name: str = "Ring of Accuracy"
    buff_class: str = "accuracy"
    DESC: ClassVar[str] = (
        "This ring increases the accuracy of the wearer, allowing them to "
        "hit targets more reliably."
    )

    def _info_lines(self, player: Optional["Player"] = None) -> list[str]:
        lines: list[str] = []
        if player is not None and self.buff_class:
            L = ring_buffed_bonus(player, self.buff_class)
            pct = (1.3 ** L - 1) * 100
            lines.append(f"Accuracy bonus: +{pct:.1f}%")
        return lines


class RingOfEvasion(Ring):
    kind: Literal["ring_evasion"] = "ring_evasion"
    name: str = "Ring of Evasion"
    buff_class: str = "evasion"
    DESC: ClassVar[str] = (
        "This ring increases the evasion of the wearer, making them harder to hit."
    )

    def _info_lines(self, player: Optional["Player"] = None) -> list[str]:
        lines: list[str] = []
        if player is not None and self.buff_class:
            L = ring_buffed_bonus(player, self.buff_class)
            pct = (1.125 ** L - 1) * 100
            lines.append(f"Evasion bonus: +{pct:.1f}%")
        return lines


class RingOfHaste(Ring):
    kind: Literal["ring_haste"] = "ring_haste"
    name: str = "Ring of Haste"
    buff_class: str = "haste"
    DESC: ClassVar[str] = (
        "This ring increases the movement speed of the wearer, allowing them "
        "to move faster."
    )

    def _info_lines(self, player: Optional["Player"] = None) -> list[str]:
        lines: list[str] = []
        if player is not None and self.buff_class:
            L = ring_buffed_bonus(player, self.buff_class)
            pct = (1.175 ** L - 1) * 100
            lines.append(f"Movement speed bonus: +{pct:.1f}%")
        return lines


class RingOfFuror(Ring):
    kind: Literal["ring_furor"] = "ring_furor"
    name: str = "Ring of Furor"
    buff_class: str = "furor"
    DESC: ClassVar[str] = (
        "This ring increases the attack speed of the wearer, allowing them "
        "to strike more rapidly."
    )

    def _info_lines(self, player: Optional["Player"] = None) -> list[str]:
        lines: list[str] = []
        if player is not None and self.buff_class:
            L = ring_buffed_bonus(player, self.buff_class)
            pct = (1.09051 ** L - 1) * 100
            lines.append(f"Attack speed bonus: +{pct:.1f}%")
        return lines


class RingOfMight(Ring):
    kind: Literal["ring_might"] = "ring_might"
    name: str = "Ring of Might"
    buff_class: str = "might"
    DESC: ClassVar[str] = (
        "This ring increases the strength and maximum health of the wearer."
    )

    def on_equip(self, player: "Player") -> None:
        old_max = player.get_total_max_hp()
        player.max_hp = int(player.max_hp * might_ht_multiplier(player))
        player.hp += player.get_total_max_hp() - old_max

    def on_unequip(self, player: "Player") -> None:
        player.max_hp = int(player.max_hp / might_ht_multiplier(player))
        player.hp = min(player.hp, player.get_total_max_hp())

    def _info_lines(self, player: Optional["Player"] = None) -> list[str]:
        lines: list[str] = []
        if player is not None and self.buff_class:
            from app.engine.entities.rings import ring_bonus
            str_bonus = ring_bonus(player, self.buff_class)
            L = ring_buffed_bonus(player, self.buff_class)
            ht_pct = (1.035 ** L - 1) * 100
            lines.append(f"Strength bonus: +{str_bonus}")
            lines.append(f"Max HP bonus: +{ht_pct:.1f}%")
        return lines


class RingOfTenacity(Ring):
    kind: Literal["ring_tenacity"] = "ring_tenacity"
    name: str = "Ring of Tenacity"
    buff_class: str = "tenacity"
    DESC: ClassVar[str] = (
        "This ring reduces damage taken as the wearer's health decreases."
    )

    def _info_lines(self, player: Optional["Player"] = None) -> list[str]:
        lines: list[str] = []
        if player is not None and self.buff_class:
            L = ring_buffed_bonus(player, self.buff_class)
            pct = (1 - 0.85 ** L) * 100
            lines.append(f"Max damage reduction at low HP: {pct:.1f}%")
        return lines


class RingOfEnergy(Ring):
    kind: Literal["ring_energy"] = "ring_energy"
    name: str = "Ring of Energy"
    buff_class: str = "energy"
    DESC: ClassVar[str] = (
        "This ring increases the recharge speed of wands and artifacts."
    )

    def _info_lines(self, player: Optional["Player"] = None) -> list[str]:
        lines: list[str] = []
        if player is not None and self.buff_class:
            L = ring_buffed_bonus(player, self.buff_class)
            pct = (1.175 ** L - 1) * 100
            lines.append(f"Recharge speed bonus: +{pct:.1f}%")
        return lines


class RingOfArcana(Ring):
    kind: Literal["ring_arcana"] = "ring_arcana"
    name: str = "Ring of Arcana"
    buff_class: str = "arcana"
    DESC: ClassVar[str] = (
        "This ring increases the power and activation chance of weapon "
        "enchantments and armor glyphs."
    )

    def _info_lines(self, player: Optional["Player"] = None) -> list[str]:
        lines: list[str] = []
        if player is not None and self.buff_class:
            L = ring_buffed_bonus(player, self.buff_class)
            pct = (1.175 ** L - 1) * 100
            lines.append(f"Enchantment power bonus: +{pct:.1f}%")
        return lines


class RingOfSharpshooting(Ring):
    kind: Literal["ring_sharpshooting"] = "ring_sharpshooting"
    name: str = "Ring of Sharpshooting"
    buff_class: str = "aim"
    DESC: ClassVar[str] = (
        "This ring increases the damage of projectile weapons and slows "
        "their durability loss."
    )

    def _info_lines(self, player: Optional["Player"] = None) -> list[str]:
        lines: list[str] = []
        if player is not None and self.buff_class:
            from app.engine.entities.rings import ring_bonus, ring_buffed_bonus
            dmg = ring_buffed_bonus(player, self.buff_class)
            dur_L = ring_bonus(player, self.buff_class)
            dur_pct = (1.2 ** dur_L - 1) * 100
            lines.append(f"Projectile damage bonus: +{dmg}")
            lines.append(f"Durability bonus: +{dur_pct:.1f}%")
        return lines


# --- effect multipliers (imported by combat/movement/etc.) -------------------

def accuracy_multiplier(player: "Player") -> float:
    """SPD RingOfAccuracy: accuracy *= 1.3^L."""
    L = ring_buffed_bonus(player, "accuracy")
    return 1.3 ** L


def evasion_multiplier(player: "Player") -> float:
    """SPD RingOfEvasion: evasion *= 1.125^L."""
    L = ring_buffed_bonus(player, "evasion")
    return 1.125 ** L


def haste_multiplier(player: "Player") -> float:
    """SPD RingOfHaste: move speed *= 1.175^L."""
    L = ring_buffed_bonus(player, "haste")
    return 1.175 ** L


def furor_multiplier(player: "Player") -> float:
    """SPD RingOfFuror: attack speed *= 1.09051^L."""
    L = ring_buffed_bonus(player, "furor")
    return 1.09051 ** L


def might_str_bonus(player: "Player") -> int:
    """SPD RingOfMight: strengthBonus = unbuffed ring_bonus."""
    return ring_bonus(player, "might")


def might_ht_multiplier(player: "Player") -> float:
    """SPD RingOfMight: HTMultiplier = 1.035^L (buffed bonus)."""
    L = ring_buffed_bonus(player, "might")
    return 1.035 ** L


def tenacity_multiplier(player: "Player") -> float:
    """SPD RingOfTenacity: damage *= 0.85^(L*(HT-HP)/HT)."""
    L = ring_buffed_bonus(player, "tenacity")
    if L <= 0:
        return 1.0
    max_hp = player.get_total_max_hp()
    if max_hp <= 0:
        return 1.0
    hp_ratio = (max_hp - player.hp) / max_hp
    return 0.85 ** (L * hp_ratio)


def energy_wand_multiplier(player: "Player") -> float:
    """SPD RingOfEnergy: wand recharge *= 1.175^L."""
    L = ring_buffed_bonus(player, "energy")
    return 1.175 ** L


def arcana_multiplier(player: "Player") -> float:
    """SPD RingOfArcana: enchant proc chance *= 1.175^L."""
    L = ring_buffed_bonus(player, "arcana")
    return 1.175 ** L


def sharpshooting_damage_bonus(player: "Player") -> int:
    """SPD RingOfSharpshooting: +flat damage to projectiles = buffed bonus."""
    return ring_buffed_bonus(player, "aim")
