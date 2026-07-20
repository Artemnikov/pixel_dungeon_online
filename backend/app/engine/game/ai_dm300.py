import random
import time

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.mobs import DM300
from app.engine.game.floor_state import FloorState


def _update_dm300_chase(game, mob: DM300, floor: FloorState, floor_id: int):
    target_player = game._find_nearest_player(mob.pos, floor_id)
    if target_player is None:
        return

    dist = game._get_distance(mob.pos, target_player.pos)
    atk_range = getattr(mob, "attack_range", 1)

    # Rocket attack at 50% HP (enraged)
    if mob.is_enraged() and mob.rocket_cooldown <= 0:
        _dm300_rocket_attack(game, mob, target_player, floor, floor_id)
        mob.rocket_cooldown = 30
        return

    # Supercharge electrical attack
    if mob.supercharged and dist > 1 and dist <= 8:
        _dm300_lightning_attack(game, mob, target_player, floor, floor_id)
        return

    if dist <= atk_range:
        current_time = time.time()
        if current_time - mob.last_attack_time >= mob.attack_cooldown:
            dx, dy = target_player.pos.x - mob.pos.x, target_player.pos.y - mob.pos.y
            game.move_entity(mob.id, dx, dy)
            _check_dm300_trap_step(game, mob, floor, floor_id)
    elif game._is_in_los(mob.pos, target_player.pos, floor_id=floor_id):
        step = game._get_next_step_to(mob.pos, target_player.pos, floor_id=floor_id, flying=mob.flying)
        if step:
            old_x, old_y = mob.pos.x, mob.pos.y
            game.move_entity(mob.id, step[0], step[1])
            _check_dm300_trap_step(game, mob, floor, floor_id)


def _check_dm300_trap_step(game, mob: DM300, floor: FloorState, floor_id: int):
    """DM-300 gains barrier + sparks when stepping on inactive traps."""
    tile = floor.grid[mob.pos.y][mob.pos.x]
    if tile != TileType.INACTIVE_TRAP:
        return
    shield_amt = 30 + (mob.max_hp - mob.hp) // 10
    mob.add_shield("dm300_barrier", shield_amt, priority=0)
    game.add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=floor_id)
    game.add_event("DM300_TRAP_STEP", {"mob": mob.id, "x": mob.pos.x, "y": mob.pos.y}, floor_id=floor_id)


def _dm300_lightning_attack(game, mob: DM300, target, floor: FloorState, floor_id: int):
    """Supercharged ranged lightning bolt, chains to nearby enemies."""
    dmg = random.randint(10, 20)
    taken = target.take_damage(dmg)
    game.add_event("ATTACK", {"source": mob.id, "target": target.id,
                              "damage": taken, "surprise": False},
                   floor_id=floor_id)
    if taken > 0:
        game.add_event("DAMAGE", {"target": target.id, "amount": taken, "shock": True}, floor_id=floor_id)
    game.add_event("LIGHTNING_ARC", {
        "source_x": mob.pos.x, "source_y": mob.pos.y,
        "target_x": target.pos.x, "target_y": target.pos.y,
    }, floor_id=floor_id)

    # Chain to 1-2 nearby enemies
    chain_targets = []
    for m in floor.mobs.values():
        if len(chain_targets) >= 2:
            break
        if not m.is_alive or m.id in (mob.id, target.id):
            continue
        if m.faction == mob.faction:
            continue
        if max(abs(m.pos.x - target.pos.x), abs(m.pos.y - target.pos.y)) > 2:
            continue
        chain_dmg = random.randint(5, 12)
        taken2 = m.take_damage(chain_dmg)
        chain_targets.append({"id": m.id, "x": m.pos.x, "y": m.pos.y})
        if taken2 > 0:
            game.add_event("DAMAGE", {"target": m.id, "amount": taken2, "shock": True}, floor_id=floor_id)
            game.add_event("LIGHTNING_ARC", {
                "source_x": target.pos.x, "source_y": target.pos.y,
                "target_x": m.pos.x, "target_y": m.pos.y,
            }, floor_id=floor_id)
    if chain_targets:
        game.add_event("SHOCKING_PROC", {
            "source": mob.id,
            "defender": target.id,
            "defender_x": target.pos.x,
            "defender_y": target.pos.y,
            "chain_targets": chain_targets,
        }, floor_id=floor_id)

    game.add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=floor_id)


def _dm300_rocket_attack(game, mob: DM300, target, floor: FloorState, floor_id: int):
    """AOE fire rocket burst at the target area."""
    cx, cy = target.pos.x, target.pos.y
    blob_id = f"dm300_rocket_{cx}_{cy}_{time.time()}"
    cells = set()
    volume = {}
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                tile = floor.grid[ny][nx]
                if tile != TileType.WALL and tile != TileType.VOID:
                    cells.add((nx, ny))
                    volume[(nx, ny)] = 5
    if cells:
        floor.blob_areas[blob_id] = {"type": "fire", "cells": cells, "volume": volume}
        cell_list = [(c[0], c[1], volume.get(c, 5)) for c in cells]
        game.add_event("BLOB_UPDATE", {"id": blob_id, "type": "fire", "cells": cell_list}, floor_id=floor_id)
        game.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
        # Damage chars in blast radius
        for m in list(floor.mobs.values()):
            if m.is_alive and max(abs(m.pos.x - cx), abs(m.pos.y - cy)) <= 2:
                dmg = random.randint(10, 20)
                taken = m.take_damage(dmg)
                game.add_event("DAMAGE", {"target": m.id, "amount": taken, "burning": True}, floor_id=floor_id)
        for p in game._players_on_floor(floor_id):
            if p.is_alive and max(abs(p.pos.x - cx), abs(p.pos.y - cy)) <= 2:
                dmg = random.randint(10, 20)
                taken = p.take_damage(dmg)
                game.add_event("DAMAGE", {"target": p.id, "amount": taken, "burning": True}, floor_id=floor_id)
