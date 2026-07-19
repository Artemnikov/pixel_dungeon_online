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
""""Universal" filler StandardRoom subclasses (registration-table indices
25-34): reused across every region, not tied to one specific region's theme.
PlantsRoom, AquariumRoom, PlatformRoom, BurnedRoom, FissureRoom,
GrassyGraveRoom, StripedRoom, StudyRoom, SuspiciousChestRoom, MinefieldRoom.

Split out of standard_rooms.py, which used to hold all ~85 StandardRoom
subclasses across every region in one file.
"""

import math
from typing import List

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.geom import Point, Rect, _to_f32
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import DoorType
from app.engine.dungeon.spd_levelgen.room_types import SizeCategory, StandardRoom
from app.engine.dungeon.spd_random import SPDRandom
from app.engine.dungeon.spd_levelgen.standard_rooms_base import PatchRoom, _neighbours8

# -- "filler" StandardRoom subclasses (registration-table indices 25-34) ---

def _random_plant_seed(rng: SPDRandom):
    """Port of PlantsRoom.randomSeed(): Generator.randomUsingDefaults(SEED) in
    a do-while excluding Firebloom.Seed. Firebloom already carries weight 0 in
    the SEED chances table (generator._SEED[0] == 0.0), so Random.chances can
    never select it and the do-while always terminates after one draw."""
    from app.engine.dungeon.spd_levelgen.generator import _random_using_defaults_seed
    return _random_using_defaults_seed(rng)


class PlantsRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 5)

    def min_height(self) -> int:
        return max(super().min_height(), 5)

    def size_cat_probs(self):
        return [3.0, 1.0, 0.0]

    def merge(self, level, other, merge_rect, merge_terrain):
        if merge_terrain == terrain.EMPTY and isinstance(other, (PlantsRoom, GrassyGraveRoom)):
            super().merge(level, other, merge_rect, terrain.GRASS)
        else:
            super().merge(level, other, merge_rect, merge_terrain)

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.GRASS)
        Painter.fill(level, self, 2, terrain.HIGH_GRASS)

        if min(self.width(), self.height()) >= 7:
            Painter.fill(level, self, 3, terrain.GRASS)

        center = self.center(rng)

        if max(self.width(), self.height()) >= 9:
            if min(self.width(), self.height()) >= 11:
                Painter.draw_line(level, Point(self.left + 2, center.y), Point(self.right - 2, center.y), terrain.HIGH_GRASS)
                Painter.draw_line(level, Point(center.x, self.top + 2), Point(center.x, self.bottom - 2), terrain.HIGH_GRASS)
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x - 1, center.y - 1)))
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x + 1, center.y - 1)))
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x - 1, center.y + 1)))
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x + 1, center.y + 1)))
            elif self.width() > self.height() or (self.width() == self.height() and rng.IntMax(2) == 0):
                Painter.draw_line(level, Point(center.x, self.top + 2), Point(center.x, self.bottom - 2), terrain.HIGH_GRASS)
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x - 1, center.y)))
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x + 1, center.y)))
            else:
                Painter.draw_line(level, Point(self.left + 2, center.y), Point(self.right - 2, center.y), terrain.HIGH_GRASS)
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x, center.y - 1)))
                level.plant(_random_plant_seed(rng), level.point_to_cell(Point(center.x, center.y + 1)))
        else:
            level.plant(_random_plant_seed(rng), level.point_to_cell(center))

        for door in self.connected.values():
            door.set(DoorType.REGULAR)


class AquariumRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 7)

    def min_height(self) -> int:
        return max(super().min_height(), 7)

    def size_cat_probs(self):
        return [3.0, 1.0, 0.0]

    def can_place_item(self, p, level) -> bool:
        return super().can_place_item(p, level) and level.map[level.point_to_cell(p)] != terrain.WATER

    def can_place_character(self, p, level) -> bool:
        return super().can_place_character(p, level) and level.map[level.point_to_cell(p)] != terrain.WATER

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)
        Painter.fill(level, self, 2, terrain.EMPTY_SP)
        Painter.fill(level, self, 3, terrain.WATER)

        min_dim = min(self.width(), self.height())
        num_fish = (min_dim - 4) // 3

        for _ in range(num_fish):
            cls_name = "PhantomPiranha" if rng.Float() < 0.02 else "Piranha"
            while True:
                pos = level.point_to_cell(self.random(rng, 3))
                if level.map[pos] == terrain.WATER and level.find_mob(pos) is None:
                    break
            level.mobs.append(GenMob(cls_name=cls_name, pos=pos, depth=level.depth))

        for door in self.connected.values():
            door.set(DoorType.REGULAR)


class PlatformRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 6)

    def min_height(self) -> int:
        return max(super().min_height(), 6)

    def size_cat_probs(self):
        return [6.0, 3.0, 1.0]

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.CHASM)

        platforms: List[Rect] = []
        self._split_platforms(rng, Rect(self.left + 2, self.top + 2, self.right - 2, self.bottom - 2), platforms)

        for platform in platforms:
            Painter.fill(level, platform.left, platform.top,
                         platform.width() + 1, platform.height() + 1, terrain.EMPTY_SP)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)
            Painter.draw_inside(level, self, door, 2, terrain.EMPTY_SP)

    def _split_platforms(self, rng: SPDRandom, cur: Rect, all_platforms: List[Rect]) -> None:
        cur_area = (cur.width() + 1) * (cur.height() + 1)

        # chance to split scales between 0% and 100% between areas of 25 and 36
        if rng.Float() < (cur_area - 25) / 11.0:
            if cur.width() > cur.height() or (cur.width() == cur.height() and rng.IntMax(2) == 0):

                split_x = rng.IntRange(cur.left + 2, cur.right - 2)
                self._split_platforms(rng, Rect(cur.left, cur.top, split_x - 1, cur.bottom), all_platforms)
                self._split_platforms(rng, Rect(split_x + 1, cur.top, cur.right, cur.bottom), all_platforms)

                bridge_y = rng.NormalIntRange(cur.top, cur.bottom)
                all_platforms.append(Rect(split_x - 1, bridge_y, split_x + 1, bridge_y))

            else:
                split_y = rng.IntRange(cur.top + 2, cur.bottom - 2)
                self._split_platforms(rng, Rect(cur.left, cur.top, cur.right, split_y - 1), all_platforms)
                self._split_platforms(rng, Rect(cur.left, split_y + 1, cur.right, cur.bottom), all_platforms)

                bridge_x = rng.NormalIntRange(cur.left, cur.right)
                all_platforms.append(Rect(bridge_x, split_y - 1, bridge_x, split_y + 1))
        else:
            all_platforms.append(cur)


class BurnedRoom(PatchRoom):
    def size_cat_probs(self):
        return [4.0, 1.0, 0.0]

    def _fill(self) -> float:
        return min(1.0, 1.48 - (self.width() + self.height()) * 0.03)

    def _clustering(self) -> int:
        return 2

    def _ensure_path(self) -> bool:
        return False

    def _clean_edges(self) -> bool:
        return False

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        self._setup_patch(level, rng)

        # TrapMechanism.revealHiddenTrapChance() baseline (fresh game, no
        # trinket -> trinketLevel == -1) is always 0, so revealInc never
        # crosses 1 and the `case 3` branch always lands on SECRET_TRAP.
        for i in range(self.top + 1, self.bottom):
            for j in range(self.left + 1, self.right):
                if not self.patch[self._xy_to_patch_coords(j, i)]:
                    continue
                cell = i * level.width() + j
                roll = rng.IntMax(5)
                if roll == 0:
                    t = terrain.EMPTY
                elif roll == 1:
                    t = terrain.EMBERS
                elif roll == 2:
                    t = terrain.TRAP
                    # level.setTrap(BurningTrap().reveal(), cell) -- zero-RNG, omitted
                elif roll == 3:
                    t = terrain.SECRET_TRAP
                    # level.setTrap(BurningTrap().hide(), cell) -- zero-RNG, omitted
                else:
                    t = terrain.INACTIVE_TRAP
                    # level.setTrap(trap, cell) -- zero-RNG, omitted
                level.map[cell] = t


class FissureRoom(StandardRoom):
    def min_height(self) -> int:
        return max(5, super().min_height())

    def min_width(self) -> int:
        return max(5, super().min_width())

    def size_cat_probs(self):
        return [6.0, 3.0, 1.0]

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.geom import _f32_div

        Painter.fill(level, self, terrain.WALL)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)
        Painter.fill(level, self, 1, terrain.EMPTY)

        if self.square() <= 25:
            p = self.center(rng)
            Painter.set(level, p.x, p.y, terrain.CHASM)
        else:
            smallest_dim = min(self.width(), self.height())
            floor_w = int(math.sqrt(smallest_dim))
            edge_floor_chance = _to_f32(math.fmod(_to_f32(math.sqrt(smallest_dim)), 1.0))
            edge_floor_chance = _to_f32(_f32_div(
                _to_f32(edge_floor_chance + _to_f32((floor_w - 1) * 0.5)),
                _to_f32(floor_w),
            ))

            for i in range(self.top + 2, self.bottom - 1):
                for j in range(self.left + 2, self.right - 1):
                    v = min(i - self.top, self.bottom - i)
                    h = min(j - self.left, self.right - j)
                    if min(v, h) > floor_w or (min(v, h) == floor_w and rng.Float() > edge_floor_chance):
                        Painter.set(level, j, i, terrain.CHASM)

        # CavesFissureEntranceRoom/CavesFissureExitRoom inherit this paint()
        # without their own override (see the "entrance variants" section
        # below for the pattern other real-paint rooms use) -- carve/stamp
        # the transition tile here, same as _stub_paint's tail, so those
        # subclasses' floors always have their ENTRANCE/EXIT terrain even
        # though the anchor point may land on a just-painted CHASM cell.
        if self.is_entrance() or self.is_exit():
            cell = level.point_to_cell(self.random(rng, 2))
            for nb in _neighbours8(level.width()):
                Painter.set(level, cell + nb, terrain.EMPTY)
            Painter.set(level, cell, terrain.ENTRANCE if self.is_entrance() else terrain.EXIT)


class GrassyGraveRoom(StandardRoom):
    def merge(self, level, other, merge_rect, merge_terrain):
        if merge_terrain == terrain.EMPTY and isinstance(other, (GrassyGraveRoom, PlantsRoom)):
            super().merge(level, other, merge_rect, terrain.GRASS)
        else:
            super().merge(level, other, merge_rect, merge_terrain)

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)
        Painter.fill(level, self, 1, terrain.GRASS)

        w = self.width() - 2
        h = self.height() - 2
        n_graves = max(w, h) // 2

        index = rng.IntMax(n_graves)
        shift = rng.IntMax(2)
        for i in range(n_graves):
            if w > h:
                pos = self.left + 1 + shift + i * 2 + (self.top + 2 + rng.IntMax(h - 2)) * level.width()
            else:
                pos = (self.left + 2 + rng.IntMax(w - 2)) + (self.top + 1 + shift + i * 2) * level.width()
            if i == index:
                item = gen.generator_random(level.run_state.generator_state, rng, level.depth)
            else:
                gen._roll_gold_item(rng, level.depth)
                item = frozenset({"Gold"})
            level.drop(item, pos).type = "TOMB"


class StripedRoom(StandardRoom):
    def size_cat_probs(self):
        return [2.0, 1.0, 0.0]

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        if self.size_cat == SizeCategory.NORMAL:
            Painter.fill(level, self, 1, terrain.EMPTY_SP)
            if self.width() > self.height() or (self.width() == self.height() and rng.IntMax(2) == 0):
                i = self.left + 2
                while i < self.right:
                    Painter.fill(level, i, self.top + 1, 1, self.height() - 2, terrain.HIGH_GRASS)
                    i += 2
            else:
                i = self.top + 2
                while i < self.bottom:
                    Painter.fill(level, self.left + 1, i, self.width() - 2, 1, terrain.HIGH_GRASS)
                    i += 2

        elif self.size_cat == SizeCategory.LARGE:
            layers = (min(self.width(), self.height()) - 1) // 2
            for i in range(1, layers + 1):
                Painter.fill(level, self, i, terrain.EMPTY_SP if i % 2 == 1 else terrain.HIGH_GRASS)


class StudyRoom(StandardRoom):
    def min_width(self) -> int:
        return max(super().min_width(), 7)

    def min_height(self) -> int:
        return max(super().min_height(), 7)

    def size_cat_probs(self):
        return [2.0, 1.0, 0.0]

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.BOOKSHELF)
        Painter.fill(level, self, 2, terrain.EMPTY_SP)

        for door in self.connected.values():
            Painter.draw_inside(level, self, door, 2, terrain.EMPTY_SP)
            door.set(DoorType.REGULAR)

        if self.size_cat == SizeCategory.LARGE:
            pillar_w = (self.width() - 7) // 2
            pillar_h = (self.height() - 7) // 2

            Painter.fill(level, self.left + 3, self.top + 3, pillar_w, 1, terrain.BOOKSHELF)
            Painter.fill(level, self.left + 3, self.top + 3, 1, pillar_h, terrain.BOOKSHELF)

            Painter.fill(level, self.left + 3, self.bottom - 2 - 1, pillar_w, 1, terrain.BOOKSHELF)
            Painter.fill(level, self.left + 3, self.bottom - 2 - pillar_h, 1, pillar_h, terrain.BOOKSHELF)

            Painter.fill(level, self.right - 2 - pillar_w, self.top + 3, pillar_w, 1, terrain.BOOKSHELF)
            Painter.fill(level, self.right - 2 - 1, self.top + 3, 1, pillar_h, terrain.BOOKSHELF)

            Painter.fill(level, self.right - 2 - pillar_w, self.bottom - 2 - 1, pillar_w, 1, terrain.BOOKSHELF)
            Painter.fill(level, self.right - 2 - 1, self.bottom - 2 - pillar_h, 1, pillar_h, terrain.BOOKSHELF)

        center = self.center(rng)
        Painter.set(level, center, terrain.PEDESTAL)

        prize = level.find_prize_item(rng) if rng.IntMax(2) == 0 else None

        pos = level.point_to_cell(center)
        if prize is not None:
            level.drop(prize, pos)
        else:
            cat = "POTION" if rng.IntMax(2) == 0 else "SCROLL"
            item = gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, cat)
            level.drop(item, pos)


class SuspiciousChestRoom(StandardRoom):
    def min_width(self) -> int:
        return max(5, super().min_width())

    def min_height(self) -> int:
        return max(5, super().min_height())

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        item = level.find_prize_item(rng)
        if item is None:
            gen._roll_gold_item(rng, level.depth)  # new Gold().random()
            item = frozenset({"Gold"})

        center = level.point_to_cell(self.center(rng))
        Painter.set(level, center, terrain.PEDESTAL)

        mimic_chance = (1.0 / 3.0) * gen.MIMIC_CHANCE_MULTIPLIER
        if rng.Float() < mimic_chance:
            level.mobs.append(gen.spawn_mimic(rng, level, center, item, level.depth))
        else:
            heap = level.drop(item, center)
            heap.type = "CHEST"


class MinefieldRoom(StandardRoom):
    def size_cat_probs(self):
        return [4.0, 1.0, 0.0]

    def can_merge(self, level, other, p, merge_terrain) -> bool:
        cell = level.point_to_cell(self.point_inside(p, 1))
        return level.map[cell] == terrain.EMPTY

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.traps import ExplosiveTrap, reveal_hidden_trap_chance

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)
        for door in self.connected.values():
            door.set(DoorType.REGULAR)

        # Math.round(double): floor(x + 0.5), double precision (no float32
        # truncation -- Math.sqrt/Math.round(double) here, unlike the float32
        # helpers elsewhere in this module).
        mines = math.floor(math.sqrt(self.square()) + 0.5)
        if self.size_cat == SizeCategory.NORMAL:
            mines -= 3
        elif self.size_cat == SizeCategory.LARGE:
            mines += 3
        elif self.size_cat == SizeCategory.GIANT:
            mines += 9

        revealed_chance = reveal_hidden_trap_chance()
        reveal_inc = 0.0
        nbrs = _neighbours8(level.width())
        for _ in range(mines):
            while True:
                pos = level.point_to_cell(self.random(rng, 1))
                if pos not in level.traps:
                    break

            for _ in range(8):
                c = nbrs[rng.IntMax(8)]
                if pos + c not in level.traps and level.map[pos + c] == terrain.EMPTY:
                    Painter.set(level, pos + c, terrain.EMBERS)

            reveal_inc += revealed_chance
            if reveal_inc >= 1:
                Painter.set(level, pos, terrain.TRAP)
                level.set_trap(ExplosiveTrap().reveal(), pos)
                reveal_inc -= 1
            else:
                Painter.set(level, pos, terrain.SECRET_TRAP)
                level.set_trap(ExplosiveTrap().hide(), pos)
