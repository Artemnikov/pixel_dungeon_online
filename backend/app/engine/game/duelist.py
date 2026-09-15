# Copyright (C) 2026 ArtemNikov
#
"""Duelist class mechanics for GameInstance.

Weapon charge system, weapon abilities dispatch, Champion dual-wielding,
Monk energy system & abilities, and Duelist armor abilities.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING

from app.engine.entities.base import chebyshev_distance
from app.engine.entities.buffs import add_buff, get_buff, has_buff
from app.engine.entities.player import CharacterClass, Player
from app.engine.entities.talent_enum import ArmorAbilityType, Talent
from app.engine.game.duelist_armor_abilities import (
    DUELIST_ARMOR_ABILITY_MAP,
    ChallengeArmorAbility,
    get_duelist_armor_ability,
)
from app.engine.game.duelist_monk import (
    calculate_monk_kill_energy,
    get_monk_ability,
)
from app.engine.game.duelist_weapon_skills import (
    get_weapon_skill_for_weapon,
)

if TYPE_CHECKING:
    from app.engine.entities.items.equip import KindOfWeapon
    from app.engine.manager import GameInstance


class DuelistSubclassStrategy(ABC):
    """Abstract Strategy for subclass-specific Duelist resource rules."""

    @abstractmethod
    def get_max_charges(self, player: Player) -> int:
        ...

    @abstractmethod
    def get_regen_speed_multiplier(self, player: Player) -> float:
        ...

    @abstractmethod
    def on_combat_hit(self, game: GameInstance, player: Player, target: Any) -> None:
        ...

    @abstractmethod
    def on_combat_kill(self, game: GameInstance, player: Player, target: Any) -> None:
        ...


class BaseDuelistStrategy(DuelistSubclassStrategy):
    """Base Duelist resource calculations."""

    def get_max_charges(self, player: Player) -> int:
        return min(8, 2 + (player.level - 1) // 3)

    def get_regen_speed_multiplier(self, player: Player) -> float:
        return 0.5 if player.brawler_stance else 1.0

    def on_combat_hit(self, game: GameInstance, player: Player, target: Any) -> None:
        pass

    def on_combat_kill(self, game: GameInstance, player: Player, target: Any) -> None:
        pass


class ChampionStrategy(DuelistSubclassStrategy):
    """Champion Subclass: 1.5x charge regen, higher max charges (cap 10)."""

    def get_max_charges(self, player: Player) -> int:
        return min(10, 4 + (player.level - 1) // 3)

    def get_regen_speed_multiplier(self, player: Player) -> float:
        mult = 1.5
        if player.brawler_stance:
            mult *= 0.5
        return mult

    def on_combat_hit(self, game: GameInstance, player: Player, target: Any) -> None:
        pass

    def on_combat_kill(self, game: GameInstance, player: Player, target: Any) -> None:
        pass


class MonkStrategy(DuelistSubclassStrategy):
    """Monk Subclass: Generates Monk Energy on kills."""

    def get_max_charges(self, player: Player) -> int:
        return min(8, 2 + (player.level - 1) // 3)

    def get_regen_speed_multiplier(self, player: Player) -> float:
        return 0.5 if player.brawler_stance else 1.0

    def on_combat_hit(self, game: GameInstance, player: Player, target: Any) -> None:
        pass

    def on_combat_kill(self, game: GameInstance, player: Player, target: Any) -> None:
        energy_gain = calculate_monk_kill_energy(player, target)
        player.gain_monk_energy(energy_gain)
        game.add_event(
            "MONK_ENERGY",
            {
                "player": player.id,
                "energy": player.monk_energy,
                "max_energy": player.get_max_monk_energy(),
                "empowered": player.is_monk_empowered(),
            },
            floor_id=player.floor_id,
            source_player_id=player.id,
        )


_SUBCLASS_STRATEGIES: Dict[Optional[str], DuelistSubclassStrategy] = {
    None: BaseDuelistStrategy(),
    "base": BaseDuelistStrategy(),
    "champion": ChampionStrategy(),
    "monk": MonkStrategy(),
}


def get_duelist_subclass_strategy(subclass: Optional[str]) -> DuelistSubclassStrategy:
    return _SUBCLASS_STRATEGIES.get(subclass, _SUBCLASS_STRATEGIES[None])


class DuelistMixin:
    """GameInstance mixin for all Duelist capabilities."""

    def tick_duelist(self, player: Player, dt: float) -> None:
        """Called every game tick (~20Hz) from player_tick."""
        if player.class_type != CharacterClass.DUELIST:
            return

        subclass_strat = get_duelist_subclass_strategy(player.subclass_info.subclass)
        max_charges = subclass_strat.get_max_charges(player)

        # Regenerate weapon charge when deficit exists
        if player.weapon_charge < max_charges:
            deficit = max_charges - player.weapon_charge
            # SPD formula: 60 - 1.5 * deficit seconds/turns per charge
            turns_per_charge = max(30.0, 60.0 - 1.5 * deficit)
            base_rate = (1.0 / turns_per_charge) * subclass_strat.get_regen_speed_multiplier(player)

            # Weapon Recharging talent bonus
            wr_level = player.talent_info.level(Talent.WEAPON_RECHARGING)
            if wr_level > 0 and (has_buff(player.buffs, "recharging") or has_buff(player.buffs, "artifact_recharge")):
                # +1 charge every 20 - 5*points turns (15t at R1, 10t at R2)
                bonus_rate = 1.0 / (20.0 - 5.0 * wr_level)
                base_rate += bonus_rate

            player._weapon_charge_accum = getattr(player, "_weapon_charge_accum", 0.0) + base_rate * dt
            if player._weapon_charge_accum >= 1.0:
                gained = int(player._weapon_charge_accum)
                player._weapon_charge_accum -= gained
                player.gain_weapon_charge(float(gained))
                self.add_event(
                    "WEAPON_CHARGE",
                    {
                        "player": player.id,
                        "charge": player.weapon_charge,
                        "max_charge": max_charges,
                        "finisher_ready": player.finisher_ready,
                    },
                    floor_id=player.floor_id,
                    source_player_id=player.id,
                )

        # Duel Mode tick (Challenge armor ability)
        if player.duel_mode_active:
            player.duel_mode_turns_left = max(0.0, player.duel_mode_turns_left - dt)
            floor = self._get_or_create_floor(player.floor_id)
            target = floor.mobs.get(player.duel_mode_target_id) if player.duel_mode_target_id else None
            if target is None or not target.is_alive:
                challenge_ability = DUELIST_ARMOR_ABILITY_MAP.get(ArmorAbilityType.CHALLENGE)
                if isinstance(challenge_ability, ChallengeArmorAbility):
                    challenge_ability.end_duel(self, player, target_killed=True)
            elif player.duel_mode_turns_left <= 0 or chebyshev_distance(player.pos.x, player.pos.y, target.pos.x, target.pos.y) > 6:
                challenge_ability = DUELIST_ARMOR_ABILITY_MAP.get(ArmorAbilityType.CHALLENGE)
                if isinstance(challenge_ability, ChallengeArmorAbility):
                    challenge_ability.end_duel(self, player, target_killed=False)

    def on_duelist_hit(self, player: Player) -> None:
        """Called from combat when Duelist lands a melee hit."""
        if player.class_type != CharacterClass.DUELIST:
            return
        subclass_strat = get_duelist_subclass_strategy(player.subclass_info.subclass)
        subclass_strat.on_combat_hit(self, player, None)
        # Combo hit accumulation for Combo Strike skill (Gloves/Sai/Gauntlet)
        weapon = getattr(getattr(player, "belongings", None), "weapon", None)
        if weapon is not None and getattr(weapon, "name", "") in ("Gloves", "Sai", "Gauntlet"):
            combo_buff = get_buff(player.buffs, "combo_hits_tracker")
            cur = combo_buff.level if combo_buff else 0
            add_buff(player.buffs, "combo_hits_tracker", duration=5.0, level=cur + 1)

    def on_duelist_kill(self, player: Player, target: Any) -> None:
        """Called from combat on kill."""
        if player.class_type != CharacterClass.DUELIST:
            return
        subclass_strat = get_duelist_subclass_strategy(player.subclass_info.subclass)
        subclass_strat.on_combat_kill(self, player, target)

    def use_weapon_ability(
        self,
        player_id: str,
        target_x: Optional[int] = None,
        target_y: Optional[int] = None,
        use_secondary: bool = False,
    ) -> bool:
        """Execute weapon skill for primary or secondary equipped melee weapon."""
        player = self.players.get(player_id)
        if not player or player.is_downed or not player.is_alive:
            return False

        b = player.belongings
        weapon = b.secondary_weapon if (use_secondary and b.secondary_weapon) else b.weapon
        if weapon is None:
            return False

        # STR requirement check
        str_req = getattr(weapon, "strength_requirement", 10)
        if player.strength < str_req:
            self.add_event(
                "ACTION_FAILED",
                {"player": player.id, "reason": "insufficient_strength"},
                floor_id=player.floor_id,
                player_id=player.id,
            )
            return False

        skill = get_weapon_skill_for_weapon(weapon)
        if skill is None:
            return False

        cost = skill.charge_cost(player, weapon)
        if player.weapon_charge < cost:
            self.add_event(
                "ACTION_FAILED",
                {"player": player.id, "reason": "insufficient_weapon_charge", "cost": cost},
                floor_id=player.floor_id,
                player_id=player.id,
            )
            return False

        ok, err = skill.can_execute(self, player, weapon, target_x, target_y)
        if not ok:
            if err:
                self.add_event(
                    "ACTION_FAILED",
                    {"player": player.id, "reason": err},
                    floor_id=player.floor_id,
                    player_id=player.id,
                )
            return False

        success = skill.execute(self, player, weapon, target_x, target_y)
        if success:
            if cost > 0:
                player.spend_weapon_charge(cost)
            self.add_event(
                "WEAPON_ABILITY_USED",
                {
                    "player": player.id,
                    "ability": skill.id,
                    "weapon": getattr(weapon, "name", ""),
                    "charge_left": player.weapon_charge,
                },
                floor_id=player.floor_id,
                source_player_id=player.id,
            )
        return success

    def action_duelist_finisher(self, player: Player, tx: int, ty: int) -> None:
        """Legacy adapter routing DUELIST_FINISHER messages to equipped weapon skill."""
        self.use_weapon_ability(player.id, target_x=tx, target_y=ty, use_secondary=False)

    def swap_weapons(self, player_id: str) -> bool:
        """Champion: Instantaneous 0-delay weapon swap between primary and secondary."""
        player = self.players.get(player_id)
        if not player or player.is_downed or not player.is_alive:
            return False
        b = player.belongings
        if b.secondary_weapon is None:
            return False

        primary = b.weapon
        secondary = b.secondary_weapon

        b.weapon = secondary
        b.secondary_weapon = primary

        self.add_event(
            "SWAP_WEAPONS",
            {
                "player": player.id,
                "primary": getattr(secondary, "name", ""),
                "secondary": getattr(primary, "name", "") if primary else None,
            },
            floor_id=player.floor_id,
            source_player_id=player.id,
        )
        return True

    def use_monk_ability(
        self,
        player_id: str,
        ability_id: str,
        target_x: Optional[int] = None,
        target_y: Optional[int] = None,
    ) -> bool:
        """Execute a Monk energy command (Flurry, Focus, Dash, Dragon Kick, Meditate)."""
        player = self.players.get(player_id)
        if not player or player.is_downed or not player.is_alive:
            return False
        if player.subclass_info.subclass != "monk":
            return False

        ability = get_monk_ability(ability_id)
        if ability is None:
            return False

        cost = ability.energy_cost(player)
        if player.monk_energy < cost:
            self.add_event(
                "ACTION_FAILED",
                {"player": player.id, "reason": "insufficient_monk_energy", "cost": cost},
                floor_id=player.floor_id,
                player_id=player.id,
            )
            return False

        ok, err = ability.can_use(self, player, target_x, target_y)
        if not ok:
            if err:
                self.add_event(
                    "ACTION_FAILED",
                    {"player": player.id, "reason": err},
                    floor_id=player.floor_id,
                    player_id=player.id,
                )
            return False

        return ability.execute(self, player, target_x, target_y)

    def action_challenge(self, player: Player, tx: int, ty: int) -> None:
        """Challenge armor ability."""
        ability = get_duelist_armor_ability(ArmorAbilityType.CHALLENGE)
        if ability is not None:
            ability.use(self, player, tx, ty)

    def action_elemental_strike(self, player: Player, tx: int, ty: int) -> None:
        """Elemental Strike armor ability."""
        ability = get_duelist_armor_ability(ArmorAbilityType.ELEMENTAL_STRIKE)
        if ability is not None:
            ability.use(self, player, tx, ty)

    def action_feint(self, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> None:
        """Feint armor ability."""
        ability = get_duelist_armor_ability(ArmorAbilityType.FEINT)
        if ability is not None:
            ability.use(self, player, tx, ty)
