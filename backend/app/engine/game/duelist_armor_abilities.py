# Copyright (C) 2026 ArtemNikov
#
"""Polymorphic Duelist Armor Abilities Strategy Hierarchy.

Covers Challenge, Elemental Strike, and Feint armor abilities and their T4 talent upgrades.
"""
from __future__ import annotations

import math
import random
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction, Position, chebyshev_distance
from app.engine.entities.buffs import add_buff, get_buff, has_buff, remove_buff
from app.engine.entities.player import Mob
from app.engine.entities.talent_enum import ArmorAbilityType, Talent
from app.engine.systems.combat import resolve_melee_attack

if TYPE_CHECKING:
    from app.engine.entities.player import Player
    from app.engine.manager import GameInstance

_HEROIC_ENERGY_MULT = [1.0, 0.88, 0.77, 0.68, 0.60]


def _heroic_energy_mult(player: Player) -> float:
    pts = player.talent_info.level(Talent.HEROIC_ENERGY)
    return _HEROIC_ENERGY_MULT[min(pts, 4)]


class DuelistArmorAbility(ABC):
    """Abstract Strategy interface for Duelist Class Armor abilities."""

    id: str = "base_armor_ability"
    name: str = "Base Armor Ability"
    base_cost: int = 35

    def get_cost(self, player: Player, game: Optional[GameInstance] = None) -> int:
        cost = self.base_cost * _heroic_energy_mult(player)
        return max(1, int(cost))

    @abstractmethod
    def can_use(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        ...

    @abstractmethod
    def use(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        ...


class ChallengeArmorAbility(DuelistArmorAbility):
    """35% Charge: Forces 1v1 duel for 10 turns, freezing all spectator enemies."""

    id = ArmorAbilityType.CHALLENGE
    name = "Challenge"
    base_cost = 35

    def get_cost(self, player: Player, game: Optional[GameInstance] = None) -> int:
        cost = float(self.base_cost)
        # Elimination Match talent: Challenging again within 3 turns of duel ending
        em_level = player.talent_info.level(Talent.ELIMINATION_MATCH)
        if em_level > 0 and game is not None:
            turns_since_duel = getattr(game, "turns", 0) - getattr(player, "last_duel_ended_turn", -100)
            if 0 <= turns_since_duel <= 3:
                # 0.84 ** em_level
                cost *= (0.84 ** em_level)
        cost *= _heroic_energy_mult(player)
        return max(1, int(cost))

    def can_use(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        cost = self.get_cost(player, game)
        if player.armor_charge < cost:
            return False, f"Not enough armor charge (needs {cost}%)"
        if tx is None or ty is None:
            return False, "Target enemy required"
        dist = chebyshev_distance(player.pos.x, player.pos.y, tx, ty)
        if dist > 5:
            return False, "Target must be within 5 tiles"
        floor = game._get_or_create_floor(player.floor_id)
        target = next((m for m in floor.mobs.values() if m.is_alive and m.pos.x == tx and m.pos.y == ty), None)
        if target is None or target.faction == Faction.PLAYER:
            return False, "No valid enemy target"
        return True, None

    def use(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        target = next((m for m in floor.mobs.values() if m.is_alive and m.pos.x == tx and m.pos.y == ty), None)
        if target is None:
            return False

        cost = self.get_cost(player, game)
        if player.armor_charge < cost:
            return False
        player.armor_charge -= cost

        # Close the Gap talent: Leap towards target
        ctg_level = player.talent_info.level(Talent.CLOSE_THE_GAP)
        if ctg_level > 0:
            max_leap = 1 + ctg_level  # 2, 3, 4, 5
            dx = target.pos.x - player.pos.x
            dy = target.pos.y - player.pos.y
            dist = max(abs(dx), abs(dy))
            if dist > 1:
                step_count = min(max_leap, dist - 1)
                norm_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
                norm_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
                lx = player.pos.x + norm_x * step_count
                ly = player.pos.y + norm_y * step_count
                if 0 <= lx < floor.width and 0 <= ly < floor.height and floor.grid[ly][lx] != TileType.WALL:
                    if not any(m.is_alive and m.pos.x == lx and m.pos.y == ly for m in floor.mobs.values()):
                        player.pos.x = lx
                        player.pos.y = ly
                        game.add_event("MOVE", {"entity": player.id, "x": lx, "y": ly}, floor_id=player.floor_id)

        player.duel_mode_active = True
        player.duel_mode_target_id = target.id
        player.duel_mode_taken_damage = 0
        player.duel_mode_turns_left = 10

        # Freeze spectator mobs
        for mob in floor.mobs.values():
            if mob.is_alive and mob.faction != Faction.PLAYER and mob.id != target.id:
                add_buff(mob.buffs, "spectator_freeze", duration=10.0, level=1)

        game.add_event(
            "CHALLENGE",
            {"player": player.id, "target": target.id, "turns": 10},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )
        return True

    def end_duel(self, game: GameInstance, player: Player, target_killed: bool = False) -> None:
        """Called when a duel ends (target dies or moves too far)."""
        player.duel_mode_active = False
        player.duel_mode_target_id = None
        player.last_duel_ended_turn = getattr(game, "turns", 0)

        # Unfreeze spectators
        floor = game._get_or_create_floor(player.floor_id)
        for mob in floor.mobs.values():
            remove_buff(mob.buffs, "spectator_freeze")

        # Invigorating Victory talent: heal on defeating target
        if target_killed:
            iv_level = player.talent_info.level(Talent.INVIGORATING_VICTORY)
            if iv_level > 0:
                # 5*points + round(taken_damage * (1 - 0.707^points))
                pct = 1.0 - (0.707 ** iv_level)
                heal_amt = (5 * iv_level) + round(player.duel_mode_taken_damage * pct)
                player.hp = min(player.get_total_max_hp(), player.hp + heal_amt)
                game.add_event(
                    "HEAL",
                    {"target": player.id, "amount": heal_amt, "source": "invigorating_victory"},
                    floor_id=player.floor_id,
                )

        player.duel_mode_taken_damage = 0
        game.add_event(
            "DUEL_END",
            {"player": player.id, "reason": "target_killed" if target_killed else "expired"},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )


class ElementalStrikeArmorAbility(DuelistArmorAbility):
    """25% Charge: Melee strike + 65° cone releasing weapon enchantment in area."""

    id = ArmorAbilityType.ELEMENTAL_STRIKE
    name = "Elemental Strike"
    base_cost = 25

    def can_use(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        cost = self.get_cost(player, game)
        if player.armor_charge < cost:
            return False, f"Not enough armor charge (needs {cost}%)"
        return True, None

    def use(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        cost = self.get_cost(player, game)
        if player.armor_charge < cost:
            return False
        player.armor_charge -= cost

        floor = game._get_or_create_floor(player.floor_id)
        weapon = getattr(getattr(player, "belongings", None), "weapon", None)
        enchant = getattr(weapon, "enchantment", None) or player.last_weapon_enchant or ""

        # Talents
        er_level = player.talent_info.level(Talent.ELEMENTAL_REACH)
        sf_level = player.talent_info.level(Talent.STRIKING_FORCE)
        dp_level = player.talent_info.level(Talent.DIRECTED_POWER)

        max_range = 4 + er_level  # 5, 6, 7, 8
        power_mult = 1.0 + 0.30 * sf_level  # +30% per rank

        target_tile_x = tx if tx is not None else player.pos.x
        target_tile_y = ty if ty is not None else player.pos.y

        # Direct melee target if adjacent
        direct_target = next((
            m for m in floor.mobs.values()
            if m.is_alive and m.pos.x == target_tile_x and m.pos.y == target_tile_y
            and chebyshev_distance(player.pos.x, player.pos.y, target_tile_x, target_tile_y) <= 1
            and m.faction != Faction.PLAYER
        ), None)

        # Collect enemies in cone / area
        affected_mobs: List[Any] = []
        for mob in floor.mobs.values():
            if not mob.is_alive or mob.faction == Faction.PLAYER:
                continue
            dist = chebyshev_distance(player.pos.x, player.pos.y, mob.pos.x, mob.pos.y)
            if 1 <= dist <= max_range:
                affected_mobs.append(mob)

        # Directed Power: boosts direct strike enchantment power
        if direct_target:
            direct_bonus_enchant = (1.0 + 0.30 * dp_level * len(affected_mobs)) if dp_level > 0 else 1.0
            resolve_melee_attack(
                attacker=player,
                defender=direct_target,
                floor_mobs=floor.mobs,
                tile_x=direct_target.pos.x,
                tile_y=direct_target.pos.y,
                dmg_multi=direct_bonus_enchant,
                guaranteed_hit=True,
                floor=floor,
                add_event=lambda t, d: game.add_event(t, d, floor_id=player.floor_id),
                game=game,
            )
            if not direct_target.is_alive:
                game._finish_kill(player, direct_target, floor, player.floor_id)

        # Apply elemental effects in area
        for mob in affected_mobs:
            if not mob.is_alive or mob is direct_target:
                continue
            if not enchant:
                dmg = max(1, round(random.randint(6, 12) * power_mult))
                mob.take_damage(dmg)
            elif "blaz" in enchant or "fire" in enchant:
                add_buff(mob.buffs, "burning", duration=8.0 * power_mult, level=1, stack_mode="extend")
            elif "chill" in enchant or "frost" in enchant:
                add_buff(mob.buffs, "frost", duration=8.0 * power_mult, level=1)
            elif "shock" in enchant:
                add_buff(mob.buffs, "paralysis", duration=1.0 * power_mult, level=1, stack_mode="extend")
            elif "bloom" in enchant:
                add_buff(mob.buffs, "rooted", duration=6.0 * power_mult, level=1)
            elif "block" in enchant:
                shield_amt = round(6 * power_mult)
                player.add_shield("elemental_blocking", shield_amt, priority=1, decay=600)
            elif "vamp" in enchant:
                heal_amt = round(2.5 * power_mult)
                player.hp = min(player.get_total_max_hp(), player.hp + heal_amt)
            elif "elast" in enchant:
                # Push back
                dx = mob.pos.x - player.pos.x
                dy = mob.pos.y - player.pos.y
                nx = mob.pos.x + (1 if dx > 0 else (-1 if dx < 0 else 0))
                ny = mob.pos.y + (1 if dy > 0 else (-1 if dy < 0 else 0))
                if 0 <= nx < floor.width and 0 <= ny < floor.height and floor.grid[ny][nx] != TileType.WALL:
                    mob.pos.x, mob.pos.y = nx, ny
            else:
                dmg = max(1, round(random.randint(6, 12) * power_mult))
                mob.take_damage(dmg)

            if not mob.is_alive:
                game._finish_kill(player, mob, floor, player.floor_id)

        game.add_event(
            "ELEMENTAL_STRIKE",
            {"player": player.id, "enchant": enchant, "hit_count": len(affected_mobs)},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )
        return True


class FeintArmorAbility(DuelistArmorAbility):
    """50% Charge: Leaps to adjacent cell, leaving an AfterImage decoy."""

    id = ArmorAbilityType.FEINT
    name = "Feint"
    base_cost = 50

    def can_use(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        cost = self.get_cost(player, game)
        if player.armor_charge < cost:
            return False, f"Not enough armor charge (needs {cost}%)"
        floor = game._get_or_create_floor(player.floor_id)
        # Find adjacent passable landing cell
        passable_adjacent = [
            (player.pos.x + dx, player.pos.y + dy)
            for dx in (-1, 0, 1) for dy in (-1, 0, 1)
            if (dx != 0 or dy != 0)
            and 0 <= player.pos.x + dx < floor.width
            and 0 <= player.pos.y + dy < floor.height
            and floor.grid[player.pos.y + dy][player.pos.x + dx] != TileType.WALL
            and not any(m.is_alive and m.pos.x == player.pos.x + dx and m.pos.y == player.pos.y + dy for m in floor.mobs.values())
        ]
        if not passable_adjacent:
            return False, "No space to leap"
        return True, None

    def use(
        self, game: GameInstance, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        cost = self.get_cost(player, game)
        if player.armor_charge < cost:
            return False

        floor = game._get_or_create_floor(player.floor_id)
        old_x, old_y = player.pos.x, player.pos.y

        # Select landing cell
        if tx is not None and ty is not None and chebyshev_distance(old_x, old_y, tx, ty) == 1:
            if floor.grid[ty][tx] != TileType.WALL and not any(m.is_alive and m.pos.x == tx and m.pos.y == ty for m in floor.mobs.values()):
                landing = (tx, ty)
            else:
                landing = None
        else:
            landing = None

        if landing is None:
            passable = [
                (old_x + dx, old_y + dy)
                for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if (dx != 0 or dy != 0)
                and 0 <= old_x + dx < floor.width
                and 0 <= old_y + dy < floor.height
                and floor.grid[old_y + dy][old_x + dx] != TileType.WALL
                and not any(m.is_alive and m.pos.x == old_x + dx and m.pos.y == old_y + dy for m in floor.mobs.values())
            ]
            if not passable:
                return False
            landing = random.choice(passable)

        player.armor_charge -= cost

        # Spawn afterimage at old_x, old_y
        afterimage = Mob(
            id=f"afterimage_{uuid.uuid4().hex[:8]}",
            name="Afterimage",
            type="afterimage",
            pos=Position(x=old_x, y=old_y),
            hp=1, max_hp=1,
            attack=0, defense=0, defense_skill=0, dr_min=0, dr_max=0,
            properties=["INORGANIC", "DECOY"],
            faction=Faction.PLAYER,
        )
        afterimage.owner_id = player.id
        floor.mobs[afterimage.id] = afterimage

        player.pos.x, player.pos.y = landing[0], landing[1]
        player.feint_afterimage_pos = (old_x, old_y)

        # Aggro nearby enemies to afterimage
        for mob in floor.mobs.values():
            if mob.is_alive and mob.faction != Faction.PLAYER:
                if chebyshev_distance(old_x, old_y, mob.pos.x, mob.pos.y) <= 3:
                    if hasattr(mob, "aggro_target_id"):
                        mob.aggro_target_id = afterimage.id
                    mob.ai_state = "hunting"

        game.add_event("MOVE", {"entity": player.id, "x": landing[0], "y": landing[1]}, floor_id=player.floor_id)
        game.add_event(
            "FEINT",
            {"player": player.id, "afterimage": afterimage.id, "x": old_x, "y": old_y},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )
        return True

    def on_afterimage_struck(self, game: GameInstance, player: Player, attacker: Any) -> None:
        """Called when a mob strikes the afterimage decoy."""
        fr_level = player.talent_info.level(Talent.FEIGNED_RETREAT)
        if fr_level > 0:
            # Grants 2, 4, 6, 8 turns Haste
            add_buff(player.buffs, "haste", duration=float(fr_level * 2), level=1)

        ew_level = player.talent_info.level(Talent.EXPOSE_WEAKNESS)
        if ew_level > 0 and attacker is not None:
            # Inflicts Vulnerable and Weakness
            duration = float(ew_level * 2)
            add_buff(attacker.buffs, "vulnerable", duration=duration, level=1)
            add_buff(attacker.buffs, "weakness", duration=duration, level=1)

        ca_level = player.talent_info.level(Talent.COUNTER_ABILITY)
        if ca_level > 0:
            player.feint_cooldown_refund_ready = True


DUELIST_ARMOR_ABILITY_MAP: Dict[str, DuelistArmorAbility] = {
    ArmorAbilityType.CHALLENGE: ChallengeArmorAbility(),
    ArmorAbilityType.ELEMENTAL_STRIKE: ElementalStrikeArmorAbility(),
    ArmorAbilityType.FEINT: FeintArmorAbility(),
}


def get_duelist_armor_ability(ability_type: str) -> Optional[DuelistArmorAbility]:
    return DUELIST_ARMOR_ABILITY_MAP.get(ability_type)
