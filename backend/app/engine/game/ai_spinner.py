import time


"""Spinner: shoots web (cripple) when hunting, poisons on melee, flees after poison."""


def _update_spinner(game, mob, floor, floor_id: int) -> bool:
    target = game._find_nearest_player(mob.pos, floor_id)
    if target is None:
        return False

    if mob.ai_state != "hunting":
        return False

    dist = game._get_distance(mob.pos, target.pos)
    in_los = game._is_in_los(mob.pos, target.pos, floor_id=floor_id)

    if dist == 1:
        return False

    web_cooldown = getattr(mob, "web_cooldown", 0)
    if web_cooldown > 0:
        mob.web_cooldown = max(0, web_cooldown - 1)

    if dist <= mob.attack_range and in_los and web_cooldown <= 0:
        _spinner_shoot_web(game, mob, target, floor, floor_id)
        return True

    return False


def _spinner_shoot_web(game, mob, target, floor, floor_id: int):
    bolt_type = getattr(mob, "bolt_type", "magic_missile")
    game.add_event("RANGED_ATTACK", {
        "source": mob.id,
        "x": mob.pos.x,
        "y": mob.pos.y,
        "target_x": target.pos.x,
        "target_y": target.pos.y,
        "projectile": bolt_type,
        "is_wand": True,
        "sound": "MISS",
        "crit": False,
        "grim_proc": False,
    }, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "MISS"}, floor_id=floor_id)

    mob.last_attack_time = time.time()
    mob.web_cooldown = 10

    target.add_buff("cripple", duration=5.0, level=1)
