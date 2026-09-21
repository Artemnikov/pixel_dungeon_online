# Copyright (C) 2026 ArtemNikov
#
"""Shared charge-drawn armor-ability template.

Warrior, Rogue, and Cleric armor abilities share the same charge lifecycle
(validate preconditions, deduct charge, then perform the effect). This base
class implements that template once; the class modules only set
``required_class`` / ``heroic_scaled`` / ``base_cost`` and override
``perform`` (or ``get_cost`` / ``can_use`` / ``use`` where their behavior
deviates).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Optional, Tuple

from app.engine.entities.base import find_mob_at
from app.engine.entities.player import Player
from app.engine.entities.subclasses import heroic_energy_mult, CLASS_TALENT_BASE


def resolve_target_entity(game: Any, player: Player, floor: Any, tx: int, ty: int) -> Optional[Any]:
    if hasattr(game, "_entity_at"):
        target = game._entity_at(floor, player.floor_id, tx, ty, exclude_id=player.id, active_players_only=True)
        if target is not None:
            return target
    return find_mob_at(floor, tx, ty)


def armor_class_guard(player: Player, required_class: str) -> Optional[str]:
    """Return an error message if ``player`` may not use a class ability.

    Precondition shared by every class armor ability: the hero must be that
    class, alive, and not downed.
    """
    base_class = CLASS_TALENT_BASE.get(player.class_type, player.class_type)
    if base_class != required_class or player.is_downed or not player.is_alive:
        return f"Only a living {required_class.capitalize()} may use this ability"
    return None


class ArmorAbilityBase(ABC):
    """Template for charge-drawn class armor abilities.

    Concrete abilities implement :meth:`perform` and may override
    :meth:`get_cost` / :meth:`can_use` / :meth:`use` for custom cost or
    precondition logic. Every class branch must declare ``required_class``
    explicitly (see :meth:`__init_subclass__`).
    """

    base_cost: int = 40
    required_class: ClassVar[str] = ""
    heroic_scaled: bool = True

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Every class branch must pin required_class; the empty-string
        # sentinel catches missing overrides at class-creation time.
        if not cls.required_class:
            raise TypeError(f"{cls.__name__} must declare required_class")

    def get_cost(self, player: Player) -> int:
        if self.heroic_scaled:
            return max(1, int(self.base_cost * heroic_energy_mult(player)))
        return self.base_cost

    def _class_guard(self, player: Player) -> Optional[str]:
        return armor_class_guard(player, self.required_class)

    def _check_charge(self, player: Player) -> Optional[str]:
        cost = self.get_cost(player)
        if player.armor_charge < cost:
            return f"Not enough armor charge (needs {cost}%)"
        return None

    def can_use(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        guard = self._class_guard(player)
        if guard is not None:
            return False, guard
        charge_error = self._check_charge(player)
        if charge_error is not None:
            return False, charge_error
        return True, None

    def _spend(self, player: Player) -> bool:
        cost = self.get_cost(player)
        if player.armor_charge < cost:
            return False
        player.armor_charge -= cost
        return True

    def use(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        """Validate the preconditions, deduct charge, then perform the effect.

        Class and charge preconditions are checked before any charge is
        spent — an invalid target must never cost armor charge. Subclasses
        may add target validation in ``can_use`` before calling
        ``super().can_use()``.
        """
        ok, _err = self.can_use(game, player, tx, ty)
        if not ok:
            return False
        if not self._spend(player):
            return False
        self.perform(game, player, tx, ty)
        return True

    @abstractmethod
    def perform(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> None:
        """Apply the ability's effect without spending charge."""
        ...