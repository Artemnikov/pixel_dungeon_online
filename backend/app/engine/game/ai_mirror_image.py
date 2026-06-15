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
"""Scroll of Mirror Image: spawn invisible hero clones that fight enemies.

Mirrors SPD's MirrorImage.java - clones have 1 HP, copy a fraction of the
hero's combat stats, and start invisible (guaranteeing their first attack is
a surprise hit). Movement/combat AI is the existing shadow-ally tick path.
"""

import random
import uuid
from typing import List, Optional

from app.engine.dungeon.spd_levelgen.level import _CIRCLE8_OFFSETS
from app.engine.entities.mobs import MirrorImage
from app.engine.entities.base import Position
from app.engine.game.floor_state import FloorState

# SPD's Scroll of Mirror Image always spawns 2 clones (no per-level scaling).
MIRROR_IMAGE_CLONE_COUNT = 2


class MirrorImageMixin:
    def _spawn_mirror_images(self, player, floor: FloorState, floor_id: int) -> List[str]:
        neighbors = list(_CIRCLE8_OFFSETS)
        random.shuffle(neighbors)

        occupied = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
        candidates = []
        for ddx, ddy in neighbors:
            cx, cy = player.pos.x + ddx, player.pos.y + ddy
            if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                continue
            if not floor.flags or not floor.flags.passable[cy][cx]:
                continue
            if (cx, cy) in occupied:
                continue
            candidates.append((cx, cy))
            occupied.add((cx, cy))
            if len(candidates) >= MIRROR_IMAGE_CLONE_COUNT:
                break

        clone_ids: List[str] = []
        for (cx, cy) in candidates:
            clone = MirrorImage(
                id=f"mirror_image_{uuid.uuid4().hex[:8]}",
                pos=Position(x=cx, y=cy),
            )
            clone.owner_id = player.id
            clone.add_buff("invisibility", duration=999999.0)
            floor.mobs[clone.id] = clone
            self._refresh_mirror_image_stats(clone, player, floor, floor_id)
            clone_ids.append(clone.id)

        return clone_ids

    def _refresh_mirror_image_stats(self, clone, owner, floor: FloorState, floor_id: int) -> None:
        if owner is None or not owner.is_alive or owner.floor_id != floor_id:
            clone.is_alive = False
            clone.hp = 0
            floor.mobs.pop(clone.id, None)
            self.add_event("DEATH", {"target": clone.id}, floor_id=floor_id)
            return

        clone.damage_min = max(1, (owner.get_damage_min() + 1) // 2)
        clone.damage_max = max(1, (owner.get_damage_max() + 1) // 2)
        clone.attack_skill = owner.attack_skill
        # SPD scales clone evasion by clone-level + hero evasion; there's no
        # "clone level" concept here, so this is a flat half of the hero's
        # effective defense skill as a simpler stand-in.
        clone.defense_skill = round(owner.get_effective_defense_skill() / 2)
        clone.dr_min = 0
        clone.dr_max = 2
        clone.view_distance = owner.view_distance
