# Copyright (C) 2026 ArtemNikov
#
import math
import random
import time
from typing import List, Optional, Tuple

from app.engine.dungeon.constants import TileType
from app.engine.dungeon.spd_levelgen.geom import Rect
from app.engine.entities.base import Position
from app.engine.entities.mobs import DM300, Pylon
from app.engine.entities.player import Mob as MobEntity, Player
from app.engine.entities.wands.base import knockback_char
from app.engine.game.constants import AUTO_MOVE_INTERVAL, GAME_LOOP_HZ, GAME_TURN_TICKS
from app.engine.game.floor_state import FloorState
from app.engine.systems.ballistica import ballistica_path

# Arena bounds from caves_boss_layout.py (mirrors CavesBossLevel.java)
MAIN_ARENA = Rect(5, 14, 28, 37)
DIGGABLE_AREA = Rect(2, 11, 31, 40)
GATE = Rect(14, 13, 19, 14)
PYLON_COORDS = [(4, 13), (28, 13), (4, 37), (28, 37)]

MIN_COOLDOWN_TURNS = 5
MAX_COOLDOWN_TURNS = 9

_CIRCLE8 = [
    (0, -1), (1, -1), (1, 0), (1, 1),
    (0, 1), (-1, 1), (-1, 0), (-1, -1),
]


def _tick_dm300_pending_rockfall(game, mob: DM300, floor: FloorState, floor_id: int) -> None:
    """Port of DM300.FallingRockBuff / DelayedRockFall: decrements the tick
    countdown and resolves falling rock impact (6-12 dmg + 3-turn paralysis)."""
    rockfall = getattr(mob, "pending_rockfall", None)
    if not rockfall:
        return

    rockfall["ticks_left"] -= 1
    if rockfall["ticks_left"] > 0:
        return

    mob.pending_rockfall = None
    cells = rockfall.get("cells", [])

    is_stronger = "stronger_bosses" in getattr(game, "challenges", set())
    paralysis_dur = 5.0 if is_stronger else 3.0

    for cx, cy in cells:
        # Damage and paralyze players on rock cells
        for p in game._players_on_floor(floor_id):
            if p.is_alive and p.pos.x == cx and p.pos.y == cy:
                dmg = random.randint(10, 20) if is_stronger else random.randint(6, 12)
                taken = p.take_damage(dmg)
                p.add_buff("paralysis", duration=paralysis_dur, level=1, stack_mode="extend")
                game.add_event("MESSAGE", {"text": "You are paralyzed!"}, player_id=p.id)
                game.add_event("DAMAGE", {"target": p.id, "amount": taken}, floor_id=floor_id)
                game.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id, source_player_id=p.id)

        # Damage other mobs (DM300 and Pylons are immune to falling rocks)
        for m in list(floor.mobs.values()):
            if m.is_alive and not isinstance(m, (DM300, Pylon)) and m.pos.x == cx and m.pos.y == cy:
                dmg = random.randint(10, 20) if is_stronger else random.randint(6, 12)
                taken = m.take_damage(dmg)
                m.add_buff("paralysis", duration=paralysis_dur, level=1, stack_mode="extend")
                game.add_event("DAMAGE", {"target": m.id, "amount": taken}, floor_id=floor_id)
                if not m.is_alive:
                    m.die(floor_mobs=floor.mobs, tile_x=m.pos.x, tile_y=m.pos.y,
                          players=list(game._players_on_floor(floor_id)))
                    game.add_event("DEATH", {"target": m.id}, floor_id=floor_id)
                    game.handle_mob_death(m, floor, floor_id)

    game.add_event("DM300_ROCKFALL", {"cells": cells}, floor_id=floor_id)
    game.add_event("SCREEN_SHAKE", {"intensity": 3, "duration_ms": 700}, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "ROCKS", "x": mob.pos.x, "y": mob.pos.y}, floor_id=floor_id)


def _dm300_vent_gas(game, mob: DM300, target, floor: FloorState, floor_id: int) -> None:
    """Port of DM300.ventGas(): fires toxic gas along a line to the target,
    depositing 100 at collision, 20 per path cell, and topping up around DM300
    to a 250 total minimum."""
    path = ballistica_path(mob.pos.x, mob.pos.y, target.pos.x, target.pos.y,
                           floor.flags, floor.width, floor.height)
    if not path:
        return

    is_stronger = "stronger_bosses" in getattr(game, "challenges", set())
    multi = 2 if is_stronger else 1

    volume: dict[Tuple[int, int], int] = {}
    collision_cell = path[-1]
    volume[collision_cell] = 100 * multi
    gas_vented = 0

    for cell in path:
        volume[cell] = volume.get(cell, 0) + 20 * multi
        gas_vented += 20 * multi

    if gas_vented < 250 * multi:
        to_vent_around = int(math.ceil(((250 * multi) - gas_vented) / 8.0))
        for dx, dy in _CIRCLE8:
            nx, ny = mob.pos.x + dx, mob.pos.y + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                if not (floor.flags and floor.flags.solid[ny][nx]):
                    volume[(nx, ny)] = volume.get((nx, ny), 0) + to_vent_around

    blob_id = f"dm300_gas_{mob.pos.x}_{mob.pos.y}_{time.time()}"
    cells_set = set(volume.keys())
    floor.blob_areas[blob_id] = {"type": "toxic_gas", "cells": cells_set, "volume": volume}

    cell_list = [(c[0], c[1], vol) for c, vol in volume.items()]
    game.add_event("BLOB_UPDATE", {"id": blob_id, "type": "toxic_gas", "cells": cell_list}, floor_id=floor_id)
    game.add_event("DM300_GAS", {"mob": mob.id, "target_x": target.pos.x, "target_y": target.pos.y}, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "GAS", "x": mob.pos.x, "y": mob.pos.y}, floor_id=floor_id)


def _dm300_drop_rocks(game, mob: DM300, target, floor: FloorState, floor_id: int) -> None:
    """Port of DM300.dropRocks(): knocks target back (2 tiles if adjacent, 1 if
    dist=2), picks a safe adjacent cell, generates a 7x7 falling rock pattern,
    emits a telegraph, and schedules delayed impact."""
    dist = game._get_distance(mob.pos, target.pos)

    if dist <= 1:
        dx = target.pos.x - mob.pos.x
        dy = target.pos.y - mob.pos.y
        lx, ly = knockback_char(
            floor, target, dx, dy, power=2, damage_on_collision=False,
            add_event=game.add_event,
            floor_id=floor_id,
        )
        rock_center = (lx, ly)
    elif dist == 2 and game._is_in_los(mob.pos, target.pos, floor_id=floor_id):
        dx = target.pos.x - mob.pos.x
        dy = target.pos.y - mob.pos.y
        lx, ly = knockback_char(
            floor, target, dx, dy, power=1, damage_on_collision=False,
            add_event=game.add_event,
            floor_id=floor_id,
        )
        rock_center = (lx, ly)
    else:
        rock_center = (target.pos.x, target.pos.y)

    # Safe cell selection: random neighbor of rock center, re-rolled if on
    # DM300, or with 50% chance if solid or energized.
    safe_cell: Optional[Tuple[int, int]] = None
    for _ in range(20):
        ox, oy = random.choice(_CIRCLE8)
        candidate = (rock_center[0] + ox, rock_center[1] + oy)
        if candidate == (mob.pos.x, mob.pos.y):
            continue
        is_solid = not (0 <= candidate[0] < floor.width and 0 <= candidate[1] < floor.height) or (
            floor.flags is not None and floor.flags.solid[candidate[1]][candidate[0]]
        )
        if is_solid and random.random() < 0.5:
            continue
        is_energized = any(
            candidate in b.get("cells", set())
            for b in floor.blob_areas.values()
            if b.get("type") == "pylon_energy"
        )
        if is_energized and random.random() < 0.5:
            continue
        safe_cell = candidate
        break

    if safe_cell is None:
        ox, oy = random.choice(_CIRCLE8)
        safe_cell = (rock_center[0] + ox, rock_center[1] + oy)

    # 7x7 falling rock pattern around rock_center
    rock_cells: List[Tuple[int, int]] = []
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            cx, cy = rock_center[0] + dx, rock_center[1] + dy
            if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                continue
            if floor.flags and floor.flags.solid[cy][cx]:
                continue
            if (cx, cy) == safe_cell:
                continue
            d = max(abs(dx), abs(dy))
            if d <= 1 or random.randrange(d) == 0:
                rock_cells.append((cx, cy))

    # Telegraph: ~2s warning duration before rocks crash down
    delay_ms = 2000
    delay_ticks = int(round(2.0 * GAME_LOOP_HZ))
    mob.pending_rockfall = {"cells": rock_cells, "ticks_left": delay_ticks}

    tiles_list = [[c[0], c[1]] for c in rock_cells]
    game.add_event("DM300_ROCKFALL_WARN", {"mob": mob.id, "tiles": tiles_list, "duration_ms": delay_ms}, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "ROCKS", "x": mob.pos.x, "y": mob.pos.y}, floor_id=floor_id)


def _dm300_wall_smash(game, mob: DM300, target, floor: FloorState, floor_id: int) -> bool:
    """Port of DM300.getCloser(): while supercharged, if DM-300 cannot path to
    its target, it smashes through diggable arena walls to make a path."""
    best_pos = (mob.pos.x, mob.pos.y)
    curr_dist = game._get_distance(mob.pos, target.pos)

    # Find neighbor cell that reduces distance to target
    for dx, dy in _CIRCLE8:
        nx, ny = mob.pos.x + dx, mob.pos.y + dy
        if not (0 <= nx < floor.width and 0 <= ny < floor.height):
            continue
        ndist = max(abs(nx - target.pos.x), abs(ny - target.pos.y))
        if ndist < curr_dist:
            best_pos = (nx, ny)
            curr_dist = ndist

    if best_pos == (mob.pos.x, mob.pos.y):
        return False

    # Break breakable walls in 3x3 around mob
    smashed = False
    map_patches = []
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            sx, sy = mob.pos.x + dx, mob.pos.y + dy
            if not (0 <= sx < floor.width and 0 <= sy < floor.height):
                continue
            # Gate protection: don't break the gate or walls around it
            if sy < GATE.bottom and GATE.left - 2 <= sx < GATE.right + 2:
                continue
            # Must be within diggableArea
            if not (DIGGABLE_AREA.left <= sx < DIGGABLE_AREA.right and DIGGABLE_AREA.top <= sy < DIGGABLE_AREA.bottom):
                continue
            tile = floor.grid[sy][sx]
            if tile in (TileType.WALL, TileType.WALL_DECO):
                floor.grid[sy][sx] = TileType.EMPTY_DECO
                map_patches.append({"x": sx, "y": sy, "tile": TileType.EMPTY_DECO})
                smashed = True

    if not smashed:
        return False

    floor.rebuild_flags()
    game.add_event("MAP_PATCH", {"tiles": map_patches}, floor_id=floor_id)
    game.add_event("SCREEN_SHAKE", {"intensity": 5, "duration_ms": 1000}, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "ROCKS", "x": mob.pos.x, "y": mob.pos.y}, floor_id=floor_id)

    # DM300 spends 3 turns (1.5s pause)
    mob.add_buff("stagger", duration=1.5)

    # Step toward target
    if floor.flags and floor.flags.passable[best_pos[1]][best_pos[0]]:
        dx = best_pos[0] - mob.pos.x
        dy = best_pos[1] - mob.pos.y
        game.move_entity(mob.id, dx, dy)

    return True


def _check_dm300_trap_step(game, mob: DM300, floor: FloorState, floor_id: int) -> None:
    """Port of DM300.move(): DM-300 gains barrier + sparks when stepping on
    inactive traps (wires), UNLESS the tile is currently energized by a pylon."""
    tile = floor.grid[mob.pos.y][mob.pos.x]
    if tile != TileType.INACTIVE_TRAP:
        return

    # Check if this cell is currently energized by pylon energy
    pos_tuple = (mob.pos.x, mob.pos.y)
    is_energized = any(
        pos_tuple in b.get("cells", set())
        for b in floor.blob_areas.values()
        if b.get("type") == "pylon_energy"
    )
    if is_energized:
        return

    shield_amt = 30 + (mob.max_hp - mob.hp) // 10
    mob.add_shield("dm300_barrier", shield_amt, priority=0)
    game.add_event("PLAY_SOUND", {"sound": "LIGHTNING", "x": mob.pos.x, "y": mob.pos.y}, floor_id=floor_id)
    game.add_event("DM300_TRAP_STEP", {"mob": mob.id, "x": mob.pos.x, "y": mob.pos.y}, floor_id=floor_id)


def _dm300_maybe_seal_arena(game, player: Player, floor: FloorState, floor_id: int) -> None:
    """Seals the floor 15 arena when a player approaches any of the 4 pylons
    (within 3 tiles), turning the entrance into a wall and starting the fight."""
    if floor_id != 15:
        return
    if floor.generation_meta.get("dm300_sealed", False):
        return

    # Check if gate is still solid (fight not already completed)
    if not (0 <= 13 < floor.height and 0 <= 14 < floor.width):
        return
    if floor.grid[13][14] != TileType.WALL_DECO:
        return

    # Check proximity to any pylon position
    near_pylon = any(
        max(abs(player.pos.x - px), abs(player.pos.y - py)) <= 3
        for px, py in PYLON_COORDS
    )
    if not near_pylon:
        return

    _dm300_seal_arena(game, floor, floor_id)


def _dm300_seal_arena(game, floor: FloorState, floor_id: int) -> None:
    """Port of CavesBossLevel.seal(): walls off entrance, locks floor,
    announces fight start and alerts DM-300."""
    floor.generation_meta["dm300_sealed"] = True
    game.qualified_for_boss_challenge = True

    entrance = floor.entrance_pos or (16, 25)
    ex, ey = entrance

    # Displace any character standing on the entrance cell
    for ch in list(game._players_on_floor(floor_id)) + list(floor.mobs.values()):
        if ch.is_alive and ch.pos.x == ex and ch.pos.y == ey:
            for dx, dy in _CIRCLE8:
                nx, ny = ex + dx, ey + dy
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    if floor.flags and floor.flags.passable[ny][nx]:
                        ch.pos = Position(x=nx, y=ny)
                        break

    # Turn entrance into wall
    floor.grid[ey][ex] = TileType.WALL
    floor.rebuild_flags()

    game.add_event("MAP_PATCH", {"tiles": [{"x": ex, "y": ey, "tile": TileType.WALL}]}, floor_id=floor_id)
    game.add_event("SCREEN_SHAKE", {"intensity": 3, "duration_ms": 700}, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "ROCKS", "x": ex, "y": ey}, floor_id=floor_id)

    # Alert all DM-300 instances on this floor
    for mob in floor.mobs.values():
        if isinstance(mob, DM300) and mob.is_alive:
            mob.fight_started = True
            mob.ai_state = "hunting"
            mob.turns_since_last_ability = 0
            mob.ability_cooldown = random.randint(MIN_COOLDOWN_TURNS, MAX_COOLDOWN_TURNS) * GAME_TURN_TICKS
            game.add_event("DM300_FIGHT_STARTED", {"mob": mob.id}, floor_id=floor_id)
            game.add_event("BOSS_YELL", {"mob": mob.id, "text": "Intruder detected.",
                                         "x": mob.pos.x, "y": mob.pos.y}, floor_id=floor_id)

    # SPD LockedFloor: 50 turns
    left = 20.0 if "stronger_bosses" in getattr(game, "challenges", set()) else 50.0
    for p in game._players_on_floor(floor_id):
        p.locked_floor_left = left


def _dm300_unseal_arena(game, floor: FloorState, floor_id: int) -> None:
    """Port of CavesBossLevel.unseal(): restores entrance, breaks open the gate
    row, and clears all pylon energy."""
    floor.generation_meta["dm300_sealed"] = False

    entrance = floor.entrance_pos or (16, 25)
    ex, ey = entrance
    patches = [{"x": ex, "y": ey, "tile": TileType.STAIRS_UP}]
    floor.grid[ey][ex] = TileType.STAIRS_UP

    # Break gate cells (x 14..18, y 13)
    for gx in range(GATE.left, GATE.right):
        if 0 <= gx < floor.width and 0 <= GATE.top < floor.height:
            floor.grid[GATE.top][gx] = TileType.FLOOR
            patches.append({"x": gx, "y": GATE.top, "tile": TileType.FLOOR})

    # Port of CavesBossLevel.ArenaVisuals: update gate row in custom_tiles to broken gate (tiles 32..36)
    for layer in floor.custom_tiles:
        if layer.get("texture") == "caves_boss" and layer.get("y") == 12:
            grow = GATE.top - layer["y"]
            for gx in range(GATE.left, GATE.right):
                gcol = gx - layer["x"]
                if 0 <= grow < layer["h"] and 0 <= gcol < layer["w"]:
                    layer["tiles"][grow][gcol] = 32 + (gx - GATE.left)
            break

    floor.rebuild_flags()
    game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)

    # Clear all pylon_energy blobs
    for bid in list(floor.blob_areas.keys()):
        if floor.blob_areas[bid].get("type") == "pylon_energy":
            del floor.blob_areas[bid]
            game.add_event("BLOB_DEPLETED", {"id": bid}, floor_id=floor_id)

    for p in game._players_on_floor(floor_id):
        p.locked_floor_left = None


def _update_dm300(game, mob: DM300, floor: FloorState, floor_id: int) -> bool:
    """Primary DM-300 tick update. Returns True if DM-300 handled its tick,
    or False to let generic AI wander / notice."""
    if mob.ai_state != "hunting":
        return False

    target_player = game._find_nearest_player(mob.pos, floor_id)
    if target_player is None:
        return False

    move_times = getattr(game, "_mob_move_times", None)
    if move_times is None:
        move_times = game._mob_move_times = {}

    now = time.time()
    speed_mult = 2.0 if mob.supercharged else 1.0
    move_interval = (2 * AUTO_MOVE_INTERVAL / max(0.1, mob.speed)) / speed_mult
    can_move = now - move_times.get(mob.id, 0.0) >= move_interval

    # Abilities only trigger when not supercharged
    if not mob.supercharged:
        if mob.turns_since_last_ability >= 0:
            mob.turns_since_last_ability += 1

        dist = game._get_distance(mob.pos, target_player.pos)
        can_reach = dist <= 1 or bool(game._get_next_step_to(mob.pos, target_player.pos, floor_id=floor_id, flying=mob.flying))

        # Aggressive ability usage when DM-300 cannot reach its target
        if not can_reach and mob.turns_since_last_ability >= MIN_COOLDOWN_TURNS * GAME_TURN_TICKS:
            target_in_los = game._is_in_los(mob.pos, target_player.pos, floor_id=floor_id)
            target_inorganic = "INORGANIC" in getattr(target_player, "properties", [])
            if target_in_los and not target_inorganic:
                _dm300_vent_gas(game, mob, target_player, floor, floor_id)
                mob.last_ability = "gas"
                mob.turns_since_last_ability = 0
                mob.ability_cooldown = random.randint(MIN_COOLDOWN_TURNS, MAX_COOLDOWN_TURNS) * GAME_TURN_TICKS
            elif not target_player.has_buff("paralysis"):
                _dm300_drop_rocks(game, mob, target_player, floor, floor_id)
                mob.last_ability = "rocks"
                mob.turns_since_last_ability = 0
                mob.ability_cooldown = random.randint(MIN_COOLDOWN_TURNS, MAX_COOLDOWN_TURNS) * GAME_TURN_TICKS
        elif mob.turns_since_last_ability >= mob.ability_cooldown and game._is_in_los(mob.pos, target_player.pos, floor_id=floor_id):
            target_inorganic = "INORGANIC" in getattr(target_player, "properties", [])
            if target_inorganic:
                chosen = "rocks"
            elif mob.last_ability == "gas":
                chosen = "gas" if random.random() < 0.25 else "rocks"
            elif mob.last_ability == "rocks":
                chosen = "gas" if random.random() < 0.75 else "rocks"
            else:
                chosen = "gas" if random.random() < 0.5 else "rocks"

            if chosen == "gas":
                _dm300_vent_gas(game, mob, target_player, floor, floor_id)
            else:
                _dm300_drop_rocks(game, mob, target_player, floor, floor_id)

            mob.last_ability = chosen
            mob.turns_since_last_ability = 0
            mob.ability_cooldown = random.randint(MIN_COOLDOWN_TURNS, MAX_COOLDOWN_TURNS) * GAME_TURN_TICKS

    # Movement / Melee combat
    dist = game._get_distance(mob.pos, target_player.pos)
    atk_range = getattr(mob, "attack_range", 1)

    if dist <= atk_range:
        current_time = time.time()
        if current_time - mob.last_attack_time >= mob.attack_cooldown:
            dx, dy = target_player.pos.x - mob.pos.x, target_player.pos.y - mob.pos.y
            game.move_entity(mob.id, dx, dy)
            _check_dm300_trap_step(game, mob, floor, floor_id)
            if mob.supercharged:
                game.qualified_for_boss_challenge = False
    elif can_move:
        step = game._get_next_step_to(mob.pos, target_player.pos, floor_id=floor_id, flying=mob.flying)
        if step:
            move_times[mob.id] = now
            game.move_entity(mob.id, step[0], step[1])
            _check_dm300_trap_step(game, mob, floor, floor_id)
        elif mob.supercharged:
            _dm300_wall_smash(game, mob, target_player, floor, floor_id)

    return True
