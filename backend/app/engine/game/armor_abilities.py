# Copyright (C) 2026 ArtemNikov
#
from typing import Any, Dict, Optional

from app.engine.entities.base import Faction, chebyshev_distance
from app.engine.entities.player import Player
from app.engine.entities.subclasses import Talent
from app.engine.game.cleric_armor_abilities import CLERIC_ARMOR_ABILITY_MAP
from app.engine.game.duelist_armor_abilities import DUELIST_ARMOR_ABILITY_MAP
from app.engine.game.rogue_armor_abilities import ROGUE_ARMOR_ABILITY_MAP
from app.engine.game.warrior_armor_abilities import WARRIOR_ARMOR_ABILITY_MAP


class ArmorAbilitiesMixin:
    # All class armor abilities dispatch through one polymorphic map. Each
    # class's abilities live in their own module with their own ABC + concrete
    # strategy classes (warrior_armor_abilities.py, rogue_armor_abilities.py,
    # cleric_armor_abilities.py, duelist_armor_abilities.py); costs, bounds,
    # and charge deduction all live on the ability classes. None targets are
    # resolved per ability.
    ARMOR_ABILITY_MAP: Dict[str, Any] = {
        **WARRIOR_ARMOR_ABILITY_MAP,
        **ROGUE_ARMOR_ABILITY_MAP,
        **CLERIC_ARMOR_ABILITY_MAP,
        **DUELIST_ARMOR_ABILITY_MAP,
    }

    def _finalize_endure(self, player: Player) -> None:
        banked = player.endure_banked
        player.endure_banked = 0.0
        if banked <= 0:
            return
        ti = player.subclass_info.talent_info
        sr = ti.level(Talent.SUSTAINED_RETRIBUTION)
        eto = ti.level(Talent.EVEN_THE_ODDS)
        if sr > 0:
            banked *= 1 + 0.15 * sr
        if eto > 0:
            floor = self._get_or_create_floor(player.floor_id)
            nearby = sum(
                1 for mob in floor.mobs.values()
                if mob.is_alive and mob.faction != Faction.PLAYER
                and chebyshev_distance(mob.pos.x, mob.pos.y, player.pos.x, player.pos.y) <= 2
            )
            banked *= 1 + nearby * 0.05 * eto
        player.endure_damage_bonus = banked
        player.endure_hits_left = 1 + sr

    def use_armor_ability(self, player_id: str, ability: str, target_x: Optional[int] = None, target_y: Optional[int] = None) -> None:
        player = self.players.get(player_id)
        if not player or player.is_downed or not player.is_alive:
            return

        ability_obj = self.ARMOR_ABILITY_MAP.get(ability)
        if ability_obj is not None:
            ability_obj.use(self, player, target_x, target_y)
