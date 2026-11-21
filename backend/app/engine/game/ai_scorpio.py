# Copyright (C) 2026 ArtemNikov
#
"""Port of SPD `actors/mobs/Scorpio.java` (and Yog-Dzewa's YogScorpio).

A Scorpio only attacks from range -- `canAttack` needs a clear PROJECTILE
line and refuses adjacent targets -- and while hunting it never closes in:
`getCloser` is `getFurther`, so a hero who reaches melee range sees it back
off. Each hit has a 50% chance to Cripple (`Scorpio.attackProc`).
"""

from typing import Optional

from app.engine.game import spd_act_clock
from app.engine.game.ai_spd_common import (
    adjacent, is_paralysed, move_cost, spd_attack, visible_enemy,
)
from app.engine.game.boss_targets import mob_fov
from app.engine.mechanics.spd_pathfinder import flee_step
from app.engine.systems.spd_ballistica import PROJECTILE, Ballistica, char_lookup


def _update_scorpio(game, mob, floor, floor_id: int) -> bool:
    return spd_act_clock.run(game, mob, lambda: scorpio_act(game, mob, floor, floor_id))


def _can_attack(game, mob, enemy, floor, floor_id: int) -> bool:
    if adjacent(mob, enemy):
        return False
    shot = Ballistica((mob.pos.x, mob.pos.y), (enemy.pos.x, enemy.pos.y), PROJECTILE,
                      floor, char_lookup(game, floor, floor_id))
    return shot.collision_pos == (enemy.pos.x, enemy.pos.y)


def scorpio_act(game, mob, floor, floor_id: int) -> Optional[float]:
    if is_paralysed(mob):
        return 1.0
    if mob.ai_state != "hunting":
        return None

    fov = mob_fov(game, mob, floor_id)
    enemy = visible_enemy(game, mob, floor, floor_id, fov)
    if enemy is not None and not mob.has_buff("charm") and _can_attack(game, mob, enemy, floor, floor_id):
        if getattr(game, "game_mode", None) == "turnbased" or game.attack_ready(mob, mob.attack_cooldown):
            game.add_event("RANGED_ATTACK", {
                "source": mob.id, "x": mob.pos.x, "y": mob.pos.y,
                "target_x": enemy.pos.x, "target_y": enemy.pos.y,
                "projectile": "fishing_spear", "crit": False, "grim_proc": False,
            }, floor_id=floor_id)
        return spd_attack(game, mob, enemy)

    if enemy is None:
        mob.ai_state = "wandering"
        return 1.0

    step = flee_step(game, mob, floor, floor_id, (enemy.pos.x, enemy.pos.y))
    if step is not None and not mob.has_buff("roots") and not mob.has_buff("rooted"):
        before = (mob.pos.x, mob.pos.y)
        game.move_entity(mob.id, step[0], step[1])
        if (mob.pos.x, mob.pos.y) != before:
            return move_cost(mob)
    return 1.0
