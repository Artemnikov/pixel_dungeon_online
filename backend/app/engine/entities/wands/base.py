# Copyright (C) 2026 ArtemNikov
#
"""Wand base classes: ZapContext, Wand, DamageWand (SPD Wand.java / DamageWand.java)."""
from __future__ import annotations

from typing import ClassVar, List, Optional

from app.engine.entities.base import *  # noqa: F401,F403
from app.engine.entities.base import _charm_value


class ZapContext:
    """Data passed to a wand's handle_zap after a ranged zap fires.

    Carries everything the wand-specific effect needs: the attacker, target
    cell, floor state, event emitter, and the result of the generic combat
    resolution (damage/hit/miss).
    """
    __slots__ = (
        "attacker", "target_x", "target_y", "target_entity",
        "damage_dealt", "hit", "crit", "missed",
        "floor", "floor_id", "floor_mobs", "floor_players",
        "add_event", "game",
    )

    def __init__(self, attacker, target_x, target_y, target_entity,
                 damage_dealt, hit, crit, missed,
                 floor, floor_id, floor_mobs, floor_players,
                 add_event, game=None):
        self.attacker = attacker
        self.target_x = target_x
        self.target_y = target_y
        self.target_entity = target_entity
        self.damage_dealt = damage_dealt
        self.hit = hit
        self.crit = crit
        self.missed = missed
        self.floor = floor
        self.floor_id = floor_id
        self.floor_mobs = floor_mobs
        self.floor_players = floor_players
        self.add_event = add_event
        self.game = game


def knockback_char(floor, char, dx, dy, power, damage_on_collision=True,
                   add_event=None, floor_id=0):
    """SPD throwChar (WandOfBlastWave): slides char up to `power` tiles along
    (dx, dy). Bosses half power; IMMOVABLE / rooted skipped. If blocked by
    wall/char, takes collision damage rand(finalDist, 2*finalDist) +
    Paralysis 1+finalDist/2.  Returns (landing_x, landing_y)."""
    import random as _rnd
    if power <= 0 or (dx == 0 and dy == 0):
        return char.pos.x, char.pos.y
    props = getattr(char, "properties", None) or []
    if "IMMOVABLE" in props:
        return char.pos.x, char.pos.y
    if char.has_buff("rooted"):
        return char.pos.x, char.pos.y
    if getattr(char, "type", None) == EntityType.BOSS:
        power = (power + 1) // 2
    if power <= 0:
        return char.pos.x, char.pos.y
    dx = (dx > 0) - (dx < 0)
    dy = (dy > 0) - (dy < 0)

    def _occupied(x, y):
        for m in floor.mobs.values():
            if m.is_alive and m.id != char.id and m.pos.x == x and m.pos.y == y:
                return True
        for p in getattr(floor, "players", {}).values() if hasattr(floor, "players") else []:
            if getattr(p, "is_alive", True) and p.id != char.id and p.pos.x == x and p.pos.y == y:
                return True
        return False

    def _slide(sx, sy, sdx, sdy, sp):
        scx, scy = sx, sy
        sdist = 0
        sblocked = False
        for _ in range(sp):
            snx, sny = scx + sdx, scy + sdy
            if not (0 <= snx < floor.width and 0 <= sny < floor.height):
                sblocked = True
                break
            if not floor.flags or not floor.flags.passable[sny][snx] or _occupied(snx, sny):
                sblocked = True
                break
            scx, scy = snx, sny
            sdist += 1
        return scx, scy, sdist, sblocked

    cx, cy = char.pos.x, char.pos.y
    cx, cy, dist, blocked = _slide(cx, cy, dx, dy, power)
    # SPD Blast Wave: if immediately blocked (hugging wall), reverse direction.
    if blocked and dist == 0:
        cx, cy, dist, blocked = _slide(cx, cy, -dx, -dy, power)
    if (cx, cy) != (char.pos.x, char.pos.y):
        char.pos = Position(x=cx, y=cy)
        from app.engine.entities.buffs import break_stationary_plant_buffs
        break_stationary_plant_buffs(char)
        from app.engine.game.terrain_effects import press_cell
        press_cell(floor, (cx, cy), char)
        if add_event:
            add_event("PUSH", {"target": char.id, "x": cx, "y": cy}, floor_id=floor_id)
    if blocked and damage_on_collision and dist > 0:
        coll_dmg = _rnd.randint(dist, 2 * dist)
        if coll_dmg > 0:
            char.take_damage(coll_dmg)
        char.add_buff("paralysis", duration=1.0 + dist / 2.0, level=1)
    if blocked:
        char.add_buff("stagger", duration=2.0, level=1)
    return cx, cy


class Wand(ItemBase):
    kind: Literal["wand"] = "wand"
    type: str = "wand"
    category: ClassVar[str] = ItemCategory.WAND
    damage: int = 0
    charges: int = 2
    max_charges: int = 2
    range: int = 4
    projectile_type: str = "magic_bolt"
    beam_type: Optional[str] = None
    wand_sound: Optional[str] = None
    partial_charge: float = 0.0
    staff_name: str = "Staff"
    recharge_scale: float = 1.0
    DESC: ClassVar[str] = "A wand of magical power. Zap an enemy to spend a charge; charges recover over time."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.ZAP] + super().actions(player)

    def default_action(self) -> Optional[str]:
        return Action.ZAP

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        if hasattr(self, "min") and hasattr(self, "max"):
            lvl = self.level if self.level_known else 0
            lines = [f"Deals {self.min(lvl)}-{self.max(lvl)} damage per hit."]
        else:
            lines = [f"Deals {self.damage} damage per hit."]
        lines.append(f"It currently holds {self.charges} of {self.max_charges} charges.")
        return lines

    def value(self, identified: bool = False) -> int:
        return _charm_value(self.level, self.level_known, self.cursed, self.cursed_known)

    def initial_charges(self) -> int:
        return 2

    def update_max_charges(self):
        """SPD Wand.updateLevel(): maxCharges = min(initial + level, 10)."""
        self.max_charges = min(self.initial_charges() + self.level, 10)
        self.charges = min(self.charges, self.max_charges)

    def upgrade(self):
        """SPD Wand.upgrade(): level+1, recalculate maxCharges, +1 charge."""
        self.level += 1
        self.update_max_charges()
        self.charges = min(self.charges + 1, self.max_charges)
        return self

    def buffed_lvl(self) -> int:
        # Transient _empower_bonus (set by the engine during a ScrollEmpower
        # empowered zap, SPD Wand.java:400-402) raises the effective level.
        return max(0, self.level) + getattr(self, "_empower_bonus", 0)

    def get_reach(self) -> int:
        return self.range

    def gain_charge(self, amt: float, overcharge: bool = False):
        self.partial_charge += amt
        while self.partial_charge >= 1.0:
            if overcharge:
                self.charges = min(self.max_charges + int(amt), self.charges + 1)
            else:
                self.charges = min(self.max_charges, self.charges + 1)
            self.partial_charge -= 1.0

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        pass

    def charges_per_cast(self) -> int:
        """Number of charges consumed per zap (override for Fireblast/Regrowth)."""
        return 1

    def handle_zap(self, ctx: ZapContext):
        """Post-damage effects after a ranged zap lands.

        Called by the engine after generic damage is resolved. Subclasses
        override this to implement wand-specific effects (gas clouds, chains,
        summons, terrain changes, etc.).
        """
        pass


class DamageWand(Wand):
    """Base for wands that deal direct damage to a target.

    Subclasses define *min(lvl)* and *max(lvl)*; *damage_roll(lvl)* returns a
    random integer in that range.
    """

    kind: Literal["damage_wand"] = "damage_wand"

    def min(self, lvl: int) -> int:
        raise NotImplementedError

    def max(self, lvl: int) -> int:
        raise NotImplementedError

    def min_damage(self) -> int:
        return self.min(self.buffed_lvl())

    def max_damage(self) -> int:
        return self.max(self.buffed_lvl())

    def damage_roll(self, lvl: int) -> int:
        from app.engine.entities.base import _random
        return _random.randint(self.min(lvl), self.max(lvl))

    def damage_roll_buffed(self, lvl_bonus: int = 0) -> int:
        return self.damage_roll(self.buffed_lvl() + lvl_bonus)

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lvl = self.level if self.level_known else 0
        lines = [f"Deals {self.min(lvl)}-{self.max(lvl)} damage per hit."]
        lines.append(f"It currently holds {self.charges} of {self.max_charges} charges.")
        return lines
