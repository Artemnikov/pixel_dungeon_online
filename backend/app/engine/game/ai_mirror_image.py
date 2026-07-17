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
"""Mirror Image spawning and stat refresh.

Mirrors SPD's MirrorImage.java - clones have 1 HP, copy a fraction of the
hero's combat stats (including Ring of Accuracy, Ring of Evasion, Ring of
Furor, weapon accuracy, weapon DR, and weapon reach), and start invisible
(guaranteeing their first attack is a surprise hit). Weapon enchantment
proc effects are delegated to the hero's weapon at attack time.
"""

import random
import uuid
from typing import List, Optional, TYPE_CHECKING

from app.engine.dungeon.spd_levelgen.level import _CIRCLE8_OFFSETS
from app.engine.entities.mobs import MirrorImage
from app.engine.entities.base import Position
from app.engine.game.floor_state import FloorState

if TYPE_CHECKING:
    from app.engine.entities.player import Player

MIRROR_IMAGE_CLONE_COUNT = 2


class MirrorImageMixin:
    def _spawn_mirror_images(
        self,
        player: "Player",
        floor: FloorState,
        floor_id: int,
        spawn_pos: Optional[Position] = None,
    ) -> List[str]:
        """Spawn mirror images around *spawn_pos* (defaults to player position).

        SPD's ``ScrollOfMirrorImage.spawnImages`` accepts an explicit pos
        used by CursedWand.SummonMonsters to place clones at the bolt
        collision cell instead of around the hero.
        """
        center = spawn_pos if spawn_pos is not None else player.pos
        neighbors = list(_CIRCLE8_OFFSETS)
        random.shuffle(neighbors)

        occupied = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
        candidates = []
        for ddx, ddy in neighbors:
            cx, cy = center.x + ddx, center.y + ddy
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

    def _refresh_mirror_image_stats(
        self, clone: MirrorImage, owner: "Player",
        floor: FloorState, floor_id: int,
    ) -> None:
        if owner is None or not owner.is_alive or owner.floor_id != floor_id:
            clone.is_alive = False
            clone.hp = 0
            floor.mobs.pop(clone.id, None)
            self.add_event("DEATH", {"target": clone.id}, floor_id=floor_id)
            return

        # --- damage (half hero damage, rounded up) ---
        clone.damage_min = max(1, (owner.get_damage_min() + 1) // 2)
        clone.damage_max = max(1, (owner.get_damage_max() + 1) // 2)

        # --- attack skill: 9 + hero.lvl, benefits from Ring of Accuracy ---
        from app.engine.entities.rings import accuracy_multiplier
        clone.attack_skill = int(owner.attack_skill * accuracy_multiplier(owner))

        # --- defense skill: 50/50 blend of base + hero evasion (incl. Ring of Evasion) ---
        from app.engine.entities.rings import evasion_multiplier
        base_evasion = 4 + owner.level
        hero_evasion = int(base_evasion * evasion_multiplier(owner))
        clone.defense_skill = (base_evasion + hero_evasion) // 2

        # --- DR: super.drRoll() + weapon.defenseFactor / 2 ---
        from app.engine.entities.items_equip import KindOfWeapon
        w = getattr(getattr(owner, "belongings", None), "weapon", None)
        weapon_dr_half = 0
        if isinstance(w, KindOfWeapon):
            weapon_dr_half = (w.dr_bonus_base + w.dr_bonus_per_lvl * w.level) // 2
        clone.dr_min = max(0, weapon_dr_half)
        clone.dr_max = max(1, 2 + weapon_dr_half)

        # --- attack delay: hero's weapon cooldown / Ring of Furor ---
        from app.engine.entities.rings import furor_multiplier
        if isinstance(w, KindOfWeapon):
            base_cooldown = w.attack_cooldown
        else:
            base_cooldown = 3.0
        clone.attack_cooldown = base_cooldown / furor_multiplier(owner)

        # --- attack range: weapon reach (e.g. Glaive range 2) ---
        if isinstance(w, KindOfWeapon):
            clone.attack_range = w.get_reach()
        else:
            clone.attack_range = 1

        clone.view_distance = owner.view_distance

        # Store owner weapon ref so combat.py can delegate enchant procs.
        clone._owner_weapon = w
