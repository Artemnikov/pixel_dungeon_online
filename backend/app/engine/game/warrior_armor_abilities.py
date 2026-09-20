# Copyright (C) 2026 ArtemNikov
#
"""Polymorphic Warrior Armor Abilities Strategy Hierarchy.

Covers Heroic Leap, Shockwave, and Endure. Charge costs and the effects
themselves live on the ability classes; the class-wide if/elif dispatch in
ArmorAbilitiesMixin.use_armor_ability only needs a map lookup.
"""
from __future__ import annotations

import math
import random
from typing import Any, ClassVar, Dict, Optional, Tuple

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction, chebyshev_distance
from app.engine.entities.buffs import add_buff
from app.engine.entities.player import CharacterClass, Player
from app.engine.entities.subclasses import COST_ARMOR_ABILITY, COST_ENDURE, Subclass
from app.engine.entities.talent_enum import ArmorAbilityType, Talent
from app.engine.game.armor_ability_base import ArmorAbilityBase


class WarriorArmorAbility(ArmorAbilityBase):
    """Abstract Strategy interface for Warrior class armor abilities."""

    base_cost: int = COST_ARMOR_ABILITY
    required_class: ClassVar[str] = CharacterClass.WARRIOR
    heroic_scaled: bool = True


class HeroicLeapArmorAbility(WarriorArmorAbility):
    """35% Charge: Leap up to 4 tiles, slamming and knocking back enemies.

    Double Jump talent: every other leap is free; a paid leap arms the next
    one. Body Slam / Impact Wave add landing damage and knockback.
    """

    def get_cost(self, player: Player) -> int:
        cost = super().get_cost(player)
        double_jump = player.talent_info.level(Talent.DOUBLE_JUMP)
        if double_jump > 0:
            cost = int(cost * (0.84 ** double_jump))
        return cost

    def can_use(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        guard = self._class_guard(player)
        if guard is not None:
            return False, guard
        if tx is None or ty is None:
            return False, "Target position required"
        floor = game._get_or_create_floor(player.floor_id)
        if not (0 <= tx < floor.width and 0 <= ty < floor.height):
            return False, "Target out of bounds"
        if floor.grid[ty][tx] == TileType.WALL:
            return False, "Cannot leap onto a wall"
        dist = chebyshev_distance(player.pos.x, player.pos.y, tx, ty)
        if dist < 1 or dist > 4:
            return False, "Leap targets must be 1-4 tiles away"
        double_jump = player.talent_info.level(Talent.DOUBLE_JUMP)
        free_jump = double_jump > 0 and player.double_jump_ready
        if not free_jump:
            charge_error = self._check_charge(player)
            if charge_error is not None:
                return False, charge_error
        return True, None

    def _spend(self, player: Player) -> bool:
        double_jump = player.talent_info.level(Talent.DOUBLE_JUMP)
        free_jump = double_jump > 0 and player.double_jump_ready
        if free_jump:
            player.double_jump_ready = False
            return True
        cost = self.get_cost(player)
        if player.armor_charge < cost:
            return False
        player.armor_charge -= cost
        if double_jump > 0:
            player.double_jump_ready = True
        return True

    def perform(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> None:
        if tx is None or ty is None:
            return  # can_use already requires a target; guard for typing/safety
        floor = game._get_or_create_floor(player.floor_id)
        player.pos.x, player.pos.y = tx, ty
        game._invalidate_fov_cache()
        game.add_event(
            "MOVE", {"entity": player.id, "x": tx, "y": ty}, floor_id=player.floor_id
        )
        game.add_event(
            "PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=player.floor_id, source_player_id=player.id
        )

        ti = player.talent_info
        body_slam = ti.level(Talent.BODY_SLAM)
        impact_wave = ti.level(Talent.IMPACT_WAVE)

        slammed = set()
        for dy_off in (-1, 0, 1):
            for dx_off in (-1, 0, 1):
                if dx_off == 0 and dy_off == 0:
                    continue
                cx, cy = tx + dx_off, ty + dy_off
                if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                    continue
                for mob in list(floor.mobs.values()):
                    if not (mob.is_alive and mob.pos.x == cx and mob.pos.y == cy):
                        continue
                    if body_slam > 0:
                        dmg = random.randint(body_slam, 4 * body_slam)
                        dmg += round(random.randint(player.get_dr_min(), player.get_dr_max()) * 0.25 * body_slam)
                        dmg -= random.randint(mob.get_dr_min(), mob.get_dr_max())
                        dmg = max(0, dmg)
                        mob.hp -= dmg
                        slammed.add(mob.id)
                        game.add_event("DAMAGE", {"target": mob.id, "amount": dmg}, floor_id=player.floor_id)
                        if not mob.is_alive:
                            game.add_event("DEATH", {"target": mob.id}, floor_id=player.floor_id)

        if impact_wave > 0:
            for dy_off in (-1, 0, 1):
                for dx_off in (-1, 0, 1):
                    if dx_off == 0 and dy_off == 0:
                        continue
                    cx, cy = tx + dx_off, ty + dy_off
                    if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                        continue
                    for mob in list(floor.mobs.values()):
                        if not (mob.is_alive and mob.pos.x == cx and mob.pos.y == cy):
                            continue
                        if mob.id in slammed:
                            continue
                        knock = 1 + impact_wave
                        knock_x = cx + (cx - tx) * knock
                        knock_y = cy + (cy - ty) * knock
                        if 0 <= knock_x < floor.width and 0 <= knock_y < floor.height and floor.grid[knock_y][knock_x] != TileType.WALL:
                            mob.pos.x = knock_x
                            mob.pos.y = knock_y
                        if random.randint(0, 3) < impact_wave:
                            add_buff(mob.buffs, "vulnerable", duration=5.0, level=1)


class ShockwaveArmorAbility(WarriorArmorAbility):
    """35% Charge: cone shockwave damaging and knocking back enemies.

    Expanding Wave widens the cone, Striking Wave adds combo synergy, and
    Shock Force amps damage and stuns.
    """

    def perform(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> None:
        floor = game._get_or_create_floor(player.floor_id)
        game.add_event(
            "PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=player.floor_id, source_player_id=player.id
        )

        ti = player.talent_info
        expanding = ti.level(Talent.EXPANDING_WAVE)
        striking = ti.level(Talent.STRIKING_WAVE)
        shock_force = ti.level(Talent.SHOCK_FORCE)

        scaling_str = player.get_effective_strength() - 10
        max_dist = 5 + expanding
        cone_deg = 60 + 15 * expanding
        half_cone = math.radians(cone_deg / 2)

        aim_x = tx if tx is not None else player.pos.x
        aim_y = ty if ty is not None else player.pos.y
        dir_x, dir_y = aim_x - player.pos.x, aim_y - player.pos.y
        if dir_x == 0 and dir_y == 0:
            dir_x, dir_y = 0, 1
        dir_angle = math.atan2(dir_y, dir_x)

        hit_any = False
        for mob in list(floor.mobs.values()):
            if not mob.is_alive or mob.faction == Faction.PLAYER:
                continue
            mx, my = mob.pos.x - player.pos.x, mob.pos.y - player.pos.y
            dist = chebyshev_distance(player.pos.x, player.pos.y, mob.pos.x, mob.pos.y)
            if dist < 1 or dist > max_dist:
                continue
            angle = math.atan2(my, mx)
            diff = abs(math.atan2(math.sin(angle - dir_angle), math.cos(angle - dir_angle)))
            if diff > half_cone:
                continue

            dmg = random.randint(5 + scaling_str, 10 + 2 * scaling_str)
            dmg -= random.randint(mob.get_dr_min(), mob.get_dr_max())
            if shock_force > 0:
                dmg = int(dmg * (1 + 0.2 * shock_force))
            dmg = max(0, dmg)
            mob.hp -= dmg
            hit_any = True
            game.add_event("DAMAGE", {"target": mob.id, "amount": dmg}, floor_id=player.floor_id)
            if not mob.is_alive:
                game.add_event("DEATH", {"target": mob.id}, floor_id=player.floor_id)
                continue

            if shock_force > 0 and random.randint(0, 3) < shock_force:
                add_buff(mob.buffs, "paralysis", duration=5.0, level=1)
            else:
                knock_x = mob.pos.x + (mob.pos.x - player.pos.x)
                knock_y = mob.pos.y + (mob.pos.y - player.pos.y)
                if 0 <= knock_x < floor.width and 0 <= knock_y < floor.height and floor.grid[knock_y][knock_x] != TileType.WALL:
                    mob.pos.x = knock_x
                    mob.pos.y = knock_y
                add_buff(mob.buffs, "cripple", duration=5.0, level=1)

            if striking > 0 and random.randint(0, 9) < 3 * striking:
                game.add_event("PLAY_SOUND", {"sound": "HIT"}, floor_id=player.floor_id, source_player_id=player.id)
                if player.subclass_info.subclass == Subclass.GLADIATOR:
                    player.combo_count += 1
                    player.combo_timer = max(player.combo_timer, 5.0)
                if striking >= 4:
                    add_buff(player.buffs, "striking_wave_tracker", duration=5.0, level=1)

        if hit_any:
            game._invalidate_fov_cache()


class EndureArmorAbility(WarriorArmorAbility):
    """50% Charge: temporarily absorb damage, converting it to bonus damage.

    Sustained Retribution / Even the Odds scale the payout (see
    ArmorAbilitiesMixin._finalize_endure at tick time).
    """

    base_cost = COST_ENDURE

    def perform(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> None:
        player.endure_banked = 0.0
        add_buff(player.buffs, "endure_tracker", duration=12.0, level=1)
        # Endure + Combo (Gladiator): activating Endure while Combo is
        # active adds 3 turns to the combo timer.
        if player.subclass_info.subclass == Subclass.GLADIATOR and player.combo_count > 0:
            player.combo_timer += 3.0
        game.add_event(
            "PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=player.floor_id, source_player_id=player.id
        )


WARRIOR_ARMOR_ABILITY_MAP: Dict[str, WarriorArmorAbility] = {
    ArmorAbilityType.HEROIC_LEAP: HeroicLeapArmorAbility(),
    ArmorAbilityType.SHOCKWAVE: ShockwaveArmorAbility(),
    ArmorAbilityType.ENDURE: EndureArmorAbility(),
}