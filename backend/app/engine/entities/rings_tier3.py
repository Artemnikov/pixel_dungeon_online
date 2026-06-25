# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# Tier-3 ring subclasses (SPD's mechanics-dependent rings) — Ring of Force,
# Ring of Elements, Ring of Wealth — plus their standalone helpers. Split from
# rings.py to stay under the 400-line limit.
from __future__ import annotations

from typing import ClassVar, Literal, Optional, TYPE_CHECKING

from app.engine.entities.base import Ring
from app.engine.entities.rings import ring_bonus, ring_buffed_bonus

if TYPE_CHECKING:
    from app.engine.entities.base import Player


class RingOfForce(Ring):
    kind: Literal["ring_force"] = "ring_force"
    name: str = "Ring of Force"
    buff_class: str = "force"
    DESC: ClassVar[str] = (
        "This ring channels the wearer's strength into unarmed strikes, "
        "dealing damage as if wielding a weapon."
    )

    def _info_lines(self, player: Optional[Player] = None) -> list[str]:
        lines: list[str] = []
        if player is not None and self.buff_class:
            L = ring_buffed_bonus(player, self.buff_class)
            str_val = player.get_effective_strength()
            tier = _force_tier(str_val)
            if L <= 0:
                tier = 1
            dmin = max(0, round(tier + L))
            dmax = max(0, round(5 * (tier + 1) + L * (tier + 1)))
            lines.append(f"Unarmed damage: {dmin}-{dmax}")
        return lines


class RingOfElements(Ring):
    kind: Literal["ring_elements"] = "ring_elements"
    name: str = "Ring of Elements"
    buff_class: str = "resistance"
    DESC: ClassVar[str] = (
        "This ring provides resistance to elemental and magical effects, "
        "reducing their damage and duration."
    )

    def _info_lines(self, player: Optional[Player] = None) -> list[str]:
        lines: list[str] = []
        if player is not None and self.buff_class:
            L = ring_buffed_bonus(player, self.buff_class)
            pct = (1 - 0.825 ** L) * 100
            lines.append(f"Resistance to elements: {pct:.1f}%")
        return lines


class RingOfWealth(Ring):
    kind: Literal["ring_wealth"] = "ring_wealth"
    name: str = "Ring of Wealth"
    buff_class: str = "wealth"
    DESC: ClassVar[str] = (
        "This ring increases the likelihood of finding better loot from "
        "defeated enemies."
    )

    def _info_lines(self, player: Optional[Player] = None) -> list[str]:
        lines: list[str] = []
        if player is not None and self.buff_class:
            L = ring_buffed_bonus(player, self.buff_class)
            pct = (1.2 ** L - 1) * 100
            lines.append(f"Loot chance bonus: +{pct:.1f}%")
        return lines


# --- RingOfForce: unarmed combat (SPD RingOfForce.java:73-127) ---------------

def _force_tier(str_val: int) -> float:
    """SPD RingOfForce.tier(STR): max(1, (STR-8)/2), capped after 5."""
    tier = max(1, (str_val - 8) / 2)
    if tier > 5:
        tier = 5 + (tier - 5) / 2
    return tier


def using_force(player: Player) -> bool:
    """True if the player has a Ring of Force equipped (any bonus > 0)."""
    return ring_buffed_bonus(player, "force") > 0


def force_damage_range(player: Player) -> tuple[int, int]:
    """SPD RingOfForce.damageRoll: unarmed damage [min, max] based on STR tier
    and ring level. Cursed (L<=0) forces tier=1."""
    L = ring_buffed_bonus(player, "force")
    str_val = player.get_effective_strength()
    tier = _force_tier(str_val)
    if L <= 0:
        tier = 1
    dmin = max(0, round(tier + L))
    dmax = max(0, round(5 * (tier + 1) + L * (tier + 1)))
    return (dmin, dmax)


# --- RingOfElements: status resistance (SPD RingOfElements.java:72-98) -------

# Buff types that Ring of Elements resists (SPD RESISTS set + AntiMagic set).
RESISTS = frozenset({
    "burning", "chill", "frost", "ooze", "paralysis", "poison", "corrosion",
    "toxic_gas", "electricity",
    "magical_sleep", "charm", "weakness", "vulnerable", "hex", "degrade",
})


def resist_multiplier(player: Player, effect_type: str) -> float:
    """SPD RingOfElements.resist: 0.825^L if effect is resistable, else 1.0."""
    if effect_type not in RESISTS:
        return 1.0
    L = ring_buffed_bonus(player, "resistance")
    if L <= 0:
        return 1.0
    return 0.825 ** L


# --- RingOfWealth: drop chance + bonus drops (SPD RingOfWealth.java) ---------

def wealth_drop_multiplier(player: Player) -> float:
    """SPD RingOfWealth.dropChanceMultiplier: 1.2^L."""
    L = ring_buffed_bonus(player, "wealth")
    return 1.2 ** L
