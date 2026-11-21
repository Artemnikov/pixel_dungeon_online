import random
import time
import uuid

from app.engine.entities.base import Position
from app.engine.entities.mobs import DKWarlock, Warlock
from app.engine.entities.player import Player
from app.engine.game.ai_ranged_common import (
    ranged_accuracy_roll, ranged_approach, ranged_death_check, ranged_dr_damage,
)


def _update_warlock(game, mob: Warlock, floor, floor_id: int) -> bool:
    approach = ranged_approach(game, mob, floor_id)
    if approach is None:
        return False
    target, dist, in_los = approach

    if dist <= mob.attack_range and in_los:
        now = time.time()
        last = getattr(mob, "last_attack_time", 0)
        if now - last < getattr(mob, "attack_cooldown", 1.0):
            return False
        _warlock_zap(game, mob, target, floor, floor_id)
        return True

    return False


def _warlock_zap(game, mob, target, floor, floor_id: int):
    if isinstance(mob, DKWarlock) and isinstance(target, Player):
        if hasattr(game, "boss_scores") and 3 in game.boss_scores:
            game.boss_scores[3] -= 400
    bolt_type = getattr(mob, "bolt_type", "shadow")
    game.add_event("RANGED_ATTACK", {
        "source": mob.id,
        "x": mob.pos.x,
        "y": mob.pos.y,
        "target_x": target.pos.x,
        "target_y": target.pos.y,
        "projectile": bolt_type,
        "is_wand": True,
        "sound": "ZAP",
        "crit": False,
        "grim_proc": False,
    }, floor_id=floor_id)

    mob.last_attack_time = time.time()

    if not ranged_accuracy_roll(game, mob, target, floor_id):
        return

    dmg = random.randint(mob.damage_min, mob.damage_max)
    dealt = ranged_dr_damage(game, mob, target, floor_id, dmg, bolt_type)

    if dealt > 0:
        proc = getattr(mob, "attack_proc", None)
        if proc:
            proc(target)
        pending_steal = getattr(mob, "pending_steal_name", "")
        if pending_steal:
            game.add_event("MESSAGE", {"text": f"The Crystal Mimic stole your {pending_steal}!", "player": target.id if hasattr(target, 'id') else ""}, floor_id=floor_id)
            mob.pending_steal_name = ""
            mob.ai_state = "fleeing"
            stolen_item = getattr(mob, "pending_stolen_item", None)
            if stolen_item is not None:
                stolen_item = stolen_item.model_copy(deep=True)
                stolen_item.id = str(uuid.uuid4())
                stolen_item.pos = Position(x=mob.pos.x, y=mob.pos.y)
                floor.items[stolen_item.id] = stolen_item
                mob.pending_stolen_item = None
        pending_tp = getattr(mob, "pending_teleport", False)
        if pending_tp:
            game._teleport_entity_to_free_cell(target, floor, floor_id)
            mob.pending_teleport = False
        pending = getattr(mob, "_pending_sound", None)
        if pending:
            game.add_event("PLAY_SOUND", {"sound": pending}, floor_id=floor_id)
            mob._pending_sound = None

    ranged_death_check(game, target, floor_id)
