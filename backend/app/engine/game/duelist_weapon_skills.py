# Copyright (C) 2026 ArtemNikov
#
"""Polymorphic Weapon Skills Strategy Hierarchy for Duelist.

Every melee weapon in Shattered Pixel Dungeon has a unique weapon skill
that costs weapon charges to execute.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple, TYPE_CHECKING

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction, chebyshev_distance, find_mob_at
from app.engine.entities.buffs import add_buff, get_buff, has_buff, remove_buff
from app.engine.entities.talent_enum import Subclass, Talent
from app.engine.systems.combat import resolve_melee_attack

if TYPE_CHECKING:
    from app.engine.entities.items.equip import KindOfWeapon
    from app.engine.entities.player import Player
    from app.engine.manager import GameInstance


class WeaponSkill(ABC):
    """Abstract Strategy interface for all weapon skills."""

    id: str = "base_skill"
    name: str = "Base Skill"
    description: str = ""

    def charge_cost(self, player: Player, weapon: KindOfWeapon) -> float:
        """Base charge cost (typically 1.0)."""
        return 1.0

    @abstractmethod
    def requires_target(self) -> bool:
        """Whether this skill requires explicit target coordinates."""
        ...

    @abstractmethod
    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        """Validates prerequisites before charge deduction."""
        ...

    @abstractmethod
    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        """Executes the skill."""
        ...

    def on_melee_hit(self, game: GameInstance, player: Player) -> None:
        """Hook fired when the duelist lands a melee hit while wielding this
        weapon. Base: no-op; subclasses track per-skill state (e.g. combo
        hits for weapons using Combo Strike)."""

    def _apply_aggressive_barrier(self, game: GameInstance, player: Player) -> None:
        """Grants shielding if player has Aggressive Barrier and HP <= 50%."""
        if player.hp <= player.get_total_max_hp() * 0.5:
            ab_level = player.talent_info.level(Talent.AGGRESSIVE_BARRIER)
            if ab_level > 0:
                shield_amt = 1 + 2 * ab_level  # 3 at rank 1, 5 at rank 2
                player.add_shield("aggressive_barrier", shield_amt, priority=1, decay=600)
                game.add_event(
                    "SHIELD",
                    {"player": player.id, "amount": shield_amt, "source": "aggressive_barrier"},
                    floor_id=player.floor_id,
                    source_player_id=player.id,
                )

    def _apply_lethal_haste_on_kill(self, game: GameInstance, player: Player) -> None:
        """Grants Greater Haste if player has Lethal Haste talent."""
        lh_level = player.talent_info.level(Talent.LETHAL_HASTE)
        if lh_level > 0:
            duration = 1.0 + 2.0 * lh_level  # 3t at rank 1, 5t at rank 2
            add_buff(player.buffs, "haste", duration=duration, level=2)

    def _apply_precise_assault_tracker(self, game: GameInstance, player: Player) -> None:
        """Grants accuracy boost tracker on next melee attack if talent learned."""
        pa_level = player.talent_info.level(Talent.PRECISE_ASSAULT)
        if pa_level > 0:
            add_buff(player.buffs, "precise_assault_tracker", duration=5.0, level=pa_level)

    def _apply_varied_charge_check(self, game: GameInstance, player: Player, weapon: KindOfWeapon) -> None:
        """Champion Varied Charge: using 2 different weapon abilities sequentially restores charge."""
        subclass = getattr(player.subclass_info, "subclass", None)
        w_name = getattr(weapon, "name", "")
        if subclass == Subclass.CHAMPION:
            vc_level = player.talent_info.level(Talent.VARIED_CHARGE)
            if vc_level > 0 and player.last_weapon_ability_weapon_name and player.last_weapon_ability_weapon_name != w_name:
                # Regains +0.17 | +0.33 | +0.50 weapon charge
                refund = round(vc_level / 6.0, 2)
                player.gain_weapon_charge(refund)
        player.last_weapon_ability_id = self.id
        player.last_weapon_ability_weapon_name = w_name
        player.last_weapon_ability_turn = getattr(game, "turns", 0)

    def _apply_counter_ability_refund(self, game: GameInstance, player: Player) -> None:
        """Feint Counter Ability: Using weapon ability within 3t of afterimage trigger refunds charge."""
        if getattr(player, "feint_cooldown_refund_ready", False):
            player.feint_cooldown_refund_ready = False
            ca_level = player.talent_info.level(Talent.COUNTER_ABILITY)
            if ca_level > 0:
                refund = ca_level * 0.375
                player.gain_weapon_charge(refund)

    def _post_execute(self, game: GameInstance, player: Player, weapon: KindOfWeapon) -> None:
        """Shared post-execution triggers for weapon abilities."""
        self._apply_aggressive_barrier(game, player)
        self._apply_precise_assault_tracker(game, player)
        self._apply_varied_charge_check(game, player, weapon)
        self._apply_counter_ability_refund(game, player)


class LungeSkill(WeaponSkill):
    """Rapier / Katana: Leaps to adjacent cell and strikes with infinite accuracy."""

    id = "lunge"
    name = "Lunge"
    description = "Leap to an adjacent tile to strike an enemy 2 tiles away with infinite accuracy and bonus damage."

    def requires_target(self) -> bool:
        return True

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if tx is None or ty is None:
            return False, "Target required"
        dist = chebyshev_distance(player.pos.x, player.pos.y, tx, ty)
        if dist != 2:
            return False, "Target must be exactly 2 tiles away"
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None or target.faction == Faction.PLAYER:
            return False, "No valid enemy target"
        # Find intermediate landing cell
        dx = tx - player.pos.x
        dy = ty - player.pos.y
        step_x = player.pos.x + (1 if dx > 0 else (-1 if dx < 0 else 0))
        step_y = player.pos.y + (1 if dy > 0 else (-1 if dy < 0 else 0))
        if not (0 <= step_x < floor.width and 0 <= step_y < floor.height):
            return False, "Landing tile out of bounds"
        if floor.grid[step_y][step_x] == TileType.WALL:
            return False, "Landing tile blocked"
        if any(m.is_alive and m.pos.x == step_x and m.pos.y == step_y for m in floor.mobs.values()):
            return False, "Landing tile occupied"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None:
            return False
        dx = tx - player.pos.x
        dy = ty - player.pos.y
        step_x = player.pos.x + (1 if dx > 0 else (-1 if dx < 0 else 0))
        step_y = player.pos.y + (1 if dy > 0 else (-1 if dy < 0 else 0))

        # Leap to landing tile
        player.pos.x = step_x
        player.pos.y = step_y
        game.add_event("MOVE", {"entity": player.id, "x": step_x, "y": step_y}, floor_id=player.floor_id)

        lvl = weapon.buffed_lvl() if hasattr(weapon, "buffed_lvl") else weapon.level
        params = _skill_params(weapon)
        bonus = params.get("bonus", 5) + round(params.get("per_lvl", 1.5) * lvl)

        res = resolve_melee_attack(
            attacker=player,
            defender=target,
            floor_mobs=floor.mobs,
            tile_x=tx,
            tile_y=ty,
            dmg_bonus=bonus,
            guaranteed_hit=True,
            floor=floor,
            add_event=lambda t, d: game.add_event(t, d, floor_id=player.floor_id),
            game=game,
        )

        self._post_execute(game, player, weapon)

        if not target.is_alive:
            self._apply_lethal_haste_on_kill(game, player)
            game._finish_kill(player, target, floor, player.floor_id)
        return True


class SneakSkill(WeaponSkill):
    """Dagger / Dirk / Assassin's Blade: Teleport within range and gain Invisibility."""

    id = "sneak"
    name = "Sneak"
    description = "Instantly teleport to a target visible tile and turn invisible."

    def requires_target(self) -> bool:
        return True

    def _get_max_range(self, weapon: KindOfWeapon) -> int:
        return _skill_params(weapon).get("range", 3)  # Assassin's Blade default

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if tx is None or ty is None:
            return False, "Target tile required"
        max_r = self._get_max_range(weapon)
        dist = chebyshev_distance(player.pos.x, player.pos.y, tx, ty)
        if dist < 1 or dist > max_r:
            return False, f"Target out of range (max {max_r})"
        floor = game._get_or_create_floor(player.floor_id)
        if not (0 <= tx < floor.width and 0 <= ty < floor.height):
            return False, "Out of bounds"
        if floor.grid[ty][tx] == TileType.WALL:
            return False, "Target is a wall"
        if any(m.is_alive and m.pos.x == tx and m.pos.y == ty for m in floor.mobs.values()):
            return False, "Target tile occupied"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        player.pos.x = tx
        player.pos.y = ty
        game.add_event("MOVE", {"entity": player.id, "x": tx, "y": ty}, floor_id=player.floor_id)

        lvl = weapon.buffed_lvl() if hasattr(weapon, "buffed_lvl") else weapon.level
        duration = 2.0 + lvl
        add_buff(player.buffs, "invisibility", duration=duration)
        game.add_event("PLAY_SOUND", {"sound": "MELD"}, floor_id=player.floor_id, source_player_id=player.id)

        self._post_execute(game, player, weapon)
        return True


class CleaveSkill(WeaponSkill):
    """Shortsword / Sword / Greatsword: Infinite accuracy strike; free follow-up & instant on kill."""

    id = "cleave"
    name = "Cleave"
    description = "Strike an adjacent enemy with infinite accuracy. If it dies, the action is instant and the next Cleave is free."

    def charge_cost(self, player: Player, weapon: KindOfWeapon) -> float:
        if has_buff(player.buffs, "cleave_tracker"):
            return 0.0
        return 1.0

    def requires_target(self) -> bool:
        return True

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if tx is None or ty is None:
            return False, "Target required"
        dist = chebyshev_distance(player.pos.x, player.pos.y, tx, ty)
        if dist > 1:
            return False, "Enemy must be adjacent"
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None or target.faction == Faction.PLAYER:
            return False, "No valid enemy target"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None:
            return False

        lvl = weapon.buffed_lvl() if hasattr(weapon, "buffed_lvl") else weapon.level
        bonus = lvl + _skill_params(weapon).get("bonus", 3)

        remove_buff(player.buffs, "cleave_tracker")

        res = resolve_melee_attack(
            attacker=player,
            defender=target,
            floor_mobs=floor.mobs,
            tile_x=tx,
            tile_y=ty,
            dmg_bonus=bonus,
            guaranteed_hit=True,
            floor=floor,
            add_event=lambda t, d: game.add_event(t, d, floor_id=player.floor_id),
            game=game,
        )

        self._post_execute(game, player, weapon)

        if not target.is_alive:
            add_buff(player.buffs, "cleave_tracker", duration=5.0, level=1)
            self._apply_lethal_haste_on_kill(game, player)
            game._finish_kill(player, target, floor, player.floor_id)
        return True


class SpikeSkill(WeaponSkill):
    """Spear / Glaive: Reach strike knocking target back 1 tile."""

    id = "spike"
    name = "Spike"
    description = "Strike an enemy at reach range with infinite accuracy and knock them back 1 tile."

    def requires_target(self) -> bool:
        return True

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if tx is None or ty is None:
            return False, "Target required"
        dist = chebyshev_distance(player.pos.x, player.pos.y, tx, ty)
        if dist != 2:
            return False, "Target must be at reach distance (2 tiles)"
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None or target.faction == Faction.PLAYER:
            return False, "No valid enemy target"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None:
            return False

        lvl = weapon.buffed_lvl() if hasattr(weapon, "buffed_lvl") else weapon.level
        params = _skill_params(weapon)
        bonus = params.get("bonus", 9) + round(params.get("per_lvl", 2.0) * lvl)

        res = resolve_melee_attack(
            attacker=player,
            defender=target,
            floor_mobs=floor.mobs,
            tile_x=tx,
            tile_y=ty,
            dmg_bonus=bonus,
            guaranteed_hit=True,
            floor=floor,
            add_event=lambda t, d: game.add_event(t, d, floor_id=player.floor_id),
            game=game,
        )

        if target.is_alive:
            # Knock back 1 tile along trajectory
            dx = target.pos.x - player.pos.x
            dy = target.pos.y - player.pos.y
            kx = target.pos.x + (1 if dx > 0 else (-1 if dx < 0 else 0))
            ky = target.pos.y + (1 if dy > 0 else (-1 if dy < 0 else 0))
            if 0 <= kx < floor.width and 0 <= ky < floor.height and floor.grid[ky][kx] != TileType.WALL:
                if not any(m.is_alive and m.pos.x == kx and m.pos.y == ky for m in floor.mobs.values()):
                    target.pos.x = kx
                    target.pos.y = ky
                    game.add_event("MOVE", {"entity": target.id, "x": kx, "y": ky}, floor_id=player.floor_id)

        self._post_execute(game, player, weapon)

        if not target.is_alive:
            self._apply_lethal_haste_on_kill(game, player)
            game._finish_kill(player, target, floor, player.floor_id)
        return True


class DefensiveStanceSkill(WeaponSkill):
    """Quarterstaff: Triples evasion for 4 + lvl turns."""

    id = "defensive_stance"
    name = "Defensive Stance"
    description = "Assume a defensive stance, tripling your evasion for several turns."

    def requires_target(self) -> bool:
        return False

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        lvl = weapon.buffed_lvl() if hasattr(weapon, "buffed_lvl") else weapon.level
        duration = 4.0 + lvl
        add_buff(player.buffs, "defensive_stance", duration=duration, level=1)
        game.add_event("DEFENSIVE_STANCE", {"player": player.id, "duration": duration}, floor_id=player.floor_id)

        self._post_execute(game, player, weapon)
        return True


class SwordDanceSkill(WeaponSkill):
    """Scimitar: +60% attack speed and +50% accuracy for 4 + lvl turns."""

    id = "sword_dance"
    name = "Sword Dance"
    description = "Enter a fluid sword dance, granting +60% attack speed and +50% accuracy for several turns."

    def requires_target(self) -> bool:
        return False

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        lvl = weapon.buffed_lvl() if hasattr(weapon, "buffed_lvl") else weapon.level
        duration = 4.0 + lvl
        add_buff(player.buffs, "sword_dance", duration=duration, level=1)
        game.add_event("SWORD_DANCE", {"player": player.id, "duration": duration}, floor_id=player.floor_id)

        self._post_execute(game, player, weapon)
        return True


class HarvestSkill(WeaponSkill):
    """Sickle / War Scythe: Strikes with infinite accuracy, inflicting Bleeding."""

    id = "harvest"
    name = "Harvest"
    description = "Reap an adjacent enemy with infinite accuracy, inflicting severe bleeding damage over time."

    def requires_target(self) -> bool:
        return True

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if tx is None or ty is None:
            return False, "Target required"
        dist = chebyshev_distance(player.pos.x, player.pos.y, tx, ty)
        if dist > 1:
            return False, "Enemy must be adjacent"
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None or target.faction == Faction.PLAYER:
            return False, "No valid enemy target"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None:
            return False

        lvl = weapon.buffed_lvl() if hasattr(weapon, "buffed_lvl") else weapon.level
        params = _skill_params(weapon)
        total_bleed = round(params.get("total", 15) + params.get("per_lvl", 2.5) * lvl)
        add_buff(target.buffs, "bleeding", duration=10.0, level=total_bleed, stack_mode="extend")
        game.add_event("BLEED", {"target": target.id, "amount": total_bleed}, floor_id=player.floor_id)

        resolve_melee_attack(
            attacker=player,
            defender=target,
            floor_mobs=floor.mobs,
            tile_x=tx,
            tile_y=ty,
            guaranteed_hit=True,
            floor=floor,
            add_event=lambda t, d: game.add_event(t, d, floor_id=player.floor_id),
            game=game,
        )

        self._post_execute(game, player, weapon)
        if not target.is_alive:
            self._apply_lethal_haste_on_kill(game, player)
            game._finish_kill(player, target, floor, player.floor_id)
        return True


class LashSkill(WeaponSkill):
    """Whip: Strikes all visible enemies within 3 tiles simultaneously."""

    id = "lash"
    name = "Lash"
    description = "Lash all visible enemies within reach 3 simultaneously with infinite accuracy."

    def requires_target(self) -> bool:
        return False

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        floor = game._get_or_create_floor(player.floor_id)
        targets = [
            m for m in floor.mobs.values()
            if m.is_alive and m.faction != Faction.PLAYER
            and chebyshev_distance(player.pos.x, player.pos.y, m.pos.x, m.pos.y) <= 3
        ]
        for mob in targets:
            resolve_melee_attack(
                attacker=player,
                defender=mob,
                floor_mobs=floor.mobs,
                tile_x=mob.pos.x,
                tile_y=mob.pos.y,
                guaranteed_hit=True,
                floor=floor,
                add_event=lambda t, d: game.add_event(t, d, floor_id=player.floor_id),
                game=game,
            )
            if not mob.is_alive:
                self._apply_lethal_haste_on_kill(game, player)
                game._finish_kill(player, mob, floor, player.floor_id)

        self._post_execute(game, player, weapon)
        return True


class SpinSkill(WeaponSkill):
    """Flail: Channels power up to 3 stacks. Free on stacks 2 and 3."""

    id = "spin"
    name = "Spin"
    description = "Spin the flail to build momentum up to 3 stacks. Next melee attack gains infinite accuracy and massive bonus damage."

    def charge_cost(self, player: Player, weapon: KindOfWeapon) -> float:
        buff = get_buff(player.buffs, "spin_tracker")
        if buff is not None and buff.level >= 1:
            return 0.0
        return 1.0

    def requires_target(self) -> bool:
        return False

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        buff = get_buff(player.buffs, "spin_tracker")
        if buff is not None and buff.level >= 3:
            return False, "Already at maximum spin stacks (3)"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        buff = get_buff(player.buffs, "spin_tracker")
        cur_level = buff.level if buff else 0
        new_level = min(3, cur_level + 1)
        add_buff(player.buffs, "spin_tracker", duration=5.0, level=new_level)
        game.add_event("SPIN_UPDATE", {"player": player.id, "stacks": new_level}, floor_id=player.floor_id)

        self._post_execute(game, player, weapon)
        return True


class ComboStrikeSkill(WeaponSkill):
    """Gloves / Sai / Gauntlet: Consumes combo hits for bonus damage."""

    id = "combo_strike"
    name = "Combo Strike"
    description = "Unleash a flurry consuming all combo hits accumulated, dealing bonus damage per hit."

    def requires_target(self) -> bool:
        return True

    def on_melee_hit(self, game: GameInstance, player: Player) -> None:
        """Accumulate combo hits on every landed melee hit; consumed by the
        Combo Strike skill itself."""
        combo_buff = get_buff(player.buffs, "combo_hits_tracker")
        cur = combo_buff.level if combo_buff else 0
        add_buff(player.buffs, "combo_hits_tracker", duration=5.0, level=cur + 1)

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if tx is None or ty is None:
            return False, "Target required"
        dist = chebyshev_distance(player.pos.x, player.pos.y, tx, ty)
        if dist > 1:
            return False, "Enemy must be adjacent"
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None or target.faction == Faction.PLAYER:
            return False, "No valid enemy target"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None:
            return False

        combo_buff = get_buff(player.buffs, "combo_hits_tracker")
        combo_count = combo_buff.level if combo_buff else 1
        remove_buff(player.buffs, "combo_hits_tracker")

        lvl = weapon.buffed_lvl() if hasattr(weapon, "buffed_lvl") else weapon.level
        per_hit = lvl + _skill_params(weapon).get("per_hit", 3)
        bonus = per_hit * combo_count

        res = resolve_melee_attack(
            attacker=player,
            defender=target,
            floor_mobs=floor.mobs,
            tile_x=tx,
            tile_y=ty,
            dmg_bonus=bonus,
            guaranteed_hit=True,
            floor=floor,
            add_event=lambda t, d: game.add_event(t, d, floor_id=player.floor_id),
            game=game,
        )

        self._post_execute(game, player, weapon)

        if not target.is_alive:
            self._apply_lethal_haste_on_kill(game, player)
            game._finish_kill(player, target, floor, player.floor_id)
        return True


class HeavyBlowSkill(WeaponSkill):
    """Cudgel / Hand Axe / Mace / Battle Axe / War Hammer: Inflicts Daze and bonus surprise damage."""

    id = "heavy_blow"
    name = "Heavy Blow"
    description = "Strike an adjacent enemy with infinite accuracy, inflicting Daze for 5 turns and high surprise bonus damage."

    def requires_target(self) -> bool:
        return True

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if tx is None or ty is None:
            return False, "Target required"
        dist = chebyshev_distance(player.pos.x, player.pos.y, tx, ty)
        if dist > 1:
            return False, "Enemy must be adjacent"
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None or target.faction == Faction.PLAYER:
            return False, "No valid enemy target"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None:
            return False

        lvl = weapon.buffed_lvl() if hasattr(weapon, "buffed_lvl") else weapon.level
        base_bonus = _skill_params(weapon).get("base", 3)
        bonus = base_bonus + round(1.5 * lvl)

        res = resolve_melee_attack(
            attacker=player,
            defender=target,
            floor_mobs=floor.mobs,
            tile_x=tx,
            tile_y=ty,
            dmg_bonus=bonus,
            guaranteed_hit=True,
            floor=floor,
            add_event=lambda t, d: game.add_event(t, d, floor_id=player.floor_id),
            game=game,
        )

        if target.is_alive:
            add_buff(target.buffs, "daze", duration=5.0, level=1)

        self._post_execute(game, player, weapon)

        if not target.is_alive:
            self._apply_lethal_haste_on_kill(game, player)
            game._finish_kill(player, target, floor, player.floor_id)
        return True


class RetributionSkill(WeaponSkill):
    """Greataxe: Low HP execute (HP < 50%), instant on kill."""

    id = "retribution"
    name = "Retribution"
    description = "Available only below 50% HP. Strike with extreme bonus damage; takes 0 turns if it kills the enemy."

    def requires_target(self) -> bool:
        return True

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if player.hp >= player.get_total_max_hp() * 0.5:
            return False, "Retribution requires HP < 50%"
        if tx is None or ty is None:
            return False, "Target required"
        dist = chebyshev_distance(player.pos.x, player.pos.y, tx, ty)
        if dist > 1:
            return False, "Enemy must be adjacent"
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None or target.faction == Faction.PLAYER:
            return False, "No valid enemy target"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None:
            return False

        lvl = weapon.buffed_lvl() if hasattr(weapon, "buffed_lvl") else weapon.level
        bonus = 15 + 2 * lvl

        res = resolve_melee_attack(
            attacker=player,
            defender=target,
            floor_mobs=floor.mobs,
            tile_x=tx,
            tile_y=ty,
            dmg_bonus=bonus,
            guaranteed_hit=True,
            floor=floor,
            add_event=lambda t, d: game.add_event(t, d, floor_id=player.floor_id),
            game=game,
        )

        self._post_execute(game, player, weapon)

        if not target.is_alive:
            self._apply_lethal_haste_on_kill(game, player)
            game._finish_kill(player, target, floor, player.floor_id)
        return True


class GuardSkill(WeaponSkill):
    """Round Shield / Greatshield: Grants Infinite Evasion against attacks."""

    id = "guard"
    name = "Guard"
    description = "Raise your shield, granting infinite evasion against all incoming attacks until your next action."

    def requires_target(self) -> bool:
        return False

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        lvl = weapon.buffed_lvl() if hasattr(weapon, "buffed_lvl") else weapon.level
        duration = lvl + _skill_params(weapon).get("duration", 5.0)
        add_buff(player.buffs, "guard_tracker", duration=duration, level=1)
        game.add_event("GUARD_ACTIVE", {"player": player.id, "duration": duration}, floor_id=player.floor_id)

        self._post_execute(game, player, weapon)
        return True


class ChargedShotSkill(WeaponSkill):
    """Crossbow: Next attack gains infinite accuracy and special payload effects."""

    id = "charged_shot"
    name = "Charged Shot"
    description = "Charge your crossbow. Next attack knocks back in melee or supercharges fired darts."

    def requires_target(self) -> bool:
        return False

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        add_buff(player.buffs, "charged_shot", duration=10.0, level=1)
        game.add_event("CHARGED_SHOT_READY", {"player": player.id}, floor_id=player.floor_id)

        self._post_execute(game, player, weapon)
        return True


class RunicSlashSkill(WeaponSkill):
    """Runic Blade: Multiplies enchantment proc power."""

    id = "runic_slash"
    name = "Runic Slash"
    description = "Strike with infinite accuracy, dramatically amplifying enchantment power and proc rate."

    def requires_target(self) -> bool:
        return True

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if tx is None or ty is None:
            return False, "Target required"
        dist = chebyshev_distance(player.pos.x, player.pos.y, tx, ty)
        if dist > 1:
            return False, "Enemy must be adjacent"
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None or target.faction == Faction.PLAYER:
            return False, "No valid enemy target"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None:
            return False

        lvl = weapon.buffed_lvl() if hasattr(weapon, "buffed_lvl") else weapon.level
        add_buff(player.buffs, "runic_slash_power", duration=1.0, level=3 + lvl)

        res = resolve_melee_attack(
            attacker=player,
            defender=target,
            floor_mobs=floor.mobs,
            tile_x=tx,
            tile_y=ty,
            guaranteed_hit=True,
            floor=floor,
            add_event=lambda t, d: game.add_event(t, d, floor_id=player.floor_id),
            game=game,
        )

        remove_buff(player.buffs, "runic_slash_power")

        self._post_execute(game, player, weapon)

        if not target.is_alive:
            self._apply_lethal_haste_on_kill(game, player)
            game._finish_kill(player, target, floor, player.floor_id)
        return True


class PierceSkill(WeaponSkill):
    """Pickaxe: Inflicts Vulnerable and deals massive bonus against inorganic foes."""

    id = "pierce"
    name = "Pierce"
    description = "Strike with infinite accuracy, inflicting Vulnerable and dealing bonus damage against inorganic foes."

    def requires_target(self) -> bool:
        return True

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        if tx is None or ty is None:
            return False, "Target required"
        dist = chebyshev_distance(player.pos.x, player.pos.y, tx, ty)
        if dist > 1:
            return False, "Enemy must be adjacent"
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None or target.faction == Faction.PLAYER:
            return False, "No valid enemy target"
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None:
            return False

        lvl = weapon.buffed_lvl() if hasattr(weapon, "buffed_lvl") else weapon.level
        is_inorganic = "INORGANIC" in getattr(target, "properties", []) or any(
            k in getattr(target, "name", "").lower() for k in ("crab", "spinner", "scorpio", "bee", "swarm", "statue", "golem")
        )
        bonus = 8 + 2 * lvl if is_inorganic else 0

        res = resolve_melee_attack(
            attacker=player,
            defender=target,
            floor_mobs=floor.mobs,
            tile_x=tx,
            tile_y=ty,
            dmg_bonus=bonus,
            guaranteed_hit=True,
            floor=floor,
            add_event=lambda t, d: game.add_event(t, d, floor_id=player.floor_id),
            game=game,
        )

        if target.is_alive:
            add_buff(target.buffs, "vulnerable", duration=3.0, level=1)

        self._post_execute(game, player, weapon)

        if not target.is_alive:
            self._apply_lethal_haste_on_kill(game, player)
            game._finish_kill(player, target, floor, player.floor_id)
        return True


class BrawlerStanceSkill(WeaponSkill):
    """Ring of Force: Toggles unarmed brawler stance."""

    id = "brawlers_stance"
    name = "Brawler's Stance"
    description = "Toggle unarmed brawling combat while retaining weapon attributes; reduces weapon charge regeneration."

    def charge_cost(self, player: Player, weapon: KindOfWeapon) -> float:
        return 0.0

    def requires_target(self) -> bool:
        return False

    def can_execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(
        self, game: GameInstance, player: Player, weapon: KindOfWeapon, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        player.brawler_stance = not player.brawler_stance
        player.brawler_stance_turns = 50 if player.brawler_stance else 0
        game.add_event(
            "BRAWLER_STANCE_TOGGLE",
            {"player": player.id, "active": player.brawler_stance},
            floor_id=player.floor_id,
        )
        return True


# ---------------------------------------------------------------------------
# Per-weapon skill parameters. Each skill family reads only its own tuning
# keys (bonus/per_lvl, range, base, per_hit, total, duration) from this table
# instead of string-matching weapon names. Missing entries fall back to the
# family's per-skill defaults, which mirror the original bonus tables.
# ---------------------------------------------------------------------------
WEAPON_SKILL_PARAMS: Dict[str, dict] = {
    # Lunge (Rapier / Katana)
    "Katana": {"bonus": 8, "per_lvl": 2.0},
    "Rapier": {"bonus": 5, "per_lvl": 1.5},
    # Sneak (Dagger / Dirk / Assassin's Blade) -- range per weapon
    "Dagger": {"range": 5},
    "Dirk": {"range": 4},
    "Assassin's Blade": {"range": 3},
    # Cleave (sword family) -- bonus damage
    "Greatsword": {"bonus": 7},
    "Longsword": {"bonus": 6},
    "Sword": {"bonus": 5},
    "Shortsword": {"bonus": 4},
    "Worn Shortsword": {"bonus": 3},
    # Spike (Spear / Glaive) -- bonus damage
    "Glaive": {"bonus": 12, "per_lvl": 2.5},
    "Spear": {"bonus": 9, "per_lvl": 2.0},
    # Harvest (Sickle / War Scythe) -- total bleed
    "War Scythe": {"total": 30, "per_lvl": 4.5},
    "Sickle": {"total": 15, "per_lvl": 2.5},
    # Combo Strike (Gloves / Sai / Gauntlet) -- damage per combo hit
    "Gauntlet": {"per_hit": 5},
    "Sai": {"per_hit": 4},
    "Gloves": {"per_hit": 3},
    # Heavy Blow (maces / axes) -- base bonus
    "War Hammer": {"base": 6},
    "Mace": {"base": 5},
    "Battle Axe": {"base": 5},
    "Hand Axe": {"base": 4},
    "Cudgel": {"base": 3},
    # Guard (Round Shield / Greatshield) -- stance duration
    "Greatshield": {"duration": 3.0},
    "Round Shield": {"duration": 5.0},
}


def _skill_params(weapon: Optional[KindOfWeapon]) -> dict:
    """Per-weapon skill tuning for the equipped weapon (empty for none)."""
    if weapon is None:
        return {}
    return WEAPON_SKILL_PARAMS.get(getattr(weapon, "name", ""), {})


# Registry mapping weapon names / IDs to WeaponSkill strategies
SKILL_LUNGE = LungeSkill()
SKILL_SNEAK = SneakSkill()
SKILL_CLEAVE = CleaveSkill()
SKILL_SPIKE = SpikeSkill()
SKILL_DEFENSIVE_STANCE = DefensiveStanceSkill()
SKILL_SWORD_DANCE = SwordDanceSkill()
SKILL_HARVEST = HarvestSkill()
SKILL_LASH = LashSkill()
SKILL_SPIN = SpinSkill()
SKILL_COMBO_STRIKE = ComboStrikeSkill()
SKILL_HEAVY_BLOW = HeavyBlowSkill()
SKILL_RETRIBUTION = RetributionSkill()
SKILL_GUARD = GuardSkill()
SKILL_CHARGED_SHOT = ChargedShotSkill()
SKILL_RUNIC_SLASH = RunicSlashSkill()
SKILL_PIERCE = PierceSkill()
SKILL_BRAWLER_STANCE = BrawlerStanceSkill()

# Fallback strategy for weapons not yet mapped to a unique skill (mirrors
# SPD's default-like behavior); explicit so unlisted weapons stay usable.
DEFAULT_SKILL: WeaponSkill = SKILL_CLEAVE

WEAPON_SKILL_MAP: Dict[str, WeaponSkill] = {
    # T1
    "Rapier": SKILL_LUNGE,
    "Dagger": SKILL_SNEAK,
    "Gloves": SKILL_COMBO_STRIKE,
    "Cudgel": SKILL_HEAVY_BLOW,
    "Worn Shortsword": SKILL_CLEAVE,
    # T2
    "Shortsword": SKILL_CLEAVE,
    "Hand Axe": SKILL_HEAVY_BLOW,
    "Spear": SKILL_SPIKE,
    "Quarterstaff": SKILL_DEFENSIVE_STANCE,
    "Dirk": SKILL_SNEAK,
    "Sickle": SKILL_HARVEST,
    "Pickaxe": SKILL_PIERCE,
    # T3
    "Sword": SKILL_CLEAVE,
    "Mace": SKILL_HEAVY_BLOW,
    "Scimitar": SKILL_SWORD_DANCE,
    "Round Shield": SKILL_GUARD,
    "Sai": SKILL_COMBO_STRIKE,
    "Whip": SKILL_LASH,
    # T4
    "Longsword": SKILL_CLEAVE,
    "Battle Axe": SKILL_HEAVY_BLOW,
    "Flail": SKILL_SPIN,
    "Runic Blade": SKILL_RUNIC_SLASH,
    "Assassin's Blade": SKILL_SNEAK,
    "Crossbow": SKILL_CHARGED_SHOT,
    "Katana": SKILL_LUNGE,
    # T5
    "Greatsword": SKILL_CLEAVE,
    "War Hammer": SKILL_HEAVY_BLOW,
    "Glaive": SKILL_SPIKE,
    "Greataxe": SKILL_RETRIBUTION,
    "Greatshield": SKILL_GUARD,
    "Gauntlet": SKILL_COMBO_STRIKE,
    "War Scythe": SKILL_HARVEST,
    # Unarmed / Ring of Force
    "Ring of Force": SKILL_BRAWLER_STANCE,
}


def get_weapon_skill_for_weapon(weapon: Optional[KindOfWeapon]) -> Optional[WeaponSkill]:
    """Retrieve the WeaponSkill strategy for a given weapon."""
    if weapon is None:
        return None
    name = getattr(weapon, "name", "")
    return WEAPON_SKILL_MAP.get(name, DEFAULT_SKILL)
