import random
import time


"""NewbornFireElemental (Wandmaker quest, Ceremonial Candle variant):
a cooldown-gated ranged fire bolt, dealing damage directly on hit and
applying `burning`. Java's version is a 2-turn "aim then fire" telegraph
(predictive targeting a cell ahead of the target's movement, dodgeable
by moving out of the way before the second turn); this substitutes a
same-turn hit-scan bolt, matching the existing DM-200/DM-201 vent-gas
pattern already in this engine (ai_dm200.py) rather than adding new
multi-turn-commit AI infrastructure just for this one mob."""


def _update_newborn_elemental(game, mob, floor, floor_id: int) -> bool:
    target = game._find_nearest_player(mob.pos, floor_id)
    if target is None:
        return False

    if mob.ai_state != "hunting":
        return False

    dist = game._get_distance(mob.pos, target.pos)
    in_los = game._is_in_los(mob.pos, target.pos, floor_id=floor_id)

    if dist == 1:
        return False

    cooldown = getattr(mob, "ranged_cooldown", 0)
    if cooldown > 0:
        mob.ranged_cooldown = max(0, cooldown - 1)

    if dist <= mob.attack_range and in_los and cooldown <= 0:
        _newborn_elemental_fire_bolt(game, mob, target, floor_id)
        return True

    return False


def _newborn_elemental_fire_bolt(game, mob, target, floor_id: int):
    game.add_event("RANGED_ATTACK", {
        "source": mob.id,
        "x": mob.pos.x,
        "y": mob.pos.y,
        "target_x": target.pos.x,
        "target_y": target.pos.y,
        "projectile": "fire_bolt",
        "is_wand": True,
        "sound": "BLAST",
        "crit": False,
        "grim_proc": False,
    }, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)

    mob.last_attack_time = time.time()
    mob.ranged_cooldown = 40

    dmg = random.randint(mob.damage_min, mob.damage_max)
    dr = random.randint(target.get_dr_min(), target.get_dr_max())
    dealt = target.take_damage(max(0, dmg - dr))

    game.add_event("ATTACK", {
        "source": mob.id, "target": target.id,
        "damage": dealt, "surprise": False,
    }, floor_id=floor_id)
    game.add_event("DAMAGE", {
        "target": target.id, "amount": dealt,
        "projectile": "fire_bolt",
        "source_x": mob.pos.x, "source_y": mob.pos.y,
    }, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "HIT_MAGIC"}, floor_id=floor_id)

    if dealt > 0:
        target.add_buff("burning", duration=4.0, level=1, stack_mode="extend")

    if not target.is_alive:
        game.add_event("DEATH", {"target": target.id}, floor_id=floor_id)
