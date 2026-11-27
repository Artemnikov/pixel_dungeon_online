# Copyright (C) 2026 ArtemNikov
#
"""Port of SPD `actors/mobs/RipperDemon.java` (and Yog-Dzewa's YogRipper).

While hunting at range 3+ with its leap off cooldown, the Ripper aims a leap
at the cell beside its target opposite where the target came from, marks it
(red TargetedCell + warning) and waits `gate(attackDelay, ceil(target
cooldown), 3*attackDelay)`. Its next act performs the leap (costing no
time): it lands on the cell, bouncing to the nearest free neighbour if a
character is there, and a hostile victim is hit with infinite accuracy for
Bleeding of 0.75 x a damage roll. The leap then goes on cooldown for
NormalIntRange(2, 4) acts.
"""

import math
from typing import Optional

from app.engine.entities.base import normal_int_range
from app.engine.entities.buffs import is_rooted
from app.engine.entities.base import Position
from app.engine.game import spd_act_clock
from app.engine.game.ai_spd_common import (
    INFINITE_ACCURACY, attack_delay, is_paralysed, spd_hit, visible_enemy,
)
from app.engine.game.bleeding import apply_bleeding
from app.engine.game.boss_targets import hero_cooldown_turns, mob_fov
from app.engine.game.constants import (
    RIPPER_LEAP_BLEED, RIPPER_LEAP_CD, RIPPER_LEAP_MIN_DIST,
    YOG_TARGETED_CELL_COLOR, YOG_TARGETED_CELL_FADE_MS,
)
from app.engine.systems.spd_ballistica import STOP_SOLID, STOP_TARGET, Ballistica, char_lookup

CIRCLE8 = ((-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0))
NEIGHBOURS8 = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))


def _true_distance(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _update_ripper(game, mob, floor, floor_id: int) -> bool:
    return spd_act_clock.run(game, mob, lambda: ripper_act(game, mob, floor, floor_id))


def ripper_act(game, mob, floor, floor_id: int) -> Optional[float]:
    if mob.ai_state == "wandering":
        mob.leap_pos = None
    was_wandering = mob.ai_state == "wandering"
    result, enemy = _ripper_state_act(game, mob, floor, floor_id)
    if not is_paralysed(mob):
        mob.leap_cooldown -= 1
    if not (was_wandering and mob.ai_state == "hunting"):
        if enemy is not None:
            mob.last_enemy_pos = (enemy.pos.x, enemy.pos.y)
        else:
            nearest = game._find_nearest_player(mob.pos, floor_id)
            if nearest is not None:
                mob.last_enemy_pos = (nearest.pos.x, nearest.pos.y)
    return result


def _ripper_state_act(game, mob, floor, floor_id: int):
    if is_paralysed(mob):
        return 1.0, None
    if mob.ai_state != "hunting":
        return None, None

    if mob.leap_pos is not None:
        landed = _resolve_leap(game, mob, floor, floor_id)
        if landed is not None:
            return landed, None

    fov = mob_fov(game, mob, floor_id)
    enemy = visible_enemy(game, mob, floor, floor_id, fov)
    if enemy is not None and max(abs(enemy.pos.x - mob.pos.x), abs(enemy.pos.y - mob.pos.y)) == 1 \
            and not mob.has_buff("charm"):
        from app.engine.game.ai_spd_common import spd_attack
        return spd_attack(game, mob, enemy), enemy
    if enemy is None:
        return None, None

    dist = max(abs(enemy.pos.x - mob.pos.x), abs(enemy.pos.y - mob.pos.y))
    if mob.leap_cooldown <= 0 and not is_rooted(mob) and dist >= RIPPER_LEAP_MIN_DIST:
        if _prepare_leap(game, mob, enemy, floor, floor_id):
            gate = max(attack_delay(mob), min(float(math.ceil(hero_cooldown_turns(game, enemy))),
                                              3 * attack_delay(mob)))
            return gate, enemy
    return None, enemy


def _prepare_leap(game, mob, enemy, floor, floor_id: int) -> bool:
    lookup = char_lookup(game, floor, floor_id)
    epos = (enemy.pos.x, enemy.pos.y)
    target = epos
    last = mob.last_enemy_pos
    if last is not None and tuple(last) != epos:
        closest = 0
        for i in range(1, len(CIRCLE8)):
            ci = (epos[0] + CIRCLE8[i][0], epos[1] + CIRCLE8[i][1])
            cc = (epos[0] + CIRCLE8[closest][0], epos[1] + CIRCLE8[closest][1])
            if _true_distance(last, ci) < _true_distance(last, cc):
                closest = i
        off = CIRCLE8[(closest + 4) % 8]
        target = (epos[0] + off[0], epos[1] + off[1])

    b = Ballistica((mob.pos.x, mob.pos.y), target, STOP_TARGET | STOP_SOLID, floor, lookup)
    if b.collision_pos != target and target != epos:
        target = epos
        b = Ballistica((mob.pos.x, mob.pos.y), target, STOP_TARGET | STOP_SOLID, floor, lookup)
    if b.collision_pos != target:
        return False

    mob.leap_pos = target
    game.add_event("RIPPER_LEAP_PREP", {
        "mob": mob.id, "x": target[0], "y": target[1],
        "color": YOG_TARGETED_CELL_COLOR, "duration_ms": YOG_TARGETED_CELL_FADE_MS,
    }, floor_id=floor_id)
    game.add_event("MESSAGE", {"key": "mobText.ripper_leap",
                               "text": "The ripper demon prepares to leap!"}, floor_id=floor_id)
    from app.engine.game.ai_spd_common import interrupt_players_near
    interrupt_players_near(game, floor_id, [(mob.pos.x, mob.pos.y), target])
    return True


def _resolve_leap(game, mob, floor, floor_id: int) -> Optional[float]:
    """Returns the time spent if the act ends here, None to continue acting
    (a completed leap spends no time)."""
    mob.leap_cooldown = normal_int_range(*RIPPER_LEAP_CD)
    if is_rooted(mob):
        mob.leap_pos = None
        return 1.0

    lookup = char_lookup(game, floor, floor_id)
    b = Ballistica((mob.pos.x, mob.pos.y), tuple(mob.leap_pos), STOP_TARGET | STOP_SOLID, floor, lookup)
    leap_pos = b.collision_pos
    victim = lookup(*leap_pos)
    if victim is mob:
        victim = None
    end_pos = leap_pos
    if victim is not None:
        bounce = None
        flags = floor.flags
        for strict in (True, False):
            for dx, dy in NEIGHBOURS8:
                c = (leap_pos[0] + dx, leap_pos[1] + dy)
                if not (0 <= c[0] < floor.width and 0 <= c[1] < floor.height):
                    continue
                if lookup(*c) is not None:
                    continue
                ok = flags.passable[c[1]][c[0]] if strict else not flags.solid[c[1]][c[0]]
                if ok and (bounce is None or _true_distance((mob.pos.x, mob.pos.y), c)
                           < _true_distance((mob.pos.x, mob.pos.y), bounce)):
                    bounce = c
            if bounce is not None:
                break
        if bounce is None:
            mob.leap_pos = None
            return 1.0
        end_pos = bounce

    from_pos = (mob.pos.x, mob.pos.y)
    hit = None
    if victim is not None and victim.faction != mob.faction:
        hit = spd_hit(mob, victim, INFINITE_ACCURACY)
        if hit:
            apply_bleeding(victim, RIPPER_LEAP_BLEED * normal_int_range(mob.damage_min, mob.damage_max))
    mob.pos = Position(x=end_pos[0], y=end_pos[1])
    mob.leap_pos = None
    mob.leap_cooldown -= 1
    game.add_event("RIPPER_LEAP", {
        "mob": mob.id, "from_x": from_pos[0], "from_y": from_pos[1],
        "x": leap_pos[0], "y": leap_pos[1], "end_x": end_pos[0], "end_y": end_pos[1],
        "victim": victim.id if victim is not None else None, "hit": hit,
    }, floor_id=floor_id)
    if hit is not None:
        game.add_event("PLAY_SOUND", {"sound": "HIT" if hit else "MISS",
                                      "x": leap_pos[0], "y": leap_pos[1]}, floor_id=floor_id)
    game._process_cell_press(floor, mob, floor_id)
    return None
