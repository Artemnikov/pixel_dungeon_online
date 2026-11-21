# Copyright (C) 2026 ArtemNikov
#
"""Port of SPD `actors/mobs/YogFist.java`: the six fists Yog-Dzewa summons.

Each fist acts once per SPD turn of its own time (game/spd_act_clock.py).
`canAttack` is a MAGIC_BOLT line at any range while the ranged attack is off
cooldown, otherwise adjacency; `doAttack` melees an adjacent target when the
fist can't zap in melee or the zap is cooling down, and zaps otherwise.
Moving toward the target is left to the generic AI (SPD `getCloser`).

Damage side effects that need the game (status texts, LockedFloor, the
Bright/Dark half-HP teleport) are queued on the fist and drained by
`fist_flush` every real-time tick / turn-room turn.
"""

import random
from typing import Optional

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position, is_immune, normal_float, normal_int_range, spd_chances
from app.engine.entities.buffs import add_buff
from app.engine.entities.mobs import BrightFist, DarkFist
from app.engine.game import spd_act_clock
from app.engine.game.ai_spd_common import (
    adjacent, is_paralysed, spd_attack, spd_hit, visible_enemy,
)
from app.engine.game.blobs import fire_volume_at, seed_fire, seed_gas
from app.engine.game.boss_targets import arena_players, mob_fov, union_hero_fov
from app.engine.game.constants import (
    YOG_FIST_BRIGHT_DEATH_BLIND, YOG_FIST_BRIGHT_TELEPORT_BLIND,
    YOG_FIST_BRIGHT_ZAP_BLIND, YOG_FIST_DARK_LIGHT_WEAKEN, YOG_FIST_FIRE_VOLUME,
    YOG_FIST_INVULN_RADIUS, YOG_FIST_RANGED_CD, YOG_FIST_ROTTING_GAS,
    YOG_FIST_RUSTED_CRIPPLE, YOG_FIST_SOILED_ROOTS, YOG_FIST_TELEPORT_TRIES,
    YOG_FIST_ZAP_DMG,
)
from app.engine.game.floor_state import FloorState
from app.engine.game.light import detach_light, weaken_light
from app.engine.game.locked_floor import add_locked_floor_time
from app.engine.systems.spd_ballistica import MAGIC_BOLT, Ballistica, char_lookup

NEIGHBOURS8 = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))
NEIGHBOURS9 = ((-1, -1), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (-1, 1), (0, 1), (1, 1))

BOLT_BY_KIND = {
    "burning": "fire", "soiled": "foliage", "rotting": "toxic_gas",
    "rusted": "corrosion", "bright": "light_ray", "dark": "shadow",
}

_GRASS = TileType.FLOOR_GRASS
_TALL = (TileType.FURROWED_GRASS, TileType.HIGH_GRASS)


def _in_map(floor, c) -> bool:
    return 0 <= c[0] < floor.width and 0 <= c[1] < floor.height


def _solid(floor, c) -> bool:
    return bool(floor.flags.solid[c[1]][c[0]])


def _water(floor, c) -> bool:
    return floor.grid[c[1]][c[0]] == TileType.FLOOR_WATER


def _update_yog_fist(game, fist, floor: FloorState, floor_id: int) -> bool:
    fist_flush(game, fist, floor, floor_id)
    if not fist.is_alive:
        return True
    blocked = spd_act_clock.run(game, fist, lambda: fist_act(game, fist, floor, floor_id))
    fist_flush(game, fist, floor, floor_id)
    return blocked or not fist.is_alive


# --- per-tick side effects ------------------------------------------------

def fist_flush(game, fist, floor: FloorState, floor_id: int) -> None:
    if fist.fist_kind == "soiled":
        _count_grass(fist, floor)
    if fist.locked_floor_credit > 0:
        add_locked_floor_time(game, floor_id, fist.locked_floor_credit)
        fist.locked_floor_credit = 0.0
    while fist.status_popups:
        kind = fist.status_popups.pop(0)
        if kind == "invuln_warn":
            game.add_event("MESSAGE", {"key": "mob.yog_fist.invuln_warn",
                                       "text": "The fist is invulnerable while near to Yog-Dzewa!"},
                           floor_id=floor_id)
            continue
        key, _, value = kind.partition(":")
        game.add_event("STATUS_TEXT", {"target": fist.id, "key": f"status.{key}", "value": value or None,
                                       "kind": "positive" if key == "invulnerable" else "warning",
                                       "x": fist.pos.x, "y": fist.pos.y}, floor_id=floor_id)
    if isinstance(fist, (BrightFist, DarkFist)) and getattr(fist, "pending_teleport", False):
        fist.pending_teleport = False
        _half_hp_teleport(game, fist, floor, floor_id)


def _count_grass(fist, floor: FloorState) -> None:
    n = 0
    for dx, dy in NEIGHBOURS9:
        c = (fist.pos.x + dx, fist.pos.y + dy)
        if _in_map(floor, c) and floor.grid[c[1]][c[0]] in _TALL:
            n += 1
    fist.grass_cells_nearby = n


# --- the act --------------------------------------------------------------

def fist_act(game, fist, floor: FloorState, floor_id: int) -> Optional[float]:
    if fist.fist_kind == "rotting":
        _rotting_pre_act(game, fist, floor, floor_id)

    paralysed = is_paralysed(fist)
    if not paralysed and fist.ranged_cooldown > 0:
        fist.ranged_cooldown -= 1

    if fist.ai_state == "wandering":
        hero = next((p for p in arena_players(game, floor_id) if p.invisible <= 0), None)
        if hero is not None:
            fist.ai_state = "hunting"
            fist.last_known_target_pos = Position(x=hero.pos.x, y=hero.pos.y)

    result = _mob_act(game, fist, floor, floor_id, paralysed)

    if fist.is_alive:
        if fist.fist_kind == "burning":
            _burning_post_act(game, fist, floor, floor_id)
        elif fist.fist_kind == "soiled":
            _soiled_post_act(game, fist, floor, floor_id)
    return result


def _mob_act(game, fist, floor, floor_id, paralysed) -> Optional[float]:
    if paralysed:
        return 1.0
    if fist.ai_state != "hunting":
        return None
    enemy = visible_enemy(game, fist, floor, floor_id, mob_fov(game, fist, floor_id))
    if enemy is None or fist.has_buff("charm") or not _can_attack(game, fist, enemy, floor, floor_id):
        return None
    if adjacent(fist, enemy) and (not fist.can_ranged_in_melee or fist.ranged_cooldown > 0):
        return spd_attack(game, fist, enemy)
    if fist.has_ranged_cooldown:
        fist.ranged_cooldown += normal_float(*YOG_FIST_RANGED_CD)
    _zap(game, fist, enemy, floor, floor_id)
    return 1.0


def _can_attack(game, fist, enemy, floor, floor_id) -> bool:
    if fist.ranged_cooldown <= 0:
        bolt = Ballistica((fist.pos.x, fist.pos.y), (enemy.pos.x, enemy.pos.y), MAGIC_BOLT,
                          floor, char_lookup(game, floor, floor_id))
        return bolt.collision_pos == (enemy.pos.x, enemy.pos.y)
    return adjacent(fist, enemy)


def _zap(game, fist, enemy, floor, floor_id) -> None:
    kind = fist.fist_kind
    game.add_event("FIST_ZAP", {
        "mob": fist.id, "kind": kind, "bolt": BOLT_BY_KIND[kind],
        "x": fist.pos.x, "y": fist.pos.y, "target_x": enemy.pos.x, "target_y": enemy.pos.y,
    }, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "RAY" if kind == "bright" else "ZAP",
                                  "x": fist.pos.x, "y": fist.pos.y}, floor_id=floor_id)
    _ZAPS[kind](game, fist, enemy, floor, floor_id)


def _miss(game, fist, enemy, floor_id) -> None:
    game.add_event("MISS", {"source": fist.id, "target": enemy.id,
                            "defense_verb": getattr(enemy, "defense_verb", "dodged")}, floor_id=floor_id)


def _hurt(game, fist, enemy, dmg, floor_id) -> None:
    taken = enemy.take_damage(dmg)
    game.add_event("ATTACK", {"source": fist.id, "target": enemy.id, "damage": taken,
                              "surprise": False, "crit": False, "grim_proc": False}, floor_id=floor_id)
    if taken:
        game.add_event("DAMAGE", {"target": enemy.id, "amount": taken, "x": enemy.pos.x,
                                  "y": enemy.pos.y}, floor_id=floor_id)
    if getattr(enemy, "type", None) != "player" and not enemy.is_alive:
        from app.engine.game.dot_death import finish_dot_kill
        finish_dot_kill(game, enemy, floor_id)


def _evaporate(game, floor, c, floor_id, patches) -> None:
    floor.grid[c[1]][c[0]] = TileType.FLOOR
    patches.append({"x": c[0], "y": c[1], "tile": TileType.FLOOR})
    game.add_event("TERRAIN_BURST", {"cells": [[c[0], c[1], 10]], "kind": "steam"}, floor_id=floor_id)


def _commit_patches(game, floor, patches, floor_id) -> None:
    if patches:
        floor.rebuild_flags()
        game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)


def _top_up_fire(floor, centre) -> None:
    for dx, dy in NEIGHBOURS9:
        c = (centre[0] + dx, centre[1] + dy)
        if not _in_map(floor, c) or _water(floor, c) or _solid(floor, c):
            continue
        vol = fire_volume_at(floor, c)
        if vol < YOG_FIST_FIRE_VOLUME:
            seed_fire(floor, c, YOG_FIST_FIRE_VOLUME - vol)


def _zap_burning(game, fist, enemy, floor, floor_id) -> None:
    epos = (enemy.pos.x, enemy.pos.y)
    patches = []
    if _water(floor, epos):
        _evaporate(game, floor, epos, floor_id, patches)
    elif not is_immune(enemy, "burning"):
        add_buff(enemy.buffs, "burning", duration=8.0, level=1, stack_mode="extend")
    _commit_patches(game, floor, patches, floor_id)
    _top_up_fire(floor, epos)


def _can_spread_grass(fist, floor, c) -> bool:
    yog = fist.yog_pos or (16, 12)
    if not _in_map(floor, c):
        return False
    return (max(abs(c[0] - yog[0]), abs(c[1] - yog[1])) > YOG_FIST_INVULN_RADIUS
            and not _solid(floor, c) and floor.grid[c[1]][c[0]] not in _TALL)


def _zap_soiled(game, fist, enemy, floor, floor_id) -> None:
    if spd_hit(fist, enemy):
        if not getattr(enemy, "flying", False):
            add_buff(enemy.buffs, "roots", duration=YOG_FIST_SOILED_ROOTS, level=1, stack_mode="stack")
    else:
        _miss(game, fist, enemy, floor_id)
    patches, leaves = [], []
    for dx, dy in NEIGHBOURS9:
        c = (enemy.pos.x + dx, enemy.pos.y + dy)
        if _can_spread_grass(fist, floor, c):
            tile = TileType.FURROWED_GRASS if random.randint(0, 4) == 0 else _GRASS
            floor.grid[c[1]][c[0]] = tile
            patches.append({"x": c[0], "y": c[1], "tile": tile})
            leaves.append([c[0], c[1], 10])
    _commit_patches(game, floor, patches, floor_id)
    if leaves:
        game.add_event("TERRAIN_BURST", {"cells": leaves, "kind": "leaf"}, floor_id=floor_id)


def _zap_rotting(game, fist, enemy, floor, floor_id) -> None:
    seed_gas(floor, "toxic_gas", (enemy.pos.x, enemy.pos.y), YOG_FIST_ROTTING_GAS)


def _zap_rusted(game, fist, enemy, floor, floor_id) -> None:
    add_buff(enemy.buffs, "cripple", duration=YOG_FIST_RUSTED_CRIPPLE, level=1, stack_mode="stack")


def _zap_bright(game, fist, enemy, floor, floor_id) -> None:
    if not spd_hit(fist, enemy):
        _miss(game, fist, enemy, floor_id)
        return
    _hurt(game, fist, enemy, normal_int_range(*YOG_FIST_ZAP_DMG), floor_id)
    add_buff(enemy.buffs, "blindness", duration=YOG_FIST_BRIGHT_ZAP_BLIND, level=1, stack_mode="extend")


def _zap_dark(game, fist, enemy, floor, floor_id) -> None:
    if not spd_hit(fist, enemy):
        _miss(game, fist, enemy, floor_id)
        return
    _hurt(game, fist, enemy, normal_int_range(*YOG_FIST_ZAP_DMG), floor_id)
    weaken_light(enemy, YOG_FIST_DARK_LIGHT_WEAKEN)


_ZAPS = {
    "burning": _zap_burning, "soiled": _zap_soiled, "rotting": _zap_rotting,
    "rusted": _zap_rusted, "bright": _zap_bright, "dark": _zap_dark,
}


# --- per-fist act extras --------------------------------------------------

def _rotting_pre_act(game, fist, floor, floor_id) -> None:
    seed_gas(floor, "toxic_gas", (fist.pos.x, fist.pos.y), 0)
    if _water(floor, (fist.pos.x, fist.pos.y)) and fist.hp < fist.max_hp:
        heal = fist.max_hp // 50
        fist.hp = min(fist.max_hp, fist.hp + heal)
        game.add_event("HEAL", {"target": fist.id, "amount": heal, "x": fist.pos.x, "y": fist.pos.y},
                       floor_id=floor_id)


def _burning_post_act(game, fist, floor, floor_id) -> None:
    pos = (fist.pos.x, fist.pos.y)
    patches = []
    if _water(floor, pos):
        _evaporate(game, floor, pos, floor_id, patches)
    for _ in range(max(0, spd_chances([0, 1, 2]))):
        dx, dy = NEIGHBOURS8[random.randint(0, 7)]
        c = (pos[0] + dx, pos[1] + dy)
        if _in_map(floor, c) and _water(floor, c):
            _evaporate(game, floor, c, floor_id, patches)
    _commit_patches(game, floor, patches, floor_id)
    _top_up_fire(floor, pos)


def _soiled_post_act(game, fist, floor, floor_id) -> None:
    patches, leaves = [], []
    for _ in range(max(0, spd_chances([0, 2, 1]))):
        dx, dy = NEIGHBOURS9[random.randint(0, 8)]
        c = (fist.pos.x + dx, fist.pos.y + dy)
        if _in_map(floor, c) and floor.grid[c[1]][c[0]] == _GRASS:
            floor.grid[c[1]][c[0]] = TileType.FURROWED_GRASS
            patches.append({"x": c[0], "y": c[1], "tile": TileType.FURROWED_GRASS})
            leaves.append([c[0], c[1], 10])
    for dx, dy in NEIGHBOURS9:
        c = (fist.pos.x + dx, fist.pos.y + dy)
        if _can_spread_grass(fist, floor, c) and floor.grid[c[1]][c[0]] != _GRASS:
            floor.grid[c[1]][c[0]] = _GRASS
            patches.append({"x": c[0], "y": c[1], "tile": _GRASS})
    _commit_patches(game, floor, patches, floor_id)
    if leaves:
        game.add_event("TERRAIN_BURST", {"cells": leaves, "kind": "leaf"}, floor_id=floor_id)
    _count_grass(fist, floor)


# --- Bright / Dark fist half-HP teleport and death ----------------------------

def _has_path_to(game, floor, start, goal) -> bool:
    from collections import deque
    if start == goal:
        return True
    seen = {start}
    queue = deque([start])
    flags = floor.flags
    while queue:
        x, y = queue.popleft()
        for dx, dy in NEIGHBOURS8:
            n = (x + dx, y + dy)
            if n == goal:
                return True
            if n in seen or not _in_map(floor, n) or not flags.passable[n[1]][n[0]]:
                continue
            seen.add(n)
            queue.append(n)
    return False


def _flash(game, fist, floor_id) -> None:
    if isinstance(fist, BrightFist):
        game.add_event("SCREEN_FLASH", {"color": 0xFFFFFF, "alpha": 0.5, "light": True}, floor_id=floor_id)
    else:
        game.add_event("SCREEN_FLASH", {"color": 0x000000, "alpha": 1.0, "light": False}, floor_id=floor_id)


def _half_hp_teleport(game, fist, floor, floor_id) -> None:
    players = arena_players(game, floor_id)
    if isinstance(fist, BrightFist):
        for p in players:
            add_buff(p.buffs, "blindness", duration=YOG_FIST_BRIGHT_TELEPORT_BLIND, level=1, stack_mode="extend")
    else:
        for p in players:
            detach_light(p)
        game._invalidate_fov_cache()
    hero_fov = union_hero_fov(game, floor_id)
    lookup = char_lookup(game, floor, floor_id)
    exit_cell = floor.exit_pos or (16, 9)
    dest = None
    for _ in range(YOG_FIST_TELEPORT_TRIES):
        c = (random.randint(0, floor.width - 1), random.randint(0, floor.height - 1))
        if c in hero_fov or _solid(floor, c) or lookup(*c) is not None:
            continue
        if not floor.flags.passable[c[1]][c[0]] or not _has_path_to(game, floor, c, exit_cell):
            continue
        dest = c
        break
    if dest is not None:
        from_x, from_y = fist.pos.x, fist.pos.y
        fist.pos = Position(x=dest[0], y=dest[1])
        game.add_event("TELEPORT", {"mob": fist.id, "from_x": from_x, "from_y": from_y,
                                    "x": dest[0], "y": dest[1]}, floor_id=floor_id)
    fist.ai_state = "wandering"
    _flash(game, fist, floor_id)
    game.add_event("MESSAGE", {"key": f"mob.{fist.fist_kind}_fist.teleport",
                               "text": "The fist teleports away!"}, floor_id=floor_id)


def on_fist_death(game, fist, floor, floor_id) -> None:
    """`BrightFist`/`DarkFist.damage()` when the hit kills them."""
    if isinstance(fist, BrightFist):
        for p in arena_players(game, floor_id):
            add_buff(p.buffs, "blindness", duration=YOG_FIST_BRIGHT_DEATH_BLIND, level=1, stack_mode="extend")
        _flash(game, fist, floor_id)
    elif isinstance(fist, DarkFist):
        for p in arena_players(game, floor_id):
            detach_light(p)
        game._invalidate_fov_cache()
        _flash(game, fist, floor_id)

