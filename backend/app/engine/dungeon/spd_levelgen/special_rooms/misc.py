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
"""Port of the SpecialRoom subclasses that aren't drawn from either general
random-special list (EQUIP_SPECIALS/CONSUMABLE_SPECIALS) -- LaboratoryRoom/
PitRoom (CRYSTAL_KEY_SPECIALS only), DemonSpawnerRoom (HallsLevel-specific,
floors 21-24) and MassGraveRoom (Wandmaker quest room, Prison depths 7-9)."""

from __future__ import annotations

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.generator import _random_armor, generator_random
from app.engine.dungeon.spd_levelgen.geom import Point
from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import DoorType
from app.engine.dungeon.spd_levelgen.room_types import SpecialRoom
from app.engine.dungeon.spd_levelgen.special_rooms._shared import _IRON_KEY, _consume_gold_random
from app.engine.dungeon.spd_random import SPDRandom


def _pit_room_prize(rng: SPDRandom, depth: int):
    cat_idx = rng.IntMax(4)
    if cat_idx == 0 or cat_idx == 1:
        rng.Float()
    elif cat_idx == 3:
        rng.chances([1.0])
        _consume_gold_random(rng, depth)
    return frozenset()


def _laboratory_prize(level, rng: SPDRandom):
    prize = level.find_prize_item(rng, "TrinketCatalyst")
    if prize is None:
        prize = level.find_prize_item(rng, "PotionOfStrength")
        if prize is None:
            oneof_idx = rng.IntMax(2)
            if oneof_idx == 0:
                rng.Float()
            prize = frozenset()
    return prize


class LaboratoryRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        entrance = self.entrance()

        pot = None
        if entrance.x == self.left:
            pot = Point(self.right - 1, self.top + 1 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif entrance.x == self.right:
            pot = Point(self.left + 1, self.top + 1 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif entrance.y == self.top:
            pot = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.bottom - 1)
        elif entrance.y == self.bottom:
            pot = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.top + 1)
        Painter.set(level, pot, terrain.ALCHEMY)

        # Alchemy Blob.seed: zero-RNG, omitted

        while True:
            pos = level.point_to_cell(self.random(rng))
            if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                break

        level.drop(frozenset({"EnergyCrystal", "qty:5"}), pos)

        n = rng.NormalIntRange(1, 2)
        for _ in range(n):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                    break
            _laboratory_prize(level, rng)

        chapter = 1 + level.depth // 5
        pages_to_drop = chapter
        for _ in range(pages_to_drop):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                    break

        entrance.set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


class PitRoom(SpecialRoom):
    def min_width(self) -> int:
        return 6

    def max_width(self) -> int:
        return 9

    def min_height(self) -> int:
        return 6

    def max_height(self) -> int:
        return 9

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        entrance = self.entrance()
        entrance.set(DoorType.CRYSTAL)

        well = None
        if entrance.x == self.left:
            well = Point(self.right - 1, self.top + 1 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif entrance.x == self.right:
            well = Point(self.left + 1, self.top + 1 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif entrance.y == self.top:
            well = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.bottom - 1)
        elif entrance.y == self.bottom:
            well = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.top + 1)
        Painter.set(level, well, terrain.EMPTY_WELL)

        remains = level.point_to_cell(self.center(rng))

        category = rng.IntMax(3)
        if category == 0:
            gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, "RING")
        elif category == 1:
            gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, "ARTIFACT")
        else:
            oneof_idx = rng.IntMax(5)
            if oneof_idx == 2:
                gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, "MISSILE")
            elif oneof_idx >= 3:
                gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, "ARMOR")
            else:
                gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, "WEAPON")

        n = rng.IntRange(1, 2)
        for _ in range(n):
            _pit_room_prize(rng, level.depth)

        level.add_item_to_spawn(frozenset({"CrystalKey"}))

    def can_place_trap(self, p: Point) -> bool:
        return False

    def can_place_grass(self, p: Point) -> bool:
        return False


class DemonSpawnerRoom(SpecialRoom):
    """Port of DemonSpawnerRoom.java -- not part of the special-room rotation
    (SpecialRoom.java's static lists); HallsLevel.initRooms() adds exactly one
    of these directly to the init-room list for floors 21-24."""

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        door = self.entrance()
        if door is not None:
            door.set(DoorType.UNLOCKED)  # cannot be hidden randomly under any circumstance

        c = self.center(rng)
        level.mobs.append(GenMob(cls_name="DemonSpawner", pos=level.point_to_cell(c)))

    def connect(self, room: "Room") -> bool:
        # Cannot connect to the exit room, otherwise works normally.
        if room.is_exit():
            return False
        return super().connect(room)

    def can_place_trap(self, p: Point) -> bool:
        return False

    def can_place_water(self, p: Point) -> bool:
        return False

    def can_place_grass(self, p: Point) -> bool:
        return False


class MassGraveRoom(SpecialRoom):
    """Port of rooms/quest/MassGraveRoom.java -- Wandmaker quest room, Corpse
    Dust variant (Prison depths 7-9, see run_state.WandmakerQuestState).
    Reuses the existing Skeleton mob and CryptRoom's haunted-loot-heap
    pattern (SKELETON heap type -> rendered as a container by spd_adapter's
    _spawn_chest, same as CryptRoom's TOMB type). The purely cosmetic
    `Bones` CustomTilemap overlay and Heap.setHauntedIfCursed() flourish are
    dropped -- zero gameplay/RNG impact, and this engine has no
    CustomTilemap/haunted-heap rendering layer to hang them on."""

    def min_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def can_connect(self, r: "Room") -> bool:
        # MassGraveRoom.canConnect(): must be at least 3 rooms from the
        # entrance (walks up to 3 levels of r's connection graph).
        if r.is_entrance():
            return False
        for r1 in r.connected.keys():
            if r1.is_entrance():
                return False
            for r2 in r1.connected.keys():
                if r2.is_entrance():
                    return False
                for r3 in r2.connected.keys():
                    if r3.is_entrance():
                        return False
        return super().can_connect(r)

    def paint(self, level, rng: SPDRandom) -> None:
        entrance = self.entrance()
        entrance.set(DoorType.BARRICADE)
        level.add_item_to_spawn(frozenset())  # PotionOfLiquidFlame -- never a findPrizeItem match-target

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.CUSTOM_DECO_EMPTY)

        for _ in range(rng.IntMax(2) + 1):
            pos = level.point_to_cell(self.random(rng))
            while level.map[pos] != terrain.CUSTOM_DECO_EMPTY or level.find_mob(pos) is not None:
                pos = level.point_to_cell(self.random(rng))
            level.mobs.append(GenMob(cls_name="Skeleton", pos=pos, depth=level.depth))

        items = [frozenset({"CorpseDust"}), frozenset({"Gold", "qty:1"}), frozenset({"Gold", "qty:1"})]
        if rng.Float() <= 0.3:
            items.append(frozenset({"Gold", "qty:1"}))
        if rng.Float() <= 0.3:
            items.append(frozenset({"Gold", "qty:1"}))
        if rng.Float() <= 0.6:
            items.append(generator_random(level.run_state.generator_state, rng, level.depth))
        if rng.Float() <= 0.3:
            items.append(_random_armor(rng, level.depth))

        for item in items:
            pos = level.point_to_cell(self.random(rng))
            while level.map[pos] != terrain.CUSTOM_DECO_EMPTY or level.heaps.get(pos) is not None:
                pos = level.point_to_cell(self.random(rng))
            heap = level.drop(item, pos)
            heap.type = "SKELETON"
