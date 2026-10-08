# Copyright (C) 2026 ArtemNikov
#
import random

from app.engine.dungeon.spd_levelgen.level import _CIRCLE8_OFFSETS
from app.engine.entities.mobs import DemonSpawner, RipperDemon
from app.engine.game.floor_state import FloorState


def _update_demon_spawner(game, spawner: DemonSpawner, floor: FloorState, floor_id: int):
    spawner.spawn_cooldown -= 1
    if spawner.spawn_cooldown > 0:
        return

    if spawner.spawn_cooldown < -20:
        spawner.spawn_cooldown = -20

    candidates = []
    for dx, dy in _CIRCLE8_OFFSETS:
        nx, ny = spawner.pos.x + dx, spawner.pos.y + dy
        if not (0 <= nx < floor.width and 0 <= ny < floor.height):
            continue
        if not floor.flags or not floor.flags.passable[ny][nx]:
            continue
        occupied = any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values())
        occupied = occupied or any(p.is_alive and p.pos.x == nx and p.pos.y == ny for p in game._players_on_floor(floor_id))
        if not occupied:
            candidates.append((nx, ny))

    if candidates:
        sx, sy = random.choice(candidates)
        new_mob = game._spawn_mob_at(RipperDemon, sx, sy, floor_id)
        new_mob.ai_state = "hunting"
        floor.mobs[new_mob.id] = new_mob
        game.add_event("MOB_SPAWN", {"mob": new_mob.id, "cls": "RipperDemon"}, floor_id=floor_id)

        spawner.spawn_cooldown += 90
        if floor.floor_id > 21:
            spawner.spawn_cooldown -= min(30, int((floor.floor_id - 21) * 10))
