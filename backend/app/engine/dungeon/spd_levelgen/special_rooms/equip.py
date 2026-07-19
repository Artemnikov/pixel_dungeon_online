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
"""Port of the EQUIP_SPECIALS SpecialRoom subclasses (rooms/special/*.java) --
special rooms drawn from SpecialRoom.java's equipment-reward static list
(WeakFloorRoom..SacrificeRoom, see EQUIP_SPECIALS in registries.py)."""

from __future__ import annotations

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.geom import Point
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import DoorType
from app.engine.dungeon.spd_levelgen.room_types import SpecialRoom
from app.engine.dungeon.spd_levelgen.standard_rooms import EmptyRoom
from app.engine.dungeon.spd_levelgen.special_rooms._shared import _IRON_KEY, _consume_random_equipment_floorset
from app.engine.dungeon.spd_random import SPDRandom

# Weapon.Enchantment.{common,uncommon,rare} array sizes (Weapon.java:515-529) --
# Enchantment.random() -> Random.chances(typeChances) selects a rarity tier,
# then Random.element(<tier array>) -> Random.Int(<tier size>). Identity is
# irrelevant for layout-parity; only array length matters for the Int() draw.
_ENCHANT_TYPE_CHANCES = (50.0, 40.0, 10.0)
_ENCHANT_TIER_SIZES = (4, 6, 3)  # common, uncommon, rare


def _consume_generator_random_weapon(rng: SPDRandom, depth: int) -> None:
    """Port of Generator.randomWeapon()/randomWeapon(floorSet, false) ->
    Generator.random(WEP_Tn) -> Weapon.random()'s RNG draws against the
    OUTER (levelgen) sequence.

    Generator.random(Category) for deck-backed categories (WEP_T1-5) pushes
    a seeded sub-generator (`Random.pushGenerator(cat.seed)`, zero parent
    draws -- pure construction) and does ALL of its chances/skip-ahead work
    there before popping -- so from the parent's perspective those draws are
    invisible. Only `Random.chances(floorSetTierProbs[floorSet])` (selecting
    the tier, outside the push/pop) and `Weapon.random()` (called on the
    POPPED/outer generator, since popGenerator() runs before `.random()`)
    are real outer-sequence draws. The exotic-substitution check
    (`ExoticPotion/ScrollOfTransmutation.regToExo`) never matches a weapon
    class, so it draws nothing."""
    _consume_random_equipment_floorset(rng, depth // 5)


def _consume_enchantment_random(rng: SPDRandom) -> None:
    """Port of Weapon.Enchantment.random() -- Random.chances(typeChances)
    picks a rarity tier, then Random.element(<tier array>) consumes
    Random.Int(<tier size>). Identity irrelevant for layout-parity."""
    tier = rng.chances(_ENCHANT_TYPE_CHANCES)
    rng.IntMax(_ENCHANT_TIER_SIZES[tier])


def _consume_statue_random(rng: SPDRandom, depth: int) -> None:
    """Port of Statue.random()/createWeapon(true) + the
    `weapon.enchant(Enchantment.random())` overwrite in StatueRoom.paint --
    the full RNG sequence Statue.random() draws against the levelgen
    generator (Statue.pos assignment and mob registration are zero-RNG,
    out of layout-parity scope)."""
    rng.Float()  # altChance roll (ArmoredStatue vs Statue) -- always consumed
    _consume_generator_random_weapon(rng, depth)
    _consume_enchantment_random(rng)


class WeakFloorRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.CHASM)

        door = self.entrance()
        door.set(DoorType.REGULAR)

        well = None

        if door.x == self.left:
            for i in range(self.top + 1, self.bottom):
                Painter.draw_inside(level, self, Point(self.left, i), rng.IntRange(1, self.width() - 4), terrain.EMPTY_SP)
            well = Point(self.right - 1, self.top + 2 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif door.x == self.right:
            for i in range(self.top + 1, self.bottom):
                Painter.draw_inside(level, self, Point(self.right, i), rng.IntRange(1, self.width() - 4), terrain.EMPTY_SP)
            well = Point(self.left + 1, self.top + 2 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif door.y == self.top:
            for i in range(self.left + 1, self.right):
                Painter.draw_inside(level, self, Point(i, self.top), rng.IntRange(1, self.height() - 4), terrain.EMPTY_SP)
            well = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.bottom - 1)
        elif door.y == self.bottom:
            for i in range(self.left + 1, self.right):
                Painter.draw_inside(level, self, Point(i, self.bottom), rng.IntRange(1, self.height() - 4), terrain.EMPTY_SP)
            well = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.top + 2)

        Painter.set(level, well, terrain.CHASM)
        # HiddenWell CustomTilemap + WellID Blob: runtime-only, zero-RNG, out of layout-parity scope


class CryptRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        c = self.center(rng)
        cx, cy = c.x, c.y

        entrance = self.entrance()
        entrance.set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)

        if entrance.x == self.left:
            Painter.set(level, self.right - 1, self.top + 1, terrain.STATUE)
            Painter.set(level, self.right - 1, self.bottom - 1, terrain.STATUE)
            cx = self.right - 2
        elif entrance.x == self.right:
            Painter.set(level, self.left + 1, self.top + 1, terrain.STATUE)
            Painter.set(level, self.left + 1, self.bottom - 1, terrain.STATUE)
            cx = self.left + 2
        elif entrance.y == self.top:
            Painter.set(level, self.left + 1, self.bottom - 1, terrain.STATUE)
            Painter.set(level, self.right - 1, self.bottom - 1, terrain.STATUE)
            cy = self.bottom - 2
        elif entrance.y == self.bottom:
            Painter.set(level, self.left + 1, self.top + 1, terrain.STATUE)
            Painter.set(level, self.right - 1, self.top + 1, terrain.STATUE)
            cy = self.top + 2

        level.drop(_crypt_prize(level, rng, level.depth), cx + cy * level.width()).type = "TOMB"


def _crypt_prize(level, rng: SPDRandom, depth: int):
    """Port of CryptRoom.prize() -- Generator.randomArmor(floorSet+1)
    outer draw then Glyph.randomCurse() Int(8)."""
    _consume_random_equipment_floorset(rng, depth // 5 + 1)
    rng.IntMax(8)  # Armor.Glyph.randomCurse() -- Random.element(curses[8]); identity irrelevant
    return frozenset({"Armor"})


def _pool_room_prize(level, rng: SPDRandom, depth: int):
    """Port of PoolRoom.prize() -- findPrizeItem() returns early 33% of the
    time if non-null. Otherwise weapon/missile/armor at floorSet (depth/5)+1
    (identical outer-draw shape -- _consume_random_equipment_floorset covers
    weapon/missile/armor alike, see its docstring); the cursed/cursedKnown
    overwrite and the conditional `enchant(null)`/`inscribe(null)` are
    zero-RNG identity setters (per the cursed/hasCurseEnchant finding); the
    final 33% `prize.upgrade()` is zero-RNG too -- _roll_wam never rolls
    above level 2, so the extra +1 never reaches the >=4 loss-chance branch."""
    if rng.IntMax(3) == 0:
        prize = level.find_prize_item(rng)
        if prize is not None:
            return prize
    rng.IntMax(5)  # weapon (0,1) / missile (2) / armor (3,4) branch selector
    _consume_random_equipment_floorset(rng, depth // 5 + 1)
    rng.IntMax(3)  # extra-upgrade roll -- zero-RNG Item.upgrade() here
    return frozenset()


class PoolRoom(SpecialRoom):
    def min_width(self) -> int:
        return 6

    def min_height(self) -> int:
        return 6

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.WATER)

        door = self.entrance()
        door.set(DoorType.REGULAR)

        x = y = -1
        if door.x == self.left:
            x = self.right - 1
            y = self.top + self.height() // 2
            Painter.fill(level, self.left + 1, self.top + 1, 1, self.height() - 2, terrain.EMPTY_SP)
        elif door.x == self.right:
            x = self.left + 1
            y = self.top + self.height() // 2
            Painter.fill(level, self.right - 1, self.top + 1, 1, self.height() - 2, terrain.EMPTY_SP)
        elif door.y == self.top:
            x = self.left + self.width() // 2
            y = self.bottom - 1
            Painter.fill(level, self.left + 1, self.top + 1, self.width() - 2, 1, terrain.EMPTY_SP)
        elif door.y == self.bottom:
            x = self.left + self.width() // 2
            y = self.top + 1
            Painter.fill(level, self.left + 1, self.bottom - 1, self.width() - 2, 1, terrain.EMPTY_SP)

        pos = x + y * level.width()
        prize = _pool_room_prize(level, rng, level.depth)
        chest = level.drop(prize, pos)
        chest.type = "CHEST"
        Painter.set(level, pos, terrain.PEDESTAL)

        level.add_item_to_spawn(frozenset())  # PotionOfInvisibility -- never a findPrizeItem match-target

        for _ in range(3):
            cls_name = "PhantomPiranha" if rng.Float() < 0.02 else "Piranha"  # 1/50 * exoticChanceMultiplier (no RatSkull) == 0.02
            while True:
                ppos = level.point_to_cell(self.random(rng))
                if level.map[ppos] == terrain.WATER and level.find_mob(ppos) is None:
                    break
            level.mobs.append(GenMob(cls_name=cls_name, pos=ppos, depth=level.depth))


def _armory_prize(level, rng: SPDRandom, depth: int, prize_cats: list):
    """Port of ArmoryRoom.prize() -- Random.chances draws an index,
    then dispatches to Bomb/weapon/armor/missile generation. The chosen
    weight is zeroed for subsequent calls."""
    index = rng.chances(prize_cats)
    prize_cats[index] = 0.0
    if index == 0:
        rng.IntMax(4)  # Bomb.random() -- Random.Int(4)
        return frozenset({"Bomb"})
    elif index == 1:
        _consume_generator_random_weapon(rng, depth)
        return frozenset({"Weapon"})
    elif index == 2:
        _consume_random_equipment_floorset(rng, depth // 5)
        return frozenset({"Armor"})
    else:
        _consume_generator_random_weapon(rng, depth)
        return frozenset({"Missile"})


class ArmoryRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        entrance = self.entrance()
        statue = None
        if entrance.x == self.left:
            statue = Point(self.right - 1, self.top + 1 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif entrance.x == self.right:
            statue = Point(self.left + 1, self.top + 1 if rng.IntMax(2) == 0 else self.bottom - 1)
        elif entrance.y == self.top:
            statue = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.bottom - 1)
        elif entrance.y == self.bottom:
            statue = Point(self.left + 1 if rng.IntMax(2) == 0 else self.right - 1, self.top + 1)
        if statue is not None:
            Painter.set(level, statue, terrain.STATUE)

        n = rng.IntRange(2, 3)
        prize_cats = [1.0, 1.0, 1.0, 1.0]
        for _ in range(n):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY and level.heaps.get(pos) is None:
                    break
            level.drop(_armory_prize(level, rng, level.depth, prize_cats), pos)

        cata = level.find_prize_item(rng, "TrinketCatalyst")
        if cata is not None:
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY and level.heaps.get(pos) is None:
                    break
            level.drop(cata, pos)

        entrance.set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


def _sentry_prize(level, rng: SPDRandom, depth: int):
    """Port of SentryRoom.prize() -- 50% chance for prize item (findPrizeItem
    no-arg), otherwise weapon/missile/armor at floorSet+1, never cursed."""
    if rng.IntMax(2) == 0:
        prize = level.find_prize_item(rng)
        if prize is not None:
            return prize
    switch_idx = rng.IntMax(5)
    _consume_random_equipment_floorset(rng, depth // 5 + 1)
    rng.IntMax(3)  # 33% upgrade roll -- zero-RNG Item.upgrade() here
    if switch_idx == 2:
        return frozenset({"Missile"})
    return frozenset({"Weapon"})


class SentryRoom(SpecialRoom):
    def min_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        entrance = self.entrance()

        c = self.center(rng)
        sentry_pos = Point()
        treasure_pos = Point()
        danger_dist = 0

        if entrance.x == self.left:
            sentry_pos.x = self.right - 1
            sentry_pos.y = c.y
            Painter.fill(level, self.left + 1, self.top + 1, 1, self.height() - 2, terrain.EMPTY)
            if entrance.y > c.y:
                treasure_pos.x = self.left + 1
                treasure_pos.y = (self.top + 1 + c.y) // 2
                Painter.fill(level, self.left + 1, self.top + 1, 2, c.y - self.top - 1, terrain.EMPTY)
            else:
                treasure_pos.x = self.left + 1
                treasure_pos.y = (self.bottom + c.y) // 2
                Painter.fill(level, self.left + 1, c.y + 1, 2, self.bottom - c.y - 1, terrain.EMPTY)
            for x in range(self.right - 3, self.left, -1):
                if level.map[x + c.y * level.width()] == terrain.EMPTY_SP:
                    Painter.set(level, x, c.y, terrain.STATUE_SP)
                else:
                    Painter.set(level, x, c.y, terrain.STATUE)
        elif entrance.x == self.right:
            sentry_pos.x = self.left + 1
            sentry_pos.y = c.y
            Painter.fill(level, self.right - 1, self.top + 1, 1, self.height() - 2, terrain.EMPTY)
            if entrance.y > c.y:
                treasure_pos.x = self.right - 1
                treasure_pos.y = (self.top + 1 + c.y) // 2
                Painter.fill(level, self.right - 2, self.top + 1, 2, c.y - self.top - 1, terrain.EMPTY)
            else:
                treasure_pos.x = self.right - 1
                treasure_pos.y = (self.bottom + 1 + c.y) // 2
                Painter.fill(level, self.right - 2, c.y + 1, 2, self.bottom - c.y - 1, terrain.EMPTY)
            for x in range(self.left + 3, self.right):
                if level.map[x + c.y * level.width()] == terrain.EMPTY_SP:
                    Painter.set(level, x, c.y, terrain.STATUE_SP)
                else:
                    Painter.set(level, x, c.y, terrain.STATUE)
        elif entrance.y == self.top:
            sentry_pos.x = c.x
            sentry_pos.y = self.bottom - 1
            Painter.fill(level, self.left + 1, self.top + 1, self.width() - 2, 1, terrain.EMPTY)
            if entrance.x > c.x:
                treasure_pos.x = (self.left + 1 + c.x) // 2
                treasure_pos.y = self.top + 1
                Painter.fill(level, self.left + 1, self.top + 1, c.x - self.left - 1, 2, terrain.EMPTY)
            else:
                treasure_pos.x = (self.right + c.x) // 2
                treasure_pos.y = self.top + 1
                Painter.fill(level, c.x + 1, self.top + 1, self.right - c.x - 1, 2, terrain.EMPTY)
            for y in range(self.bottom - 3, self.top, -1):
                if level.map[c.x + y * level.width()] == terrain.EMPTY_SP:
                    Painter.set(level, c.x, y, terrain.STATUE_SP)
                else:
                    Painter.set(level, c.x, y, terrain.STATUE)
        elif entrance.y == self.bottom:
            sentry_pos.x = c.x
            sentry_pos.y = self.top + 1
            Painter.fill(level, self.left + 1, self.bottom - 1, self.width() - 2, 1, terrain.EMPTY)
            if entrance.x > c.x:
                treasure_pos.x = (self.left + 1 + c.x) // 2
                treasure_pos.y = self.bottom - 1
                Painter.fill(level, self.left + 1, self.bottom - 2, c.x - self.left - 1, 2, terrain.EMPTY)
            else:
                treasure_pos.x = (self.right + c.x) // 2
                treasure_pos.y = self.bottom - 1
                Painter.fill(level, c.x + 1, self.bottom - 2, self.right - c.x - 1, 2, terrain.EMPTY)
            for y in range(self.top + 3, self.bottom):
                if level.map[c.x + y * level.width()] == terrain.EMPTY_SP:
                    Painter.set(level, c.x, y, terrain.STATUE_SP)
                else:
                    Painter.set(level, c.x, y, terrain.STATUE)

        if entrance.x == self.left or entrance.x == self.right:
            danger_dist = 2 * (self.width() - 5)
        else:
            danger_dist = 2 * (self.height() - 5)
        charge_delay = danger_dist / 3.0 + 0.1

        Painter.set(level, sentry_pos, terrain.PEDESTAL)
        level.mobs.append(GenMob(
            cls_name="Sentry", pos=level.point_to_cell(sentry_pos),
            extra={"room": (self.left, self.top, self.right, self.bottom),
                   "charge_delay": charge_delay, "depth": level.depth},
        ))

        Painter.set(level, treasure_pos, terrain.PEDESTAL)
        level.drop(_sentry_prize(level, rng, level.depth), level.point_to_cell(treasure_pos)).type = "CHEST"

        level.add_item_to_spawn(frozenset())  # PotionOfHaste -- never a findPrizeItem match-target

        entrance.set(DoorType.REGULAR)


class StatueRoom(SpecialRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        c = self.center(rng)
        cx, cy = c.x, c.y

        door = self.entrance()
        door.set(DoorType.LOCKED)
        # level.addItemToSpawn(new IronKey(depth)) -- zero-RNG identity, omitted
        # (IronKey is never a findPrizeItem match-target).
        level.add_item_to_spawn(_IRON_KEY)

        if door.x == self.left:
            Painter.fill(level, self.right - 1, self.top + 1, 1, self.height() - 2, terrain.STATUE)
            cx = self.right - 2
        elif door.x == self.right:
            Painter.fill(level, self.left + 1, self.top + 1, 1, self.height() - 2, terrain.STATUE)
            cx = self.left + 2
        elif door.y == self.top:
            Painter.fill(level, self.left + 1, self.bottom - 1, self.width() - 2, 1, terrain.STATUE)
            cy = self.bottom - 2
        elif door.y == self.bottom:
            Painter.fill(level, self.left + 1, self.top + 1, self.width() - 2, 1, terrain.STATUE)
            cy = self.top + 2

        # Replicate _consume_statue_random inline so we can capture the altChance result
        # rng.Float() -- altChance roll (ArmoredStatue vs Statue, threshold 1/10)
        mob_cls = "ArmoredStatue" if rng.Float() < 0.1 else "Statue"
        _consume_generator_random_weapon(rng, level.depth)
        _consume_enchantment_random(rng)
        # Place the statue mob at the center position
        pos = cx + cy * level.width()
        level.mobs.append(GenMob(cls_name=mob_cls, pos=pos, depth=level.depth))


class CrystalVaultRoom(SpecialRoom):
    def min_width(self) -> int:
        return 7

    def max_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def max_height(self) -> int:
        return 7

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)
        Painter.fill(level, self, 2, terrain.EMPTY)

        c = level.point_to_cell(self.center(rng))

        # Collections.shuffle(prizeClasses, Random) for [WAND, RING, ARTIFACT]
        prize_classes = ["WAND", "RING", "ARTIFACT"]
        j = rng.IntMax(3)
        prize_classes[2], prize_classes[j] = prize_classes[j], prize_classes[2]
        j = rng.IntMax(2)
        prize_classes[1], prize_classes[j] = prize_classes[j], prize_classes[1]

        ri1 = gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, prize_classes[0])
        ri2 = gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, prize_classes[1])

        door_pos = level.point_to_cell(self.entrance())
        _CIRCLE8 = ((-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0))
        while True:
            neighbour_idx = rng.IntMax(8)
            off_x, off_y = _CIRCLE8[neighbour_idx]
            cx = self.left + self.width() // 2
            cy = self.top + self.height() // 2
            i1_pos = (cx + off_x) + (cy + off_y) * level.width()
            opp_idx = (neighbour_idx + 4) % 8
            opp_off_x, opp_off_y = _CIRCLE8[opp_idx]
            i2_pos = (cx + opp_off_x) + (cy + opp_off_y) * level.width()
            # level.adjacent check: Chebyshev distance > 1
            def _adj(a, b):
                ax, ay = a % level.width(), a // level.width()
                bx, by = b % level.width(), b // level.width()
                return abs(ax - bx) <= 1 and abs(ay - by) <= 1 and (ax != bx or ay != by)
            if not _adj(i1_pos, door_pos) and not _adj(i2_pos, door_pos):
                break

        level.drop(ri1, i1_pos).type = "CRYSTAL_CHEST"
        mimic_chance = rng.Float()
        if mimic_chance < 0.1:
            level.mobs.append(gen.spawn_crystal_mimic(rng, level, i2_pos, ri2, level.depth))
        else:
            level.drop(ri2, i2_pos).type = "CRYSTAL_CHEST"
        Painter.set(level, i1_pos, terrain.PEDESTAL)
        Painter.set(level, i2_pos, terrain.PEDESTAL)

        level.add_item_to_spawn(frozenset({"CrystalKey"}))
        self.entrance().set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


class CrystalChoiceRoom(SpecialRoom):
    def min_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen

        Painter.fill(level, self, terrain.WALL)

        entrance = self.entrance()

        entry = EmptyRoom()
        room1 = EmptyRoom()
        room2 = EmptyRoom()

        if entrance.x == self.left:
            entry.set(self.left + 1, self.top + 1, self.left + 2, self.bottom - 1)

            room1.set(entry.right + 2, self.top + 1, self.right - 1, self.center(rng).y - 1)
            room2.set(entry.right + 2, room1.bottom + 2, self.right - 1, self.bottom - 1)

            Painter.set(level, Point(entry.right + 1, (room1.top + room1.bottom + 1) // 2), terrain.CRYSTAL_DOOR)
            Painter.set(level, Point(entry.right + 1, (room2.top + room2.bottom) // 2), terrain.CRYSTAL_DOOR)

        elif entrance.y == self.top:
            entry.set(self.left + 1, self.top + 1, self.right - 1, self.top + 2)

            room1.set(self.left + 1, entry.bottom + 2, self.center(rng).x - 1, self.bottom - 1)
            room2.set(room1.right + 2, entry.bottom + 2, self.right - 1, self.bottom - 1)

            Painter.set(level, Point((room1.left + room1.right + 1) // 2, entry.bottom + 1), terrain.CRYSTAL_DOOR)
            Painter.set(level, Point((room2.left + room2.right) // 2, entry.bottom + 1), terrain.CRYSTAL_DOOR)

        elif entrance.x == self.right:
            entry.set(self.right - 2, self.top + 1, self.right - 1, self.bottom - 1)
            Painter.draw_line(level, Point(self.right - 1, self.top + 1), Point(self.right - 1, self.bottom - 1), terrain.EMPTY)

            room1.set(self.left + 1, self.top + 1, entry.left - 2, self.center(rng).y - 1)
            room2.set(self.left + 1, room1.bottom + 2, entry.left - 2, self.bottom - 1)

            Painter.set(level, Point(entry.left - 1, (room1.top + room1.bottom + 1) // 2), terrain.CRYSTAL_DOOR)
            Painter.set(level, Point(entry.left - 1, (room2.top + room2.bottom) // 2), terrain.CRYSTAL_DOOR)

        elif entrance.y == self.bottom:
            entry.set(self.left + 1, self.bottom - 2, self.right - 1, self.bottom - 1)

            room1.set(self.left + 1, self.top + 1, self.center(rng).x - 1, entry.top - 2)
            room2.set(room1.right + 2, self.top + 1, self.right - 1, entry.top - 2)

            Painter.set(level, Point((room1.left + room1.right + 1) // 2, entry.top - 1), terrain.CRYSTAL_DOOR)
            Painter.set(level, Point((room2.left + room2.right) // 2, entry.top - 1), terrain.CRYSTAL_DOOR)

        Painter.fill(level, entry, terrain.EMPTY)
        Painter.fill(level, room1, terrain.EMPTY_SP)
        Painter.fill(level, room2, terrain.EMPTY_SP)

        if rng.IntMax(2) == 0:
            room1, room2 = room2, room1

        n = rng.NormalIntRange(3, 4)
        for _ in range(n):
            cat = "POTION" if rng.IntMax(2) == 0 else "SCROLL"  # Random.oneOf(POTION, SCROLL)
            gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, cat)
            while True:
                if room1.square() >= 16:
                    pos = level.point_to_cell(room1.random(rng, 1))
                else:
                    pos = level.point_to_cell(room1.random(rng, 0))
                if level.heaps.get(pos) is None:
                    break
            level.drop(frozenset(), pos)

        oneof_idx = rng.IntMax(3)  # Random.oneOf(WAND, RING, ARTIFACT)
        hidden_cat = ("WAND", "RING", "ARTIFACT")[oneof_idx]
        gen._dispatch_random_category(level.run_state.generator_state, rng, level.depth, hidden_cat)
        chest_pos = level.point_to_cell(room2.center(rng))
        chest = level.drop(frozenset(), chest_pos)
        chest.type = "CHEST"
        # chest.autoExplored = true -- not modeled (GenHeap has no such field;
        # it only affects exploration-bonus bookkeeping, zero-RNG either way).

        level.add_item_to_spawn(frozenset({"CrystalKey"}))

        self.entrance().set(DoorType.LOCKED)
        level.add_item_to_spawn(_IRON_KEY)


def _sacrifice_crypt_curse(rng: SPDRandom):
    """RNG draw for randomCurse() -- same array size (8) for both
    Weapon.Enchantment and Armor.Glyph curses in SPD."""
    rng.IntMax(8)


def _sacrifice_prize(level, rng: SPDRandom, depth: int):
    """Port of SacrificeRoom.prize() -- Generator.randomWeapon(floorSet+1)
    outer draw + Enchantment.randomCurse()."""
    _consume_random_equipment_floorset(rng, depth // 5 + 1)
    _sacrifice_crypt_curse(rng)
    return frozenset({"Weapon"})


class SacrificeRoom(SpecialRoom):
    def min_width(self) -> int:
        return 7

    def min_height(self) -> int:
        return 7

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.CHASM)

        c = self.center(rng)
        door = self.entrance()
        if door.x == self.left or door.x == self.right:
            if door.y == c.y:
                c.y += -1 if rng.IntMax(2) == 0 else 1
            p = Painter.draw_inside(level, self, door, abs(door.x - c.x) - 2, terrain.EMPTY_SP)
            step_y = 1 if p.y < c.y else -1
            while p.y != c.y:
                p.y += step_y
                Painter.set(level, p, terrain.EMPTY_SP)
        else:
            if door.x == c.x:
                c.x += -1 if rng.IntMax(2) == 0 else 1
            p = Painter.draw_inside(level, self, door, abs(door.y - c.y) - 2, terrain.EMPTY_SP)
            step_x = 1 if p.x < c.x else -1
            while p.x != c.x:
                p.x += step_x
                Painter.set(level, p, terrain.EMPTY_SP)

        s = Point(c.x, c.y)
        s.x -= 2
        if s.x > self.left:
            Painter.set(level, s, terrain.STATUE)
        s.x += 2
        s.y -= 2
        if s.y > self.top:
            Painter.set(level, s, terrain.STATUE)
        s.y += 2
        s.x += 2
        if s.x < self.right:
            Painter.set(level, s, terrain.STATUE)
        s.x -= 2
        s.y += 2
        if s.y < self.bottom:
            Painter.set(level, s, terrain.STATUE)

        Painter.fill(level, c.x - 1, c.y - 1, 3, 3, terrain.EMBERS)
        Painter.set(level, c, terrain.PEDESTAL)

        prize = _sacrifice_prize(level, rng, level.depth)
        if not hasattr(level, "sacrifice_fires"):
            level.sacrifice_fires = []
        max_volume = 6 + level.depth * 4
        level.sacrifice_fires.append({
            "pos": level.point_to_cell(c),
            "volume": max_volume,
            "max_volume": max_volume,
            "prize": prize,
        })

        door.set(DoorType.EMPTY)
