import random

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction, Position
from app.engine.entities.mobs import Eye


_CHARGE_TICKS = 20  # ~1s at 20Hz (matches SPD 2x attackDelay feel)
_COOLDOWN_MIN = 80   # ~4s at 20Hz (SPD Random.IntRange(4, 6) turns)
_COOLDOWN_MAX = 120  # ~6s


class EyeAIMixin:
    def _update_eye(self, eye: Eye, floor, floor_id: int) -> bool:
        target = self._find_nearest_player(eye.pos, floor_id)
        if target is None:
            self._eye_cancel_charge(eye, floor_id)
            return False

        if eye.ai_state != "hunting":
            self._eye_cancel_charge(eye, floor_id)
            return False

        dist = self._get_distance(eye.pos, target.pos)
        in_los = self._is_in_los(eye.pos, target.pos, floor_id=floor_id)

        if eye.beam_charged:
            if dist <= eye.attack_range and in_los:
                eye.charge_ticks -= 1
                if eye.charge_ticks <= 0:
                    self._eye_fire_death_gaze(eye, target, floor, floor_id)
                return True
            else:
                self._eye_cancel_charge(eye, floor_id)
                return False

        if eye.beam_cooldown > 0:
            eye.beam_cooldown -= 1
            return False

        if dist <= eye.attack_range and in_los:
            eye.beam_charged = True
            eye.charge_ticks = _CHARGE_TICKS
            eye.charge_target_x = target.pos.x
            eye.charge_target_y = target.pos.y
            self.add_event("EYE_CHARGE", {
                "mob": eye.id,
                "target_x": target.pos.x,
                "target_y": target.pos.y,
            }, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "CHARGEUP"}, floor_id=floor_id)
            return True

        return False

    def _eye_cancel_charge(self, eye: Eye, floor_id: int):
        if eye.beam_charged:
            eye.beam_charged = False
            eye.charge_ticks = 0

    def _eye_fire_death_gaze(self, eye: Eye, target, floor, floor_id: int):
        eye.beam_charged = False
        eye.beam_cooldown = random.randint(_COOLDOWN_MIN, _COOLDOWN_MAX)

        tx, ty = eye.charge_target_x, eye.charge_target_y
        cells = self._rasterize_line(eye.pos.x, eye.pos.y, tx, ty)

        self.add_event("EYE_DEATH_RAY", {
            "mob": eye.id,
            "source_x": eye.pos.x,
            "source_y": eye.pos.y,
            "target_x": tx,
            "target_y": ty,
        }, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "RAY"}, floor_id=floor_id)

        destroyed = []
        for cx, cy in cells:
            if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                continue
            if floor.flags and floor.flags.flamable[cy][cx]:
                floor.grid[cy][cx] = TileType.EMBERS
                destroyed.append((cx, cy, TileType.EMBERS))

            for player in self._players_on_floor(floor_id):
                if not player.is_alive or player.is_downed:
                    continue
                if player.pos.x == cx and player.pos.y == cy:
                    dmg = random.randint(30, 50)
                    taken = player.take_damage(dmg)
                    self.add_event("ATTACK", {
                        "source": eye.id, "target": player.id,
                        "damage": taken, "surprise": False,
                    }, floor_id=floor_id)
                    if taken > 0:
                        self.add_event("DAMAGE", {
                            "target": player.id, "amount": taken,
                            "source_x": eye.pos.x, "source_y": eye.pos.y,
                            "projectile": "beam", "beam_type": "death_ray",
                        }, floor_id=floor_id)
                        self.add_event("PLAY_SOUND", {"sound": "HIT_MAGIC"}, floor_id=floor_id)
                    break

            for mob in floor.mobs.values():
                if not mob.is_alive or mob.id == eye.id:
                    continue
                if mob.pos.x != cx or mob.pos.y != cy:
                    continue
                if random.random() * eye.attack_skill > random.random() * mob.defense_skill:
                    dmg = random.randint(30, 50)
                    taken = mob.take_damage(dmg)
                    self.add_event("ATTACK", {
                        "source": eye.id, "target": mob.id,
                        "damage": taken, "surprise": False,
                    }, floor_id=floor_id)
                else:
                    self.add_event("MISS", {
                        "source": eye.id, "target": mob.id,
                        "defense_verb": mob.defense_verb,
                    }, floor_id=floor_id)
                break

        if destroyed:
            self.add_event("MAP_PATCH", {
                "tiles": [{"x": x, "y": y, "tile": t} for x, y, t in destroyed],
            }, floor_id=floor_id)

    def _rasterize_line(self, x0: int, y0: int, x1: int, y1: int):
        cells = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        cx, cy = x0, y0
        while True:
            cells.append((cx, cy))
            if cx == x1 and cy == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx
            if e2 < dx:
                err += dx
                cy += sy
        return cells
