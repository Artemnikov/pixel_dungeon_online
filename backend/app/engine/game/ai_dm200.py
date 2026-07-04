import random
import time


class DM200AIMixin:
    """DM-200 / DM-201: vents toxic gas projectile at range with cooldown."""

    def _update_dm200(self, mob, floor, floor_id: int) -> bool:
        target = self._find_nearest_player(mob.pos, floor_id)
        if target is None:
            return False

        if mob.ai_state != "hunting":
            return False

        dist = self._get_distance(mob.pos, target.pos)
        in_los = self._is_in_los(mob.pos, target.pos, floor_id=floor_id)

        if dist == 1:
            return False

        vent_cooldown = getattr(mob, "vent_cooldown", 0)
        if vent_cooldown > 0:
            mob.vent_cooldown = max(0, vent_cooldown - 1)

        if dist <= mob.attack_range and in_los and vent_cooldown <= 0:
            self._dm200_vent_gas(mob, target, floor, floor_id)
            return True

        return False

    def _dm200_vent_gas(self, mob, target, floor, floor_id: int):
        bolt_type = getattr(mob, "bolt_type", "toxic_gas")
        self.add_event("RANGED_ATTACK", {
            "source": mob.id,
            "x": mob.pos.x,
            "y": mob.pos.y,
            "target_x": target.pos.x,
            "target_y": target.pos.y,
            "projectile": bolt_type,
            "is_wand": True,
            "sound": "GAS",
            "crit": False,
            "grim_proc": False,
        }, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "GAS"}, floor_id=floor_id)

        mob.last_attack_time = time.time()
        mob.vent_cooldown = 30

        dmg = random.randint(mob.damage_min, mob.damage_max)
        dr = random.randint(target.get_dr_min(), target.get_dr_max())
        dealt = target.take_damage(max(0, dmg - dr))

        self.add_event("ATTACK", {
            "source": mob.id, "target": target.id,
            "damage": dealt, "surprise": False,
        }, floor_id=floor_id)
        self.add_event("DAMAGE", {
            "target": target.id, "amount": dealt,
            "projectile": bolt_type,
            "source_x": mob.pos.x, "source_y": mob.pos.y,
        }, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "HIT_MAGIC"}, floor_id=floor_id)

        if dealt > 0:
            target.add_buff("poison", duration=10.0, level=1, stack_mode="extend")

        if not target.is_alive:
            self.add_event("DEATH", {"target": target.id}, floor_id=floor_id)
