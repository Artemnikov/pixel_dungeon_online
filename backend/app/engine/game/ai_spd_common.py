# Copyright (C) 2026 ArtemNikov
#
"""Shared pieces of SPD `Mob`/`Char` behaviour for mobs whose `act()` is
ported whole (Eye, Scorpio, Ripper Demon, Yog's fists).

Each ported act runs on `game/spd_act_clock.py` and returns the SPD time it
spends, or None to let the generic AI move the mob (SPD `getCloser`).
"""

import random
import time
from typing import Optional, Set, Tuple

from app.engine.entities.base import Faction, is_hostile
from app.engine.game.boss_targets import mob_fov

INFINITE_ACCURACY = 1_000_000


def visible_enemy(game, mob, floor, floor_id: int, fov: Optional[Set[Tuple[int, int]]] = None):
    """SPD `Mob.chooseEnemy()` + `enemyInFOV`: the explicit aggro target if it
    is still alive and seen, else the nearest hostile the mob can see."""
    if fov is None:
        fov = mob_fov(game, mob, floor_id)
    aggro_id = getattr(mob, "aggro_target_id", None)
    if aggro_id:
        target = floor.mobs.get(aggro_id) or game.players.get(aggro_id)
        if target is not None and target.is_alive and (target.pos.x, target.pos.y) in fov:
            return target
    best, best_d = None, None
    for p in game._players_on_floor(floor_id):
        if not p.is_alive or getattr(p, "is_downed", False) or not is_hostile(mob, p):
            continue
        if p.invisible > 0 or getattr(p, "is_afk", False) or p.has_buff("time_stasis"):
            continue
        if (p.pos.x, p.pos.y) not in fov:
            continue
        d = game._get_distance(mob.pos, p.pos)
        if best is None or d < best_d:
            best, best_d = p, d
    for m in floor.mobs.values():
        if m.id == mob.id or not m.is_alive or not is_hostile(mob, m):
            continue
        if mob.faction == Faction.DUNGEON and m.faction != Faction.PLAYER:
            continue
        if (m.pos.x, m.pos.y) not in fov:
            continue
        d = game._get_distance(mob.pos, m.pos)
        if best is None or d < best_d:
            best, best_d = m, d
    return best


def adjacent(a, b) -> bool:
    return max(abs(a.pos.x - b.pos.x), abs(a.pos.y - b.pos.y)) == 1


def spd_hit(attacker, defender, accuracy: Optional[float] = None) -> bool:
    """SPD `Char.hit()`: `Random.Float(acu) >= Random.Float(def)`; infinite
    accuracy always hits."""
    acu = attacker.attack_skill if accuracy is None else accuracy
    if acu >= INFINITE_ACCURACY:
        return True
    get_def = getattr(defender, "get_effective_defense_skill", None)
    df = get_def() if get_def else getattr(defender, "defense_skill", 0)
    return random.random() * acu >= random.random() * df


def spd_attack(game, mob, target) -> float:
    """SPD `Mob.doAttack()` -> `attack(enemy)` through the engine's melee
    resolution (accuracy, DR, procs, events), returning the time spent.

    Turn rooms charge SPD `attackDelay()`. Real-time rooms keep the same
    attack-rate limit every other mob has (`attack_cooldown` real seconds,
    one SPD turn being one second): until it has elapsed the mob holds and
    the act is charged the remaining wait instead. The bump targets the
    enemy's cell directly, so this also resolves a ranged regular attack.
    """
    if getattr(game, "game_mode", None) != "turnbased":
        cooldown = mob_attack_cooldown(mob)
        if not game.attack_ready(mob, cooldown):
            remaining = mob.last_attack_time + cooldown - time.time()
            return max(0.05, remaining)
        game.move_entity(mob.id, target.pos.x - mob.pos.x, target.pos.y - mob.pos.y)
        return max(attack_delay(mob), 0.05)
    game.move_entity(mob.id, target.pos.x - mob.pos.x, target.pos.y - mob.pos.y)
    return attack_delay(mob)


def attack_delay(mob) -> float:
    """SPD `Char.attackDelay()` with the port's slow/haste buffs."""
    dly = float(getattr(mob, "attack_delay", 1.0))
    if mob.has_buff("slow") or mob.has_buff("chill"):
        dly *= 2.0
    if mob.has_buff("haste") or mob.has_buff("fury"):
        dly *= 0.5
    if mob.has_buff("adrenaline"):
        dly /= 1.5
    return max(0.1, dly)


def mob_attack_cooldown(mob) -> float:
    """Real-time attack-rate limit of a mob: its `attack_cooldown`, cut by
    SPD Adrenaline's `attackDelay() / 1.5`."""
    cooldown = float(getattr(mob, "attack_cooldown", 1.0))
    if mob.has_buff("adrenaline"):
        cooldown /= 1.5
    return cooldown


def mob_speed(mob) -> float:
    """SPD `Char.speed()` buff multipliers the port models for mobs."""
    speed = float(mob.speed)
    if mob.has_buff("adrenaline"):
        speed *= 2.0
    return speed


def move_cost(mob) -> float:
    return 1.0 / max(0.1, mob_speed(mob))


def is_paralysed(mob) -> bool:
    from app.engine.entities.buffs import is_frozen
    return (mob.has_buff("paralysis") or mob.has_buff("stagger")
            or is_frozen(mob.buffs) or getattr(mob, "freeze_ticks", 0) > 0)


def interrupt_players_near(game, floor_id: int, cells) -> None:
    """SPD `Dungeon.hero.interrupt()` when a telegraph is in a hero's view."""
    from app.engine.game.boss_targets import interrupt, player_fov
    cells = set(cells)
    for p in game._players_on_floor(floor_id):
        if p.is_alive and not getattr(p, "is_downed", False) and player_fov(game, p) & cells:
            interrupt(game, p)
