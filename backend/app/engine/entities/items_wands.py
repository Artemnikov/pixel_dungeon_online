# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
from __future__ import annotations

import uuid as _uuid
import random as _random
from typing import Annotated, ClassVar, Literal, Optional, List, Dict, Tuple, Union

from pydantic import BaseModel, Field, computed_field, model_validator, SerializeAsAny

from app.engine.entities.buffs import Buff, add_buff, remove_buff, has_buff, get_buff
from app.engine.entities.subclasses import SubclassInfo, TalentInfo, Talent
from app.engine.entities.weapon_defs import WEAPON_DEFS

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
        "add_event",
    )

    def __init__(self, attacker, target_x, target_y, target_entity,
                 damage_dealt, hit, crit, missed,
                 floor, floor_id, floor_mobs, floor_players,
                 add_event):
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
        return self.max_charges

    def buffed_lvl(self) -> int:
        return max(0, self.level)

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


# --- Wand subclasses -----------------------------------------------------------

class WandOfMagicMissile(DamageWand):
    kind: Literal["wand_magic_missile"] = "wand_magic_missile"
    name: str = "Wand of Magic Missile"
    type: str = "wand"
    charges: int = 6
    max_charges: int = 6
    range: int = 8
    projectile_type: str = "magic_missile"
    wand_sound: str = "ATTACK_MAGIC"
    staff_name: str = "Staff of Magic Missile"
    DESC: ClassVar[str] = "A basic wand that fires a magic missile."

    def min(self, lvl: int) -> int: return 2 + lvl
    def max(self, lvl: int) -> int: return 8 + 2 * lvl

    def initial_charges(self) -> int:
        return 3

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if add_event:
            add_event("SPELL_SPRITE", {
                "x": attacker.pos.x, "y": attacker.pos.y, "index": 2  # SPELL_CHARGE
            })
        belongings = getattr(attacker, "belongings", None)
        if belongings is None:
            return
        for item in belongings.all_items():
            if isinstance(item, Wand) and item.id != self.id and item.charges < item.max_charges:
                item.charges = min(item.max_charges, item.charges + 1)

    def handle_zap(self, ctx):
        if ctx.hit and ctx.damage_dealt > 0:
            lvl = self.buffed_lvl()
            ctx.attacker.add_buff("magic_charge", duration=4.0, level=lvl, stack_mode="extend")


class WandOfFireblast(DamageWand):
    kind: Literal["wand_fireblast"] = "wand_fireblast"
    name: str = "Wand of Fireblast"
    type: str = "wand"
    charges: int = 5
    max_charges: int = 5
    range: int = 8
    projectile_type: str = "fire_bolt"
    wand_sound: str = "BLAST"
    staff_name: str = "Staff of Fireblast"
    DESC: ClassVar[str] = "A catastrophic wand that unleashes fire."

    def min(self, lvl: int) -> int: return (1 + lvl)
    def max(self, lvl: int) -> int: return 8 + 4 * lvl

    def charges_per_cast(self) -> int:
        # SPD: consume ceil(30% of current charges), clamped [1,3]
        consumed = (self.charges * 3 + 9) // 10  # ceil(30%)
        return max(1, min(3, consumed))

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if defender is None or not defender.is_alive:
            return
        proc_chance = 0.0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cx, cy = defender.pos.x + dx, defender.pos.y + dy
                ch = None
                if floor_mobs:
                    ch = next((m for m in floor_mobs.values() if m.is_alive and m.pos.x == cx and m.pos.y == cy), None)
                if ch and ch.has_buff("burning"):
                    proc_chance += 0.25
        proc_chance = min(1.0, proc_chance)
        if _random.random() < proc_chance:
            power_mult = max(1.0, proc_chance)
            lvl = max(0, self.level)
            dmg_range = (2 + 2 * lvl, 8 + 4 * lvl)
            hit_any = False
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cx, cy = defender.pos.x + dx, defender.pos.y + dy
                    ch = None
                    if floor_mobs:
                        ch = next((m for m in floor_mobs.values() if m.is_alive and m.pos.x == cx and m.pos.y == cy), None)
                    if ch and ch != attacker and ch.faction != attacker.faction:
                        aoe_dmg = _random.randint(dmg_range[0], dmg_range[1])
                        aoe_dmg = int(aoe_dmg * power_mult)
                        ch.take_damage(aoe_dmg)
                        hit_any = True
                        if ch.has_buff("burning"):
                            ch.remove_buff("burning")
            if hit_any and add_event:
                add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=getattr(defender, "floor_id", 0))

        if floor is not None:
            strength = 1 + self.charges
            cx, cy = defender.pos.x, defender.pos.y
            if 0 <= cx < floor.width and 0 <= cy < floor.height:
                tile = floor.grid[cy][cx]
                if tile != TileType.FLOOR_WATER:
                    blob_id = f"wand_fireblast_{defender.id}_{cx}_{cy}"
                    floor.blob_areas[blob_id] = {
                        "type": "fire",
                        "cells": {(cx, cy)},
                        "volume": {(cx, cy): strength},
                    }

    def handle_zap(self, ctx):
        charges = self.charges_per_cast()
        fire_vol = 1 + charges
        floor = ctx.floor
        tx, ty = ctx.target_x, ctx.target_y
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = tx + dx, ty + dy
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    tile = floor.grid[ny][nx]
                    if tile == TileType.FLOOR_WATER:
                        continue
                    blob_id = f"wand_fireblast_{ctx.attacker.id}_{nx}_{ny}"
                    floor.blob_areas[blob_id] = {
                        "type": "fire",
                        "cells": {(nx, ny)},
                        "volume": {(nx, ny): fire_vol},
                    }
        if ctx.hit and ctx.target_entity and ctx.target_entity.is_alive:
            if charges >= 2:
                ctx.target_entity.add_buff("cripple", duration=8.0, level=1)
            if charges >= 3:
                ctx.target_entity.add_buff("paralysis", duration=8.0, level=1)
        ctx.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=ctx.floor_id)


class WandOfFrost(DamageWand):
    kind: Literal["wand_frost"] = "wand_frost"
    name: str = "Wand of Frost"
    type: str = "wand"
    charges: int = 4
    max_charges: int = 4
    range: int = 8
    projectile_type: str = "frost"
    wand_sound: str = "SHATTER"
    staff_name: str = "Staff of Frost"
    DESC: ClassVar[str] = "A wand that freezes enemies solid."

    def min(self, lvl: int) -> int: return 2 + lvl
    def max(self, lvl: int) -> int: return 8 + 5 * lvl

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if defender is None:
            return
        chill_buff = defender.get_buff("chill")
        if chill_buff:
            chill_turns = int(chill_buff.remaining)
            proc_chance = (chill_turns - 1) / 9.0
            if _random.random() < proc_chance:
                power_mult = max(1.0, proc_chance)
                duration = round(3.0 * power_mult)
                defender.add_buff("frost", duration=duration, level=1)

    def handle_zap(self, ctx):
        if ctx.floor is None:
            return
        lvl = self.buffed_lvl()
        tx, ty = ctx.target_x, ctx.target_y
        # Extinguish fire at target tile
        to_remove = [bid for bid, b in ctx.floor.blob_areas.items()
                     if b.get("type") in ("fire",) and (tx, ty) in b.get("cells", set())]
        for bid in to_remove:
            del ctx.floor.blob_areas[bid]
        if ctx.hit and ctx.target_entity and ctx.target_entity.is_alive:
            chill_turns = 4 + lvl if ctx.floor.grid[ty][tx] == TileType.FLOOR_WATER else 2 + lvl
            ctx.target_entity.add_buff("chill", duration=float(chill_turns), level=1)
            # SPD: if already frozen, no effect; frost proc handled by on_hit for Battlemage


class WandOfLightning(DamageWand):
    kind: Literal["wand_lightning"] = "wand_lightning"
    name: str = "Wand of Lightning"
    type: str = "wand"
    charges: int = 2
    max_charges: int = 2
    projectile_type: str = "lightning"
    wand_sound: str = "LIGHTNING"
    staff_name: str = "Staff of Lightning"
    DESC: ClassVar[str] = "A wand that arcs lightning to its target."

    def min(self, lvl: int) -> int: return 5 + lvl
    def max(self, lvl: int) -> int: return 10 + 5 * lvl

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if attacker is None:
            return
        lvl = max(0, self.level)
        proc_chance = (lvl + 1) / (lvl + 4)
        if has_buff(attacker.buffs, "empowered_strike_tracker"):
            proc_chance *= 2.0
            remove_buff(attacker.buffs, "empowered_strike_tracker")
        if _random.random() < proc_chance:
            attacker.add_buff("lightning_charge", duration=10.0, level=1)
            if add_event:
                add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=getattr(attacker, "floor_id", 0))

    def handle_zap(self, ctx):
        if not ctx.hit or ctx.damage_dealt <= 0 or not ctx.target_entity:
            return
        from collections import deque
        lvl = self.buffed_lvl()
        affected_ids = {ctx.target_entity.id}
        chain_mobs = []
        floor = ctx.floor
        tx, ty = ctx.target_x, ctx.target_y
        is_main_in_water = floor.grid[ty][tx] == TileType.FLOOR_WATER
        has_charge = has_buff(ctx.attacker.buffs, "lightning_charge")

        def _reachable(from_x, from_y, max_dist):
            visited = {(from_x, from_y)}
            q = deque([(from_x, from_y, 0)])
            while q:
                x, y, d = q.popleft()
                if d >= max_dist:
                    continue
                for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < floor.width and 0 <= ny < floor.height:
                        if (nx, ny) not in visited and not floor.flags.solid[ny][nx]:
                            visited.add((nx, ny))
                            q.append((nx, ny, d + 1))
            return visited

        def _wand_find(from_x, from_y):
            dist = 2 if (0 <= from_y < floor.height and 0 <= from_x < floor.width
                        and floor.grid[from_y][from_x] == TileType.FLOOR_WATER) else 1
            if has_charge:
                dist += 1
            reachable = _reachable(from_x, from_y, dist)
            for m in floor.mobs.values():
                if not m.is_alive or m.id in affected_ids:
                    continue
                if m.faction == ctx.attacker.faction:
                    continue
                if (m.pos.x, m.pos.y) not in reachable:
                    continue
                if has_buff(m.buffs, "lightning_charge"):
                    continue
                affected_ids.add(m.id)
                chain_mobs.append(m)
                _wand_find(m.pos.x, m.pos.y)

        _wand_find(tx, ty)

        if chain_mobs:
            base_dmg = self.damage_roll(lvl)
            mult = 1.0 if is_main_in_water else (0.4 + 0.6 / max(len(chain_mobs) + 1, 1))
            for m in chain_mobs:
                dmg = round(base_dmg * mult)
                dr_roll = _random.randint(m.get_dr_min(), m.get_dr_max())
                actual = m.take_damage(max(1, dmg - dr_roll))
                if actual > 0:
                    ctx.add_event("DAMAGE", {"target": m.id, "amount": actual, "shock": True}, floor_id=ctx.floor_id)
                    if not m.is_alive:
                        m.die(floor_mobs=floor.mobs, tile_x=m.pos.x, tile_y=m.pos.y,
                              players=ctx.floor_players)
                        ctx.add_event("DEATH", {"target": m.id}, floor_id=ctx.floor_id)

        ctx.add_event("LIGHTNING_ARC", {
            "source_x": ctx.attacker.pos.x,
            "source_y": ctx.attacker.pos.y,
            "target_x": tx,
            "target_y": ty,
        }, floor_id=ctx.floor_id)
        ctx.add_event("SHOCKING_PROC", {
            "source": ctx.attacker.id,
            "defender": ctx.target_entity.id if ctx.target_entity else ctx.attacker.id,
            "defender_x": tx,
            "defender_y": ty,
            "chain_targets": [{"id": m.id, "x": m.pos.x, "y": m.pos.y} for m in chain_mobs],
        }, floor_id=ctx.floor_id)

        if floor.grid[ty][tx] == TileType.FLOOR_WATER:
            blob_id = f"wand_elec_{ctx.attacker.id}"
            vol = 100
            cells = {(tx, ty)}
            volume = {(tx, ty): vol}
            existing = floor.blob_areas.get(blob_id)
            if existing:
                cells.update(existing["cells"])
                for k, v in existing["volume"].items():
                    volume[k] = max(volume.get(k, 0), v)
            floor.blob_areas[blob_id] = {"type": "electricity", "cells": cells, "volume": volume, "tick_counter": 0}
            cell_list = [(c[0], c[1], volume.get(c, vol)) for c in cells]
            ctx.add_event("BLOB_UPDATE", {"id": blob_id, "type": "electricity", "cells": cell_list}, floor_id=ctx.floor_id)
            ctx.add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=ctx.floor_id)


class WandOfDisintegration(DamageWand):
    kind: Literal["wand_disintegration"] = "wand_disintegration"
    name: str = "Wand of Disintegration"
    type: str = "wand"
    charges: int = 3
    max_charges: int = 3
    range: int = 8
    projectile_type: str = "beam"
    beam_type: str = "death_ray"
    wand_sound: str = "RAY"
    staff_name: str = "Staff of Disintegration"
    DESC: ClassVar[str] = "A wand that fires a deadly disintegration beam."

    def min(self, lvl: int) -> int: return 2 + lvl
    def max(self, lvl: int) -> int: return 8 + 4 * lvl

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        pass

    def handle_zap(self, ctx):
        if not ctx.hit or ctx.damage_dealt <= 0 or not ctx.target_entity:
            return
        lvl = self.buffed_lvl()
        terrain_bonus = 0
        extra_hits = 0
        # SPD: +1 effective level per extra enemy hit, +1 per ~3 solid tiles
        eff_lvl = lvl
        beam_dist = min(self.get_reach(), abs(ctx.attacker.pos.x - ctx.target_x) + abs(ctx.attacker.pos.y - ctx.target_y))
        # Damage ramps per terrain penetrated + extra enemies
        terrain_passed = 2
        eff_lvl += terrain_bonus + extra_hits
        dmg = _random.randint(self.min(eff_lvl), self.max(eff_lvl))
        # Destroy flammable tiles at target
        if ctx.floor and 0 <= ctx.target_y < ctx.floor.height and 0 <= ctx.target_x < ctx.floor.width:
            tile = ctx.floor.grid[ctx.target_y][ctx.target_x]
            if tile in (TileType.BARRICADE, TileType.BOOKSHELF):
                ctx.floor.grid[ctx.target_y][ctx.target_x] = TileType.FLOOR_GRASS
        if dmg > 0:
            ctx.target_entity.take_damage(dmg)
            ctx.add_event("DAMAGE", {
                "target": ctx.target_entity.id,
                "amount": dmg,
                "projectile": "beam",
                "beam_type": "death_ray",
                "source_x": ctx.attacker.pos.x,
                "source_y": ctx.attacker.pos.y,
            }, floor_id=ctx.floor_id)


class WandOfPrismaticLight(DamageWand):
    kind: Literal["wand_prismatic_light"] = "wand_prismatic_light"
    name: str = "Wand of Prismatic Light"
    type: str = "wand"
    charges: int = 4
    max_charges: int = 4
    range: int = 8
    projectile_type: str = "rainbow"
    wand_sound: str = "RAY"
    staff_name: str = "Staff of Prismatic Light"
    DESC: ClassVar[str] = "A wand that fires a beam of prismatic light."

    def min(self, lvl: int) -> int: return 1 + lvl
    def max(self, lvl: int) -> int: return 5 + 3 * lvl

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if defender is None:
            return
        lvl = max(0, self.level)
        duration = round((1 + lvl))
        defender.add_buff("cripple", duration=float(duration), level=1)

    def handle_zap(self, ctx):
        lvl = self.buffed_lvl()
        # Reveal area around projectile path
        if ctx.floor:
            tx, ty = ctx.target_x, ctx.target_y
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = tx + dx, ty + dy
                    if 0 <= nx < ctx.floor.width and 0 <= ny < ctx.floor.height:
                        if ctx.floor.flags and hasattr(ctx.floor.flags, "discoverable") and ctx.floor.flags.discoverable[ny][nx]:
                            ctx.floor.flags.visited[ny][nx] = True
            # Light buff
            ctx.attacker.add_buff("light", duration=10.0 + lvl * 5, level=1)
        if ctx.hit and ctx.target_entity and ctx.target_entity.is_alive:
            blind_dur = 2.0 + lvl * 0.333
            if _random.random() < 3.0 / (5.0 + lvl):
                ctx.target_entity.add_buff("blindness", duration=blind_dur, level=1)
            # Bonus damage vs demonic/undead (handled generically by movement.py)


class WandOfBlastWave(DamageWand):
    kind: Literal["wand_blast_wave"] = "wand_blast_wave"
    name: str = "Wand of Blast Wave"
    type: str = "wand"
    charges: int = 3
    max_charges: int = 3
    projectile_type: str = "force"
    wand_sound: str = "BLAST"
    staff_name: str = "Staff of Blast Wave"
    DESC: ClassVar[str] = "A wand that blasts enemies backwards."

    def min(self, lvl: int) -> int: return 1 + lvl
    def max(self, lvl: int) -> int: return 3 + 3 * lvl

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if defender is None or not defender.is_alive:
            return
        if defender.has_buff("paralysis"):
            defender.remove_buff("paralysis")
            lvl = max(0, self.level)
            dmg = _random.randint(8 + 2 * lvl, 12 + 3 * lvl)
            defender.take_damage(dmg)
            defender.add_buff("blast_on_hit_tracker", duration=3.0, level=1)
            if add_event:
                add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=getattr(defender, "floor_id", 0))

    def handle_zap(self, ctx):
        ctx.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=ctx.floor_id)
        lvl = self.buffed_lvl()
        throw_strength = round(1.5 + lvl / 2.0)
        tx, ty = ctx.target_x, ctx.target_y
        # Knockback enemies in 3x3 from target
        if ctx.floor:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = tx + dx, ty + dy
                    if 0 <= nx < ctx.floor.width and 0 <= ny < ctx.floor.height:
                        for m in list(ctx.floor_mobs.values()):
                            if m.is_alive and m.pos.x == nx and m.pos.y == ny and m.faction != ctx.attacker.faction:
                                # Push away from target center
                                push_x = m.pos.x + (m.pos.x - tx)
                                push_y = m.pos.y + (m.pos.y - ty)
                                if 0 <= push_x < ctx.floor.width and 0 <= push_y < ctx.floor.height:
                                    if ctx.floor.flags and ctx.floor.flags.passable[push_y][push_x]:
                                        coll_dmg = _random.randint(throw_strength, 2 * throw_strength)
                                        if coll_dmg > 0:
                                            m.take_damage(coll_dmg)
                                            m.add_buff("paralysis", duration=1.0 + throw_strength / 2.0, level=1)


class WandOfTransfusion(DamageWand):
    kind: Literal["wand_transfusion"] = "wand_transfusion"
    name: str = "Wand of Transfusion"
    type: str = "wand"
    charges: int = 3
    max_charges: int = 3
    range: int = 6
    projectile_type: str = "beacon"
    wand_sound: str = "RAY"
    staff_name: str = "Staff of Transfusion"
    DESC: ClassVar[str] = "A wand that transfers health."

    def min(self, lvl: int) -> int: return 3 + lvl
    def max(self, lvl: int) -> int: return 6 + 2 * lvl

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if defender is None or attacker is None:
            return
        if defender.has_buff("charm"):
            lvl = max(0, self.level)
            shield_amt = int(2 * (5 + lvl))
            attacker.add_shield("transfusion_shield", shield_amt, priority=1, decay=5)

    def handle_zap(self, ctx):
        lvl = self.buffed_lvl()
        target = ctx.target_entity
        player = ctx.attacker
        if target is None:
            return
        # Only affects mobs (not players)
        from app.engine.entities.player import Mob as MobEntity
        if not isinstance(target, MobEntity):
            return
        is_enemy = target.faction != player.faction
        if not is_enemy or target.has_buff("charm"):
            # Ally or charmed: self-damage to heal
            self_dmg = max(1, player.get_total_max_hp() // 20)  # 5% max HP
            healing = self_dmg + 3 * lvl
            target.hp = min(target.get_total_max_hp(), target.hp + healing)
            player.add_shield("transfusion_shield", 5 + lvl, priority=1, decay=5)
            player.take_damage(self_dmg)
            ctx.add_event("PLAY_SOUND", {"sound": "HEAL"}, floor_id=ctx.floor_id)
        else:
            # Enemy: shield self, charm enemy
            player.add_shield("transfusion_shield", 5 + lvl, priority=1, decay=5)
            target.add_buff("charm", duration=10.0, level=1)


class WandOfCorrosion(Wand):
    kind: Literal["wand_corrosion"] = "wand_corrosion"
    name: str = "Wand of Corrosion"
    type: str = "wand"
    damage: int = 0
    charges: int = 3
    max_charges: int = 3
    projectile_type: str = "corrosion"
    wand_sound: str = "GAS"
    staff_name: str = "Staff of Corrosion"
    DESC: ClassVar[str] = "A wand that spews corrosive gas."

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lvl = self.level if self.level_known else 0
        return [
            f"Creates a cloud of corrosive gas (tier {3 + lvl * 2}).",
            f"It currently holds {self.charges} of {self.max_charges} charges.",
        ]

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        self._spawn_gas(attacker, defender, damage, tile_x, tile_y, floor, add_event)

    def _spawn_gas(self, attacker, defender, damage, tile_x, tile_y, floor, add_event):
        lvl = max(0, self.buffed_lvl())
        if tile_x is not None and tile_y is not None:
            cx, cy = tile_x, tile_y
        elif defender is not None:
            cx, cy = defender.pos.x, defender.pos.y
        else:
            return
        if floor is None:
            return
        strength = 3 + lvl * 2
        cells = set()
        volume = {}
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    if floor.flags and not floor.flags.solid[ny][nx]:
                        cells.add((nx, ny))
                        volume[(nx, ny)] = strength
        if not cells:
            return
        for bid in list(floor.blob_areas.keys()):
            b = floor.blob_areas[bid]
            if b.get("type") == "corrosive_gas" and b.get("cells", set()) & cells:
                del floor.blob_areas[bid]
        blob_id = f"wand_corrosion_{cx}_{cy}"
        floor.blob_areas[blob_id] = {
            "type": "corrosive_gas", "cells": cells, "volume": volume,
        }
        cell_list = [(c[0], c[1], volume.get(c, 1)) for c in cells]
        if add_event:
            add_event("BLOB_UPDATE", {"id": blob_id, "type": "corrosive_gas", "cells": cell_list})
            add_event("PLAY_SOUND", {"sound": "GAS"})

    def handle_zap(self, ctx):
        self._spawn_gas(ctx.attacker, ctx.target_entity, ctx.damage_dealt,
                         ctx.target_x, ctx.target_y, ctx.floor, ctx.add_event)
        if ctx.hit and ctx.damage_dealt > 0:
            lvl = self.buffed_lvl()
            ctx.add_event("DAMAGE", {
                "target": ctx.target_entity.id if ctx.target_entity else ctx.attacker.id,
                "amount": 0,
                "projectile": "corrosion",
                "splash_count": lvl // 2 + 2,
                "source_x": ctx.attacker.pos.x,
                "source_y": ctx.attacker.pos.y,
            }, floor_id=ctx.floor_id)


class WandOfCorruption(Wand):
    kind: Literal["wand_corruption"] = "wand_corruption"
    name: str = "Wand of Corruption"
    type: str = "wand"
    damage: int = 0
    charges: int = 3
    max_charges: int = 3
    projectile_type: str = "shadow"
    wand_sound: str = "SHATTER"
    staff_name: str = "Staff of Corruption"
    DESC: ClassVar[str] = "A wand that corrupts the minds of enemies."

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if defender is None:
            return
        lvl = max(0, self.level)
        proc_chance = (lvl + 1) / (lvl + 6)
        if _random.random() < proc_chance:
            duration = int((4 + lvl * 2))
            defender.add_buff("amok", duration=float(duration), level=1)

    def handle_zap(self, ctx):
        target = ctx.target_entity
        player = ctx.attacker
        if target is None:
            return
        from app.engine.entities.player import Mob as MobEntity
        if not isinstance(target, MobEntity):
            return
        lvl = self.buffed_lvl()
        corrupt_power = 3.0 + lvl / 3.0
        hp_ratio = target.hp / max(1, target.get_total_max_hp())
        enemy_resist = 1.0 + 4.0 * (hp_ratio * hp_ratio)
        # Debuffs reduce resist
        debuff_count = 0
        for debuff in ("amok", "slow", "hex", "paralysis", "weakness", "vulnerable", "cripple", "blindness", "terror"):
            if target.has_buff(debuff):
                debuff_count += 1
        enemy_resist *= (0.5 ** debuff_count)
        if target.has_buff("corruption"):
            enemy_resist = corrupt_power + 0.001  # cannot re-corrupt
        if corrupt_power > enemy_resist:
            target.faction = player.faction
            target.add_buff("corruption", duration=999.0, level=1)
            ctx.add_event("PLAY_SOUND", {"sound": "CURSE"}, floor_id=ctx.floor_id)
        elif _random.random() < corrupt_power / enemy_resist:
            target.add_buff("amok", duration=6.0 + lvl * 3, level=1)
            ctx.add_event("PLAY_SOUND", {"sound": "CURSE"}, floor_id=ctx.floor_id)
        else:
            target.add_buff("weakness", duration=6.0 + lvl * 3, level=1)
            ctx.add_event("PLAY_SOUND", {"sound": "CURSE"}, floor_id=ctx.floor_id)


class WandOfRegrowth(Wand):
    kind: Literal["wand_regrowth"] = "wand_regrowth"
    name: str = "Wand of Regrowth"
    type: str = "wand"
    damage: int = 0
    charges: int = 4
    max_charges: int = 4
    projectile_type: str = "foliage"
    wand_sound: str = "PUFF"
    staff_name: str = "Staff of Regrowth"
    DESC: ClassVar[str] = "A wand that causes vegetation to spring forth."

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if attacker is None or damage <= 0:
            return
        from app.engine.dungeon.constants import TileType
        on_grass = False
        if floor and tile_x is not None and tile_y is not None:
            for px, py in [(attacker.pos.x, attacker.pos.y), (tile_x, tile_y)]:
                if 0 <= py < len(floor.grid) and 0 <= px < len(floor.grid[0]):
                    t = floor.grid[py][px]
                    if t in (TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.FURROWED_GRASS):
                        on_grass = True
                        break
        if on_grass:
            lvl = max(0, self.level)
            healing = int(damage * (lvl + 2) / (lvl + 6) / 2)
            if healing > 0:
                attacker.hp = min(attacker.get_total_max_hp(), attacker.hp + healing)

    def charges_per_cast(self) -> int:
        consumed = (self.charges * 3 + 9) // 10
        return max(1, min(3, consumed))

    def handle_zap(self, ctx):
        floor = ctx.floor
        if floor is None:
            return
        lvl = self.buffed_lvl()
        charges = self.charges_per_cast()
        grass_to_place = round((3.67 + lvl / 3.0) * charges)
        tx, ty = ctx.target_x, ctx.target_y
        cells = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = tx + dx, ty + dy
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    t = floor.grid[ny][nx]
                    if t in (TileType.FLOOR_GRASS, TileType.EMPTY_DECO, TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.FURROWED_GRASS):
                        cells.append((nx, ny))
        _random.shuffle(cells)
        placed = 0
        for nx, ny in cells:
            if placed >= grass_to_place:
                break
            floor.grid[ny][nx] = TileType.HIGH_GRASS
            placed += 1
            ctx.add_event("TERRAIN_CHANGE", {"x": nx, "y": ny, "tile": TileType.HIGH_GRASS}, floor_id=ctx.floor_id)
        # Chance to drop seeds/dew
        if cells and _random.random() < 0.5 and _random.randint(1, 6) <= charges:
            sx, sy = _random.choice(cells)
            seed = Seed(id=str(_uuid.uuid4()), pos=Position(x=sx, y=sy), name="Seed")
            floor.items[seed.id] = seed
            ctx.add_event("ITEM_DROP", {"x": sx, "y": sy, "item": seed.id, "kind": seed.kind}, floor_id=ctx.floor_id)


class WandOfWarding(Wand):
    kind: Literal["wand_warding"] = "wand_warding"
    name: str = "Wand of Warding"
    type: str = "wand"
    damage: int = 0
    charges: int = 3
    max_charges: int = 3
    projectile_type: str = "ward"
    wand_sound: str = "ATTACK_MAGIC"
    staff_name: str = "Staff of Warding"
    DESC: ClassVar[str] = "A wand that deploys a sentry ward."

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if attacker is None or floor_mobs is None:
            return
        lvl = max(0, self.level)
        proc_chance = (lvl + 1) / (lvl + 5)
        if _random.random() < proc_chance:
            for mob in floor_mobs.values():
                if mob.is_alive and getattr(mob, "mob_type", None) == "ward":
                    heal_amt = max(1, lvl)
                    mob.hp = min(mob.max_hp, mob.hp + heal_amt)

    def handle_zap(self, ctx):
        floor = ctx.floor
        if floor is None:
            return
        lvl = self.buffed_lvl()
        tx, ty = ctx.target_x, ctx.target_y
        # Find existing ward at target
        existing_ward = None
        for m in floor.mobs.values():
            if m.is_alive and getattr(m, "mob_type", None) == "ward" and m.pos.x == tx and m.pos.y == ty:
                existing_ward = m
                break
        if existing_ward:
            heal = max(1, lvl)
            existing_ward.hp = min(existing_ward.max_hp, existing_ward.hp + heal)
            ctx.add_event("PLAY_SOUND", {"sound": "HEAL"}, floor_id=ctx.floor_id)
        elif 0 <= ty < floor.height and 0 <= tx < floor.width:
            if floor.flags and floor.flags.passable[ty][tx]:
                ward_id = str(_uuid.uuid4())
                ward = MobEntity(
                    id=ward_id,
                    type="mob",
                    mob_type="ward",
                    name="Ward Sentinel",
                    pos=Position(x=tx, y=ty),
                    hp=15, max_hp=15,
                    attack=5 + lvl, defense=2 + lvl // 2,
                    damage_min=2 + lvl // 2, damage_max=8 + 2 * lvl,
                    faction=ctx.attacker.faction,
                    view_distance=4,
                )
                floor.mobs[ward.id] = ward
                ctx.add_event("SUMMON", {"id": ward.id, "x": tx, "y": ty, "name": "Ward Sentinel"}, floor_id=ctx.floor_id)


class WandOfLivingEarth(DamageWand):
    kind: Literal["wand_living_earth"] = "wand_living_earth"
    name: str = "Wand of Living Earth"
    type: str = "wand"
    charges: int = 3
    max_charges: int = 3
    projectile_type: str = "earth"
    wand_sound: str = "BLAST"
    staff_name: str = "Staff of Living Earth"
    DESC: ClassVar[str] = "A wand that summons an earth guardian."

    def min(self, lvl: int) -> int: return 4
    def max(self, lvl: int) -> int: return 6 + 2 * lvl

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        if attacker is None or damage <= 0:
            return
        armor = int(damage * 0.33)
        attacker.add_buff("rock_armor", duration=10.0, level=armor)

    def handle_zap(self, ctx):
        lvl = self.buffed_lvl()
        floor = ctx.floor
        if floor is None:
            return
        # Find existing guardian
        guardian = None
        for m in floor.mobs.values():
            if m.is_alive and getattr(m, "mob_type", None) == "earth_guardian" and m.faction == ctx.attacker.faction:
                guardian = m
                break
        tx, ty = ctx.target_x, ctx.target_y
        armor_to_add = self.damage_roll(lvl)
        guardian_threshold = 8 + lvl * 4
        if guardian:
            guardian.max_hp = 16 + 8 * lvl
            guardian.hp = min(guardian.max_hp, guardian.hp + armor_to_add)
            ctx.add_event("PLAY_SOUND", {"sound": "HEAL"}, floor_id=ctx.floor_id)
        elif armor_to_add >= guardian_threshold:
            gx, gy = tx, ty
            if ctx.target_entity and ctx.target_entity.pos:
                # Place nearest free neighbor
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = tx + dx, ty + dy
                        if 0 <= nx < floor.width and 0 <= ny < floor.height:
                            if floor.flags and floor.flags.passable[ny][nx]:
                                gx, gy = nx, ny
                                break
            guard_id = str(_uuid.uuid4())
            guard = MobEntity(
                id=guard_id,
                type="mob",
                mob_type="earth_guardian",
                name="Earth Guardian",
                pos=Position(x=gx, y=gy),
                hp=16 + 8 * lvl, max_hp=16 + 8 * lvl,
                attack=5 + lvl, defense=3 + lvl // 2,
                damage_min=2, damage_max=4 + lvl // 2,
                dr_min=lvl, dr_max=3 + 3 * lvl,
                faction=ctx.attacker.faction,
                view_distance=6,
            )
            floor.mobs[guard.id] = guard
            ctx.add_event("SUMMON", {"id": guard.id, "x": gx, "y": gy, "name": "Earth Guardian"}, floor_id=ctx.floor_id)
        else:
            ctx.attacker.add_buff("rock_armor", duration=20.0, level=armor_to_add)


class CursedWand(Wand):
    kind: Literal["cursed_wand"] = "cursed_wand"
    name: str = "Cursed Wand"
    type: str = "wand"
    charges: int = 1
    max_charges: int = 1
    cursed: bool = True
    cursed_known: bool = True
    DESC: ClassVar[str] = "A heavily cursed wand crammed with unstable magical energy. Nobody knows what it does."

    def handle_zap(self, ctx):
        from app.engine.entities.cursed_wand import fire_cursed_wand
        fire_cursed_wand(ctx.game, ctx.attacker, self, ctx.target_x, ctx.target_y)
