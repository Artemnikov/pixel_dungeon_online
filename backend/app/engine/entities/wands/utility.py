# Copyright (C) 2026 ArtemNikov
#
"""Utility wands: Corrosion, Corruption."""
from __future__ import annotations

import random as _random
from typing import ClassVar, Literal, List, Optional

from app.engine.entities.base import *  # noqa: F401,F403
from app.engine.entities.wands.base import Wand


class WandOfCorrosion(Wand):
    kind: Literal["wand_corrosion"] = "wand_corrosion"
    name: str = "Wand of Corrosion"
    type: str = "wand"
    damage: int = 0
    projectile_type: str = "corrosion"
    wand_sound: str = "GAS"
    staff_name: str = "Staff of Corrosion"
    DESC: ClassVar[str] = "A wand that spews corrosive gas."

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lvl = self.level if self.level_known else 0
        return [
            f"Creates a cloud of corrosive gas (tier {2 + lvl}).",
            f"It currently holds {self.charges} of {self.max_charges} charges.",
        ]

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        """Staff proc: apply Ooze to chars in 3×3 around target."""
        if defender is None or floor is None:
            return
        lvl = max(0, self.level)
        proc_chance = (lvl + 1) / (lvl + 3)
        if _random.random() < proc_chance:
            power_mult = max(1.0, proc_chance)
            cx, cy = defender.pos.x, defender.pos.y
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = cx + dx, cy + dy
                    if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                        continue
                    for m in floor.mobs.values():
                        if m.is_alive and m.pos.x == nx and m.pos.y == ny:
                            m.add_buff("ooze", duration=10.0 * power_mult, level=1, stack_mode="extend")
                    for p in (getattr(floor, "players", {}) or {}).values():
                        if getattr(p, "is_alive", True) and p.pos.x == nx and p.pos.y == ny:
                            p.add_buff("ooze", duration=10.0 * power_mult, level=1, stack_mode="extend")
            if add_event:
                add_event("PLAY_SOUND", {"sound": "GAS"}, floor_id=getattr(floor, "floor_id", 0))

    def handle_zap(self, ctx):
        """SPD: Blob.seed at collision pos, strength 2+lvl, volume 50+10*lvl."""
        lvl = self.buffed_lvl()
        floor = ctx.floor
        if floor is None:
            return
        cx, cy = ctx.target_x, ctx.target_y
        strength = 2 + lvl
        volume_val = 50 + 10 * lvl
        cell = (cx, cy)
        if 0 <= cx < floor.width and 0 <= cy < floor.height:
            blob_id = f"wand_corrosion_{cx}_{cy}"
            existing = floor.blob_areas.get(blob_id)
            if existing and existing.get("type") == "corrosive_gas":
                old_vol = existing.get("volume", {})
                old_vol[cell] = old_vol.get(cell, 0) + volume_val
                existing["volume"] = old_vol
                existing["cells"] = existing.get("cells", set()) | {cell}
            else:
                floor.blob_areas[blob_id] = {
                    "type": "corrosive_gas",
                    "cells": {cell},
                    "volume": {cell: volume_val},
                }
            if add_event:
                ctx.add_event("BLOB_UPDATE", {
                    "id": blob_id, "type": "corrosive_gas",
                    "cells": [(cx, cy, volume_val)],
                })
            ctx.add_event("PLAY_SOUND", {"sound": "GAS"}, floor_id=ctx.floor_id)
        # Staff proc on all chars in 3×3
        self.on_hit(ctx.attacker, ctx.target_entity, ctx.damage_dealt,
                     floor_mobs=ctx.floor_mobs, tile_x=cx, tile_y=cy,
                     floor=floor, add_event=ctx.add_event)
        if getattr(ctx.target_entity, "name", "") == "Dwarf King" and ctx.game is not None:
            ctx.game.qualified_for_boss_challenge = False
        if ctx.hit and ctx.damage_dealt > 0 and ctx.target_entity:
            ctx.add_event("DAMAGE", {
                "target": ctx.target_entity.id,
                "amount": 0,
                "projectile": "corrosion",
                "splash_count": strength,
                "source_x": ctx.attacker.pos.x,
                "source_y": ctx.attacker.pos.y,
            }, floor_id=ctx.floor_id)


class WandOfCorruption(Wand):
    kind: Literal["wand_corruption"] = "wand_corruption"
    name: str = "Wand of Corruption"
    type: str = "wand"
    damage: int = 0
    projectile_type: str = "shadow"
    wand_sound: str = "ATTACK_MAGIC"
    staff_name: str = "Staff of Corruption"
    DESC: ClassVar[str] = "A wand that corrupts the minds of enemies."

    # SPD MINOR_DEBUFFS: debuff → weight (0 = counted but not applied)
    _MINOR_DEBUFFS = {
        "weakness": 2, "vulnerable": 2, "cripple": 1, "blindness": 1, "terror": 1,
        "chill": 0, "ooze": 0, "roots": 0, "vertigo": 0, "drowsy": 0,
        "bleeding": 0, "burning": 0, "poison": 0,
    }
    # SPD MAJOR_DEBUFFS: debuff → weight
    _MAJOR_DEBUFFS = {
        "amok": 3, "slow": 2, "hex": 2, "paralysis": 1,
        "daze": 0, "dread": 0, "charm": 0, "magical_sleep": 0,
        "soul_mark": 0, "corrosion": 0, "frost": 0, "doom": 0,
    }
    _MINOR_WEAKEN = 0.25
    _MAJOR_WEAKEN = 0.5

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if defender is None:
            return
        lvl = max(0, self.level)
        proc_chance = (lvl + 1) / (lvl + 6)
        if _random.random() < proc_chance:
            power_mult = max(1.0, proc_chance)
            defender.add_buff("amok", duration=float(round((4 + lvl * 2) * power_mult)), level=1)

    def handle_zap(self, ctx):
        target = ctx.target_entity
        player = ctx.attacker
        if target is None:
            return
        from app.engine.entities.player import Mob as MobEntity
        if not isinstance(target, MobEntity):
            return
        if getattr(target, "name", "") == "Dwarf King" and ctx.game is not None:
            ctx.game.qualified_for_boss_challenge = False
        lvl = self.buffed_lvl()
        corrupting_power = 3.0 + lvl / 3.0
        # SPD: base enemy resistance from depth/exp
        floor = ctx.floor
        depth = getattr(floor, "floor_id", 1) if floor else 1
        enemy_resist = 1.0 + depth
        hp_ratio = target.hp / max(1, target.get_total_max_hp())
        enemy_resist *= (1.0 + 4.0 * hp_ratio * hp_ratio)
        # SPD: debuffs reduce resistance
        for b in target.buffs:
            if b.type in self._MAJOR_DEBUFFS:
                enemy_resist *= (1.0 - self._MAJOR_WEAKEN)
            elif b.type in self._MINOR_DEBUFFS:
                enemy_resist *= (1.0 - self._MINOR_WEAKEN)
        # SPD: cannot re-corrupt, give major debuff instead
        if target.has_buff("corruption") or target.has_buff("doom"):
            corrupting_power = enemy_resist - 0.001
        if corrupting_power > enemy_resist:
            if target.has_buff("corruption") or target.has_buff("doom"):
                self._debuff_enemy(target, self._MAJOR_DEBUFFS, lvl)
            else:
                target.faction = player.faction
                target.add_buff("corruption", duration=999.0, level=1)
                if hasattr(target, "heal"):
                    target.hp = target.get_total_max_hp()
                ctx.add_event("PLAY_SOUND", {"sound": "CURSE"}, floor_id=ctx.floor_id)
        else:
            debuff_chance = corrupting_power / enemy_resist
            if _random.random() < debuff_chance:
                self._debuff_enemy(target, self._MAJOR_DEBUFFS, lvl)
            else:
                self._debuff_enemy(target, self._MINOR_DEBUFFS, lvl)

    def _debuff_enemy(self, target, category: dict, lvl: int):
        """SPD debuffEnemy: weighted random from category, skip already-applied."""
        candidates = {}
        for debuff, weight in category.items():
            if weight <= 0:
                continue
            if target.has_buff(debuff):
                continue
            candidates[debuff] = weight
        if not candidates:
            # SPD: if no debuff can be applied, go up one tier
            if category is self._MINOR_DEBUFFS:
                self._debuff_enemy(target, self._MAJOR_DEBUFFS, lvl)
            else:
                if not target.has_buff("corruption") and not target.has_buff("doom"):
                    target.add_buff("doom", duration=999.0, level=1)
            return
        chosen = _random.choices(list(candidates.keys()), weights=list(candidates.values()), k=1)[0]
        target.add_buff(chosen, duration=6.0 + 3 * lvl, level=1)
