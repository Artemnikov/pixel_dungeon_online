# Copyright (C) 2026 ArtemNikov
#
"""Polymorphic Cleric Subclass Strategy Hierarchy.

Priest and Paladin tweak the shared cleric kit in a handful of places (free
Guiding Light casts for Priests, larger Holy Weapon/Holy Ward bonuses for
Paladins, subclass-exclusive tier-3 spells, and Priests applying Illuminated
to enemies). Each spell used to branch on `subclass == PRIEST/PALADIN`
inline; the strategy hierarchy replaces those checks with virtual hooks.
Mirrors DuelistSubclassStrategy (see duelist.py).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.engine.entities.subclasses import Subclass
from app.engine.entities.player import Player


def _resolve_subclass(player: Player) -> Optional[str]:
    if hasattr(player, "subclass_info") and player.subclass_info is not None:
        return player.subclass_info.subclass
    return getattr(player, "subclass", None)


class ClericSubclassStrategy:
    """Base (no subclass) Cleric behavior. Subclasses override the hooks that
    actually differ between Priest and Paladin."""

    # Spell ids gated behind this subclass (Radiance for Priest, Smite for
    # Paladin). The base strategy gates none.
    exclusive_spells: frozenset = frozenset()

    def guiding_light_is_free(self, player: Player) -> bool:
        """True when the next Guiding Light cast costs 0 charges."""
        return False

    def mark_guiding_light_used(self, player: Player) -> None:
        """Called after a free Guiding Light cast so the subclass may arm its
        cooldown (Priest: 50s before the next free cast)."""

    def holy_weapon_bonus(self) -> int:
        """Extra magic damage granted by Holy Weapon."""
        return 2

    def holy_ward_bonus(self) -> int:
        """Damage blocked granted by Holy Ward."""
        return 1

    def illuminate(self, game: Any, player: Player, target: Any) -> None:
        """Apply subclass-specific effects to a hostile target on holy hit
        (Priest: Illuminated; base: nothing)."""

    def extends_auras_on_cast(self, player: Player) -> bool:
        """True when casting any other spell also extends active Holy Weapon
        and Holy Ward timers (Paladin engine)."""
        return False

    def unlocks(self, spell_id: str) -> bool:
        return spell_id in self.exclusive_spells


class BaseClericStrategy(ClericSubclassStrategy):
    """Default behavior for a Cleric that has not (yet) chosen a subclass."""


class PriestStrategy(ClericSubclassStrategy):
    exclusive_spells = frozenset({"radiance"})

    def guiding_light_is_free(self, player: Player) -> bool:
        return getattr(player, "guiding_light_priest_cd", 0.0) <= 0

    def mark_guiding_light_used(self, player: Player) -> None:
        player.guiding_light_priest_cd = 50.0

    def illuminate(self, game: Any, player: Player, target: Any) -> None:
        target.add_buff("illuminated", duration=50.0)


class PaladinStrategy(ClericSubclassStrategy):
    exclusive_spells = frozenset({"smite"})

    def holy_weapon_bonus(self) -> int:
        return 6

    def holy_ward_bonus(self) -> int:
        return 3

    def extends_auras_on_cast(self, player: Player) -> bool:
        return True


_SUBCLASS_STRATEGIES: Dict[Optional[str], ClericSubclassStrategy] = {
    None: BaseClericStrategy(),
    "base": BaseClericStrategy(),
    Subclass.PRIEST: PriestStrategy(),
    Subclass.PALADIN: PaladinStrategy(),
}


def get_cleric_subclass_strategy(player: Player) -> ClericSubclassStrategy:
    """Resolve the strategy for a player's current Cleric subclass."""
    return _SUBCLASS_STRATEGIES.get(_resolve_subclass(player), _SUBCLASS_STRATEGIES[None])