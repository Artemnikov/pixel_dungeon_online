# Copyright (C) 2026 ArtemNikov
#
"""SPD `Ratmogrify`: the class-agnostic armor ability the Rat King grants in
exchange for the Dwarf King's crown.

Targeting an enemy turns it into a `TransmogRat`; targeting an existing
TransmogRat befriends it (Ratlomacy); targeting yourself summons allied rats
(Ratforcements). Every refusal is reported before any charge is spent.
"""
from __future__ import annotations

import random
from typing import Any, Dict, Optional, Tuple

from app.engine.entities.base import Faction, is_boss_or_miniboss
from app.engine.entities.mobs.sewers import Rat, SpdRat
from app.engine.entities.mobs.transmog_rat import TransmogRat
from app.engine.entities.player import Mob, Player
from app.engine.entities.talent_enum import ArmorAbilityType, Talent
from app.engine.game.armor_ability_base import ArmorAbilityBase
from app.engine.game.boss_targets import player_fov
from app.engine.game.world import _free_neighbour_cells, _spawn_mob_at
from app.engine.systems.combat import _dispel_stealth

COST_RATMOGRIFY = 50
RATLOMACY_ADRENALINE_PER_POINT = 2.0

_MESSAGES: Dict[str, str] = {
    "no_target": "There's nothing to target there!",
    "self_target": "You can't target yourself!",
    "cant_transform": "You can't ratmogrify that!",
    "too_strong": "That enemy is too strong to ratmogrify!",
}
_MESSAGE_KEYS: Dict[str, str] = {
    "no_target": "ability.target.no_target",
    "self_target": "ability.target.self_target",
    "cant_transform": "ability.ratmogrify.cant_transform",
    "too_strong": "ability.ratmogrify.too_strong",
}


class RatmogrifyArmorAbility(ArmorAbilityBase):
    base_cost = COST_RATMOGRIFY
    required_class = ArmorAbilityType.RATMOGRIFY

    def _class_guard(self, player: Player) -> Optional[str]:
        # Any class may hold Ratmogrify; it is the hero's ability, not a class's.
        if player.armor_ability != ArmorAbilityType.RATMOGRIFY or player.is_downed or not player.is_alive:
            return "Only a hero with Ratmogrify may use this ability"
        return None

    def _resolve(self, game: Any, player: Player, tx: int, ty: int) -> Tuple[Optional[str], Any]:
        """SPD `Ratmogrify.activate` target checks: (refusal, target)."""
        floor = game._get_or_create_floor(player.floor_id)
        target = game._entity_at(floor, player.floor_id, tx, ty, exclude_id=None)
        if target is None or (tx, ty) not in player_fov(game, player):
            return "no_target", None
        if target is player:
            if player.talent_info.level(Talent.RATFORCEMENTS) <= 0:
                return "self_target", None
            return None, target
        if (not isinstance(target, Mob) or target.faction != Faction.DUNGEON
                or isinstance(target, SpdRat) or getattr(target, "disguised", False)):
            return "cant_transform", None
        if isinstance(target, TransmogRat):
            if target.allied or player.talent_info.level(Talent.RATLOMACY) <= 0:
                return "cant_transform", None
            return None, target
        if is_boss_or_miniboss(target):
            return "too_strong", None
        return None, target

    def can_use(self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]) -> Tuple[bool, Optional[str]]:
        ok, err = super().can_use(game, player, tx, ty)
        if not ok:
            return ok, err
        if tx is None or ty is None:
            return False, None
        refusal = self._resolve(game, player, tx, ty)[0]
        if refusal is not None:
            game.add_event("MESSAGE", {"key": _MESSAGE_KEYS[refusal], "text": _MESSAGES[refusal]},
                           floor_id=player.floor_id, player_id=player.id)
            return False, _MESSAGES[refusal]
        return True, None

    def perform(self, game: Any, player: Player, tx: Optional[int], ty: Optional[int]) -> None:
        if tx is None or ty is None:
            return
        target = self._resolve(game, player, tx, ty)[1]
        floor_id = player.floor_id
        floor = game._get_or_create_floor(floor_id)
        if target is player:
            self._ratforcements(game, player, floor, floor_id)
        elif isinstance(target, TransmogRat):
            self._ratlomacy(game, player, target, floor_id)
        else:
            TransmogRat.transform(game, floor, floor_id, target, player)
        _dispel_stealth(player)

    @staticmethod
    def _ratforcements(game: Any, player: Player, floor, floor_id: int) -> None:
        occupied = {(p.pos.x, p.pos.y) for p in game._players_on_floor(floor_id) if p.is_alive}
        spawn_points = [c for c in _free_neighbour_cells(floor, player.pos.x, player.pos.y)
                        if c not in occupied]
        rats_to_spawn = player.talent_info.level(Talent.RATFORCEMENTS)
        while rats_to_spawn > 0 and spawn_points:
            cx, cy = spawn_points.pop(random.randrange(len(spawn_points)))
            _spawn_mob_at(game, floor, floor_id, Rat, cx, cy,
                          faction=Faction.PLAYER, ai_state="hunting", owner_id=player.id)
            rats_to_spawn -= 1

    @staticmethod
    def _ratlomacy(game: Any, player: Player, rat: TransmogRat, floor_id: int) -> None:
        rat.make_ally()
        game.add_event("RATLOMACY", {"mob": rat.id, "x": rat.pos.x, "y": rat.pos.y}, floor_id=floor_id)
        game.add_event("PLAY_SOUND", {"sound": "TELEPORT", "x": rat.pos.x, "y": rat.pos.y}, floor_id=floor_id)
        points = player.talent_info.level(Talent.RATLOMACY)
        if points > 1:
            rat.add_buff("adrenaline", duration=RATLOMACY_ADRENALINE_PER_POINT * (points - 1), level=1)


RATMOGRIFY_ARMOR_ABILITY_MAP: Dict[str, ArmorAbilityBase] = {
    ArmorAbilityType.RATMOGRIFY: RatmogrifyArmorAbility(),
}
