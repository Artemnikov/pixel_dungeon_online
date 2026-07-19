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
"""Port of the CONSUMABLE_SPECIALS SpecialRoom subclasses (rooms/special/*.java)
-- special rooms drawn from SpecialRoom.java's consumable-reward static list
(RunestoneRoom..CrystalPathRoom, see CONSUMABLE_SPECIALS in registries.py)."""

from __future__ import annotations

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.geom import Point
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import DoorType
from app.engine.dungeon.spd_levelgen.room_types import SpecialRoom
from app.engine.dungeon.spd_levelgen.standard_rooms import EmptyRoom
from app.engine.dungeon.spd_levelgen.special_rooms._shared import _IRON_KEY, _consume_gold_random, _consume_random_equipment_floorset
from app.engine.dungeon.spd_random import SPDRandom


def _consume_generator_random_scroll(rng: SPDRandom) -> None:
    """Port of Generator.random(Category.SCROLL)'s OUTER-sequence draw.

    The deck push/pop and internal chances() picks are invisible to the
    parent (pure-construction sub-generator, per the WEAPON precedent). But
    *every* class in SCROLL.classes (including ScrollOfUpgrade) has an entry
    in ExoticScroll.regToExo, so the post-pop
    `if (regToExo.containsKey(itemCls)) if (Random.Float() < ...)` exotic
    check ALWAYS evaluates its Random.Float() against the outer generator,
    regardless of which scroll class was picked."""
    rng.Float()


def _runestone_prize(level, rng: SPDRandom):
    """Port of RunestoneRoom.prize() -- findPrizeItem(Class) is a deterministic
    linear scan (no RNG); Generator.random(Category.STONE) is a deck-backed
    default-branch pick (Runestone.random() is the zero-RNG Item base no-op,
    and Runestone is never an Exotic{Potion,Scroll} substitution target) --
    so the whole fallback consumes zero RNG. Identity irrelevant."""
    prize = level.find_prize_item(rng, "TrinketCatalyst")
    if prize is None:
        prize = level.find_prize_item(rng, "Runestone")
        if prize is None:
            prize = frozenset()
    return prize


def _traps_room_prize(level, rng: SPDRandom, depth: int):
    """Port of TrapsRoom.prize(). findPrizeItem() (no-arg, may consume
    rng.IntMax(len(itemsToSpawn)) -- see GenLevel.find_prize_item) returns
    early 67% of the time if non-null. Otherwise: Int(2) branch selector,
    then randomWeapon/randomArmor(floorSet+1) (identical outer-draw shape --
    see _consume_random_equipment_floorset), then cursed/cursedKnown
    assignment (zero-RNG), then a 33% upgrade roll whose Item.upgrade() is
    zero-RNG for these fresh sub-level-4 items (enchantHardened/glyphHardened
    start false, hasCurseEnchant/hasCurseGlyph already cleared above, and
    level() < 4 so the loss-chance branches never evaluate their Float(10))."""
    if rng.IntMax(3) != 0:
        prize = level.find_prize_item(rng)
        if prize is not None:
            return prize
    rng.IntMax(2)  # weapon-vs-armor branch selector -- both consume the same shape
    _consume_random_equipment_floorset(rng, depth // 5 + 1)
    rng.IntMax(3)  # upgrade roll -- Item.upgrade() is zero-RNG here, see above
    return frozenset()


def _library_room_prize(level, rng: SPDRandom):
    """Port of LibraryRoom.prize() -- findPrizeItem(Class) is RNG-free;
    Generator.random(Category.SCROLL)'s only outer-sequence draw is the
    always-fires exotic-substitution roll (_consume_generator_random_scroll)."""
    prize = level.find_prize_item(rng, "TrinketCatalyst")
    if prize is None:
        prize = level.find_prize_item(rng, "Scroll")
        if prize is None:
            _consume_generator_random_scroll(rng)
            prize = frozenset()
    return prize


def _consumable_prize(level, rng: SPDRandom, depth: int):
    if rng.IntMax(3) != 0:
        prize = level.find_prize_item(rng)
        if prize is not None:
            return prize
    cat_idx = rng.IntMax(4)
    if cat_idx == 0 or cat_idx == 1:
        rng.Float()
    elif cat_idx == 3:
        rng.chances([1.0])
        _consume_gold_random(rng, depth)
    return frozenset()


class RunestoneRoom(SpecialRoom):
    def min_width(self) -> int:
        return 6

    def min_height(self) -> int:
        return 6

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.CHASM)

        Painter.draw_inside(level, self, self.entrance(), 2, terrain.EMPTY_SP)
        Painter.fill(level, self, 2, terrain.EMPTY)

        n = rng.NormalIntRange(2, 3)
        for _ in range(n):
            while True:
                drop_pos = level.point_to_cell(self.random(rng))
                if level.map[drop_pos] == terrain.EMPTY and level.heaps.get(drop_pos) is None:
                    break
            prize = _runestone_prize(level, rng)
            level.drop(prize, drop_pos)  # registers the heap so later iterations' collision check sees it

        self.entrance().set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


class GardenRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.HIGH_GRASS)
        Painter.fill(level, self, 2, terrain.GRASS)

        self.entrance().set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)

        bushes = rng.IntMax(3)
        if bushes == 0:
            level.point_to_cell(self.random(rng))
        elif bushes == 1:
            level.point_to_cell(self.random(rng))
        elif rng.IntMax(5) == 0:
            level.point_to_cell(self.random(rng))
            level.point_to_cell(self.random(rng))
        # Foliage blob seed loops: zero-RNG, omitted


class LibraryRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        entrance = self.entrance()

        Painter.fill(level, self.left + 1, self.top + 1, self.width() - 2, 1, terrain.BOOKSHELF)
        Painter.draw_inside(level, self, entrance, 1, terrain.EMPTY_SP)

        n = rng.NormalIntRange(1, 3)
        for i in range(n):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                    break
            if i == 0:
                rng.IntMax(2)  # ScrollOfIdentify vs ScrollOfRemoveCurse -- identity irrelevant
                prize = frozenset({"Scroll"})
            else:
                prize = _library_room_prize(level, rng)
            level.drop(prize, pos)  # registers the heap so later iterations' collision check sees it

        entrance.set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


class StorageRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        honey_pot = rng.IntMax(2) == 0
        n = rng.IntRange(3, 4)
        for _ in range(n):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                    break
            if honey_pot:
                level.drop(frozenset({"Honeypot"}), pos)
                honey_pot = False
            else:
                level.drop(_consumable_prize(level, rng, level.depth), pos)

        self.entrance().set(DoorType.BARRICADE)
        level.add_item_to_spawn(frozenset())  # PotionOfLiquidFlame


class TreasuryRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        Painter.set(level, self.center(rng), terrain.STATUE)

        heap_type = "CHEST" if rng.IntMax(2) == 0 else "HEAP"
        n = rng.IntRange(2, 3)

        for _ in range(n):
            item = level.find_prize_item(rng, "TrinketCatalyst")
            if item is None:
                rng.chances([1.0])
                _consume_gold_random(rng, level.depth)

            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY and level.heaps.get(pos) is None and level.find_mob(pos) is None:
                    break

            if heap_type == "CHEST" and level.depth > 1:
                if rng.Float() < 0.2:
                    gen.roll_mimic_prize(level.run_state.generator_state, rng, level.depth)

        if heap_type == "HEAP":
            for _ in range(6):
                while True:
                    pos = level.point_to_cell(self.random(rng))
                    if level.map[pos] == terrain.EMPTY:
                        break
                rng.IntRange(5, 12)

        self.entrance().set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


class MagicWellRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        c = self.center(rng)
        Painter.set(level, c.x, c.y, terrain.WELL)

        # overrideWater is only ever set by external quest wiring (always None
        # in fresh levelgen) -- Random.element(WATERS) always fires.
        # WATERS = {WaterOfAwareness, WaterOfHealth} -- index 0 -> awareness.
        water_type = "awareness" if rng.IntMax(2) == 0 else "health"
        if not hasattr(level, "magic_wells"):
            level.magic_wells = []
        level.magic_wells.append({"pos": level.point_to_cell(c), "water_type": water_type})

        self.entrance().set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


class ToxicGasRoom(SpecialRoom):
    def min_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        Painter.set(level, self.center(rng), terrain.STATUE)

        # Blob.seed -- pure actor-state setup, zero RNG, out of layout-parity scope.

        traps = min(self.width() - 2, self.height() - 2)

        for _ in range(traps):
            while True:
                cell = level.point_to_cell(self.random(rng, 2))
                if level.map[cell] == terrain.EMPTY:
                    break
            # level.setTrap/Blob.seed/Painter.set -- zero-RNG side effects, omitted.

        gold_positions: list[int] = []
        for _ in range(8):
            while True:
                pos_to_add = level.point_to_cell(self.random(rng, 2))
                if level.map[pos_to_add] != terrain.STATUE and pos_to_add not in gold_positions:
                    break
            gold_positions.append(pos_to_add)

        entry_pos = level.point_to_cell(self.entrance())
        furthest_pos = -1
        for i in gold_positions:
            if furthest_pos == -1 or level.true_distance(entry_pos, i) > level.true_distance(entry_pos, furthest_pos):
                furthest_pos = i

        gold_positions.remove(furthest_pos)
        _consume_gold_random(rng, level.depth)
        # level.drop(mainGold, furthestPos) -- zero-RNG, omitted.

        for _ in range(2):
            item = level.find_prize_item(rng, "TrinketCatalyst")
            if item is None:
                _consume_gold_random(rng, level.depth)
            gold_positions.pop(0)
            # level.drop -- zero-RNG, omitted.

        # PotionOfPurity is never a findPrizeItem match-target -- empty
        # descriptor mirrors SPAWN_FOOD/SPAWN_STYLUS (identity doesn't matter).
        level.add_item_to_spawn(frozenset())

        self.entrance().set(DoorType.REGULAR)


class MagicalFireRoom(SpecialRoom):
    class EternalFire:
        pass

    def min_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.standard_rooms import EmptyRoom

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        door = self.entrance()
        door.set(DoorType.REGULAR)

        fire_pos = self.center(rng)
        behind_fire = EmptyRoom()

        if door.x == self.left or door.x == self.right:
            fire_pos.y = self.top + 1
            while fire_pos.y != self.bottom:
                Painter.set(level, fire_pos, terrain.EMPTY_SP)
                fire_pos.y += 1
            if door.x == self.left:
                behind_fire.set(fire_pos.x + 1, self.top + 1, self.right - 1, self.bottom - 1)
            else:
                behind_fire.set(self.left + 1, self.top + 1, fire_pos.x - 1, self.bottom - 1)
        else:
            fire_pos.x = self.left + 1
            while fire_pos.x != self.right:
                Painter.set(level, fire_pos, terrain.EMPTY_SP)
                fire_pos.x += 1
            if door.y == self.top:
                behind_fire.set(self.left + 1, fire_pos.y + 1, self.right - 1, self.bottom - 1)
            else:
                behind_fire.set(self.left + 1, self.top + 1, self.right - 1, fire_pos.y - 1)

        Painter.fill(level, behind_fire, terrain.EMPTY_SP)

        honey_pot = rng.IntMax(2) == 0
        n = rng.IntRange(3, 4)
        for _ in range(n):
            while True:
                pos = level.point_to_cell(behind_fire.random(rng, 0))
                if level.heaps.get(pos) is None:
                    break
            if honey_pot:
                level.drop(frozenset({"Honeypot"}), pos)
                honey_pot = False
            else:
                level.drop(_consumable_prize(level, rng, level.depth), pos)

        level.add_item_to_spawn(frozenset())  # PotionOfFrost


class TrapsRoom(SpecialRoom):
    def min_width(self) -> int:
        return 6

    def max_width(self) -> int:
        return 8

    def min_height(self) -> int:
        return 6

    def max_height(self) -> int:
        return 8

    # Class-identity-irrelevant per-region trap pools (TrapsRoom.java:160-171)
    # -- only the array length matters for Random.oneOf's Random.Int draw.
    _LEVEL_TRAP_COUNTS = (3, 3, 3, 3, 1)

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)

        trap_present = rng.IntMax(4) != 0
        if trap_present:
            rng.IntMax(self._LEVEL_TRAP_COUNTS[level.depth // 5])  # Random.oneOf -- identity irrelevant

        if not trap_present:
            Painter.fill(level, self, 1, terrain.CHASM)
        else:
            Painter.fill(level, self, 1, terrain.TRAP)

        door = self.entrance()
        door.set(DoorType.REGULAR)

        last_row = (terrain.CHASM
                    if level.map[self.left + 1 + (self.top + 1) * level.width()] == terrain.CHASM
                    else terrain.EMPTY)

        x = y = -1
        if door.x == self.left:
            x = self.right - 1
            y = self.top + self.height() // 2
            Painter.fill(level, x, self.top + 1, 1, self.height() - 2, last_row)
        elif door.x == self.right:
            x = self.left + 1
            y = self.top + self.height() // 2
            Painter.fill(level, x, self.top + 1, 1, self.height() - 2, last_row)
        elif door.y == self.top:
            x = self.left + self.width() // 2
            y = self.bottom - 1
            Painter.fill(level, self.left + 1, y, self.width() - 2, 1, last_row)
        elif door.y == self.bottom:
            x = self.left + self.width() // 2
            y = self.top + 1
            Painter.fill(level, self.left + 1, y, self.width() - 2, 1, last_row)

        # getPoints()/setTrap loop -- zero-RNG actor registration, omitted
        # (Reflection.newInstance(trapClass).reveal() is deterministic).

        pos = x + y * level.width()
        if rng.IntMax(3) == 0:
            if last_row == terrain.CHASM:
                Painter.set(level, pos, terrain.EMPTY)
            level.drop(_traps_room_prize(level, rng, level.depth), pos).type = "CHEST"
        else:
            Painter.set(level, pos, terrain.PEDESTAL)
            level.drop(_traps_room_prize(level, rng, level.depth), pos).type = "CHEST"

        level.add_item_to_spawn(frozenset())  # PotionOfLevitation -- never a findPrizeItem match-target


class CrystalPathRoom(SpecialRoom):
    def min_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def paint(self, level, rng: SPDRandom) -> None:
        # Deferred import: run_state imports special_rooms (room registries),
        # so importing it at module scope here would cycle.
        from app.engine.dungeon.spd_levelgen.run_state import (
            POTION_DEFAULT_PROBS_TOTAL, POTION_EXPERIENCE_INDEX,
            SCROLL_DEFAULT_PROBS_TOTAL, SCROLL_TRANSMUTATION_INDEX,
            generator_random_class_index,
        )

        Painter.fill(level, self, terrain.WALL)

        # rooms are ordered from closest to furthest from the entrance
        rooms = [EmptyRoom() for _ in range(6)]

        entry = self.entrance().clone()

        prize1 = prize2 = 0
        if entry.x == self.left or entry.x == self.right:

            Painter.draw_inside(level, self, entry, 5 if self.width() > 8 else 3, terrain.EMPTY)

            room_w1 = 2 if self.width() >= 9 else 1
            room_w2 = 2 if self.width() % 2 == 0 else 1
            room_h = 2 if self.height() >= 9 else 1

            if entry.x == self.left:
                rooms[0].set_pos(self.left + 1, entry.y - room_h - 1).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[0].left, rooms[0].bottom + 1, terrain.CRYSTAL_DOOR)
                rooms[1].set_pos(self.left + 1, entry.y + 2).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[1].left, rooms[1].top - 1, terrain.CRYSTAL_DOOR)

                rooms[2].set_pos(rooms[1].right + 2, entry.y - room_h - 1).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[2].left, rooms[2].bottom + 1, terrain.CRYSTAL_DOOR)
                rooms[3].set_pos(rooms[1].right + 2, entry.y + 2).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[3].left, rooms[3].top - 1, terrain.CRYSTAL_DOOR)

                rooms[4].set_pos(rooms[3].right + 2, entry.y - room_h - 1).resize(room_w2 - 1, room_h)
                Painter.set(level, rooms[4].left - 1, rooms[4].bottom - 1, terrain.CRYSTAL_DOOR)
                rooms[5].set_pos(rooms[3].right + 2, entry.y + 1).resize(room_w2 - 1, room_h)
                Painter.set(level, rooms[5].left - 1, rooms[5].top + 1, terrain.CRYSTAL_DOOR)

                prize1 = level.point_to_cell(Point(rooms[4].left, rooms[4].bottom))
                prize2 = level.point_to_cell(Point(rooms[5].left, rooms[5].top))
            else:
                rooms[0].set_pos(self.right - room_w1, entry.y - room_h - 1).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[0].right, rooms[0].bottom + 1, terrain.CRYSTAL_DOOR)
                rooms[1].set_pos(self.right - room_w1, entry.y + 2).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[1].right, rooms[1].top - 1, terrain.CRYSTAL_DOOR)

                rooms[2].set_pos(rooms[1].left - room_w1 - 1, entry.y - room_h - 1).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[2].right, rooms[2].bottom + 1, terrain.CRYSTAL_DOOR)
                rooms[3].set_pos(rooms[1].left - room_w1 - 1, entry.y + 2).resize(room_w1 - 1, room_h - 1)
                Painter.set(level, rooms[3].right, rooms[3].top - 1, terrain.CRYSTAL_DOOR)

                rooms[4].set_pos(rooms[3].left - room_w2 - 1, entry.y - room_h - 1).resize(room_w2 - 1, room_h)
                Painter.set(level, rooms[4].right + 1, rooms[4].bottom - 1, terrain.CRYSTAL_DOOR)
                rooms[5].set_pos(rooms[3].left - room_w2 - 1, entry.y + 1).resize(room_w2 - 1, room_h)
                Painter.set(level, rooms[5].right + 1, rooms[5].top + 1, terrain.CRYSTAL_DOOR)

                prize1 = level.point_to_cell(Point(rooms[4].right, rooms[4].bottom))
                prize2 = level.point_to_cell(Point(rooms[5].right, rooms[5].top))

        else:
            Painter.draw_inside(level, self, entry, 5 if self.height() > 8 else 3, terrain.EMPTY)

            room_w = 2 if self.width() >= 9 else 1
            room_h1 = 2 if self.height() >= 9 else 1
            room_h2 = 2 if self.height() % 2 == 0 else 1

            if entry.y == self.top:
                rooms[0].set_pos(entry.x - room_w - 1, self.top + 1).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[0].right + 1, rooms[0].top, terrain.CRYSTAL_DOOR)
                rooms[1].set_pos(entry.x + 2, self.top + 1).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[1].left - 1, rooms[1].top, terrain.CRYSTAL_DOOR)

                rooms[2].set_pos(entry.x - room_w - 1, rooms[1].bottom + 2).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[2].right + 1, rooms[2].top, terrain.CRYSTAL_DOOR)
                rooms[3].set_pos(entry.x + 2, rooms[1].bottom + 2).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[3].left - 1, rooms[3].top, terrain.CRYSTAL_DOOR)

                rooms[4].set_pos(entry.x - room_w - 1, rooms[3].bottom + 2).resize(room_w, room_h2 - 1)
                Painter.set(level, rooms[4].right - 1, rooms[4].top - 1, terrain.CRYSTAL_DOOR)
                rooms[5].set_pos(entry.x + 1, rooms[3].bottom + 2).resize(room_w, room_h2 - 1)
                Painter.set(level, rooms[5].left + 1, rooms[5].top - 1, terrain.CRYSTAL_DOOR)

                prize1 = level.point_to_cell(Point(rooms[4].right, rooms[4].top))
                prize2 = level.point_to_cell(Point(rooms[5].left, rooms[5].top))
            else:
                rooms[0].set_pos(entry.x - room_w - 1, self.bottom - room_h1).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[0].right + 1, rooms[0].bottom, terrain.CRYSTAL_DOOR)
                rooms[1].set_pos(entry.x + 2, self.bottom - room_h1).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[1].left - 1, rooms[1].bottom, terrain.CRYSTAL_DOOR)

                rooms[2].set_pos(entry.x - room_w - 1, rooms[1].top - room_h1 - 1).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[2].right + 1, rooms[2].bottom, terrain.CRYSTAL_DOOR)
                rooms[3].set_pos(entry.x + 2, rooms[1].top - room_h1 - 1).resize(room_w - 1, room_h1 - 1)
                Painter.set(level, rooms[3].left - 1, rooms[3].bottom, terrain.CRYSTAL_DOOR)

                rooms[4].set_pos(entry.x - room_w - 1, rooms[3].top - room_h2 - 1).resize(room_w, room_h2 - 1)
                Painter.set(level, rooms[4].right - 1, rooms[4].bottom + 1, terrain.CRYSTAL_DOOR)
                rooms[5].set_pos(entry.x + 1, rooms[3].top - room_h2 - 1).resize(room_w, room_h2 - 1)
                Painter.set(level, rooms[5].left + 1, rooms[5].bottom + 1, terrain.CRYSTAL_DOOR)

                prize1 = level.point_to_cell(Point(rooms[4].right, rooms[4].bottom))
                prize2 = level.point_to_cell(Point(rooms[5].left, rooms[5].bottom))

        for room in rooms:
            Painter.fill(level, room, terrain.EMPTY_SP)
        Painter.set(level, prize1, terrain.PEDESTAL)
        Painter.set(level, prize2, terrain.PEDESTAL)

        # random potion/scroll in rooms 1-4, with lower value ones going into
        # earlier rooms. Items are tracked as class indices into
        # POTION/SCROLL.classes (never as full Item objects -- see
        # generator_random_class_index's docstring for why class identity
        # alone suffices: the exotic-substitution roll never substitutes on
        # a fresh game, so the rolled regular-class index IS the final identity).
        run_state = level.run_state
        potion_deck = run_state.potion_deck
        scroll_deck = run_state.scroll_deck

        potions: list[int] = []
        scrolls: list[int] = []
        # (deck_name, index) pairs needing Generator.undoDrop after rolling
        duplicates: list[tuple[str, int]] = []

        def add_reward_item(deck, deck_name: str, items: list[int]) -> None:
            while True:
                idx = generator_random_class_index(deck, rng)
                if idx in items:
                    duplicates.append((deck_name, idx))
                else:
                    items.append(idx)
                    return

        if rng.IntMax(2) == 0:
            add_reward_item(potion_deck, "POTION", potions)
            rng.Float()  # Random.Float() < consumableExoticChance() -- always false: ScrollOfTransmutation
            scrolls.append(SCROLL_TRANSMUTATION_INDEX)
        else:
            rng.Float()  # Random.Float() < consumableExoticChance() -- always false: PotionOfExperience
            potions.append(POTION_EXPERIENCE_INDEX)
            add_reward_item(scroll_deck, "SCROLL", scrolls)
        add_reward_item(potion_deck, "POTION", potions)
        add_reward_item(scroll_deck, "SCROLL", scrolls)
        add_reward_item(potion_deck, "POTION", potions)
        add_reward_item(scroll_deck, "SCROLL", scrolls)

        # need to undo the changes to spawn chances that the duplicates created
        for deck_name, idx in duplicates:
            (potion_deck if deck_name == "POTION" else scroll_deck).undo_drop(idx)

        # rarer potions/scrolls go later in the order (stable sort, descending
        # by defaultProbsTotal -- matches Collections.sort/Comparator)
        potions.sort(key=lambda i: -POTION_DEFAULT_PROBS_TOTAL[i])
        scrolls.sort(key=lambda i: -SCROLL_DEFAULT_PROBS_TOTAL[i])

        # least valuable items go into rooms 2&3, then rooms 0&1, finally 4&5.
        # Deck-index identity is dropped here -- as with every other reward
        # room in this file, the concrete item is a generic "Potion"/"Scroll"
        # descriptor (_DESCRIPTOR_ITEM_MAP), so which rolled index went where
        # doesn't affect what actually gets dropped -- but room.center(rng)
        # DOES draw, so it must still be consumed in the original call order.
        shuffle = rng.IntMax(2)
        level.drop(frozenset({"Potion"}), level.point_to_cell(rooms[2 if shuffle == 1 else 3].center(rng)))
        level.drop(frozenset({"Scroll"}), level.point_to_cell(rooms[3 if shuffle == 1 else 2].center(rng)))

        level.drop(frozenset({"Potion"}), level.point_to_cell(rooms[0 if shuffle == 1 else 1].center(rng)))
        level.drop(frozenset({"Scroll"}), level.point_to_cell(rooms[1 if shuffle == 1 else 0].center(rng)))

        # prize1/prize2 cells need no center() roll. Java marks these
        # autoExplored=true (player can only see them after unlocking both
        # crystal doors) -- not modeled, GenHeap has no such field, same as
        # the CrystalVaultRoom precedent above.
        level.drop(frozenset({"Potion"}), prize1 if shuffle == 1 else prize2)
        level.drop(frozenset({"Scroll"}), prize2 if shuffle == 1 else prize1)

        level.add_item_to_spawn(frozenset({"CrystalKey"}))
        level.add_item_to_spawn(frozenset({"CrystalKey"}))
        level.add_item_to_spawn(frozenset({"CrystalKey"}))

        self.entrance().set(DoorType.REGULAR)
