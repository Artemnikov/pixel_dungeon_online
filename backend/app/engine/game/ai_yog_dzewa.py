# Copyright (C) 2026 ArtemNikov
#
"""Full 1-1 SPD implementation of Yog-Dzewa boss AI and the six YogFists minion
behaviors (HallsBossLevel / YogDzewa.java / YogFist.java).
"""

import random
from typing import List, Optional, Tuple

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position, is_immune
from app.engine.entities.buffs import add_buff
from app.engine.entities.mobs import (
    BrightFist, BurningFist, DarkFist, DemonSpawner, Larva, RottingFist,
    RustedFist, SoiledFist, YogDzewa, YogEye, YogRipper, YogScorpio,
)
from app.engine.entities.mobs.halls import _is_fist_near_yog
from app.engine.game.ai_ranged_common import ranged_accuracy_roll
from app.engine.game.constants import TICKS_PER_TURN as _TICKS_PER_TURN
from app.engine.game.floor_state import FloorState
from app.engine.systems.ballistica import bresenham
from app.engine.systems.loot import roll_drops


def ballistica_wont_stop(src_x: int, src_y: int, target_x: int, target_y: int,
                         width: int, height: int) -> List[Tuple[int, int]]:
    """Port of Ballistica.WONT_STOP -- projects ray through target to map edge."""
    dx = target_x - src_x
    dy = target_y - src_y
    if dx == 0 and dy == 0:
        return [(src_x, src_y)]
    scale = max(width, height) * 2
    end_x = src_x + dx * scale
    end_y = src_y + dy * scale
    cells = bresenham(src_x, src_y, end_x, end_y)
    path = []
    for cx, cy in cells:
        if 0 <= cx < width and 0 <= cy < height:
            path.append((cx, cy))
        else:
            break
    return path


def _get_spawners_alive(game) -> int:
    """Return count of alive DemonSpawner mobs on floors 21..24."""
    count = 0
    for fid in (21, 22, 23, 24):
        f = game.floors.get(fid)
        if f:
            for m in f.mobs.values():
                if isinstance(m, DemonSpawner) and m.is_alive:
                    count += 1
    return count


def build_fist_schedule(challenged: bool) -> Tuple[List[str], List[str]]:
    """Port of YogDzewa fist pairings and challenge spawns."""
    fist_summons = [
        random.choice(["BurningFist", "SoiledFist"]),
        random.choice(["RottingFist", "RustedFist"]),
        random.choice(["BrightFist", "DarkFist"]),
    ]
    random.shuffle(fist_summons)

    pairs = {
        "BurningFist": "SoiledFist",
        "SoiledFist": "BurningFist",
        "RottingFist": "RustedFist",
        "RustedFist": "RottingFist",
        "BrightFist": "DarkFist",
        "DarkFist": "BrightFist",
    }

    challenge_summons = []
    if challenged:
        if random.random() < 0.5:
            challenge_summons = [
                pairs[fist_summons[1]],
                pairs[fist_summons[2]],
                pairs[fist_summons[0]],
            ]
        else:
            challenge_summons = [
                pairs[fist_summons[2]],
                pairs[fist_summons[0]],
                pairs[fist_summons[1]],
            ]

    return fist_summons, challenge_summons


def build_regular_summons(spawners_alive: int, challenged: bool) -> List[type]:
    """Port of YogDzewa regular minion deck based on alive DemonSpawners."""
    summons = []
    if challenged:
        for i in range(6):
            if i >= 4:
                summons.append(YogRipper)
            elif i >= spawners_alive:
                summons.append(Larva)
            else:
                summons.append(YogEye if i % 2 == 0 else YogScorpio)
    else:
        for i in range(4):
            if i >= spawners_alive:
                summons.append(Larva)
            else:
                summons.append(YogRipper)
    random.shuffle(summons)
    return summons


def _yog_phase_view_distance(phase: int) -> int:
    """SPD: level.viewDistance during the Yog fight, shrinking each phase
    (phase 1->4, 2->3, 3->2, 4->1, 5->1)."""
    if phase <= 1:
        return 4
    return max(4 - (phase - 1), 1)


def _yog_maybe_seal_arena(game, player, floor: FloorState, floor_id: int) -> None:
    """Port of HallsBossLevel.seal(): seals the entrance, applies LockedFloor buff,
    starts boss music, and kicks off Phase 1."""
    if floor_id != 25 or floor.generation_meta.get("yog_sealed", False):
        return

    yog = next((m for m in floor.mobs.values() if isinstance(m, YogDzewa) and m.is_alive), None)
    if not yog:
        return

    entrance = floor.entrance_pos or (16, 26)
    dist_from_ent = max(abs(player.pos.x - entrance[0]), abs(player.pos.y - entrance[1]))
    dist_from_yog = max(abs(player.pos.x - yog.pos.x), abs(player.pos.y - yog.pos.y))

    if dist_from_ent >= 2 or dist_from_yog <= 12:
        floor.generation_meta["yog_sealed"] = True
        ex, ey = entrance
        floor.grid[ey][ex] = TileType.FLOOR_WOOD
        floor.rebuild_flags()
        game.add_event("MAP_PATCH", {"tiles": [{"x": ex, "y": ey, "tile": TileType.FLOOR_WOOD}]}, floor_id=floor_id)
        game.add_event("PLAY_SOUND", {"sound": "BOSS"}, floor_id=floor_id)
        game.add_event("BOSS_YELL", {"mob": yog.id, "text": "Hope is an illusion...", "x": yog.pos.x, "y": yog.pos.y}, floor_id=floor_id)

        for p in game._players_on_floor(floor_id):
            p.locked_floor_left = 0.0

        yog.fight_started = True
        yog.phase = 1
        spawners_alive = _get_spawners_alive(game)
        challenged = "stronger_bosses" in game.challenges
        fist_summons, challenge_summons = build_fist_schedule(challenged)
        yog.fist_order = fist_summons
        yog.challenge_summons = challenge_summons
        yog.regular_summons = [cls.__name__ for cls in build_regular_summons(spawners_alive, challenged)]
        yog.ability_cooldown = random.uniform(10, 15) * _TICKS_PER_TURN
        yog.summon_cooldown = random.uniform(10, 15) * _TICKS_PER_TURN
        floor.view_distance = _yog_phase_view_distance(yog.phase)

        game.add_event("YOG_FIGHT_STARTED", {"mob": yog.id}, floor_id=floor_id)
        game.add_event("PLAY_MUSIC", {"track": "halls_boss"}, floor_id=floor_id)


def _spawn_fist_at_altar(game, floor: FloorState, floor_id: int, yog: YogDzewa, fist_cls_name: str) -> None:
    _FIST_CLASSES = {
        "BurningFist": BurningFist,
        "SoiledFist": SoiledFist,
        "RottingFist": RottingFist,
        "RustedFist": RustedFist,
        "BrightFist": BrightFist,
        "DarkFist": DarkFist,
    }
    fist_cls = _FIST_CLASSES.get(fist_cls_name, BurningFist)

    altar = floor.exit_pos or (16, 9)
    candidates = [
        (altar[0], altar[1] + 1),
        (altar[0] - 1, altar[1] + 1),
        (altar[0] + 1, altar[1] + 1),
        altar,
    ]
    spawn_pos = candidates[0]
    for c in candidates:
        if not any(m.is_alive and m.pos.x == c[0] and m.pos.y == c[1] for m in floor.mobs.values()):
            spawn_pos = c
            break

    new_fist = game._spawn_mob_at(fist_cls, spawn_pos[0], spawn_pos[1])
    new_fist.yog_id = yog.id
    new_fist.ai_state = "hunting"
    floor.mobs[new_fist.id] = new_fist
    yog.fist_ids.append(new_fist.id)

    game.add_event("YOG_FIST_SPAWN",
                   {"mob": yog.id, "fist": new_fist.id, "cls": fist_cls_name,
                    "x": spawn_pos[0], "y": spawn_pos[1]},
                   floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "BURST"}, floor_id=floor_id)


def _update_yog_dzewa(game, yog: YogDzewa, floor: FloorState, floor_id: int):
    """Main tick update for Yog-Dzewa boss on floor 25."""
    if not yog.fight_started:
        target = game._find_nearest_player(yog.pos, floor_id)
        if target is not None and max(abs(yog.pos.x - target.pos.x), abs(yog.pos.y - target.pos.y)) <= 12:
            _yog_maybe_seal_arena(game, target, floor, floor_id)
        return

    alive_fists = [m for m in floor.mobs.values()
                   if m.id in yog.fist_ids and m.is_alive]

    HP_FLOORS = {1: 700, 2: 400, 3: 100, 4: 100}

    if yog.phase in (1, 2, 3) and yog.hp <= HP_FLOORS[yog.phase]:
        yog.hp = HP_FLOORS[yog.phase]
        yog.phase += 1

        if yog.fist_order:
            next_fist = yog.fist_order.pop(0)
            _spawn_fist_at_altar(game, floor, floor_id, yog, next_fist)
        if yog.challenge_summons:
            next_ch_fist = yog.challenge_summons.pop(0)
            _spawn_fist_at_altar(game, floor, floor_id, yog, next_ch_fist)

        floor.view_distance = _yog_phase_view_distance(yog.phase)
        yog.ability_cooldown = max(yog.ability_cooldown, 5 * _TICKS_PER_TURN)
        yog.summon_cooldown = max(yog.summon_cooldown, 5 * _TICKS_PER_TURN)

        game.add_event("YOG_PHASE_CHANGE", {"mob": yog.id, "phase": yog.phase}, floor_id=floor_id)
        game.add_event("BOSS_YELL", {"mob": yog.id, "text": "The darkness thickens...", "x": yog.pos.x, "y": yog.pos.y}, floor_id=floor_id)

    elif yog.phase == 4:
        alive_fists = [m for m in floor.mobs.values()
                       if m.id in yog.fist_ids and m.is_alive]
        if len(alive_fists) == 0:
            yog.phase = 5
            floor.view_distance = _yog_phase_view_distance(yog.phase)
            yog.summon_cooldown = -15
            game.add_event("YOG_FINAL_PHASE", {"mob": yog.id}, floor_id=floor_id)
            game.add_event("BOSS_YELL", {"mob": yog.id, "text": "Hope... is an illusion...", "x": yog.pos.x, "y": yog.pos.y}, floor_id=floor_id)
            game.add_event("PLAY_MUSIC", {"track": "halls_boss_finale"}, floor_id=floor_id)

    if yog.phase < 5 and yog.hp < HP_FLOORS[yog.phase]:
        yog.hp = HP_FLOORS[yog.phase]

    target = game._find_nearest_player(yog.pos, floor_id)
    if target is None:
        return

    # Death Ray handling (Telegraph -> Fire)
    if yog.targeted_cells and yog.ability_telegraph_timer > 0:
        yog.ability_telegraph_timer -= 1
        if yog.ability_telegraph_timer == 0:
            _fire_yog_death_ray(game, yog, floor, floor_id)
    else:
        if yog.ability_cooldown > 0:
            yog.ability_cooldown -= 1
        else:
            _charge_yog_death_ray(game, yog, target, floor, floor_id)

    # Minion summon handling
    if yog.summon_cooldown > 0:
        yog.summon_cooldown -= 1
    else:
        _summon_yog_minion(game, yog, target, floor, floor_id, alive_fists)


def _charge_yog_death_ray(game, yog: YogDzewa, target, floor: FloorState, floor_id: int):
    beams = max(1, 1 + (yog.max_hp - yog.hp) // 400)
    targeted_paths = []
    affected_cells = set()

    for b_idx in range(beams):
        t_pos = (target.pos.x, target.pos.y)
        if b_idx != 0:
            offsets = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
            dx, dy = random.choice(offsets)
            candidate = (target.pos.x + dx, target.pos.y + dy)
            if 0 <= candidate[0] < floor.width and 0 <= candidate[1] < floor.height:
                t_pos = candidate

        path = ballistica_wont_stop(yog.pos.x, yog.pos.y, t_pos[0], t_pos[1], floor.width, floor.height)
        targeted_paths.append(path)
        affected_cells.update(path)

    yog.targeted_cells = list(affected_cells)
    yog.ability_telegraph_timer = int(0.75 * _TICKS_PER_TURN)

    cooldown = (random.randint(10, 15) - (yog.phase - 1)) * _TICKS_PER_TURN
    if yog.phase == 5:
        cooldown = min(cooldown, 2 * _TICKS_PER_TURN)
    yog.ability_cooldown = max(2 * _TICKS_PER_TURN, cooldown)

    game.add_event("TARGETED_CELLS", {"cells": [list(c) for c in affected_cells], "color": "red"}, floor_id=floor_id)


def _fire_yog_death_ray(game, yog: YogDzewa, floor: FloorState, floor_id: int):
    cells = yog.targeted_cells
    if not cells:
        return

    is_challenged = "stronger_bosses" in game.challenges
    dmg_range = (30, 50) if is_challenged else (20, 30)

    patches = []

    for cx, cy in cells:
        for p in game._players_on_floor(floor_id):
            if p.is_alive and p.pos.x == cx and p.pos.y == cy:
                dmg = random.randint(*dmg_range)
                taken = p.take_damage(dmg)
                game.boss_scores[4] = max(0, game.boss_scores[4] - 500)
                game.add_event("ATTACK", {"source": yog.id, "target": p.id, "damage": taken, "surprise": False}, floor_id=floor_id)
                if taken > 0:
                    game.add_event("DAMAGE", {"target": p.id, "amount": taken}, floor_id=floor_id)

        for m in list(floor.mobs.values()):
            if m.is_alive and m.id != yog.id and m.id not in yog.fist_ids and m.pos.x == cx and m.pos.y == cy:
                dmg = random.randint(*dmg_range)
                taken = m.take_damage(dmg)
                if taken > 0:
                    game.add_event("DAMAGE", {"target": m.id, "amount": taken}, floor_id=floor_id)

        t = floor.grid[cy][cx]
        if t in (TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.FURROWED_GRASS, TileType.BOOKSHELF, TileType.BARRICADE):
            floor.grid[cy][cx] = TileType.EMBERS
            patches.append({"x": cx, "y": cy, "tile": TileType.EMBERS})

    if patches:
        floor.rebuild_flags()
        game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)

    game.add_event("YOG_DEATH_RAY", {"mob": yog.id, "cells": [list(c) for c in cells]}, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "RAY"}, floor_id=floor_id)
    yog.targeted_cells = []


def _summon_yog_minion(game, yog: YogDzewa, target, floor: FloorState, floor_id: int, alive_fists: list):
    if not yog.regular_summons:
        spawners_alive = _get_spawners_alive(game)
        challenged = "stronger_bosses" in game.challenges
        yog.regular_summons = [cls.__name__ for cls in build_regular_summons(spawners_alive, challenged)]

    minion_name = yog.regular_summons.pop(0)
    yog.regular_summons.append(minion_name)

    _MINION_MAP = {
        "Larva": Larva,
        "YogRipper": YogRipper,
        "YogEye": YogEye,
        "YogScorpio": YogScorpio,
    }
    minion_cls = _MINION_MAP.get(minion_name, Larva)

    neighbors = [
        (yog.pos.x + dx, yog.pos.y + dy)
        for dx, dy in [(-1, -1), (0, -1), (1, -1), (-1, 0),
                        (1, 0), (-1, 1), (0, 1), (1, 1)]
    ]
    neighbors.sort(key=lambda p: abs(p[0] - target.pos.x) + abs(p[1] - target.pos.y))

    for sx, sy in neighbors:
        if not (0 <= sx < floor.width and 0 <= sy < floor.height):
            continue
        if floor.grid[sy][sx] == TileType.WALL:
            continue
        occupied = any(
            m.is_alive and m.pos.x == sx and m.pos.y == sy
            for m in floor.mobs.values()
        )
        if not occupied:
            minion = game._spawn_mob_at(minion_cls, sx, sy)
            floor.mobs[minion.id] = minion
            game.add_event("MOB_SPAWN", {"mob": minion.id, "cls": minion_name, "x": sx, "y": sy}, floor_id=floor_id)
            break

    cooldown = (random.randint(10, 15) - (yog.phase - 1)) * _TICKS_PER_TURN
    if alive_fists:
        cooldown += 10 * _TICKS_PER_TURN
    if yog.phase == 5:
        cooldown = min(cooldown, 3 * _TICKS_PER_TURN)
    yog.summon_cooldown = max(1, cooldown)


def _burning_fist_tick_passive(game, fist, floor: FloorState, floor_id: int):
    patches = []
    if floor.grid[fist.pos.y][fist.pos.x] == TileType.FLOOR_WATER:
        floor.grid[fist.pos.y][fist.pos.x] = TileType.FLOOR
        patches.append({"x": fist.pos.x, "y": fist.pos.y, "tile": TileType.FLOOR})

    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nx, ny = fist.pos.x + dx, fist.pos.y + dy
        if 0 <= nx < floor.width and 0 <= ny < floor.height:
            if floor.grid[ny][nx] == TileType.FLOOR_WATER:
                floor.grid[ny][nx] = TileType.FLOOR
                patches.append({"x": nx, "y": ny, "tile": TileType.FLOOR})

    if patches:
        floor.rebuild_flags()
        game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)

    cells_set = set()
    vol_dict = {}
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            fx, fy = fist.pos.x + dx, fist.pos.y + dy
            if 0 <= fx < floor.width and 0 <= fy < floor.height:
                if floor.grid[fy][fx] not in (TileType.WALL, TileType.WALL_DECO, TileType.FLOOR_WATER):
                    cells_set.add((fx, fy))
                    vol_dict[(fx, fy)] = 4
    if cells_set:
        blob_id = f"burning_fist_fire_{fist.id}"
        floor.blob_areas[blob_id] = {"type": "fire", "cells": cells_set, "volume": vol_dict, "origin": (fist.pos.x, fist.pos.y)}
        game.add_event("BLOB_UPDATE", {"id": blob_id, "type": "fire", "cells": [list(c) for c in cells_set]}, floor_id=floor_id)


def _soiled_fist_tick_passive(game, fist, floor: FloorState, floor_id: int):
    yog = floor.mobs.get(fist.yog_id) if fist.yog_id else None
    yog_pos = (yog.pos.x, yog.pos.y) if yog else (16, 12)

    patches = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            gx, gy = fist.pos.x + dx, fist.pos.y + dy
            if 0 <= gx < floor.width and 0 <= gy < floor.height:
                dist_to_yog = max(abs(gx - yog_pos[0]), abs(gy - yog_pos[1]))
                if dist_to_yog > 4:
                    curr_tile = floor.grid[gy][gx]
                    if curr_tile == TileType.FLOOR:
                        floor.grid[gy][gx] = TileType.FLOOR_GRASS
                        patches.append({"x": gx, "y": gy, "tile": TileType.FLOOR_GRASS})

    if patches:
        floor.rebuild_flags()
        game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)


def _update_yog_fist(game, fist, floor: FloorState, floor_id: int) -> bool:
    """Main tick update for Yog's fists."""
    if fist.ranged_cooldown > 0:
        fist.ranged_cooldown -= 1

    if isinstance(fist, RustedFist) and fist.viscosity_stacks > 0:
        released = max(1, fist.viscosity_stacks // 10)
        released = min(released, fist.viscosity_stacks)
        fist.hp = max(0, fist.hp - released)
        fist.viscosity_stacks -= released
        if fist.hp <= 0:
            fist.is_alive = False
            fist.die(floor_mobs=floor.mobs, tile_x=fist.pos.x, tile_y=fist.pos.y,
                     players=game._players_on_floor(floor_id))
            game.add_event("DEATH", {"target": fist.id}, floor_id=floor_id)
            game.handle_mob_death(fist, floor, floor_id)
            for item in roll_drops(fist, game.drop_counters, fist.pos.x, fist.pos.y,
                                    players=list(game._players_on_floor(floor_id))):
                floor.items[item.id] = item

    if isinstance(fist, RottingFist) and fist.is_alive:
        if floor.grid[fist.pos.y][fist.pos.x] == TileType.FLOOR_WATER and fist.hp < fist.max_hp:
            fist.hp = min(fist.max_hp, fist.hp + fist.max_hp // 50)
            game.add_event("HEAL", {"target": fist.id, "amount": fist.max_hp // 50}, floor_id=floor_id)

    if isinstance(fist, (BrightFist, DarkFist)) and getattr(fist, "pending_teleport", False):
        _yog_fist_teleport(game, fist, floor, floor_id)

    if isinstance(fist, BurningFist) and fist.is_alive:
        _burning_fist_tick_passive(game, fist, floor, floor_id)

    if isinstance(fist, SoiledFist) and fist.is_alive:
        _soiled_fist_tick_passive(game, fist, floor, floor_id)

    if not fist.is_alive:
        return True

    target = game._find_nearest_player(fist.pos, floor_id)
    if target is None:
        return False

    dist = game._get_distance(fist.pos, target.pos)

    if _is_fist_near_yog(fist, floor.mobs) and not getattr(fist, "invuln_warned", False):
        fist.invuln_warned = True
        game.add_event("MESSAGE", {"text": f"{fist.name} is invulnerable while close to Yog-Dzewa!"}, floor_id=floor_id)

    if isinstance(fist, (BrightFist, DarkFist)):
        if game._is_in_los(fist.pos, target.pos, floor_id=floor_id):
            if isinstance(fist, BrightFist):
                _fist_zap_bright(game, fist, target, floor_id)
            else:
                _fist_zap_dark(game, fist, target, floor_id)
            return True
        return False

    if dist > 1 and fist.ranged_cooldown <= 0 and game._is_in_los(fist.pos, target.pos, floor_id=floor_id):
        if isinstance(fist, BurningFist):
            _fist_zap_burning(game, fist, target, floor_id)
        elif isinstance(fist, SoiledFist):
            _fist_zap_soiled(game, fist, target, floor_id)
        elif isinstance(fist, RottingFist):
            _fist_zap_rotting(game, fist, target, floor_id)
        elif isinstance(fist, RustedFist):
            _fist_zap_rusted(game, fist, target, floor_id)
        fist.ranged_cooldown = random.uniform(8, 12)
        return True

    return False


def _yog_fist_teleport(game, fist, floor: FloorState, floor_id: int):
    floor_tiles = [
        (x, y) for y in range(floor.height) for x in range(floor.width)
        if floor.grid[y][x] in [TileType.FLOOR, TileType.FLOOR_WOOD, TileType.FLOOR_WATER,
                                 TileType.FLOOR_COBBLE, TileType.FLOOR_GRASS]
        and not any(m.is_alive and m.pos.x == x and m.pos.y == y for m in floor.mobs.values())
        and not any(p.is_alive and p.pos.x == x and p.pos.y == y for p in game._players_on_floor(floor_id))
    ]
    if floor_tiles:
        x, y = random.choice(floor_tiles)
        fist.pos = Position(x=x, y=y)
        fist.ai_state = "wandering"

        target = game._find_nearest_player(fist.pos, floor_id)
        if target is not None:
            add_buff(target.buffs, "blindness", duration=15.0, level=2, stack_mode="extend")

        game.add_event("FIST_TELEPORT", {"mob": fist.id, "x": x, "y": y}, floor_id=floor_id)

    fist.pending_teleport = False


def _fist_zap_burning(game, fist, target, floor_id: int):
    if not ranged_accuracy_roll(game, fist, target, floor_id, {"fire": True}):
        return
    dmg = target.take_damage(random.randint(8, 16))
    if not is_immune(target, "burning"):
        add_buff(target.buffs, "burning", duration=3.0, level=1, stack_mode="extend")
    game.add_event("ATTACK", {"source": fist.id, "target": target.id,
                              "damage": dmg, "surprise": False, "fire": True}, floor_id=floor_id)
    if dmg > 0:
        game.add_event("DAMAGE", {"target": target.id, "amount": dmg}, floor_id=floor_id)


def _fist_zap_soiled(game, fist, target, floor_id: int):
    if not ranged_accuracy_roll(game, fist, target, floor_id):
        return
    add_buff(target.buffs, "rooted", duration=3.0, level=1)
    game.add_event("ATTACK", {"source": fist.id, "target": target.id,
                              "damage": 0, "surprise": False, "root": True}, floor_id=floor_id)


def _fist_zap_rotting(game, fist, target, floor_id: int):
    if not ranged_accuracy_roll(game, fist, target, floor_id, {"gas": True}):
        return
    dmg = target.take_damage(random.randint(10, 20))
    if random.random() < 0.5:
        add_buff(target.buffs, "ooze", duration=5.0, level=1)
    game.add_event("ATTACK", {"source": fist.id, "target": target.id,
                              "damage": dmg, "surprise": False, "gas": True}, floor_id=floor_id)
    if dmg > 0:
        game.add_event("DAMAGE", {"target": target.id, "amount": dmg}, floor_id=floor_id)


def _fist_zap_rusted(game, fist, target, floor_id: int):
    if not ranged_accuracy_roll(game, fist, target, floor_id):
        return
    add_buff(target.buffs, "cripple", duration=4.0, level=1)
    game.add_event("ATTACK", {"source": fist.id, "target": target.id,
                              "damage": 0, "surprise": False, "cripple": True}, floor_id=floor_id)


def _fist_zap_bright(game, fist, target, floor_id: int):
    if not ranged_accuracy_roll(game, fist, target, floor_id, {"light_beam": True}):
        return
    dmg = target.take_damage(random.randint(10, 20))
    add_buff(target.buffs, "blindness", duration=10.0, level=1, stack_mode="extend")
    game.add_event("ATTACK", {"source": fist.id, "target": target.id,
                              "damage": dmg, "surprise": False, "light_beam": True}, floor_id=floor_id)
    if dmg > 0:
        game.add_event("DAMAGE", {"target": target.id, "amount": dmg}, floor_id=floor_id)


def _fist_zap_dark(game, fist, target, floor_id: int):
    if not ranged_accuracy_roll(game, fist, target, floor_id, {"dark_bolt": True}):
        return
    dmg = target.take_damage(random.randint(10, 20))
    add_buff(target.buffs, "blindness", duration=10.0, level=1, stack_mode="extend")
    game.add_event("ATTACK", {"source": fist.id, "target": target.id,
                              "damage": dmg, "surprise": False, "dark_bolt": True}, floor_id=floor_id)
    if dmg > 0:
        game.add_event("DAMAGE", {"target": target.id, "amount": dmg}, floor_id=floor_id)


def _yog_unseal_arena(game, floor: FloorState, floor_id: int) -> None:
    """Port of HallsBossLevel.unseal(): kills remaining minion spawns, restores
    entrance stairs, reveals exit stairs at (16, 9), updates custom tilemaps
    for CenterPieceVisuals and CenterPieceWalls, and clears locked floor status."""
    for m in list(floor.mobs.values()):
        if isinstance(m, (Larva, YogRipper, YogEye, YogScorpio)) and m.is_alive:
            m.is_alive = False
            game.add_event("DEATH", {"target": m.id}, floor_id=floor_id)

    patches = []

    entrance = floor.entrance_pos or (16, 26)
    ex, ey = entrance
    floor.grid[ey][ex] = TileType.STAIRS_UP
    patches.append({"x": ex, "y": ey, "tile": TileType.STAIRS_UP})

    exit_pos = floor.exit_pos or (16, 9)
    xx, xy = exit_pos
    floor.grid[xy][xx] = TileType.STAIRS_DOWN
    patches.append({"x": xx, "y": xy, "tile": TileType.STAIRS_DOWN})

    from app.engine.dungeon.spd_levelgen.halls_boss_layout import (
        get_center_piece_visuals,
        get_center_piece_walls,
    )
    for layer in floor.custom_tiles:
        if layer.get("texture") == "halls_special":
            layer["tiles"] = get_center_piece_visuals(unsealed=True)

    for layer in floor.custom_walls:
        if layer.get("texture") == "halls_special":
            layer["tiles"] = get_center_piece_walls(unsealed=True)

    floor.rebuild_flags()
    game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)

    floor.view_distance = None

    for p in game._players_on_floor(floor_id):
        p.locked_floor_left = None
