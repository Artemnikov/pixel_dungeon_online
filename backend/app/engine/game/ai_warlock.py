import random
import time
import uuid

from app.engine.entities.base import Position
from app.engine.entities.mobs import Warlock


class WarlockAIMixin:
    def _update_warlock(self, mob: Warlock, floor, floor_id: int) -> bool:
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
            self._warlock_zap(mob, target, floor, floor_id)
            return True

        return False

    def _warlock_zap(self, mob, target, floor, floor_id: int):
        bolt_type = getattr(mob, "bolt_type", "shadow")
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
            proc = getattr(mob, "attack_proc", None)
            if proc:
                proc(target)
            pending_steal = getattr(mob, "pending_steal_name", "")
            if pending_steal:
                self.add_event("MESSAGE", {"text": f"The Crystal Mimic stole your {pending_steal}!", "player": target.id if hasattr(target, 'id') else ""}, floor_id=floor_id)
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
                self._teleport_entity_to_free_cell(target, floor, floor_id)
                mob.pending_teleport = False
            pending = getattr(mob, "_pending_sound", None)
            if pending:
                self.add_event("PLAY_SOUND", {"sound": pending}, floor_id=floor_id)
                mob._pending_sound = None

        if not target.is_alive:
            self.add_event("DEATH", {"target": target.id}, floor_id=floor_id)
