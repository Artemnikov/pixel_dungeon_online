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
"""Port of the SecretRoom subclasses (rooms/secret/*.java) -- see ALL_SECRETS
in registries.py for the SecretRoom.ALL_SECRETS registration order."""

from __future__ import annotations

from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.geom import Point
from app.engine.dungeon.spd_levelgen.painter import Painter
from app.engine.dungeon.spd_levelgen.room import DoorType
from app.engine.dungeon.spd_levelgen.room_types import SecretRoom
from app.engine.dungeon.spd_levelgen.special_rooms._shared import _consume_gold_random, _consume_random_equipment_floorset
from app.engine.dungeon.spd_random import SPDRandom

_POTION_CHANCES = [
    ("Healing", 1.0),
    ("MindVision", 2.0),
    ("Frost", 3.0),
    ("LiquidFlame", 3.0),
    ("ToxicGas", 3.0),
    ("Haste", 4.0),
    ("Invisibility", 4.0),
    ("Levitation", 4.0),
    ("ParalyticGas", 4.0),
    ("Purity", 4.0),
    ("Experience", 6.0),
]

_WELL_WATERS_SIZE = 2


def _patch_generate(rng: SPDRandom, w: int, h: int, fill: float, clustering: int, force_fill_rate: bool) -> list[bool]:
    length = w * h
    cur = [False] * length
    off = [False] * length

    fill_diff = -round(length * fill)

    if force_fill_rate and clustering > 0:
        fill += (0.5 - fill) * 0.5

    for i in range(length):
        off[i] = rng.Float() < fill
        if off[i]:
            fill_diff += 1

    for _ in range(clustering):
        for y in range(h):
            for x in range(w):
                pos = x + y * w
                count = 0
                neighbours = 0
                if y > 0:
                    if x > 0:
                        if off[pos - w - 1]:
                            count += 1
                        neighbours += 1
                    if off[pos - w]:
                        count += 1
                    neighbours += 1
                    if x < w - 1:
                        if off[pos - w + 1]:
                            count += 1
                        neighbours += 1
                if x > 0:
                    if off[pos - 1]:
                        count += 1
                    neighbours += 1
                if off[pos]:
                    count += 1
                neighbours += 1
                if x < w - 1:
                    if off[pos + 1]:
                        count += 1
                    neighbours += 1
                if y < h - 1:
                    if x > 0:
                        if off[pos + w - 1]:
                            count += 1
                        neighbours += 1
                    if off[pos + w]:
                        count += 1
                    neighbours += 1
                    if x < w - 1:
                        if off[pos + w + 1]:
                            count += 1
                        neighbours += 1
                cur[pos] = 2 * count >= neighbours
                if cur[pos] != off[pos]:
                    fill_diff += 1 if cur[pos] else -1

        tmp = cur
        cur = off
        off = tmp

    if force_fill_rate and min(w, h) > 2:
        neighbour_offsets = [-w - 1, -w, -w + 1, -1, 0, +1, +w - 1, +w, +w + 1]
        growing = fill_diff < 0

        while fill_diff != 0:
            cell = 0
            tries = 0
            while True:
                cell = rng.IntRange(1, w - 1) + rng.IntRange(1, h - 1) * w
                tries += 1
                if off[cell] != growing or tries * 10 >= length:
                    break

            for ni in neighbour_offsets:
                if fill_diff != 0 and off[cell + ni] != growing:
                    off[cell + ni] = growing
                    fill_diff += 1 if growing else -1

    return off


def _maze_check_valid_move(maze: list[list[bool]], x: int, y: int, mov_x: int, mov_y: int) -> bool:
    h = len(maze)
    w = len(maze[0])
    side_x = 1 - abs(mov_x)
    side_y = 1 - abs(mov_y)

    x += mov_x
    y += mov_y

    if x <= 0 or x >= h - 1 or y <= 0 or y >= w - 1:
        return False
    if maze[x][y] or maze[x + side_x][y + side_y] or maze[x - side_x][y - side_y]:
        return False

    x += mov_x
    y += mov_y

    if x <= 0 or x >= h - 1 or y <= 0 or y >= w - 1:
        return False
    if maze[x][y]:
        return False
    if maze[x + side_x][y + side_y] or maze[x - side_x][y - side_y]:
        return False

    return True


def _maze_decide_direction(rng: SPDRandom, maze: list[list[bool]], x: int, y: int) -> tuple[int, int] | None:
    if rng.IntMax(4) == 0 and _maze_check_valid_move(maze, x, y, 0, -1):
        return (0, -1)
    if rng.IntMax(3) == 0 and _maze_check_valid_move(maze, x, y, 1, 0):
        return (1, 0)
    if rng.IntMax(2) == 0 and _maze_check_valid_move(maze, x, y, 0, 1):
        return (0, 1)
    if _maze_check_valid_move(maze, x, y, -1, 0):
        return (-1, 0)
    return None


def _maze_generate(rng: SPDRandom, maze: list[list[bool]]) -> None:
    """Mutates maze in-place — true=FILLED (wall), false=EMPTY (path)."""
    h = len(maze)
    w = len(maze[0])
    fails = 0
    while fails < 2500:
        while True:
            x = rng.IntMax(h)
            y = rng.IntMax(w)
            if maze[x][y]:
                break

        mov = _maze_decide_direction(rng, maze, x, y)
        if mov is None:
            fails += 1
        else:
            fails = 0
            moves = 0
            mov_x, mov_y = mov
            while True:
                x += mov_x
                y += mov_y
                maze[x][y] = True
                moves += 1
                if not (rng.IntMax(moves) == 0 and _maze_check_valid_move(maze, x, y, mov_x, mov_y)):
                    break


def _pathfinder_build_distance_map(maze_w: int, maze_h: int, start: int, passable: list[bool]) -> list[int]:
    size = maze_w * maze_h
    max_val = 10 ** 9
    distance = [max_val] * size
    queue = [0] * size

    head = 0
    tail = 0

    queue[tail] = start
    tail += 1
    distance[start] = 0

    while head < tail:
        step = queue[head]
        head += 1
        next_dist = distance[step] + 1
        x = step % maze_w
        start_i = 3 if x == 0 else 0
        end_i = 3 if (x + 1) == maze_w else 0
        dir_lr = [-1 - maze_w, -1, -1 + maze_w, -maze_w, +maze_w, +1 - maze_w, +1, +1 + maze_w]
        for i in range(start_i, len(dir_lr) - end_i):
            n = step + dir_lr[i]
            if 0 <= n < size and passable[n] and distance[n] > next_dist:
                queue[tail] = n
                tail += 1
                distance[n] = next_dist

    return distance


class SecretGardenRoom(SecretRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.GRASS)

        iw = self.width() - 2
        ih = self.height() - 2
        grass = _patch_generate(rng, iw, ih, 0.5, 0, True)
        for i in range(self.top + 1, self.bottom):
            for j in range(self.left + 1, self.right):
                px = (j - self.left - 1) + ((i - self.top - 1) * iw)
                if grass[px]:
                    level.map[i * level.width() + j] = terrain.HIGH_GRASS

        self.entrance().set(DoorType.HIDDEN)

        for _ in range(3):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.plants.get(pos) is None:
                    break
            level.plant("Starflower", pos)

        if rng.IntMax(2) == 0:
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.plants.get(pos) is None:
                    break
            level.plant("Seedpod", pos)
        else:
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.plants.get(pos) is None:
                    break
            level.plant("Dewcatcher", pos)


class SecretLaboratoryRoom(SecretRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        self.entrance().set(DoorType.HIDDEN)

        pot = self.center(rng)
        Painter.set(level, pot, terrain.ALCHEMY)

        for _ in range(2):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                    break
            qty = rng.IntRange(3, 5)
            level.drop(frozenset({"EnergyCrystal", f"qty:{qty}"}), pos)

        n = rng.IntRange(2, 3)
        weights = [w for _, w in _POTION_CHANCES]
        for _ in range(n):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                    break

            idx = rng.chances(weights)
            weights[idx] = 0.0
            exotic_chance = rng.Float()
            level.drop(frozenset({"Potion"}), pos)


class SecretLibraryRoom(SecretRoom):
    def min_width(self) -> int:
        return max(7, super().min_width())

    def min_height(self) -> int:
        return max(7, super().min_height())

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.BOOKSHELF)

        Painter.fill_ellipse(level, self, 2, terrain.EMPTY_SP)

        entrance = self.entrance()
        if entrance.x == self.left or entrance.x == self.right:
            Painter.draw_inside(level, self, entrance, (self.width() - 3) // 2, terrain.EMPTY_SP)
        else:
            Painter.draw_inside(level, self, entrance, (self.height() - 3) // 2, terrain.EMPTY_SP)
        entrance.set(DoorType.HIDDEN)

        n = rng.IntRange(2, 3)
        for _ in range(n):
            while True:
                pos = level.point_to_cell(self.random(rng))
                if level.map[pos] == terrain.EMPTY_SP and level.heaps.get(pos) is None:
                    break
            # Random.chances(HashMap<ScrollClass,Float>) -- one Float(sum) draw;
            # identity irrelevant (the chosen weight is zeroed for the next pick,
            # but that only changes the *value* drawn, not the draw count). Every
            # key in scrollChances has an entry in ExoticScroll.regToExo, so the
            # post-pick `Random.Float() < consumableExoticChance()` exotic roll
            # ALWAYS fires too -- exactly 2 Float() draws per iteration.
            rng.Float()
            rng.Float()
            level.drop(frozenset(), pos)  # registers the heap so later iterations' collision check sees it


class SecretLarderRoom(SecretRoom):
    def min_width(self) -> int:
        return 6

    def min_height(self) -> int:
        return 6

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        c = self.center(rng)

        Painter.fill(level, c.x - 1, c.y - 1, 3, 3, terrain.WATER)
        Painter.set(level, c, terrain.GRASS)

        extra_food = int(300 * (1 + level.depth / 5))
        while extra_food > 0:
            if extra_food >= 600:
                extra_food -= 600
                food_type = "Pasty"
            else:
                extra_food -= 300
                food_type = "ChargrilledMeat"

            while True:
                food_pos = level.point_to_cell(self.random(rng))
                if level.map[food_pos] == terrain.EMPTY_SP and level.heaps.get(food_pos) is None:
                    break
            level.drop(frozenset({"Food", food_type}), food_pos)

        self.entrance().set(DoorType.HIDDEN)


class SecretWellRoom(SecretRoom):
    def can_connect_point(self, p: Point) -> bool:
        return super().can_connect_point(p) and ((p.x > self.left + 1 and p.x < self.right - 1) or (p.y > self.top + 1 and p.y < self.bottom - 1))

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        door = self.entrance()
        if door.x == self.left:
            well = Point(self.right - 2, door.y)
        elif door.x == self.right:
            well = Point(self.left + 2, door.y)
        elif door.y == self.top:
            well = Point(door.x, self.bottom - 2)
        else:
            well = Point(door.x, self.top + 2)

        Painter.fill(level, well.x - 1, well.y - 1, 3, 3, terrain.CHASM)
        Painter.draw_line(level, door, well, terrain.EMPTY)

        Painter.set(level, well, terrain.WELL)

        rng.IntMax(_WELL_WATERS_SIZE)

        self.entrance().set(DoorType.HIDDEN)


_STONE_PROBS = (0.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 0.0)


class SecretRunestoneRoom(SecretRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        entrance = self.entrance()
        center = self.center(rng)

        if entrance.x == self.left or entrance.x == self.right:
            Painter.draw_line(level, Point(center.x, self.top + 1), Point(center.x, self.bottom - 1), terrain.BOOKSHELF)
            if entrance.x == self.left:
                Painter.fill(level, center.x + 1, self.top + 1, self.right - center.x - 1, self.height() - 2, terrain.EMPTY_SP)
            else:
                Painter.fill(level, self.left + 1, self.top + 1, center.x - self.left - 1, self.height() - 2, terrain.EMPTY_SP)
        else:
            Painter.draw_line(level, Point(self.left + 1, center.y), Point(self.right - 1, center.y), terrain.BOOKSHELF)
            if entrance.y == self.top:
                Painter.fill(level, self.left + 1, center.y + 1, self.width() - 2, self.bottom - center.y - 1, terrain.EMPTY_SP)
            else:
                Painter.fill(level, self.left + 1, self.top + 1, self.width() - 2, center.y - self.top - 1, terrain.EMPTY_SP)

        while True:
            drop_pos = level.point_to_cell(self.random(rng))
            if level.map[drop_pos] == terrain.EMPTY:
                break
        rng.chances(_STONE_PROBS)
        level.drop(frozenset({"Runestone"}), drop_pos)

        while True:
            drop_pos = level.point_to_cell(self.random(rng))
            if level.map[drop_pos] == terrain.EMPTY and level.heaps.get(drop_pos) is None:
                break
        rng.chances(_STONE_PROBS)
        level.drop(frozenset({"Runestone"}), drop_pos)

        while True:
            drop_pos = level.point_to_cell(self.random(rng))
            if level.map[drop_pos] == terrain.EMPTY_SP:
                break

        self.entrance().set(DoorType.HIDDEN)

    def can_place_water(self, p: Point) -> bool:
        return False

    def can_place_grass(self, p: Point) -> bool:
        return False

    def can_place_character(self, p: Point, l) -> bool:
        return super().can_place_character(p, l) and l.map[l.point_to_cell(p)] != terrain.EMPTY_SP


class SecretArtilleryRoom(SecretRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY_SP)

        Painter.set(level, self.center(rng), terrain.STATUE_SP)

        for i in range(3):
            while True:
                item_pos = level.point_to_cell(self.random(rng))
                if level.map[item_pos] == terrain.EMPTY_SP and level.heaps.get(item_pos) is None:
                    break

            if i != 0:
                _consume_random_equipment_floorset(rng, level.depth // 5)
            level.drop(frozenset({"Weapon"}), item_pos)

        self.entrance().set(DoorType.HIDDEN)


class SecretChestChasmRoom(SecretRoom):
    def min_width(self) -> int:
        return 8

    def max_width(self) -> int:
        return 9

    def min_height(self) -> int:
        return 8

    def max_height(self) -> int:
        return 9

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen
        from app.engine.dungeon.spd_levelgen.run_state import SPAWN_GOLDEN_KEY

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.CHASM)

        chests = 0

        # Four chest positions (inner corners of the room)
        p = Point(self.left + 3, self.top + 3)
        Painter.set(level, p, terrain.EMPTY_SP)
        item = gen.generator_random_using_defaults(level.run_state.generator_state, rng, level.depth)
        dropped = level.drop(item, level.point_to_cell(p))
        dropped.type = "LOCKED_CHEST"
        if level.heaps.get(level.point_to_cell(p)) is dropped:
            chests += 1

        p.x = self.right - 3
        Painter.set(level, p, terrain.EMPTY_SP)
        item = gen.generator_random_using_defaults(level.run_state.generator_state, rng, level.depth)
        dropped = level.drop(item, level.point_to_cell(p))
        dropped.type = "LOCKED_CHEST"
        if level.heaps.get(level.point_to_cell(p)) is dropped:
            chests += 1

        p.y = self.bottom - 3
        Painter.set(level, p, terrain.EMPTY_SP)
        item = gen.generator_random_using_defaults(level.run_state.generator_state, rng, level.depth)
        dropped = level.drop(item, level.point_to_cell(p))
        dropped.type = "LOCKED_CHEST"
        if level.heaps.get(level.point_to_cell(p)) is dropped:
            chests += 1

        p.x = self.left + 3
        Painter.set(level, p, terrain.EMPTY_SP)
        item = gen.generator_random_using_defaults(level.run_state.generator_state, rng, level.depth)
        dropped = level.drop(item, level.point_to_cell(p))
        dropped.type = "LOCKED_CHEST"
        if level.heaps.get(level.point_to_cell(p)) is dropped:
            chests += 1

        # Four key positions (outer corners) -- one golden key per chest
        p = Point(self.left + 1, self.top + 1)
        Painter.set(level, p, terrain.EMPTY_SP)
        if chests > 0:
            level.drop(SPAWN_GOLDEN_KEY, level.point_to_cell(p))
            chests -= 1

        p.x = self.right - 1
        Painter.set(level, p, terrain.EMPTY_SP)
        if chests > 0:
            level.drop(SPAWN_GOLDEN_KEY, level.point_to_cell(p))
            chests -= 1

        p.y = self.bottom - 1
        Painter.set(level, p, terrain.EMPTY_SP)
        if chests > 0:
            level.drop(SPAWN_GOLDEN_KEY, level.point_to_cell(p))
            chests -= 1

        p.x = self.left + 1
        Painter.set(level, p, terrain.EMPTY_SP)
        if chests > 0:
            level.drop(SPAWN_GOLDEN_KEY, level.point_to_cell(p))
            chests -= 1

        level.add_item_to_spawn(frozenset())  # PotionOfLevitation

        self.entrance().set(DoorType.HIDDEN)


class SecretHoneypotRoom(SecretRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        broken_pot_pos = self.center(rng)

        broken_pot_pos.x = (broken_pot_pos.x + self.entrance().x) // 2
        broken_pot_pos.y = (broken_pot_pos.y + self.entrance().y) // 2

        broken_cell = level.point_to_cell(broken_pot_pos)
        level.drop(frozenset({"Bomb", "ShatteredPot"}), broken_cell)

        while True:
            item_pos = level.point_to_cell(self.random(rng))
            if level.heaps.get(item_pos) is None:
                break
        level.drop(frozenset({"Bomb", "Honeypot"}), item_pos)

        while True:
            item_pos = level.point_to_cell(self.random(rng))
            if level.heaps.get(item_pos) is None:
                break
        level.drop(frozenset({"Bomb"}), item_pos)

        rng.IntMax(2)

        self.entrance().set(DoorType.HIDDEN)


class SecretHoardRoom(SecretRoom):
    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        rng.IntMax(2)

        total_gold = ((self.width() - 2) * (self.height() - 2)) // 2
        for _ in range(total_gold):
            while True:
                gold_pos = level.point_to_cell(self.random(rng))
                if level.heaps.get(gold_pos) is None:
                    break
            _consume_gold_random(rng, level.depth)
            level.drop(frozenset({"Gold"}), gold_pos)

        for x in range(self.left, self.right + 1):
            for y in range(self.top, self.bottom + 1):
                roll_hit = rng.IntMax(2) == 0
                if roll_hit and level.map[level.point_to_cell(Point(x, y))] == terrain.EMPTY:
                    Painter.set(level, x, y, terrain.TRAP)

        self.entrance().set(DoorType.HIDDEN)


class SecretMazeRoom(SecretRoom):
    def min_width(self) -> int:
        return 14

    def min_height(self) -> int:
        return 14

    def max_width(self) -> int:
        return 18

    def max_height(self) -> int:
        return 18

    def paint(self, level, rng: SPDRandom) -> None:
        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.EMPTY)

        mw = self.width()
        mh = self.height()
        maze = [[False] * mh for _ in range(mw)]
        for x in range(mw):
            for y in range(mh):
                if x == 0 or x == mw - 1 or y == 0 or y == mh - 1:
                    maze[x][y] = True

        for d in self.connected.values():
            maze[d.x - self.left][d.y - self.top] = False

        _maze_generate(rng, maze)

        Painter.fill(level, self, 1, terrain.EMPTY)
        passable = [False] * (mw * mh)
        for x in range(mw):
            for y in range(mh):
                if maze[x][y]:
                    Painter.fill(level, x + self.left, y + self.top, 1, 1, terrain.WALL)
                passable[x + mw * y] = not maze[x][y]

        entrance = self.entrance()
        entrance_pos = (entrance.x - self.left) + mw * (entrance.y - self.top)
        distance = _pathfinder_build_distance_map(mw, mh, entrance_pos, passable)

        best_dist = 0
        best_p = Point()
        for i in range(mw * mh):
            if distance[i] != 10**9 and distance[i] > best_dist:
                best_dist = distance[i]
                best_p.x = (i % mw) + self.left
                best_p.y = (i // mw) + self.top

        rng.IntMax(2)
        _consume_random_equipment_floorset(rng, level.depth // 5 + 1)
        rng.IntMax(3)

        best_cell = level.point_to_cell(best_p)
        level.drop(frozenset({"Weapon"}), best_cell)

        self.entrance().set(DoorType.HIDDEN)


class SecretSummoningRoom(SecretRoom):
    def max_width(self) -> int:
        return 8

    def max_height(self) -> int:
        return 8

    def paint(self, level, rng: SPDRandom) -> None:
        from app.engine.dungeon.spd_levelgen import generator as gen
        from app.engine.dungeon.spd_levelgen.traps import SummoningTrap, reveal_hidden_trap_chance

        Painter.fill(level, self, terrain.WALL)
        Painter.fill(level, self, 1, terrain.SECRET_TRAP)

        center = self.center(rng)
        gen.generator_random(level.run_state.generator_state, rng, level.depth)

        center_cell = level.point_to_cell(center)
        level.drop(frozenset({"Scroll"}), center_cell)

        revealed_chance = reveal_hidden_trap_chance()
        reveal_inc = 0
        for p in self.get_points():
            cell_idx = level.point_to_cell(p)
            if level.map[cell_idx] == terrain.SECRET_TRAP:
                reveal_inc += revealed_chance
                if reveal_inc >= 1:
                    level.set_trap(SummoningTrap().reveal(), cell_idx)
                    Painter.set(level, cell_idx, terrain.TRAP)
                    reveal_inc -= 1
                else:
                    level.set_trap(SummoningTrap().hide(), cell_idx)

        self.entrance().set(DoorType.HIDDEN)
