# Copyright (C) 2026 ArtemNikov
#
"""Polymorphic Monk Ability Command Hierarchy for Duelist Monk Subclass.

Monk energy system and commands: Flurry of Blows, Focus, Dash, Dragon Kick, Meditate.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction, Position, chebyshev_distance
from app.engine.entities.buffs import add_buff
from app.engine.entities.talent_enum import Talent

if TYPE_CHECKING:
    from app.engine.entities.player import Player
    from app.engine.manager import GameInstance


def calculate_monk_kill_energy(player: Player, mob: Any) -> float:
    """Calculate Monk energy gained upon killing a mob, factoring in Unencumbered Spirit."""
    mob_name = getattr(mob, "name", "").lower()
    is_boss = getattr(mob, "is_boss", False) or "boss" in getattr(mob, "properties", [])
    is_miniboss = "miniboss" in getattr(mob, "properties", [])

    if is_boss:
        base_energy = 5.0
    elif is_miniboss:
        base_energy = 3.0
    elif any(k in mob_name for k in ("ghoul", "ripper", "larva", "wraith", "swarm")):
        base_energy = 0.5
    else:
        base_energy = 1.0

    # Equipment tier multipliers from Unencumbered Spirit
    ti = player.talent_info
    rank = ti.level(Talent.UNENCUMBERED_SPIRIT)
    if rank == 0:
        return base_energy

    def _tier_bonus(tier: int) -> float:
        if tier <= 1 and rank >= 3:
            return 1.00
        if tier <= 2 and rank >= 2:
            return 0.75
        if tier <= 3 and rank >= 1:
            return 0.50
        return 0.0

    armor = getattr(getattr(player, "belongings", None), "armor", None)
    weapon = getattr(getattr(player, "belongings", None), "weapon", None)

    armor_tier = getattr(armor, "tier", 1) if armor is not None else 1
    weapon_tier = getattr(weapon, "tier", 1) if weapon is not None else 1

    multiplier = 1.0 + _tier_bonus(armor_tier) + _tier_bonus(weapon_tier)
    return base_energy * multiplier


class MonkAbility(ABC):
    """Abstract Command interface for Monk abilities."""

    id: str = "base_monk_ability"
    name: str = "Base Monk Ability"
    description: str = ""
    base_cost: int = 1

    def energy_cost(self, player: Player) -> int:
        return self.base_cost

    @abstractmethod
    def requires_target(self) -> bool:
        ...

    @abstractmethod
    def can_use(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        ...

    @abstractmethod
    def execute(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        ...

    def _handle_combined_energy(self, game: GameInstance, player: Player) -> None:
        """Combined Energy (Monk T3): using weapon ability & Monk ability sequentially refunds 1 energy."""
        ce_level = player.talent_info.level(Talent.COMBINED_ENERGY)
        if ce_level > 0:
            threshold = 5 - ce_level  # 4+ at rank 1, 3+ at rank 2, 2+ at rank 3
            if self.base_cost >= threshold:
                turns_since_weapon = getattr(game, "turns", 0) - player.last_weapon_ability_turn
                if 0 <= turns_since_weapon <= 5 and player.last_weapon_ability_id:
                    player.gain_monk_energy(1.0)
                    game.add_event(
                        "COMBINED_ENERGY",
                        {"player": player.id, "refund": 1.0},
                        floor_id=player.floor_id,
                    )
        player.last_monk_ability_id = self.id
        player.last_monk_ability_turn = getattr(game, "turns", 0)


class FlurryOfBlowsAbility(MonkAbility):
    """1 Energy: 2 instant unarmed strikes ignoring defense/armor; empowered procs weapon enchantment."""

    id = "flurry"
    name = "Flurry of Blows"
    description = "Unleash 2 rapid unarmed strikes ignoring armor. Empowered: procs equipped weapon enchantment."
    base_cost = 1

    def requires_target(self) -> bool:
        return True

    def can_use(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if player.monk_energy < self.base_cost:
            return False, "Not enough Monk energy (costs 1)"
        if tx is None or ty is None:
            return False, "Target required"
        if chebyshev_distance(player.pos.x, player.pos.y, tx, ty) > 1:
            return False, "Target must be adjacent"
        floor = game._get_or_create_floor(player.floor_id)
        target = next((m for m in floor.mobs.values() if m.is_alive and m.pos.x == tx and m.pos.y == ty), None)
        if target is None or target.faction == Faction.PLAYER:
            return False, "No valid enemy target"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        target = next((m for m in floor.mobs.values() if m.is_alive and m.pos.x == tx and m.pos.y == ty), None)
        if target is None:
            return False

        empowered = player.is_monk_empowered()
        player.spend_monk_energy(self.base_cost)

        # 1.5 * (STR - 8) per strike
        str_val = getattr(player, "strength", 10)
        damage_per_hit = max(1, round(1.5 * max(1, str_val - 8)))

        total_damage = 0
        for _ in range(2):
            if not target.is_alive:
                break
            # Unarmed ignores defense & armor
            dealt = target.take_damage(damage_per_hit)
            total_damage += dealt

            if empowered:
                weapon = getattr(getattr(player, "belongings", None), "weapon", None)
                enchant = getattr(weapon, "enchantment", None)
                if weapon is not None and enchant:
                    from app.engine.entities.weapons.weapon_enchants import apply_enchant_proc
                    apply_enchant_proc(
                        enchant, player, target, weapon, dealt, dealt, target.hp + dealt, {}, floor.mobs, tx, ty, floor,
                        add_event=lambda t, d: game.add_event(t, d, floor_id=player.floor_id),
                    )

        game.add_event(
            "FLURRY_OF_BLOWS",
            {"player": player.id, "target": target.id, "damage": total_damage, "empowered": empowered},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )

        self._handle_combined_energy(game, player)

        if not target.is_alive:
            game._finish_kill(player, target, floor, player.floor_id)
        return True


class FocusAbility(MonkAbility):
    """2 Energy: Grants infinite evasion against next attack. Empowered: instant action."""

    id = "focus"
    name = "Focus"
    description = "Gain complete evasion and parry against the next incoming attack. Empowered: instant action."
    base_cost = 2

    def requires_target(self) -> bool:
        return False

    def can_use(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if player.monk_energy < self.base_cost:
            return False, "Not enough Monk energy (costs 2)"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        empowered = player.is_monk_empowered()
        player.spend_monk_energy(self.base_cost)

        add_buff(player.buffs, "focus_parry_buff", duration=10.0, level=1)
        game.add_event(
            "MONK_FOCUS",
            {"player": player.id, "empowered": empowered},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )

        self._handle_combined_energy(game, player)
        return True


class DashAbility(MonkAbility):
    """3 Energy: Leaps up to 4 tiles (Empowered: up to 8 tiles) instantly."""

    id = "dash"
    name = "Dash"
    description = "Instantly leap across up to 4 tiles. Empowered: range extended up to 8 tiles."
    base_cost = 3

    def requires_target(self) -> bool:
        return True

    def can_use(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if player.monk_energy < self.base_cost:
            return False, "Not enough Monk energy (costs 3)"
        if tx is None or ty is None:
            return False, "Target tile required"
        empowered = player.is_monk_empowered()
        max_dist = 8 if empowered else 4
        dist = chebyshev_distance(player.pos.x, player.pos.y, tx, ty)
        if dist < 1 or dist > max_dist:
            return False, f"Target out of range (max {max_dist})"
        floor = game._get_or_create_floor(player.floor_id)
        if not (0 <= tx < floor.width and 0 <= ty < floor.height):
            return False, "Out of bounds"
        if floor.grid[ty][tx] == TileType.WALL:
            return False, "Target is a wall"
        if any(m.is_alive and m.pos.x == tx and m.pos.y == ty for m in floor.mobs.values()):
            return False, "Target occupied"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        empowered = player.is_monk_empowered()
        player.spend_monk_energy(self.base_cost)

        player.pos.x = tx
        player.pos.y = ty
        game.add_event("MOVE", {"entity": player.id, "x": tx, "y": ty}, floor_id=player.floor_id)
        game.add_event(
            "MONK_DASH",
            {"player": player.id, "x": tx, "y": ty, "empowered": empowered},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )

        self._handle_combined_energy(game, player)
        return True


class DragonKickAbility(MonkAbility):
    """4 Energy: Deals 6x (Empowered: 9x) unarmed dmg, knocks back 6 tiles, paralyzes. Empowered: hits all adjacent."""

    id = "dragon_kick"
    name = "Dragon Kick"
    description = "Powerful kick knocking target back 6 tiles and paralyzing it. Empowered: hits all adjacent enemies for 9x damage."
    base_cost = 4

    def requires_target(self) -> bool:
        return True

    def can_use(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if player.monk_energy < self.base_cost:
            return False, "Not enough Monk energy (costs 4)"
        if tx is None or ty is None:
            return False, "Target required"
        if chebyshev_distance(player.pos.x, player.pos.y, tx, ty) > 1:
            return False, "Target must be adjacent"
        floor = game._get_or_create_floor(player.floor_id)
        target = next((m for m in floor.mobs.values() if m.is_alive and m.pos.x == tx and m.pos.y == ty), None)
        if target is None or target.faction == Faction.PLAYER:
            return False, "No valid enemy target"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        empowered = player.is_monk_empowered()
        player.spend_monk_energy(self.base_cost)

        str_val = getattr(player, "strength", 10)
        mult = 9.0 if empowered else 6.0
        dmg = max(1, round(mult * max(1, str_val - 8)))

        targets = []
        if empowered:
            targets = [
                m for m in floor.mobs.values()
                if m.is_alive and m.faction != Faction.PLAYER
                and chebyshev_distance(player.pos.x, player.pos.y, m.pos.x, m.pos.y) <= 1
            ]
        else:
            primary = next((m for m in floor.mobs.values() if m.is_alive and m.pos.x == tx and m.pos.y == ty), None)
            if primary:
                targets = [primary]

        for target in targets:
            dealt = target.take_damage(dmg)
            # Push up to 6 tiles
            dx = target.pos.x - player.pos.x
            dy = target.pos.y - player.pos.y
            step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
            step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
            pushed = 0
            cx, cy = target.pos.x, target.pos.y
            for _ in range(6):
                nx, ny = cx + step_x, cy + step_y
                if 0 <= nx < floor.width and 0 <= ny < floor.height and floor.grid[ny][nx] != TileType.WALL:
                    if not any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values()):
                        cx, cy = nx, ny
                        pushed += 1
                        continue
                break
            if pushed > 0:
                target.pos.x = cx
                target.pos.y = cy
                game.add_event("MOVE", {"entity": target.id, "x": cx, "y": cy}, floor_id=player.floor_id)
            if pushed > 0:
                add_buff(target.buffs, "paralysis", duration=float(pushed), level=1, stack_mode="extend")

            if not target.is_alive:
                game._finish_kill(player, target, floor, player.floor_id)

        game.add_event(
            "DRAGON_KICK",
            {"player": player.id, "hit_count": len(targets), "empowered": empowered},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )

        self._handle_combined_energy(game, player)
        return True


class MeditateAbility(MonkAbility):
    """5 Energy: Cleanses debuffs, grants 8t wand/artifact recharge. Empowered: 80% DR and 20% missing HP heal."""

    id = "meditate"
    name = "Meditate"
    description = "Channel meditation to cleanse negative debuffs and recharge wands/artifacts. Empowered: heals 20% missing HP and grants 80% DR."
    base_cost = 5

    def requires_target(self) -> bool:
        return False

    def can_use(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if player.monk_energy < self.base_cost:
            return False, "Not enough Monk energy (costs 5)"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        empowered = player.is_monk_empowered()
        player.spend_monk_energy(self.base_cost)

        # Cleanse negative debuffs
        negative_types = {
            "poison", "burning", "frozen", "frost", "chilled", "chill",
            "paralysis", "cripple", "blindness", "blinded", "weakness",
            "vulnerable", "hex", "ooze", "corrosion", "vertigo", "terror",
            "bleeding", "rooted", "slow", "daze",
        }
        player.buffs = [b for b in player.buffs if b.type not in negative_types]

        # Recharging buffs
        add_buff(player.buffs, "recharging", duration=8.0, level=1)
        add_buff(player.buffs, "artifact_recharge", duration=8.0, level=1)

        healed = 0
        if empowered:
            # 80% DR
            add_buff(player.buffs, "meditate_resistance", duration=5.0, level=1)
            # Heal 20% missing HP
            missing = player.get_total_max_hp() - player.hp
            healed = max(1, round(missing / 5.0))
            player.hp = min(player.get_total_max_hp(), player.hp + healed)
            game.add_event(
                "HEAL",
                {"target": player.id, "amount": healed, "source": "meditate"},
                floor_id=player.floor_id,
            )

        game.add_event(
            "MONK_MEDITATE",
            {"player": player.id, "healed": healed, "empowered": empowered},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )

        self._handle_combined_energy(game, player)
        return True


MONK_ABILITY_MAP: Dict[str, MonkAbility] = {
    "flurry": FlurryOfBlowsAbility(),
    "focus": FocusAbility(),
    "dash": DashAbility(),
    "dragon_kick": DragonKickAbility(),
    "meditate": MeditateAbility(),
}


def get_monk_ability(ability_id: str) -> Optional[MonkAbility]:
    """Retrieve MonkAbility command by identifier."""
    return MONK_ABILITY_MAP.get(ability_id)
