import random
import time

from app.engine.entities.mobs import RedShaman, BlueShaman, PurpleShaman


class ShamanAIMixin:
    def _update_shaman(self, mob, floor, floor_id: int) -> bool:
        target = self._find_nearest_player(mob.pos, floor_id)
        if target is None:
            return False

        if mob.ai_state != "hunting":
            return False

        dist = self._get_distance(mob.pos, target.pos)
        in_los = self._is_in_los(mob.pos, target.pos, floor_id=floor_id)

        if dist == 1:
            return False

        if dist <= mob.attack_range and in_los:
            now = time.time()
            last = getattr(mob, "last_attack_time", 0)
            if now - last < 1.5:
                return False
            self._shaman_zap(mob, target, floor, floor_id)
            return True

        return False

    def _shaman_zap(self, mob, target, floor, floor_id: int):
        bolt_type = getattr(mob, "bolt_type", "shaman_purple")
        self.add_event("RANGED_ATTACK", {
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
        self.add_event("PLAY_SOUND", {"sound": "ZAP"}, floor_id=floor_id)

        mob.last_attack_time = time.time()

        acu = random.random() * mob.attack_skill
        df = random.random() * target.get_effective_defense_skill()
        if acu < df:
            self.add_event("ATTACK", {
                "source": mob.id, "target": target.id,
                "damage": 0, "surprise": False,
            }, floor_id=floor_id)
            self.add_event("MISS", {
                "source": mob.id, "target": target.id,
                "defense_verb": target.defense_verb,
            }, floor_id=floor_id)
            return

        dmg = random.randint(6, 15)
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
            if isinstance(mob, RedShaman) and random.random() < 0.5:
                target.add_buff("weakness", duration=10.0, level=1)
                self.add_event("PLAY_SOUND", {"sound": "DEBUFF"}, floor_id=floor_id)
            elif isinstance(mob, BlueShaman) and random.random() < 0.5:
                target.add_buff("vulnerable", duration=15.0, level=1)
                self.add_event("PLAY_SOUND", {"sound": "DEBUFF"}, floor_id=floor_id)
            elif isinstance(mob, PurpleShaman) and random.random() < 0.5:
                target.add_buff("hex", duration=10.0, level=1)
                self.add_event("PLAY_SOUND", {"sound": "DEBUFF"}, floor_id=floor_id)

        if not target.is_alive:
            self.add_event("DEATH", {"target": target.id}, floor_id=floor_id)
