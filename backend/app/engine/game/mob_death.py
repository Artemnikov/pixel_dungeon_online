# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
"""Mob-death handling for GameInstance: boss-specific on-death drops and
SacrificialFire feeding, called at every mob-death site.

Split out of world.py, which used to bundle this with unrelated trap/search/
door and NPC shop/quest concerns.
"""

import random
import uuid

from app.engine.entities.base import Position
from app.engine.entities.items_consumable import Key
from app.engine.game.floor_state import FloorState
from app.engine.game.ai_goo import _goo_unseal_entrance

def _sacrifice_exp_value(mob) -> int:
    """Port of SacrificialFire.sacrifice()'s per-type exp lookup (same rates
    as Wand of Corruption, except Swarms)."""
    from app.engine.entities.mobs import (
        Bee, Mimic, GoldenMimic, EbonyMimic, CrystalMimic,
        Piranha, PhantomPiranha, Statue, ArmoredStatue, Swarm, TormentedSpirit, Wraith,
    )
    depth = getattr(mob, "floor_level", 1)
    if isinstance(mob, (Statue, ArmoredStatue, Mimic, GoldenMimic, EbonyMimic, CrystalMimic)):
        return 1 + depth
    if isinstance(mob, (Piranha, PhantomPiranha, Bee)):
        return 1 + depth // 2
    if isinstance(mob, (Wraith, TormentedSpirit)):
        return 1 + depth // 3
    if isinstance(mob, Swarm) and mob.exp == 0:
        return 1
    if mob.exp > 0:
        return 1 + mob.exp
    return 0


class MobDeathMixin:
    def _process_sacrifice_fire_death(self, mob, floor: FloorState, floor_id: int) -> None:
        """Port of SacrificialFire.sacrifice(): a mob that dies within the
        fire's blast radius (its 3x3 EMBERS block plus one ring of
        NEIGHBOURS9 marking) feeds the room's reward pool; once the pool is
        exhausted the pre-rolled prize drops. Simplified from SPD's
        continuous per-turn Marked-buff tracking to a proximity check taken
        at the moment of death (the fire only marks/consumes on death
        either way, so the outcome matches for the common case of a mob
        dying to a hit landed while adjacent to the fire)."""
        fires = floor.generation_meta.get("sacrifice_fires")
        if not fires:
            return
        for fire in fires:
            if fire["volume"] <= 0:
                continue
            fx, fy = fire["pos"]
            if max(abs(mob.pos.x - fx), abs(mob.pos.y - fy)) > 2:
                continue
            exp_value = _sacrifice_exp_value(mob) * random.randint(2, 3)
            if exp_value <= 0:
                self.add_event("SACRIFICE_UNWORTHY", {"x": mob.pos.x, "y": mob.pos.y}, floor_id=floor_id)
                return
            fire["volume"] -= exp_value
            if fire["volume"] > 0:
                self.add_event("SACRIFICE_FEED", {"x": fx, "y": fy}, floor_id=floor_id)
                return
            from app.engine.game.spd_adapter import _descriptor_to_item
            prize_item = _descriptor_to_item(fire["prize"], fx, fy)
            floor.items[prize_item.id] = prize_item
            self.add_event("SACRIFICE_REWARD", {"x": fx, "y": fy}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
            return

    def handle_mob_death(self, mob, floor: FloorState, floor_id: int) -> None:
        """Boss-specific on-death drops, called at every mob-death site.

        The Goo drops the key that unlocks the sealed arena exit (SPD Goo.die
        drops a WornKey). Regular loot (goo blobs) is handled by roll_drops; the
        key is dropped here because it needs the floor-specific lock id, and it
        must drop no matter how Goo died (melee or bleed) so progression can't
        soft-lock."""
        from app.engine.entities.items_consumable import DwarfToken
        from app.engine.entities.mobs import DM300, Golem, Goo, Monk, Necromancer, Pylon, Skeleton, Tengu, YogDzewa
        from app.engine.entities.wandmaker_quest import NewbornFireElemental, RotHeart
        from app.engine.entities.wandmaker_quest_items import Embers, RotberrySeed

        self._process_sacrifice_fire_death(mob, floor, floor_id)

        # Mimic/GoldenMimic/EbonyMimic die(): drop all carried items at the
        # mob's death position (SPD Mimic.die drops the `items` LinkedList).
        from app.engine.entities.mobs import EbonyMimic, GoldenMimic, Mimic as MimicCls
        if isinstance(mob, (MimicCls, GoldenMimic, EbonyMimic)) and mob.carried_items:
            for item in mob.carried_items:
                drop = item.model_copy(deep=True)
                drop.id = str(uuid.uuid4())
                drop.pos = Position(x=mob.pos.x, y=mob.pos.y)
                floor.items[drop.id] = drop
            mob.carried_items = []

        # Imp.Quest.process(): once the quest is given (and not yet
        # completed), killing a Monk (alternative) or Golem (!alternative)
        # anywhere in the dungeon (except floor 20) drops a DwarfToken.
        quest = self.run_state.imp_quest
        if quest.given and not quest.completed and floor_id != 20:
            wanted = Monk if quest.alternative else Golem
            if isinstance(mob, wanted):
                token = DwarfToken(id=str(uuid.uuid4()), pos=Position(x=mob.pos.x, y=mob.pos.y))
                floor.items[token.id] = token

        # RotHeart.die(): always drops the Rotberry seed, regardless of how
        # the Wandmaker quest's Rotberry variant is currently tracked.
        if isinstance(mob, RotHeart):
            seed = RotberrySeed(id=str(uuid.uuid4()), pos=Position(x=mob.pos.x, y=mob.pos.y))
            floor.items[seed.id] = seed

        # Elemental.NewbornFireElemental.die(): always drops embers.
        if isinstance(mob, NewbornFireElemental):
            embers = Embers(id=str(uuid.uuid4()), pos=Position(x=mob.pos.x, y=mob.pos.y))
            floor.items[embers.id] = embers

        # Ghost.Quest.process(): called directly from each quest-boss's
        # die() override in the original (FetidRat/GnollTrickster/GreatCrab),
        # gated by depth == the floor the quest was given on.
        ghost_quest = self.run_state.ghost_quest
        if ghost_quest.boss_id and mob.id == ghost_quest.boss_id and ghost_quest.process(floor_id):
            self.add_event("MESSAGE", {"text": "Thank you... come find me..."}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "GHOST"}, floor_id=floor_id)

        # CavesBossLevel.eliminatePylon -> DM300.loseSupercharge: when an
        # activated Pylon dies, DM300 becomes vulnerable again. No
        # chain-activation of another pylon.
        if isinstance(mob, Pylon):
            for other in floor.mobs.values():
                if isinstance(other, DM300):
                    other.supercharged = False
                    break

        # Skeleton explosion: play bones sound on death (SPD Skeleton.die)
        if isinstance(mob, Skeleton):
            self.add_event("PLAY_SOUND", {"sound": "BONES"}, floor_id=floor_id)

        # GhostHeroMob death: clear ghost_id on the owner's DriedRose so
        # the rose can be recharged and re-summoned.
        from app.engine.entities.items_artifacts import DriedRose
        from app.engine.entities.mobs import GhostHeroMob
        if isinstance(mob, GhostHeroMob) and mob.owner_id:
            owner = self.players.get(mob.owner_id)
            if owner:
                for item in owner.belongings.all_items():
                    if isinstance(item, DriedRose) and item.ghost_id == mob.id:
                        item.ghost_id = None
                        break

        # Necromancer.die(): kill the linked NecroSkeleton (mob.die already
        # zeroed its HP); emit DEATH so the frontend plays its death animation.
        if isinstance(mob, Necromancer) and mob.my_skeleton_id:
            skeleton = floor.mobs.get(mob.my_skeleton_id)
            if skeleton and not skeleton.is_alive:
                self.add_event("DEATH", {"target": skeleton.id}, floor_id=floor_id)

        # Tengu (floor 10): award base score + check badge qualification
        if isinstance(mob, Tengu):
            self.boss_scores[1] += 2000
            if self.qualified_for_boss_challenge:
                self.add_event("TENGU_BADGE_QUALIFIED", {}, floor_id=floor_id)
            self.add_event("BOSS_SLAIN", {"mob": mob.id, "depth": floor_id, "badge_image": 48}, floor_id=floor_id)
            self.add_event("BOSS_YELL", {"mob": mob.id, "text": "Free at last...",
                                         "x": mob.pos.x, "y": mob.pos.y}, floor_id=floor_id)
            return

        if isinstance(mob, YogDzewa):
            key_id = next(iter(floor.locked_doors.values()), "goo_door")
            if not any(isinstance(i, Key) and getattr(i, "key_id", None) == key_id
                       for i in floor.items.values()):
                key = Key(
                    id=str(uuid.uuid4()),
                    name="Worn Key",
                    pos=Position(x=mob.pos.x, y=mob.pos.y),
                    key_id=key_id,
                )
                floor.items[key.id] = key
            self.add_event("PLAY_SOUND", {"sound": "BOSS"}, floor_id=floor_id)
            return

        if not isinstance(mob, Goo):
            return
        key_id = next(iter(floor.locked_doors.values()), "goo_door")
        # Don't double-drop if the boss death is processed from two sites.
        if any(isinstance(i, Key) and getattr(i, "key_id", None) == key_id
               for i in floor.items.values()):
            return
        key = Key(
            id=str(uuid.uuid4()),
            name="Worn Key",
            pos=Position(x=mob.pos.x, y=mob.pos.y),
            key_id=key_id,
        )
        floor.items[key.id] = key
        self.add_event("PLAY_SOUND", {"sound": "BOSS"}, floor_id=floor_id)
        self.add_event("BOSS_SLAIN", {"mob": mob.id, "depth": floor_id, "badge_image": 15}, floor_id=floor_id)
        _goo_unseal_entrance(self, floor, floor_id)
        self.boss_scores[0] += 1000
        if self.qualified_for_boss_challenge:
            self.add_event("GOO_BADGE_QUALIFIED", {}, floor_id=floor_id)
