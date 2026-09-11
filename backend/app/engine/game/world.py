# Copyright (C) 2026 ArtemNikov
#
"""World interaction for GameInstance: searching, locked doors, and traps.

Reveals hidden doors/traps around a searching player, consumes keys to open
locked doors, and resolves trap triggers when a player steps onto one.

Mob-death handling lives in mob_death.py, NPC shop/quest-reward economy in
npc_economy.py -- this file used to hold all three; split apart since they
were unrelated concerns bundled under one 1300-line mixin.
"""

import random
import time
import uuid
from typing import Callable, Dict, List

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction, Position
from app.engine.entities.player import CharacterClass, Player, hurt_warning_sound
from app.engine.game.floor_state import FloorState
from app.engine.game.constants import KEY_TIME_TO_UNLOCK

_FIRE_CARDINALS = [(0, -1), (1, 0), (0, 1), (-1, 0)]
_ELECTRIC_CARDINALS = [(0, -1), (1, 0), (0, 1), (-1, 0)]


def _electric_reachable_cells(floor: FloorState, cx: int, cy: int, max_dist: int):
    """BFS returning set of (x,y) reachable within max_dist cardinal steps, avoiding solids."""
    from collections import deque
    visited = {(cx, cy)}
    q = deque([(cx, cy, 0)])
    while q:
        x, y, d = q.popleft()
        if d >= max_dist:
            continue
        for dx, dy in _ELECTRIC_CARDINALS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                if (nx, ny) not in visited and not floor.flags.solid[ny][nx]:
                    visited.add((nx, ny))
                    q.append((nx, ny, d + 1))
    return visited


def _spawn_trap_electricity(floor: FloorState, cx: int, cy: int, radius: int, strength: int) -> None:
    """Seed an electricity blob covering all cells within radius.
    radius=1 uses square (NEIGHBOURS9 matching SPD); radius>1 uses BFS pathfinding.

    The blob records its `origin` cell so evolution events (damage, sound,
    blob updates) are LOS-scoped to players who can see the effect's location —
    not to whoever triggered it (who may move or respawn mid-blob)."""
    blob_id = f"electric_trap_{cx}_{cy}"
    cells = set()
    volume = {}
    if radius <= 1:
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    if floor.flags and not floor.flags.solid[ny][nx]:
                        cells.add((nx, ny))
                        volume[(nx, ny)] = strength
    else:
        for nx, ny in _electric_reachable_cells(floor, cx, cy, radius):
            cells.add((nx, ny))
            volume[(nx, ny)] = strength
    if cells:
        floor.blob_areas[blob_id] = {"type": "electricity", "cells": cells, "volume": volume,
                                     "origin": (cx, cy)}


def _spawn_trap_fire(floor: FloorState, cx: int, cy: int, radius: int, strength: int) -> None:
    blob_id = f"fire_trap_{cx}_{cy}"
    cells = set()
    volume = {}
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                tile = floor.grid[ny][nx]
                if tile == TileType.FLOOR_WATER:
                    continue
                can_burn = (floor.flags.flamable[ny][nx] if floor.flags else False)
                can_burn = can_burn or tile in (TileType.FLOOR, TileType.EMPTY_DECO)
                if can_burn or tile not in (TileType.WALL, TileType.VOID):
                    cells.add((nx, ny))
                    volume[(nx, ny)] = strength
    if cells:
        floor.blob_areas[blob_id] = {"type": "fire", "cells": cells, "volume": volume}


def _spawn_blazing_trap_fire(floor: FloorState, cx: int, cy: int) -> None:
    blob_id = f"blazing_trap_{cx}_{cy}"
    cells = set()
    volume = {}
    visited = set()
    queue = [(cx, cy, 0)]
    while queue:
        nx, ny, dist = queue.pop(0)
        if (nx, ny) in visited or dist > 2:
            continue
        visited.add((nx, ny))
        if not (0 <= nx < floor.width and 0 <= ny < floor.height):
            continue
        tile = floor.grid[ny][nx]
        if tile in (TileType.WALL, TileType.VOID, TileType.FLOOR_WATER):
            continue
        if dist > 0:
            cells.add((nx, ny))
            volume[(nx, ny)] = 5
        for dx, dy in _FIRE_CARDINALS:
            queue.append((nx + dx, ny + dy, dist + 1))
    if cells:
        floor.blob_areas[blob_id] = {"type": "fire", "cells": cells, "volume": volume}

# --- Trap handlers, dispatched by _trigger_trap_if_needed ------------------
# Each handler returns (damage, dealt) for the common MAP_PATCH/TRAP_TRIGGERED/
# DAMAGE epilogue, or None if it already fully handled its own event emission
# and outcome (pitfall_trap's hero-fall path -- see its docstring).

def _trap_tengu_dart(game, floor, player, floor_id, is_player, patches):
    damage = 8
    dealt = player.take_damage(damage)
    from app.engine.entities.buffs import add_buff
    add_buff(player.buffs, "poison", duration=8.0, level=1, stack_mode="extend")
    if is_player:
        game.boss_scores[1] -= 100
        game.qualified_for_boss_challenge = False
    return damage, dealt


def _trap_burning(game, floor, player, floor_id, is_player, patches):
    _spawn_trap_fire(floor, player.pos.x, player.pos.y, 2, 2)
    game.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
    return 0, 0


def _trap_blazing(game, floor, player, floor_id, is_player, patches):
    _spawn_blazing_trap_fire(floor, player.pos.x, player.pos.y)
    game.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
    return 0, 0


def _trap_shocking(game, floor, player, floor_id, is_player, patches):
    _spawn_trap_electricity(floor, player.pos.x, player.pos.y, 1, 10)
    game.add_event("PLAY_SOUND", {"sound": "LIGHTNING",
                                  "x": player.pos.x, "y": player.pos.y},
                   floor_id=floor_id)
    return 0, 0


def _trap_storm(game, floor, player, floor_id, is_player, patches):
    _spawn_trap_electricity(floor, player.pos.x, player.pos.y, 2, 20)
    game.add_event("PLAY_SOUND", {"sound": "LIGHTNING",
                                  "x": player.pos.x, "y": player.pos.y},
                   floor_id=floor_id)
    return 0, 0


def _trap_toxic(game, floor, player, floor_id, is_player, patches):
    from app.engine.game.terrain_effects import _create_gas
    _create_gas(floor, (player.pos.x, player.pos.y), 4 + floor_id // 3, "toxic_gas")
    game.add_event("PLAY_SOUND", {"sound": "GAS"}, floor_id=floor_id)
    return 0, 0


def _trap_poison_dart(game, floor, player, floor_id, is_player, patches):
    from app.engine.entities.buffs import add_buff
    from app.engine.game.terrain_effects import _create_gas
    add_buff(player.buffs, "poison", duration=10.0, level=1, stack_mode="extend")
    _create_gas(floor, (player.pos.x, player.pos.y), 2, "toxic_gas")
    game.add_event("PLAY_SOUND", {"sound": "GAS"}, floor_id=floor_id)
    return 0, 0


def _trap_chilling(game, floor, player, floor_id, is_player, patches):
    from app.engine.game.terrain_effects import _freeze_area
    _freeze_area(floor, (player.pos.x, player.pos.y))
    player.add_buff("chilled", duration=5.0, level=1, stack_mode="extend")
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
    return 0, 0


def _trap_frost(game, floor, player, floor_id, is_player, patches):
    from app.engine.game.terrain_effects import _freeze_area
    _freeze_area(floor, (player.pos.x, player.pos.y))
    player.add_buff("frozen", duration=5.0, level=1, stack_mode="extend")
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
    return 0, 0


def _trap_confusion(game, floor, player, floor_id, is_player, patches):
    player.add_buff("vertigo", duration=5.0, level=1, stack_mode="replace")
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
    return 0, 0


def _trap_ooze(game, floor, player, floor_id, is_player, patches):
    player.add_buff("ooze", duration=10.0, level=1, stack_mode="extend")
    return 0, 0


def _trap_corrosion(game, floor, player, floor_id, is_player, patches):
    from app.engine.game.terrain_effects import _create_gas
    _create_gas(floor, (player.pos.x, player.pos.y), 1 + floor_id // 4, "corrosive_gas")
    game.add_event("PLAY_SOUND", {"sound": "GAS"}, floor_id=floor_id)
    return 0, 0


def _trap_flock(game, floor, player, floor_id, is_player, patches):
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
    return 0, 0


def _trap_weakening(game, floor, player, floor_id, is_player, patches):
    player.add_buff("weakness", duration=10.0, level=1, stack_mode="extend")
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
    return 0, 0


def _trap_gripping(game, floor, player, floor_id, is_player, patches):
    _spawn_trap_fire(floor, player.pos.x, player.pos.y, 1, 1)
    game.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
    return 0, 0


def _trap_geyser(game, floor, player, floor_id, is_player, patches):
    _spawn_trap_electricity(floor, player.pos.x, player.pos.y, 1, 5)
    game.add_event("PLAY_SOUND", {"sound": "LIGHTNING",
                                  "x": player.pos.x, "y": player.pos.y},
                   floor_id=floor_id)
    return 0, 0


def _trap_explosive(game, floor, player, floor_id, is_player, patches):
    damage = max(1, player.hp // 6)
    dealt = player.take_damage(damage)
    game.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)
    blast_cells = []
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            blast_cells.append([player.pos.x + ox, player.pos.y + oy])
    game.add_event("BOMB_BLAST", {
        "x": player.pos.x, "y": player.pos.y,
        "kind": "bomb", "cells": blast_cells,
    }, floor_id=floor_id)
    game.add_event("SCREEN_SHAKE", {"intensity": 2, "duration_ms": 300},
                   floor_id=floor_id)
    return damage, dealt


def _trap_pitfall(game, floor, player, floor_id, is_player, patches):
    """SPD PitfallTrap: opens a 3x3 pit around the trap cell; mobs on those
    cells fall to their death (Chasm.mobFall) and the hero falls to the next
    floor (Chasm.heroFall). No-op on boss floors or beyond depth 25 (SPD:
    "the ground is too solid").

    Returns None instead of a (damage, dealt) pair when the hero-fall path
    already fully handled its own event emission and outcome: it must emit
    TRAP_TRIGGERED itself before the fall moves the player to the next floor
    (after which floor_id is stale), so _trigger_trap_if_needed's common
    epilogue has to be skipped entirely in that case.
    """
    from app.engine.dungeon.spd_levelgen.run_state import is_boss_level
    from app.engine.game.constants import MAX_FLOOR_ID
    dealt = 0
    if is_boss_level(floor_id) or floor_id > 25 or floor_id >= MAX_FLOOR_ID:
        # Too solid — trap triggers but no pit opens.
        if is_player:
            game.add_event("MESSAGE",
                {"text": "The ground is too solid for a pitfall trap to work here."},
                player_id=player.id)
        return 0, dealt

    # PitfallParticle burst on the 3x3 around the trap cell.
    pit_cells = []
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            cx, cy = player.pos.x + ox, player.pos.y + oy
            if 0 <= cx < floor.width and 0 <= cy < floor.height:
                if floor.flags and floor.flags.passable[cy][cx]:
                    pit_cells.append((cx, cy))
    # Emit VFX for the pit opening (reuses LEAF_BURST-style per-cell
    # particle spawn; the client renders a dust/earth burst).
    for cx, cy in pit_cells:
        game.add_event("LEAF_BURST", {"x": cx, "y": cy}, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)

    # Mobs on pit cells fall to their death (Chasm.mobFall).
    for cx, cy in pit_cells:
        for mob in list(floor.mobs.values()):
            if mob.is_alive and mob.pos.x == cx and mob.pos.y == cy:
                if not mob.flying and mob.faction != Faction.PLAYER:
                    mob.is_alive = False
                    game.add_event("MOB_CHASM_FALL",
                        {"mob": mob.id, "x": cx, "y": cy},
                        floor_id=floor_id)
                    # DEATH event so the client's death animation
                    # triggers alongside the fall VFX.
                    game.add_event("DEATH", {"target": mob.id},
                        floor_id=floor_id)
                    game.handle_mob_death(mob, floor, floor_id)

    # Hero falls last (SPD: "process hero falling last").
    if is_player and not player.has_buff("levitation"):
        # Emit TRAP_TRIGGERED before the fall moves the player to
        # the next floor (after which floor_id is stale).
        if patches:
            game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)
        game.add_event("TRAP_TRIGGERED",
            {"player": player.id, "trap": "pitfall_trap", "damage": 0,
             "x": player.pos.x, "y": player.pos.y},
            floor_id=floor_id)
        game._perform_chasm_fall(player, floor_id, player.pos.x, player.pos.y)
        return None
    # Non-player entity falls to death in the pit.
    elif not is_player and not player.has_buff("levitation"):
        player.is_alive = False
        game.add_event("MOB_CHASM_FALL",
            {"mob": player.id, "x": player.pos.x, "y": player.pos.y},
            floor_id=floor_id)
        game.add_event("DEATH", {"target": player.id}, floor_id=floor_id)
        game.handle_mob_death(player, floor, floor_id)
    return 0, dealt


def _neighbours8(cx: int, cy: int):
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            if ox == 0 and oy == 0:
                continue
            yield cx + ox, cy + oy


def _free_neighbour_cells(floor: FloorState, cx: int, cy: int) -> List[tuple]:
    """PathFinder.NEIGHBOURS8 cells that are passable and unoccupied by a
    living char (SummoningTrap/DistortionTrap candidate-cell scan)."""
    occupied = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
    out = []
    for nx, ny in _neighbours8(cx, cy):
        if 0 <= nx < floor.width and 0 <= ny < floor.height:
            if floor.flags and floor.flags.passable[ny][nx] and (nx, ny) not in occupied:
                out.append((nx, ny))
    return out


def _teleport_char_generic(game, floor, floor_id: int, entity) -> bool:
    """ScrollOfTeleportation.teleportChar port: random passable, unoccupied
    cell on the floor, no special-room bias (that's the Hero-only
    teleportPreferringUnseen path used when reading the scroll directly --
    see _teleport_player in scroll_actions.py)."""
    occupied = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive and m is not entity}
    occupied |= {
        (p.pos.x, p.pos.y) for p in game.players.values()
        if p.floor_id == floor_id and p.is_alive and p is not entity
    }
    pool = [
        (x, y) for y in range(floor.height) for x in range(floor.width)
        if floor.flags and floor.flags.passable[y][x] and (x, y) not in occupied
    ]
    if not pool:
        return False
    from_x, from_y = entity.pos.x, entity.pos.y
    tx, ty = random.choice(pool)
    entity.pos = Position(x=tx, y=ty)
    entity.remove_buff("rooted")
    from app.engine.entities.buffs import break_stationary_plant_buffs
    break_stationary_plant_buffs(entity)
    if getattr(entity, "ai_state", None) == "hunting":
        entity.ai_state = "wandering"
    game.add_event("TELEPORT", {
        "player": entity.id, "from_x": from_x, "from_y": from_y, "x": tx, "y": ty,
    }, floor_id=floor_id)
    return True


def _trap_alarm(game, floor, player, floor_id, is_player, patches):
    """AlarmTrap.activate(): beckon (wake toward the trigger) every mob on
    the floor. No damage."""
    for mob in floor.mobs.values():
        if mob.is_alive:
            mob.ai_state = "hunting"
            mob.target_id = player.id
    game.add_event("PLAY_SOUND", {"sound": "ALERT"}, floor_id=floor_id)
    return 0, 0


def _spawn_wandering_mob(game, floor, floor_id: int, cls, cx: int, cy: int):
    """Construct `cls` at (cx, cy), stamp floor_level, register it on the
    floor as wandering and emit the SUMMON event. Shared by the traps that
    spawn already-woken mobs (SummoningTrap/DistortionTrap/GuardianTrap)."""
    mob = cls(id=str(uuid.uuid4()), pos=Position(x=cx, y=cy), faction=Faction.DUNGEON)
    if hasattr(mob, "floor_level"):
        mob.floor_level = floor_id
    mob.ai_state = "wandering"
    floor.mobs[mob.id] = mob
    game.add_event("SUMMON", {"id": mob.id, "x": cx, "y": cy, "name": mob.name}, floor_id=floor_id)
    return mob


def _trap_summoning(game, floor, player, floor_id, is_player, patches):
    """SummoningTrap.activate(): spawns 1-3 depth/region-appropriate mobs on
    free neighbour cells, wandering."""
    from app.engine.game.spd_adapter import random_regional_mob_class

    n_mobs = 1
    if random.random() < 0.5:
        n_mobs += 1
        if random.random() < 0.5:
            n_mobs += 1

    candidates = _free_neighbour_cells(floor, player.pos.x, player.pos.y)
    random.shuffle(candidates)
    for (cx, cy) in candidates[:n_mobs]:
        cls = random_regional_mob_class(floor_id)
        _spawn_wandering_mob(game, floor, floor_id, cls, cx, cy)
    return 0, 0


def _trap_teleportation(game, floor, player, floor_id, is_player, patches):
    """TeleportationTrap.activate(): teleports every char in the 3x3 around
    the trap. (Relocating item heaps on the trap cell -- SPD's secondary
    effect -- is skipped: this engine models dropped items as free-standing
    positioned Items, not a Heap the trap can special-case; not a gameplay
    mechanic, just anti-farming flavor.)"""
    for cx, cy in list(_neighbours8(player.pos.x, player.pos.y)) + [(player.pos.x, player.pos.y)]:
        for mob in list(floor.mobs.values()):
            if mob.is_alive and mob.pos.x == cx and mob.pos.y == cy:
                _teleport_char_generic(game, floor, floor_id, mob)
        for other in list(game.players.values()):
            if other.floor_id == floor_id and other.is_alive and other.pos.x == cx and other.pos.y == cy:
                _teleport_char_generic(game, floor, floor_id, other)
    return 0, 0


def _trap_gateway(game, floor, player, floor_id, is_player, patches):
    """GatewayTrap.activate(): like TeleportationTrap, but every char caught
    by it is sent to the same shared destination cell (picked once, cached
    on the FloorState's per-trap state) rather than each rolling their own
    landing spot."""
    key = (player.pos.x, player.pos.y)
    dest = floor.generation_meta.setdefault("gateway_dest", {}).get(key)
    if dest is None:
        occupied = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
        occupied |= {(p.pos.x, p.pos.y) for p in game.players.values() if p.floor_id == floor_id and p.is_alive}
        pool = [
            (x, y) for y in range(floor.height) for x in range(floor.width)
            if floor.flags and floor.flags.passable[y][x] and (x, y) not in occupied
        ]
        if not pool:
            return 0, 0
        dest = random.choice(pool)
        floor.generation_meta["gateway_dest"][key] = dest

    tx, ty = dest
    for cx, cy in list(_neighbours8(player.pos.x, player.pos.y)) + [(player.pos.x, player.pos.y)]:
        for mob in list(floor.mobs.values()):
            if mob.is_alive and mob.pos.x == cx and mob.pos.y == cy and (mob.pos.x, mob.pos.y) != (tx, ty):
                from_x, from_y = mob.pos.x, mob.pos.y
                mob.pos = Position(x=tx, y=ty)
                mob.remove_buff("rooted")
                if mob.ai_state == "hunting":
                    mob.ai_state = "wandering"
                game.add_event("TELEPORT", {"player": mob.id, "from_x": from_x, "from_y": from_y, "x": tx, "y": ty}, floor_id=floor_id)
        for other in list(game.players.values()):
            if other.floor_id == floor_id and other.is_alive and other.pos.x == cx and other.pos.y == cy and (other.pos.x, other.pos.y) != (tx, ty):
                from_x, from_y = other.pos.x, other.pos.y
                other.pos = Position(x=tx, y=ty)
                other.remove_buff("rooted")
                game.add_event("TELEPORT", {"player": other.id, "from_x": from_x, "from_y": from_y, "x": tx, "y": ty}, floor_id=floor_id)
    return 0, 0


def _trap_warping(game, floor, player, floor_id, is_player, patches):
    """WarpingTrap extends TeleportationTrap. SPD also wipes the hero's
    visited/mapped memory when triggered up close -- skipped here: this
    engine doesn't track per-player fog-of-war server-side (it's purely a
    frontend rendering concern), so there's no server state to wipe."""
    return _trap_teleportation(game, floor, player, floor_id, is_player, patches)


def _trap_flashing(game, floor, player, floor_id, is_player, patches):
    """FlashingTrap.activate(): bleed+blindness+cripple on whoever's
    standing on it, beckons them if a mob."""
    from app.engine.entities.buffs import add_buff

    dr_roll = random.randint(player.get_dr_min(), player.get_dr_max())
    damage = max(0, (4 + floor_id // 2) - dr_roll // 2)
    if damage > 0:
        add_buff(player.buffs, "bleeding", duration=damage / 2.0, level=damage, stack_mode="replace")
    player.add_buff("blindness", duration=10.0)
    player.add_buff("cripple", duration=20.0)
    if not is_player:
        if player.ai_state == "hunting":
            player.ai_state = "wandering"
        player.target_id = None
    game.add_event("FLASH", {}, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)
    return 0, 0


def _trap_disarming(game, floor, player, floor_id, is_player, patches):
    """DisarmingTrap.activate(): insta-kills a Statue standing on it;
    otherwise unequips + far-drops the hero's uncursed weapon. (Relocating
    item heaps already on the trap cell is skipped -- see
    _trap_teleportation's docstring.)"""
    from app.engine.entities.mobs import Statue

    if isinstance(player, Statue):
        player.is_alive = False
        game.add_event("DEATH", {"target": player.id}, floor_id=floor_id)
        game.handle_mob_death(player, floor, floor_id)
        return 0, 0

    if is_player and not player.has_buff("levitation"):
        weapon = player.belongings.weapon
        if weapon is not None and not weapon.cursed:
            occupied = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
            occupied |= {(p.pos.x, p.pos.y) for p in game.players.values() if p.floor_id == floor_id and p.is_alive}
            cell = None
            for _ in range(50):
                x = random.randint(0, floor.width - 1)
                y = random.randint(0, floor.height - 1)
                dist = ((x - player.pos.x) ** 2 + (y - player.pos.y) ** 2) ** 0.5
                if 10 <= dist <= 20 and (x, y) not in occupied and floor.flags and floor.flags.passable[y][x]:
                    cell = (x, y)
                    break
            if cell is not None:
                cx, cy = cell
                weapon.pos = Position(x=cx, y=cy)
                player.belongings.weapon = None
                floor.items[weapon.id] = weapon
                game.add_event("ITEM_DROP", {"x": cx, "y": cy, "item": weapon.id, "kind": weapon.kind}, floor_id=floor_id)
                game.add_event("MESSAGE", {"text": "Your weapon is teleported away from you!"}, player_id=player.id)
                game.add_event("PLAY_SOUND", {"sound": "TELEPORT"}, floor_id=floor_id)
    return 0, 0


def _curse_hero_equipment(player) -> None:
    """CursingTrap.curse(Hero): prefers un-enchanted gear so the curse
    actually adds a new negative effect; falls back to re-cursing
    already-enchanted gear if that's all there is."""
    from app.engine.entities.weapons.weapon_enchants import CURSES
    from app.engine.entities.armors.armor_glyphs import CURSE_GLYPHS

    priority = []
    can_curse = []
    weapon = player.belongings.weapon
    if weapon is not None:
        (priority if not weapon.enchantment else can_curse).append(("weapon", weapon))
    armor = player.belongings.armor
    if armor is not None:
        (priority if armor.enchantment.type == "none" else can_curse).append(("armor", armor))

    random.shuffle(priority)
    random.shuffle(can_curse)
    pick = priority[0] if priority else (can_curse[0] if can_curse else None)
    if pick is None:
        return
    kind, item = pick
    item.cursed = True
    item.cursed_known = True
    if kind == "weapon" and not item.enchantment:
        item.enchantment = random.choice(CURSES)
    elif kind == "armor" and item.enchantment.type == "none":
        item.enchantment.type = random.choice(CURSE_GLYPHS)


def _trap_cursing(game, floor, player, floor_id, is_player, patches):
    """CursingTrap.activate(): curses the hero's weapon/armor. (Cursing item
    heaps already on the trap cell is skipped -- see
    _trap_teleportation's docstring.)"""
    if is_player and not player.has_buff("levitation"):
        _curse_hero_equipment(player)
        game.add_event("MESSAGE", {"text": "You feel a malevolent aura!"}, player_id=player.id)
    game.add_event("PLAY_SOUND", {"sound": "CURSED"}, floor_id=floor_id)
    return 0, 0


def _trap_distortion(game, floor, player, floor_id, is_player, patches):
    """DistortionTrap.activate(): summons 3-5 mixed mobs -- some regional
    rotation picks, some "distorted"/rare specials (Wraith/Piranha/Mimic/
    Statue). Simplified from SPD's exact 5-slot switch (RatKing 1% on slot
    1, guaranteed rare-alt on slot 4): the regional rotation already folds
    rare alts in via swap-alts, so this keeps the "varied, weirder than a
    normal encounter" flavor without needing every edge case (RatKing
    depth-5 exclusion, Piranha.random(), Mimic.spawnAt hiding state, etc)."""
    from app.engine.entities.mobs import Statue, Wraith, Piranha, Mimic
    from app.engine.game.spd_adapter import random_regional_mob_class

    n_mobs = 3
    if random.random() < 0.5:
        n_mobs += 1
        if random.random() < 0.5:
            n_mobs += 1

    candidates = _free_neighbour_cells(floor, player.pos.x, player.pos.y)
    random.shuffle(candidates)
    specials = [Wraith, Piranha, Mimic, Statue]
    for (cx, cy) in candidates[:n_mobs]:
        if random.random() < 0.2:
            cls = random.choice(specials)
        else:
            depth = random.randint(0, 24)
            cls = random_regional_mob_class(depth)
        _spawn_wandering_mob(game, floor, floor_id, cls, cx, cy)
    return 0, 0


def _trap_grim(game, floor, player, floor_id, is_player, patches):
    """GrimTrap.activate(): instantly deals (maxHP/2 + curHP/2) damage
    (capped to 90% maxHP for the hero). SPD targets Actor.findChar(pos),
    i.e. whoever's standing on the trap -- always the triggerer in this
    engine, since _trigger_trap_if_needed only ever calls trap handlers for
    the char currently occupying the trap's cell. SPD's fallback ("closest
    char in LOS") only fires when Actor.findChar(pos) finds nobody there,
    which can't happen given this engine's trigger model, so it's dropped
    rather than ported."""
    dmg = round(player.max_hp / 2.0 + player.hp / 2.0)
    if isinstance(player, Player):
        dmg = min(dmg, int(player.max_hp * 0.9))
    dealt = player.take_damage(dmg)
    return dmg, dealt


def _trap_guardian(game, floor, player, floor_id, is_player, patches):
    """GuardianTrap.activate(): beckons every mob on the floor (like
    AlarmTrap), then spawns (scalingDepth-5)//5 wandering Guardian statues.
    (SPD arms each Guardian with a random uncursed, unenchanted, level-0
    melee weapon that drives its damage roll -- skipped here: MobEntity
    combat has no notion of an equipped weapon, only flat damage_min/max,
    so Guardian just fights with Statue's own stats instead.)"""
    from app.engine.entities.mobs import Guardian

    for mob in floor.mobs.values():
        if mob.is_alive:
            mob.ai_state = "hunting"
            mob.target_id = player.id
    game.add_event("PLAY_SOUND", {"sound": "ALERT"}, floor_id=floor_id)

    n_guardians = max(0, (floor_id - 5) // 5)
    if n_guardians:
        candidates = _free_neighbour_cells(floor, player.pos.x, player.pos.y)
        random.shuffle(candidates)
        for (cx, cy) in candidates[:n_guardians]:
            guardian = _spawn_wandering_mob(game, floor, floor_id, Guardian, cx, cy)
            guardian.target_id = player.id
    return 0, 0


_TRAP_HANDLERS: Dict[str, Callable] = {
    "tengu_dart": _trap_tengu_dart,
    "burning_trap": _trap_burning,
    "blazing_trap": _trap_blazing,
    "shocking_trap": _trap_shocking,
    "storm_trap": _trap_storm,
    "toxic_trap": _trap_toxic,
    "poison_dart_trap": _trap_poison_dart,
    "chilling_trap": _trap_chilling,
    "frost_trap": _trap_frost,
    "confusion_trap": _trap_confusion,
    "ooze_trap": _trap_ooze,
    "corrosion_trap": _trap_corrosion,
    "flock_trap": _trap_flock,
    "weakening_trap": _trap_weakening,
    "gripping_trap": _trap_gripping,
    "geyser_trap": _trap_geyser,
    "explosive_trap": _trap_explosive,
    "pitfall_trap": _trap_pitfall,
    "alarm_trap": _trap_alarm,
    "summoning_trap": _trap_summoning,
    "teleportation_trap": _trap_teleportation,
    "gateway_trap": _trap_gateway,
    "warping_trap": _trap_warping,
    "flashing_trap": _trap_flashing,
    "disarming_trap": _trap_disarming,
    "cursing_trap": _trap_cursing,
    "distortion_trap": _trap_distortion,
    "grim_trap": _trap_grim,
    "guardian_trap": _trap_guardian,
}




class WorldInteractionMixin:
    def search(self, player_id: str):
        player = self.players.get(player_id)
        if not player:
            return

        floor = self._get_or_create_floor(player.floor_id)
        patches: List[dict] = []
        # Every in-bounds cell scanned this search, so the client can sweep a
        # CheckedCell ring over the whole radius (mirrors the original drawing a
        # CheckedCell on each cell in range, not only the ones that revealed something).
        checked: List[List[int]] = []
        found_secret = False

        wide_search = player.subclass_info.talent_info.level("wide_search")
        distance = 2 if player.class_type == CharacterClass.ROGUE else 1
        circular = False
        if wide_search > 0:
            distance += 1
            circular = wide_search == 1

        for dy in range(-distance, distance + 1):
            for dx in range(-distance, distance + 1):
                if dx == 0 and dy == 0:
                    continue
                if circular and dx * dx + dy * dy > distance * distance:
                    continue
                tx = player.pos.x + dx
                ty = player.pos.y + dy
                if not (0 <= tx < floor.width and 0 <= ty < floor.height):
                    continue

                checked.append([tx, ty])
                pos = (tx, ty)
                if pos in floor.hidden_doors:
                    actual_tile = floor.hidden_doors.pop(pos)
                    floor.grid[ty][tx] = actual_tile
                    patches.append({"x": tx, "y": ty, "tile": actual_tile})
                    found_secret = True

                trap = floor.traps.get(pos)
                if trap and trap.hidden and trap.can_be_searched:
                    trap.hidden = False
                    found_secret = True
                    if floor.grid[ty][tx] == TileType.SECRET_TRAP:
                        floor.grid[ty][tx] = TileType.TRAP
                        patches.append({"x": tx, "y": ty, "tile": TileType.TRAP})

        if patches:
            # Tile mutations changed the grid — refresh derived flag maps
            # so LOS / pathfinding / openSpace pick up the new state on
            # the next query (a revealed door is now passable + see-through).
            floor.rebuild_flags()
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=player.floor_id)

        # Original plays the SECRET sound whenever a door OR a trap is revealed.
        if found_secret:
            self.add_event("PLAY_SOUND", {"sound": "SECRET"}, player_id=player_id)

        # Drives the operate (hand-raise) animation + the cyan ring sweep. Tagged
        # with source_player_id so the effect plays for the searcher and any player
        # in direct line-of-sight of them. x/y is the hero position the rings emanate from.
        self.add_event(
            "SEARCH",
            {
                "player": player_id,
                "x": player.pos.x,
                "y": player.pos.y,
                "cells": checked,
                "revealed_tiles": len(patches),
            },
            floor_id=player.floor_id,
            source_player_id=player_id,
        )

    def _try_unlock_locked_door(self, player: Player, floor: FloorState, x: int, y: int) -> bool:
        key_id = floor.locked_doors.get((x, y))
        if not key_id:
            return False

        # Already being unlocked by another player — don't double-spend a key.
        if (x, y) in floor.pending_unlocks:
            return True

        # Tengu cell entrance: any player may pass freely once fight starts.
        if key_id != "tengu_boss" and not player.remove_key(key_id, floor.floor_id):
            self.add_event("LOCKED", {"player": player.id, "x": x, "y": y}, floor_id=player.floor_id)
            return False

        # Key consumed + input blocked now; the door stays locked while the
        # hero plays the operate animation, then the tick resolves the pending
        # unlock (tile swap + sound) once KEY_TIME_TO_UNLOCK passes.
        player.action_until = max(player.action_until, time.time() + KEY_TIME_TO_UNLOCK)
        self.add_event("UNLOCK", {"player": player.id, "x": x, "y": y}, floor_id=player.floor_id)
        self._register_pending_unlock(floor, x, y, "door", player.id)
        return True

    def trigger_trap_at(self, floor: FloorState, x: int, y: int, floor_id: int):
        pos = (x, y)
        trap = floor.traps.get(pos)
        if not trap or not trap.active:
            return

        if trap.hidden:
            trap.hidden = False
        trap.active = False

        patches: List[dict] = []
        tile = floor.grid[y][x]
        if tile in (TileType.SECRET_TRAP, TileType.TRAP):
            floor.grid[y][x] = TileType.INACTIVE_TRAP
            patches.append({"x": x, "y": y, "tile": TileType.INACTIVE_TRAP})

        occupant = self._entity_at(floor, floor_id, x, y, exclude_id="")

        dealt = 0
        if occupant is not None:
            is_player = isinstance(occupant, Player)
            handler = _TRAP_HANDLERS.get(trap.trap_type)
            if handler is not None:
                result = handler(self, floor, occupant, floor_id, is_player, patches)
                if result is not None:
                    _, dealt = result
            else:
                dealt = occupant.take_damage(2)

            if dealt > 0:
                self.add_event("DAMAGE", {"target": occupant.id, "amount": dealt}, floor_id=floor_id)
                self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id, source_player_id=occupant.id if is_player else None)
                if is_player:
                    warn_sound = hurt_warning_sound(dealt, occupant.hp, occupant.get_total_max_hp())
                    if warn_sound:
                        self.add_event("PLAY_SOUND", {"sound": warn_sound}, player_id=occupant.id)
            self.add_event(
                "TRAP_TRIGGERED",
                {"player": occupant.id, "trap": trap.trap_type, "damage": dealt, "x": x, "y": y},
                floor_id=floor_id,
            )
        else:
            dummy = type("_TrapPos", (), {
                "pos": Position(x=x, y=y), "buffs": [], "id": "",
                "take_damage": lambda d: 0, "has_buff": lambda b: False,
                "add_buff": lambda *a, **kw: None,
                "get_total_max_hp": lambda: 1, "hp": 1,
            })()
            handler = _TRAP_HANDLERS.get(trap.trap_type)
            if handler is not None:
                handler(self, floor, dummy, floor_id, False, patches)
            self.add_event(
                "TRAP_TRIGGERED",
                {"player": "", "trap": trap.trap_type, "damage": 0, "x": x, "y": y},
                floor_id=floor_id,
            )

        if patches:
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)
            floor.rebuild_flags()

    def _trigger_trap_if_needed(self, floor: FloorState, player, floor_id: int):
        if player.has_buff("levitation"):
            return
        self.trigger_trap_at(floor, player.pos.x, player.pos.y, floor_id)

