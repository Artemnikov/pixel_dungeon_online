# Copyright (C) 2026 ArtemNikov
#
"""Polymorphic Cleric Armor Abilities Strategy Hierarchy.

Covers Ascended Form, Trinity, and Power of Many armor abilities. Mirrors the
DuelistArmorAbility pattern (see duelist_armor_abilities.py): charge cost and
the effect itself live on the ability class, and the class-wide if/elif
dispatch in ArmorAbilitiesMixin.use_armor_ability only needs a map lookup.
"""
from __future__ import annotations

import uuid as _uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from app.engine.entities.base import Faction, Position
from app.engine.entities.player import CharacterClass, Mob, Player
from app.engine.entities.talent_enum import ArmorAbilityType, Talent

# Cleric armor ability charge costs (SPD baseChargeUse).
COST_ASCENDED_FORM = 40
COST_TRINITY = 33
COST_POWER_OF_MANY = 50

# Heroic Energy (universal T4): reduces any armor ability's charge cost.
# [0,1,2,3,4] points -> multiplier.
_HEROIC_ENERGY_MULT = [1.0, 0.88, 0.77, 0.68, 0.60]


def _heroic_energy_mult(player: Player) -> float:
    pts = player.subclass_info.talent_info.level(Talent.HEROIC_ENERGY)
    return _HEROIC_ENERGY_MULT[min(pts, 4)]


class ClericArmorAbility(ABC):
    """Abstract Strategy interface for Cleric class armor abilities."""

    id: str = "base_cleric_armor_ability"
    name: str = "Base Cleric Armor Ability"
    base_cost: int = 40

    def get_cost(self, player: Player) -> int:
        return max(1, int(self.base_cost * _heroic_energy_mult(player)))

    def can_use(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if player.class_type != CharacterClass.CLERIC or player.is_downed or not player.is_alive:
            return False, "Only a living Cleric may use this ability"
        cost = self.get_cost(player)
        if player.armor_charge < cost:
            return False, f"Not enough armor charge (needs {cost}%)"
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

        Preconditions (target bounds/passability, class, charge) are checked
        before any charge is spent — an invalid target must never cost armor
        charge.
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


class AscendedFormArmorAbility(ClericArmorAbility):
    """40% Charge: buff all spells + shield for 10s."""

    id = ArmorAbilityType.ASCENDED_FORM
    name = "Ascended Form"
    base_cost = COST_ASCENDED_FORM

    def perform(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> None:
        shield = 30
        player.add_shield("ascended_form", shield, priority=2, decay=0)
        player.add_buff("shielded", duration=10.0, level=shield)
        player.ascended_form_active = True
        player.ascended_form_timer = 10.0
        player.ascended_form_casts = 0
        player.flash_casts = 0
        game.add_event(
            "ASCENDED_FORM",
            {"player": player.id},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )


class TrinityArmorAbility(ClericArmorAbility):
    """33% Charge: borrow one item form (up to 3)."""

    id = ArmorAbilityType.TRINITY
    name = "Trinity"
    base_cost = COST_TRINITY

    def borrow(self, game: Any, player: Player, item_kind: str) -> None:
        """Core Trinity effect: cycle in one borrowed item form."""
        if len(player.current_trinity_forms) >= 3:
            player.current_trinity_forms.pop(0)
        player.current_trinity_forms.append(item_kind)
        game.add_event(
            "TRINITY_FORM",
            {"player": player.id, "forms": player.current_trinity_forms},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )

    def perform(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> None:
        self.borrow(game, player, "scroll")


class PowerOfManyArmorAbility(ClericArmorAbility):
    """50% Charge: summon a Light Ally at the target cell."""

    id = ArmorAbilityType.POWER_OF_MANY
    name = "Power of Many"
    base_cost = COST_POWER_OF_MANY

    def can_use(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        ok, err = super().can_use(game, player, tx, ty)
        if not ok:
            return ok, err
        floor = game._get_or_create_floor(player.floor_id)
        cell_x = tx if tx is not None else player.pos.x
        cell_y = ty if ty is not None else player.pos.y
        if not (0 <= cell_x < floor.width and 0 <= cell_y < floor.height):
            return False, "Target cell out of bounds"
        if not (floor.flags and floor.flags.passable[cell_y][cell_x]):
            return False, "Target cell is not passable"
        return True, None

    def perform(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> None:
        floor = game._get_or_create_floor(player.floor_id)
        cell_x = tx if tx is not None else player.pos.x
        cell_y = ty if ty is not None else player.pos.y

        if not (0 <= cell_x < floor.width and 0 <= cell_y < floor.height):
            return
        if not (floor.flags and floor.flags.passable[cell_y][cell_x]):
            return

        if player.powered_ally_id and player.powered_ally_id in floor.mobs:
            existing = floor.mobs[player.powered_ally_id]
            existing.is_alive = False
            game.add_event("DEATH", {"target": existing.id}, floor_id=player.floor_id)
            del floor.mobs[player.powered_ally_id]

        ally_id = f"light_ally_{_uuid.uuid4().hex[:8]}"
        ally_hp = 80 + player.level * 4
        ally = Mob(
            id=ally_id,
            type="mob",
            mob_type="light_ally",
            name="Light Ally",
            pos=Position(x=cell_x, y=cell_y),
            hp=ally_hp,
            max_hp=ally_hp,
            attack=player.attack,
            defense=player.defense // 2,
            damage_min=player.damage_min,
            damage_max=player.damage_max,
            faction=Faction.PLAYER,
            owner_id=player.id,
        )
        floor.mobs[ally.id] = ally
        ally._owner_ref = player
        player.powered_ally_id = ally_id
        player._active_powered_ally = ally
        game.add_event(
            "POWER_OF_MANY",
            {"player": player.id, "ally_id": ally_id, "x": cell_x, "y": cell_y},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )


CLERIC_ARMOR_ABILITY_MAP: Dict[str, ClericArmorAbility] = {
    ArmorAbilityType.ASCENDED_FORM: AscendedFormArmorAbility(),
    ArmorAbilityType.TRINITY: TrinityArmorAbility(),
    ArmorAbilityType.POWER_OF_MANY: PowerOfManyArmorAbility(),
}