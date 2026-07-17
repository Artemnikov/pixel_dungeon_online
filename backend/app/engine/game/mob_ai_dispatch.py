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
"""Per-mob tick entry point: skip/ally handling and dispatch to boss-specific
AI update methods (defined in the various ai_*.py mixins), falling through to
generic mob AI (see mob_ai_movement.py) when no special case applies.
"""

import time
from typing import Optional

from app.engine.entities.base import Faction, Position
from app.engine.entities.mobs import (
    CrystalMimic, GhostHeroMob, MirrorImage, Goo, DwarfKing, YogDzewa, DM300,
    DemonSpawner, Pylon, BurningFist, SoiledFist, RottingFist, RustedFist,
    BrightFist, DarkFist, Guard, Necromancer, Tengu, Eye, RedShaman,
    BlueShaman, PurpleShaman, Warlock, Spinner, DM200,
)
from app.engine.entities.wandmaker_quest import NewbornFireElemental
from app.engine.game.constants import AUTO_MOVE_INTERVAL
from app.engine.game.floor_state import FloorState


class MobAIDispatchMixin:
    def _tick_mob(self, mob, floor: FloorState, floor_id: int) -> None:
        if not mob.is_alive:
            return

        if isinstance(mob, CrystalMimic) and mob.disguised:
            return

        if mob.faction == Faction.PLAYER:
            if isinstance(mob, GhostHeroMob):
                owner = self.players.get(mob.owner_id)
                self._refresh_ghost_hero_stats(mob, owner, floor, floor_id)
                if not mob.is_alive:
                    return
            if isinstance(mob, MirrorImage):
                owner = self.players.get(mob.owner_id)
                self._refresh_mirror_image_stats(mob, owner, floor, floor_id)
                if not mob.is_alive:
                    return
            if mob.type not in ("ninja_log", "npc"):
                self._update_shadow_ally(mob, floor, floor_id)
            return

        if isinstance(mob, Goo):
            if self._update_goo(mob, floor, floor_id):
                return

        if isinstance(mob, DwarfKing):
            self._update_dwarf_king(mob, floor, floor_id)
            if "IMMOVABLE" in getattr(mob, "properties", []):
                return

        if isinstance(mob, YogDzewa):
            self._update_yog_dzewa(mob, floor, floor_id)
            return

        if isinstance(mob, DM300):
            if not mob.fight_started:
                target = self._find_nearest_player(mob.pos, floor_id)
                if target is not None:
                    mob.fight_started = True
                    self.add_event("DM300_FIGHT_STARTED", {"mob": mob.id}, floor_id=floor_id)
            if mob.supercharged:
                self._update_dm300_chase(mob, floor, floor_id)
                self._update_dm300_chase(mob, floor, floor_id)
                return

        if isinstance(mob, DemonSpawner):
            self._update_demon_spawner(mob, floor, floor_id)
            return

        if isinstance(mob, Pylon):
            self._update_pylon(mob, floor, floor_id)
            return

        if isinstance(mob, (BurningFist, SoiledFist, RottingFist,
                             RustedFist, BrightFist, DarkFist)):
            if self._update_yog_fist(mob, floor, floor_id):
                return

        if isinstance(mob, Guard):
            self._update_guard(mob, floor, floor_id)

        if isinstance(mob, Necromancer):
            if self._update_necromancer(mob, floor, floor_id):
                return

        if isinstance(mob, Tengu):
            if self._update_tengu(mob, floor, floor_id):
                return

        if isinstance(mob, Eye):
            if self._update_eye(mob, floor, floor_id):
                return

        if isinstance(mob, (RedShaman, BlueShaman, PurpleShaman)):
            if self._update_shaman(mob, floor, floor_id):
                return

        if isinstance(mob, Warlock):
            if self._update_warlock(mob, floor, floor_id):
                return

        if isinstance(mob, Spinner):
            if self._update_spinner(mob, floor, floor_id):
                return

        if isinstance(mob, DM200):
            if self._update_dm200(mob, floor, floor_id):
                return

        if isinstance(mob, NewbornFireElemental):
            if self._update_newborn_elemental(mob, floor, floor_id):
                return

        return self._tick_generic_mob_ai(mob, floor, floor_id)

    def _refresh_ghost_hero_stats(self, mob, owner, floor: FloorState, floor_id: int) -> None:
        from app.engine.entities.items_artifacts import DriedRose
        if owner is None or not owner.is_alive or owner.floor_id != floor_id:
            mob.is_alive = False
            mob.hp = 0
            floor.mobs.pop(mob.id, None)
            self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)
            return

        rose: Optional[DriedRose] = None
        for item in owner.belongings.all_items():
            if isinstance(item, DriedRose):
                rose = item
                break

        mhp = 20 if rose is None else 20 + 8 * rose.level
        mob.max_hp = mhp
        mob.hp = min(mob.hp, mhp)
        mob.defense_skill = owner.lvl + 4
        mob.attack_skill = owner.lvl + 9
        if rose and rose.weapon:
            mob.damage_min = rose.weapon.damage_min
            mob.damage_max = rose.weapon.damage_max
        else:
            mob.damage_min = 0
            mob.damage_max = 5

    def _update_shadow_ally(self, ally, floor: FloorState, floor_id: int):
        from app.engine.entities.mobs import GhostHeroMob
        move_times = getattr(self, "_ally_move_times", None)
        if move_times is None:
            move_times = self._ally_move_times = {}
        now = time.time()
        if now - move_times.get(ally.id, 0.0) < AUTO_MOVE_INTERVAL:
            return

        enemies = [m for m in floor.mobs.values()
                   if m.is_alive and m.faction != Faction.PLAYER]

        # If GhostHeroMob has a direct position, prioritize it
        if isinstance(ally, GhostHeroMob) and ally.direct_x is not None:
            dx, dy = ally.direct_x, ally.direct_y
            # Find nearest enemy to the direct position
            target = None
            best = 999
            for m in enemies:
                d = self._get_distance(Position(x=dx, y=dy), m.pos)
                if d < best and self._is_in_los(ally.pos, m.pos, floor_id=floor_id):
                    best, target = d, m
            if target is not None and best <= 1:
                move_times[ally.id] = now
                ally.last_attack_time = now - ally.attack_cooldown
                adx = (target.pos.x > ally.pos.x) - (target.pos.x < ally.pos.x)
                ady = (target.pos.y > ally.pos.y) - (target.pos.y < ally.pos.y)
                self.move_entity(ally.id, adx, ady)
                return
            if ally.pos.x != dx or ally.pos.y != dy:
                move_times[ally.id] = now
                step = self._get_next_step_to(ally.pos, Position(x=dx, y=dy), floor_id=floor_id, flying=getattr(ally, "flying", False))
                if step:
                    self.move_entity(ally.id, step[0], step[1])
                return
            # Already at direct position, defend it (attack adjacent enemies)
            if target is not None and best <= ally.attack_range:
                move_times[ally.id] = now
                ally.last_attack_time = now - ally.attack_cooldown
                adx = (target.pos.x > ally.pos.x) - (target.pos.x < ally.pos.x)
                ady = (target.pos.y > ally.pos.y) - (target.pos.y < ally.pos.y)
                self.move_entity(ally.id, adx, ady)
            return

        target = None
        best = 999
        for m in enemies:
            d = self._get_distance(ally.pos, m.pos)
            if d < best and self._is_in_los(ally.pos, m.pos, floor_id=floor_id):
                best, target = d, m

        if target is not None:
            move_times[ally.id] = now
            if best <= getattr(ally, "attack_range", 1):
                ally.last_attack_time = now - ally.attack_cooldown
                adx = (target.pos.x > ally.pos.x) - (target.pos.x < ally.pos.x)
                ady = (target.pos.y > ally.pos.y) - (target.pos.y < ally.pos.y)
                self.move_entity(ally.id, adx, ady)
            else:
                step = self._get_next_step_to(ally.pos, target.pos, floor_id=floor_id, flying=getattr(ally, "flying", False))
                if step:
                    self.move_entity(ally.id, step[0], step[1])
            return

        # No enemy visible: mirror images wander randomly (SPD MirrorImage
        # wanders like any mob when idle), other allies return to owner.
        if isinstance(ally, MirrorImage):
            step = self._pick_wander_step(ally, floor, floor_id, now)
            if step:
                move_times[ally.id] = now
                self.move_entity(ally.id, *step)
        else:
            owner = self.players.get(getattr(ally, "owner_id", None) or "")
            if owner is not None and owner.floor_id == floor_id:
                if self._get_distance(ally.pos, owner.pos) > 1:
                    move_times[ally.id] = now
                    step = self._get_next_step_to(ally.pos, owner.pos, floor_id=floor_id, flying=getattr(ally, "flying", False))
                    if step:
                        self.move_entity(ally.id, step[0], step[1])
