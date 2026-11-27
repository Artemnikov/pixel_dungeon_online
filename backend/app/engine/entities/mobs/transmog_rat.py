# Copyright (C) 2026 ArtemNikov
#
"""SPD `Ratmogrify.TransmogRat`: an enemy temporarily turned into a rat.

The rat derives its stats from the mob it replaced, which is kept off the
floor until the transformation runs out (`TRANSMOG_RAT_DURATION` turns, the
`transmog_timer` buff) and is then put back with the rat's HP and position.
Ratlomacy makes the rat a permanent ally.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from app.engine.entities.base import Faction, Position
from app.engine.entities.locale_keys import mob_locale_key
from app.engine.entities.player import Mob as MobEntity
from app.engine.entities.talent_enum import Talent
from app.engine.game.constants import TRANSMOG_RAT_DURATION

TRANSMOG_TIMER = "transmog_timer"
RATSISTANCE_FACTOR = 0.9


class TransmogRat(MobEntity):
    name: str = "Ratmogrified Mob"
    mob_type: Optional[str] = "transmog_rat"
    original_name: str = ""
    original_locale_key: Optional[str] = None
    allied: bool = False
    attack_delay: float = 1.0
    caster_id: Optional[str] = None
    original: Optional[Any] = Field(default=None, exclude=True)

    _caster: Any = None

    @classmethod
    def transform(cls, game, floor, floor_id: int, original: MobEntity, caster) -> "TransmogRat":
        """SPD `Ratmogrify.activate` enemy branch: swap `original` for a rat
        on the same cell."""
        rat = cls(pos=Position(x=original.pos.x, y=original.pos.y))
        rat.floor_id = floor_id
        rat.setup(original, caster)

        # SPD Actor.remove(ch) detaches every buff that does not persist
        # through revival; the port has no such buff on mobs.
        original.buffs = []
        del floor.mobs[original.id]
        floor.mobs[rat.id] = rat
        rat.add_buff(TRANSMOG_TIMER, duration=TRANSMOG_RAT_DURATION, level=1)

        game.add_event("SPAWN_MOB", {"mob": rat.model_dump()}, floor_id=floor_id)
        game.add_event("WOOL_BURST", {"x": rat.pos.x, "y": rat.pos.y}, floor_id=floor_id)
        game.add_event("PLAY_SOUND", {"sound": "PUFF", "x": rat.pos.x, "y": rat.pos.y}, floor_id=floor_id)

        # For rare cases where a buff was keeping a mob alive.
        if rat.hp <= 0:
            rat.is_alive = False
            game.add_event("DEATH", {"target": rat.id}, floor_id=floor_id)
            game.handle_mob_death(rat, floor, floor_id)
        return rat

    def setup(self, original: MobEntity, caster) -> None:
        self.original = original
        self.caster_id = caster.id if caster is not None else None
        self._caster = caster
        self.original_name = original.name
        self.original_locale_key = mob_locale_key(original)
        self.name = f"Ratmogrified {original.name}"

        self.hp = original.hp
        self.max_hp = original.max_hp
        self.defense_skill = original.defense_skill
        self.attack_skill = original.attack_skill
        self.exp = original.exp
        self.max_lvl = original.max_lvl
        self.attack_cooldown = original.attack_cooldown
        self.attack_delay = float(getattr(original, "attack_delay", 1.0))
        # SPD rollToDropLoot() is delegated to the original; the port's drops
        # are table-driven, so the rat carries the original's tables.
        self.loot_table = list(original.loot_table)
        self.weighted_drops = list(original.weighted_drops)

        if original.ai_state == "sleeping":
            self.ai_state = "sleeping"
        elif original.ai_state == "hunting":
            self.ai_state = "hunting"
        else:
            self.ai_state = "wandering"

    def get_original(self) -> Optional[MobEntity]:
        if self.original is not None:
            self.original.hp = self.hp
            self.original.pos = Position(x=self.pos.x, y=self.pos.y)
        return self.original

    def get_damage_min(self) -> int:
        return self.original.get_damage_min() if self.original is not None else self.damage_min

    def get_damage_max(self) -> int:
        return self.original.get_damage_max() if self.original is not None else self.damage_max

    def get_dr_min(self) -> int:
        return self.original.get_dr_min() if self.original is not None else self.dr_min

    def get_dr_max(self) -> int:
        return self.original.get_dr_max() if self.original is not None else self.dr_max

    def adjust_damage_roll(self, roll: int) -> int:
        caster = self._caster
        if self.allied or caster is None:
            return roll
        points = caster.talent_info.level(Talent.RATSISTANCE)
        if points <= 0:
            return roll
        return int(roll * RATSISTANCE_FACTOR ** points)

    def make_ally(self) -> None:
        """SPD `TransmogRat.makeAlly`: friendly and permanent."""
        self.allied = True
        self.faction = Faction.PLAYER
        self.owner_id = self.caster_id
        self.remove_buff(TRANSMOG_TIMER)

    def revert(self, game, floor, floor_id: int) -> bool:
        """SPD `TransmogRat.act` once `timeLeft` runs out: put the original
        back where the rat stands. Returns True when the rat left the floor."""
        original = self.get_original()
        self.original = None
        if original is None or floor.mobs.get(self.id) is not self:
            return False
        self.exp = 0
        del floor.mobs[self.id]
        floor.mobs[original.id] = original
        game.add_event("SPAWN_MOB", {"mob": original.model_dump()}, floor_id=floor_id)
        game.add_event("WOOL_BURST", {"x": original.pos.x, "y": original.pos.y}, floor_id=floor_id)
        game.add_event("PLAY_SOUND", {"sound": "PUFF", "x": original.pos.x, "y": original.pos.y},
                       floor_id=floor_id)
        return True
