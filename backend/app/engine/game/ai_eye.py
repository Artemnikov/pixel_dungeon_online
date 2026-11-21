# Copyright (C) 2026 ArtemNikov
#
"""Port of SPD `actors/mobs/Eye.java` (Evil Eye; Yog-Dzewa's YogEye too).

The Eye charges its death gaze for `2 * attackDelay` once it has a clear
STOP_SOLID line to its target, then fires on its next act at the cell it
aimed at -- even if the target has since stepped away or out of sight. The
gaze hits every character on the path, burns flammable terrain, and puts the
beam on a 4..6 turn cooldown; in between, the Eye melees only adjacent foes.
"""

import random
from typing import Optional

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import normal_int_range
from app.engine.entities.mobs import Eye
from app.engine.game import spd_act_clock
from app.engine.game.ai_spd_common import (
    adjacent, attack_delay, is_paralysed, spd_attack, spd_hit, visible_enemy,
)
from app.engine.game.boss_targets import mob_fov
from app.engine.game.constants import EYE_BEAM_CD, EYE_GAZE_DMG
from app.engine.systems.spd_ballistica import STOP_SOLID, Ballistica, char_lookup


def _update_eye(game, eye: Eye, floor, floor_id: int) -> bool:
    return spd_act_clock.run(game, eye, lambda: eye_act(game, eye, floor, floor_id))


def _beam(game, eye, floor, floor_id: int, cell) -> Ballistica:
    return Ballistica((eye.pos.x, eye.pos.y), cell, STOP_SOLID, floor, char_lookup(game, floor, floor_id))


def eye_act(game, eye: Eye, floor, floor_id: int) -> Optional[float]:
    if eye.beam_charged and eye.ai_state != "hunting":
        eye.beam_charged = False
        game.add_event("EYE_CHARGE_END", {"mob": eye.id}, floor_id=floor_id)
    if eye.beam_cooldown > 0:
        eye.beam_cooldown -= 1

    if is_paralysed(eye):
        return 1.0
    if eye.ai_state != "hunting":
        return None

    fov = mob_fov(game, eye, floor_id)
    enemy = visible_enemy(game, eye, floor, floor_id, fov)

    if eye.beam_charged and enemy is None and eye.beam_target_id:
        enemy = floor.mobs.get(eye.beam_target_id) or game.players.get(eye.beam_target_id)
        if enemy is not None and not enemy.is_alive:
            enemy = None
    if eye.beam_charged and enemy is not None and _can_attack(game, eye, enemy, floor, floor_id, fov):
        return _do_attack(game, eye, enemy, floor, floor_id)

    if enemy is not None and _can_attack(game, eye, enemy, floor, floor_id, fov):
        return _do_attack(game, eye, enemy, floor, floor_id)
    return None


def _can_attack(game, eye: Eye, enemy, floor, floor_id: int, fov) -> bool:
    if eye.beam_cooldown == 0:
        aim = _beam(game, eye, floor, floor_id, (enemy.pos.x, enemy.pos.y))
        seen = (enemy.pos.x, enemy.pos.y) in fov and getattr(enemy, "invisible", 0) == 0
        if seen and not enemy.has_buff("charm") and (
                adjacent(eye, enemy) or (enemy.pos.x, enemy.pos.y) in aim.sub_path(1, aim.dist)):
            eye.beam_target_x, eye.beam_target_y = enemy.pos.x, enemy.pos.y
            eye.has_beam_target = True
            eye.beam_target_id = enemy.id
            return True
        return eye.beam_charged
    return adjacent(eye, enemy)


def _do_attack(game, eye: Eye, enemy, floor, floor_id: int) -> float:
    if eye.has_beam_target:
        beam = _beam(game, eye, floor, floor_id, (eye.beam_target_x, eye.beam_target_y))
        on_line = (enemy.pos.x, enemy.pos.y) in beam.sub_path(1, beam.dist)
    else:
        beam, on_line = None, False

    if eye.beam_cooldown > 0 or (not eye.beam_charged and not on_line):
        return spd_attack(game, eye, enemy)

    if not eye.beam_charged:
        eye.beam_charged = True
        game.add_event("EYE_CHARGE", {
            "mob": eye.id, "target_x": eye.beam_target_x, "target_y": eye.beam_target_y,
        }, floor_id=floor_id)
        game.add_event("PLAY_SOUND", {"sound": "CHARGEUP", "x": eye.pos.x, "y": eye.pos.y},
                       floor_id=floor_id)
        return attack_delay(eye) * 2.0

    death_gaze(game, eye, floor, floor_id, beam)
    return attack_delay(eye)


def death_gaze(game, eye: Eye, floor, floor_id: int, beam: Optional[Ballistica]) -> None:
    """`Eye.deathGaze()`."""
    if not eye.beam_charged or eye.beam_cooldown > 0 or beam is None:
        return
    eye.beam_charged = False
    eye.beam_cooldown = random.randint(*EYE_BEAM_CD)

    cx, cy = beam.collision_pos
    game.add_event("EYE_DEATH_RAY", {
        "mob": eye.id, "source_x": eye.pos.x, "source_y": eye.pos.y,
        "target_x": cx, "target_y": cy,
    }, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "RAY", "x": eye.pos.x, "y": eye.pos.y}, floor_id=floor_id)

    destroyed = []
    lookup = char_lookup(game, floor, floor_id)
    for x, y in beam.sub_path(1, beam.dist):
        if floor.flags and floor.flags.flamable[y][x]:
            floor.grid[y][x] = TileType.EMBERS
            destroyed.append({"x": x, "y": y, "tile": TileType.EMBERS})
        ch = lookup(x, y)
        if ch is None or not ch.is_alive:
            continue
        if not spd_hit(eye, ch):
            game.add_event("MISS", {"source": eye.id, "target": ch.id,
                                    "defense_verb": getattr(ch, "defense_verb", "dodged")}, floor_id=floor_id)
            continue
        dmg = normal_int_range(*EYE_GAZE_DMG)
        if isinstance(ch, Eye):
            dmg = round(dmg * 0.5)
        taken = ch.take_damage(dmg)
        game.add_event("ATTACK", {"source": eye.id, "target": ch.id, "damage": taken,
                                  "surprise": False, "crit": False, "grim_proc": False}, floor_id=floor_id)
        game.add_event("DAMAGE", {"target": ch.id, "amount": taken, "source_x": eye.pos.x,
                                  "source_y": eye.pos.y, "projectile": "beam",
                                  "beam_type": "death_ray", "purple_burst": True,
                                  "x": x, "y": y}, floor_id=floor_id)
        if not ch.is_alive and getattr(ch, "type", None) != "player":
            from app.engine.game.dot_death import finish_dot_kill
            finish_dot_kill(game, ch, floor_id)

    if destroyed:
        floor.rebuild_flags()
        game.add_event("MAP_PATCH", {"tiles": destroyed}, floor_id=floor_id)
    eye.has_beam_target = False
    eye.beam_target_id = ""
