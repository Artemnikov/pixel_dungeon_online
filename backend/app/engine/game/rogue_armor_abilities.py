# Copyright (C) 2026 ArtemNikov
#
"""Polymorphic Rogue Armor Abilities Strategy Hierarchy.

Covers Smoke Bomb, Death Mark, and Shadow Clone. Charge costs and the effects
themselves live on the ability classes; the class-wide if/elif dispatch in
ArmorAbilitiesMixin.use_armor_ability only needs a map lookup.
"""
from __future__ import annotations

import uuid
from typing import Any, ClassVar, Dict, Optional, Tuple

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction, Position, chebyshev_distance, find_mob_at
from app.engine.entities.buffs import add_buff
from app.engine.entities.player import CharacterClass, Mob, Player
from app.engine.entities.talent_enum import ArmorAbilityType, Talent
from app.engine.game.armor_ability_base import ArmorAbilityBase

# Rogue armor ability charge costs (SPD baseChargeUse).
COST_SMOKE_BOMB = 50
COST_DEATH_MARK = 25
COST_SHADOW_CLONE = 35


class RogueArmorAbility(ArmorAbilityBase):
    """Abstract Strategy interface for Rogue class armor abilities."""

    base_cost: int = COST_SMOKE_BOMB
    required_class: ClassVar[str] = CharacterClass.ROGUE
    heroic_scaled: bool = False


class SmokeBombArmorAbility(RogueArmorAbility):
    """50% Charge: Blink up to 6 tiles, blinding adjacent foes.

    Shadow Step talent makes the jump free enough to keep stealth; Body
    Replacement leaves a Ninja Log decoy behind.
    """

    def get_cost(self, player: Player) -> int:
        cost = self.base_cost
        if player.invisible > 0 and player.talent_info.has(Talent.SHADOW_STEP):
            cost = int(cost * (0.84 ** player.talent_info.level(Talent.SHADOW_STEP)))
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
            return False, "Cannot blink onto a wall"
        dist = chebyshev_distance(tx, ty, player.pos.x, player.pos.y)
        if dist < 1 or dist > 6:
            return False, "Smoke Bomb targets must be 1-6 tiles away"
        if any(m.is_alive and m.pos.x == tx and m.pos.y == ty for m in floor.mobs.values()):
            return False, "Target cell is occupied"
        charge_error = self._check_charge(player)
        if charge_error is not None:
            return False, charge_error
        return True, None

    def perform(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> None:
        if tx is None or ty is None:
            return  # can_use already requires a target; guard for typing/safety
        floor = game._get_or_create_floor(player.floor_id)
        shadow_step = player.invisible > 0 and player.talent_info.has(Talent.SHADOW_STEP)

        body_replacement = player.talent_info.level(Talent.BODY_REPLACEMENT)
        if not shadow_step and body_replacement > 0:
            for mob in list(floor.mobs.values()):
                if mob.type == "ninja_log" and mob.owner_id == player.id:
                    mob.is_alive = False
                    game.add_event("DEATH", {"target": mob.id}, floor_id=player.floor_id)
            hp = 20 * body_replacement
            log = Mob(
                id=f"ninja_log_{uuid.uuid4().hex[:8]}",
                name="Ninja Log",
                type="ninja_log",
                pos=Position(x=player.pos.x, y=player.pos.y),
                hp=hp, max_hp=hp,
                attack=0, defense=0,
                defense_skill=0,
                dr_min=body_replacement, dr_max=3 * body_replacement,
                properties=["INORGANIC"],
                faction=Faction.PLAYER,
            )
            log.owner_id = player.id
            floor.mobs[log.id] = log
            game.add_event(
                "SPAWN", {"entity": log.id, "x": log.pos.x, "y": log.pos.y, "kind": "ninja_log"}, floor_id=player.floor_id
            )

        player.pos.x, player.pos.y = tx, ty
        game._invalidate_fov_cache()
        game.add_event("MOVE", {"entity": player.id, "x": tx, "y": ty}, floor_id=player.floor_id)
        game.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=player.floor_id, source_player_id=player.id)

        if not shadow_step:
            for mob in list(floor.mobs.values()):
                if not mob.is_alive or mob.faction == Faction.PLAYER:
                    continue
                if chebyshev_distance(mob.pos.x, mob.pos.y, tx, ty) <= 1:
                    add_buff(mob.buffs, "blinded", duration=5.0, level=1)
                    if getattr(mob, "ai_state", "") == "hunting":
                        mob.ai_state = "wandering"
            if player.talent_info.has(Talent.HASTY_RETREAT):
                dur = 1.0 + player.talent_info.level(Talent.HASTY_RETREAT)
                add_buff(player.buffs, "haste", duration=dur, level=1)
                player.add_buff("invisibility", duration=dur, level=1)


class DeathMarkArmorAbility(RogueArmorAbility):
    """25% Charge: Mark a visible enemy for +25% damage.

    Double Mark talent: every other mark is free (and otherwise cheaper).
    """

    base_cost = COST_DEATH_MARK

    def perform(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> None:
        """Unused — ``use`` is overridden for its charge state handling."""

    def use(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if self._class_guard(player) is not None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        target = find_mob_at(floor, tx, ty)
        if target is None or target.faction == Faction.PLAYER:
            return False
        if not game._is_in_los(player.pos, target.pos, floor_id=player.floor_id):
            return False

        # Double Mark: every other cast is free (and otherwise cheaper).
        double = player.talent_info.has(Talent.DOUBLE_MARK)
        cost = self.get_cost(player)
        if double and player.get_buff("double_mark_ready"):
            cost = 0
            player.remove_buff("double_mark_ready")
        elif double:
            cost = int(cost * (0.707 ** player.talent_info.level(Talent.DOUBLE_MARK)))
        if player.armor_charge < cost:
            return False
        player.armor_charge -= cost
        if double and not player.get_buff("double_mark_ready"):
            player.add_buff("double_mark_ready", duration=999.0, level=1)

        add_buff(target.buffs, "death_mark", duration=5.0, level=1, source_id=player.id)
        game.add_event(
            "DEATH_MARK", {"player": player.id, "target": target.id}, floor_id=player.floor_id, source_player_id=player.id
        )
        game.add_event("PLAY_SOUND", {"sound": "MELD"}, floor_id=player.floor_id, player_id=player.id)
        return True


class ShadowCloneArmorAbility(RogueArmorAbility):
    """35% Charge: Summon a shadow ally that scales with Shadow Clone talents."""

    base_cost = COST_SHADOW_CLONE

    def perform(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> None:
        """Unused — ``use`` is overridden so a failed summon never costs charge."""

    def use(
        self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]
    ) -> bool:
        if self._class_guard(player) is not None:
            return False
        cost = self.get_cost(player)
        if player.armor_charge < cost:
            return False

        floor = game._get_or_create_floor(player.floor_id)
        spawn = None
        for ddx, ddy in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            cx, cy = player.pos.x + ddx, player.pos.y + ddy
            if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                continue
            if not floor.flags or not floor.flags.passable[cy][cx]:
                continue
            if any(m.is_alive and m.pos.x == cx and m.pos.y == cy for m in floor.mobs.values()):
                continue
            spawn = (cx, cy)
            break
        if spawn is None:
            return False  # no valid spawn cell — never charge for a failed summon
        player.armor_charge -= cost

        perfect_copy = player.talent_info.level(Talent.PERFECT_COPY)
        hp = 80 + round(0.1 * perfect_copy * (15 + 5 * player.level))

        damage_min, damage_max = 10, 20
        shadow_blade = player.talent_info.level(Talent.SHADOW_BLADE)
        if shadow_blade > 0:
            weapon = player.belongings.weapon
            attack_delay = getattr(weapon, "attack_cooldown", 1.0) if weapon is not None else 1.0
            hero_avg_damage = (player.get_damage_min() + player.get_damage_max()) / 2
            bonus_dmg = round(0.08 * shadow_blade * (hero_avg_damage / attack_delay))
            if bonus_dmg > 0:
                damage_min += bonus_dmg
                damage_max += bonus_dmg

        dr_min, dr_max = 0, 2
        cloned_armor = player.talent_info.level(Talent.CLONED_ARMOR)
        if cloned_armor > 0:
            hero_avg_dr = (player.get_dr_min() + player.get_dr_max()) / 2
            bonus_dr = round(0.12 * cloned_armor * hero_avg_dr)
            if bonus_dr > 0:
                dr_min += bonus_dr
                dr_max += bonus_dr

        clone = Mob(
            id=f"shadow_clone_{uuid.uuid4().hex[:8]}",
            name="Shadow Clone",
            type="shadow_clone",
            pos=Position(x=spawn[0], y=spawn[1]),
            hp=hp, max_hp=hp,
            attack=10, defense=player.level + 4,
            defense_skill=player.level + 4,
            damage_min=damage_min, damage_max=damage_max,
            dr_min=dr_min, dr_max=dr_max,
            attack_cooldown=1.0,
            faction=Faction.PLAYER,
        )
        clone.owner_id = player.id
        floor.mobs[clone.id] = clone
        game.add_event(
            "PLAY_SOUND", {"sound": "PUFF"}, floor_id=player.floor_id, source_player_id=player.id
        )
        game.add_event(
            "SHADOW_CLONE",
            {"player": player.id, "clone": clone.id, "x": spawn[0], "y": spawn[1]},
            floor_id=player.floor_id,
        )
        return True


ROGUE_ARMOR_ABILITY_MAP: Dict[str, RogueArmorAbility] = {
    ArmorAbilityType.SMOKE_BOMB: SmokeBombArmorAbility(),
    ArmorAbilityType.DEATH_MARK: DeathMarkArmorAbility(),
    ArmorAbilityType.SHADOW_CLONE: ShadowCloneArmorAbility(),
}