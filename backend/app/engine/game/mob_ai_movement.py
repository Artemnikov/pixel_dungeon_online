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
"""Generic mob AI state machine: target acquisition/detection, fleeing,
engagement, and difficulty-scaled chase/wander movement. This is the
fallback path for mobs with no boss-specific update method (see
mob_ai_dispatch.py for the dispatch that leads here).
"""

import math
import random
import time

from app.engine.entities.base import Position
from app.engine.entities.buffs import is_frozen
from app.engine.entities.mobs import CrystalMimic, Goo
from app.engine.entities.player import Difficulty, Player
from app.engine.entities.wandmaker_quest import RotLasher
from app.engine.game.constants import AUTO_MOVE_INTERVAL
from app.engine.game.floor_state import FloorState


class MobAIMovementMixin:
    def _tick_generic_mob_ai(self, mob, floor: FloorState, floor_id: int) -> None:
        move_times = getattr(self, "_mob_move_times", None)
        if move_times is None:
            move_times = self._mob_move_times = {}
        now = time.time()
        move_interval = 2 * AUTO_MOVE_INTERVAL / max(0.1, mob.speed)
        if mob.has_buff("slow") or mob.has_buff("chill"):
            move_interval *= 2
        if mob.has_buff("paralysis"):
            move_interval = 9999
        # TimekeepersHourglass: frozen mobs skip AI entirely.
        if getattr(mob, "freeze_ticks", 0) > 0:
            mob.freeze_ticks -= 1
            return
        # SPD Frost paralyses: a frozen mob does nothing until it thaws.
        if is_frozen(mob.buffs):
            return
        can_move = now - move_times.get(mob.id, 0.0) >= move_interval

        if mob.has_buff("amok"):
            target_player = self._find_nearest_entity(mob.pos, floor_id, exclude_id=mob.id)
        else:
            target_player = self._find_nearest_player(mob.pos, floor_id)
        if mob.ai_state == "fleeing":
            if can_move and target_player:
                dx = mob.pos.x - target_player.pos.x
                dy = mob.pos.y - target_player.pos.y
                if abs(dx) >= abs(dy):
                    step = (1 if dx > 0 else -1, 0)
                else:
                    step = (0, 1 if dy > 0 else -1)
                nx, ny = mob.pos.x + step[0], mob.pos.y + step[1]
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    occupied = any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values() if m.id != mob.id)
                    if not occupied:
                        move_times[mob.id] = now
                        self.move_entity(mob.id, step[0], step[1])
            if isinstance(mob, CrystalMimic):
                active_players = [p for p in self._players_on_floor(floor_id) if p.is_alive]
                far_enough = all(
                    self._get_distance(mob.pos, p.pos) >= 6 for p in active_players
                )
                if far_enough and active_players:
                    fov_cells = set()
                    for p in active_players:
                        fov = self._fov_from(p.pos, floor, self._view_distance(p), viewer_id=p.id)
                        for fy in range(floor.height):
                            for fx in range(floor.width):
                                if fov[fy * floor.width + fx]:
                                    fov_cells.add((fx, fy))
                    if (mob.pos.x, mob.pos.y) not in fov_cells:
                        mob.is_alive = False
                        self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)
                        return
            return

        if target_player and isinstance(target_player, Player) and (target_player.invisible > 0 or target_player.is_afk):
            target_player = None

        if target_player and getattr(mob, "never_wakes", False):
            target_player = None
        elif target_player and isinstance(target_player, Player) and getattr(mob, "ai_state", "") in ("idle", "sleeping"):
            dist = self._get_distance(mob.pos, target_player.pos)
            # SPD Mob.act(): enemyInFOV needs fieldOfView[enemy.pos],
            # so high grass and walls block noticing, not just range.
            if dist > self._view_distance(mob) or not self._is_in_los(
                    mob.pos, target_player.pos, floor_id=floor_id,
                    distance=self._view_distance(mob)):
                target_player = None
            else:
                stealth = target_player.get_stealth()
                detect_chance = 1.0 / max(0.01, dist + stealth)
                subclass_info = getattr(target_player, "subclass_info", None)
                if subclass_info:
                    silent_level = subclass_info.talent_info.level("silent_steps")
                    if silent_level > 0 and dist >= 4 - silent_level:
                        detect_chance = 0.0
                if random.random() >= detect_chance:
                    target_player = None
                else:
                    mob.ai_state = "hunting"

        if target_player and isinstance(target_player, Player) and getattr(mob, "ai_state", "") == "wandering":
            dist = self._get_distance(mob.pos, target_player.pos)
            if dist > self._view_distance(mob) or not self._is_in_los(
                    mob.pos, target_player.pos, floor_id=floor_id,
                    distance=self._view_distance(mob)):
                target_player = None
            else:
                stealth = target_player.get_stealth()
                subclass_info = getattr(target_player, "subclass_info", None)
                if subclass_info:
                    stealth += subclass_info.talent_info.level("heightened_senses") * 2
                detect_chance = 1.0 / max(0.01, dist / 2 + stealth)
                if random.random() >= detect_chance:
                    target_player = None
                else:
                    mob.ai_state = "hunting"

        if (isinstance(mob, Goo) and mob.ai_state == "hunting" and not mob.fight_started
                and target_player is not None
                and self._is_in_los(mob.pos, target_player.pos, floor_id=floor_id,
                                     distance=self._view_distance(target_player))):
            mob.fight_started = True
            self.add_event("GOO_FIGHT_STARTED", {"mob": mob.id}, floor_id=floor_id)
            self.qualified_for_boss_challenge = True
            self._goo_seal_entrance(floor, floor_id)

        # Track last known position while target is visible (mirrors
        # SPD HUNTING: mob remembers where it last saw the player).
        # `target_player` comes from nearest-player search, not LOS, so
        # it stays non-None even behind a closed door - track visibility
        # separately or the search_pos fallback below never fires.
        target_in_los = target_player is not None and self._is_in_los(
            mob.pos, target_player.pos, floor_id=floor_id)
        if target_in_los:
            mob.last_known_target_pos = Position(x=target_player.pos.x, y=target_player.pos.y)

        # If target isn't currently visible (out of LOS - e.g. it just
        # walked through a door - or actually gone, e.g. invisible),
        # move toward the last known position. Once there with no
        # sign of them, drop the stale waypoint and amble (the wander
        # branch below) but stay "hunting" - reverting to "wandering"
        # here would route reacquisition through the ambient
        # stealth-roll notice check below, which is meant for mobs
        # that never noticed the player yet, not ones that just had
        # a door briefly block an already-spotted target. That roll
        # made re-chasing through doors unreliable.
        search_pos = None
        if not target_in_los and mob.ai_state == "hunting" and mob.last_known_target_pos is not None:
            search_pos = mob.last_known_target_pos
            # Must actually stand on the last-seen tile (not just be
            # adjacent) before giving up - the tile itself is often a
            # doorway, and stopping short of it means the mob never
            # steps through to the other side.
            if mob.pos.x == search_pos.x and mob.pos.y == search_pos.y:
                mob.last_known_target_pos = None
                search_pos = None

        dist = self._get_distance(mob.pos, target_player.pos) if target_player else float("inf")
        atk_range = getattr(mob, "attack_range", 1)
        is_passive = getattr(mob, "ai_state", "") == "passive"

        if is_passive and mob.hp >= mob.max_hp:
            if random.random() < 0.02:
                dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)])
                self.move_entity(mob.id, dx, dy)
            return

        # SPD's sleeping mobs stay completely motionless until they
        # notice a player - they don't amble around while "asleep".
        # "idle" is our default spawn state and maps to SPD's default
        # SLEEPING state (almost every mob starts asleep).
        if target_player is None and mob.ai_state in ("idle", "sleeping"):
            return

        # Char.Property.IMMOVABLE (getCloser()/getFurther() both
        # false in SPD): never chases, only attacks (bump-into, same
        # mechanism the difficulty branches below use) a target
        # already within range. Not itself difficulty-gated in SPD,
        # so this intercepts before the branches below.
        if isinstance(mob, RotLasher) and mob.hp < mob.max_hp and dist > 1:
            # RotLasher.act(): heals 5/turn whenever no enemy is
            # directly adjacent (checked before the IMMOVABLE
            # short-circuit below, same as Java's ordering).
            mob.hp = min(mob.max_hp, mob.hp + 5)

        if "IMMOVABLE" in getattr(mob, "properties", []):
            if target_player and dist <= atk_range:
                if not mob.engaged:
                    mob.engaged = True
                    mob.last_attack_time = time.time() - max(
                        0.0, mob.attack_cooldown - mob.aggro_windup
                    )
                dx, dy = target_player.pos.x - mob.pos.x, target_player.pos.y - mob.pos.y
                self.move_entity(mob.id, dx, dy)
            else:
                mob.engaged = False
            return

        in_attack_range = target_player is not None and dist <= atk_range
        if in_attack_range:
            if not mob.engaged:
                mob.engaged = True
                mob.last_attack_time = time.time() - max(
                    0.0, mob.attack_cooldown - mob.aggro_windup
                )
        else:
            mob.engaged = False

        if self.difficulty == Difficulty.EASY:
            if target_player and dist <= atk_range:
                dx, dy = target_player.pos.x - mob.pos.x, target_player.pos.y - mob.pos.y
                self.move_entity(mob.id, dx, dy)
            elif search_pos and can_move:
                step = self._get_next_step_to(mob.pos, search_pos, floor_id=floor_id, flying=mob.flying)
                if step:
                    move_times[mob.id] = now
                    self.move_entity(mob.id, step[0], step[1])
                else:
                    mob.last_known_target_pos = None
                    mob.ai_state = "wandering"
            elif can_move:
                step = self._pick_wander_step(mob, floor, floor_id, now)
                if step:
                    move_times[mob.id] = now
                    self.move_entity(mob.id, *step)

        elif self.difficulty == Difficulty.NORMAL:
            if target_player and dist <= atk_range:
                dx, dy = target_player.pos.x - mob.pos.x, target_player.pos.y - mob.pos.y
                self.move_entity(mob.id, dx, dy)
            elif target_player and target_in_los:
                if can_move:
                    step = self._get_next_step_to(mob.pos, target_player.pos, floor_id=floor_id, flying=mob.flying)
                    if step and (dist > atk_range or not any(
                        m.is_alive and m.pos.x == mob.pos.x + step[0] and m.pos.y == mob.pos.y + step[1]
                        for m in floor.mobs.values() if m.id != mob.id
                    )):
                        move_times[mob.id] = now
                        self.move_entity(mob.id, step[0], step[1])
            elif search_pos and can_move:
                step = self._get_next_step_to(mob.pos, search_pos, floor_id=floor_id, flying=mob.flying)
                if step:
                    move_times[mob.id] = now
                    self.move_entity(mob.id, step[0], step[1])
                else:
                    mob.last_known_target_pos = None
                    mob.ai_state = "wandering"
            elif can_move:
                step = self._pick_wander_step(mob, floor, floor_id, now)
                if step:
                    move_times[mob.id] = now
                    self.move_entity(mob.id, *step)

        elif self.difficulty == Difficulty.HARD:
            if target_player and dist <= atk_range:
                dx, dy = target_player.pos.x - mob.pos.x, target_player.pos.y - mob.pos.y
                self.move_entity(mob.id, dx, dy)
            elif target_player and dist < 20:
                if can_move:
                    step = self._get_next_step_to(mob.pos, target_player.pos, floor_id=floor_id, flying=mob.flying)
                    if step:
                        move_times[mob.id] = now
                        self.move_entity(mob.id, step[0], step[1])
            elif search_pos and can_move:
                step = self._get_next_step_to(mob.pos, search_pos, floor_id=floor_id, flying=mob.flying)
                if step:
                    move_times[mob.id] = now
                    self.move_entity(mob.id, step[0], step[1])
                else:
                    mob.last_known_target_pos = None
                    mob.ai_state = "wandering"
            elif can_move:
                step = self._pick_wander_step(mob, floor, floor_id, now)
                if step:
                    move_times[mob.id] = now
                    self.move_entity(mob.id, *step)

    def _pick_wander_step(self, mob, floor: FloorState, floor_id: int, now: float):
        """Step toward a wander waypoint, pausing briefly between waypoints.

        Mirrors SPD's WANDERING state: a mob picks a nearby destination and
        walks straight toward it, then pauses for a beat before picking a new
        one - rather than re-rolling a random direction every step.
        """
        targets = getattr(self, "_mob_wander_targets", None)
        if targets is None:
            targets = self._mob_wander_targets = {}
        pauses = getattr(self, "_mob_wander_pause_until", None)
        if pauses is None:
            pauses = self._mob_wander_pause_until = {}

        if now < pauses.get(mob.id, 0.0):
            return None

        def passable(x, y):
            if not (0 <= x < floor.width and 0 <= y < floor.height):
                return False
            return bool(floor.flags and floor.flags.passable[y][x])

        dest = targets.get(mob.id)
        if dest is not None and (mob.pos.x, mob.pos.y) == dest:
            # Reached the waypoint - pause for a beat before picking a new one.
            targets.pop(mob.id, None)
            pauses[mob.id] = now + random.uniform(0.5, 2.0)
            return None

        if dest is None:
            for _ in range(8):
                angle = random.random() * 2 * math.pi
                radius = random.uniform(3, 6)
                nx = int(round(mob.pos.x + math.cos(angle) * radius))
                ny = int(round(mob.pos.y + math.sin(angle) * radius))
                if passable(nx, ny):
                    dest = (nx, ny)
                    targets[mob.id] = dest
                    break
            if dest is None:
                return None

        step = self._get_next_step_to(mob.pos, Position(x=dest[0], y=dest[1]), floor_id=floor_id, flying=mob.flying)
        if step is None:
            targets.pop(mob.id, None)
            pauses[mob.id] = now + random.uniform(0.5, 1.0)
            return None
        return step
