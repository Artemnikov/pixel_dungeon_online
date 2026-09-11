# Copyright (C) 2026 ArtemNikov
#
"""Wand of Regrowth (SPD WandOfRegrowth.java)."""
from __future__ import annotations

import math as _math
import random as _random
import uuid as _uuid
from typing import ClassVar, Literal, Set, Tuple

from app.engine.entities.base import *  # noqa: F401,F403
from app.engine.entities.wands.base import Wand


# Growable terrain tiles (SPD: EMPTY, EMBERS, EMPTY_DECO, GRASS, HIGH_GRASS, FURROWED_GRASS)
_GROWABLE_TILES = None

def _is_growable(tile) -> bool:
    from app.engine.dungeon.constants import TileType
    return tile in (
        TileType.FLOOR, TileType.EMBERS, TileType.EMPTY_DECO,
        TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.FURROWED_GRASS,
    )


def _cone_cells(src_x: int, src_y: int, tgt_x: int, tgt_y: int,
                max_dist: int, angle_deg: float,
                floor=None) -> Set[Tuple[int, int]]:
    """Compute cells within a cone from src toward tgt."""
    dx = tgt_x - src_x
    dy = tgt_y - src_y
    dist = _math.sqrt(dx * dx + dy * dy)
    if dist < 0.5:
        return set()
    ux, uy = dx / dist, dy / dist
    cos_half = _math.cos(_math.radians(angle_deg / 2))
    cells: Set[Tuple[int, int]] = set()
    for cx in range(max(0, src_x - max_dist), min(floor.width if floor else 80, src_x + max_dist + 1)):
        for cy in range(max(0, src_y - max_dist), min(floor.height if floor else 80, src_y + max_dist + 1)):
            vx, vy = cx - src_x, cy - src_y
            d = _math.sqrt(vx * vx + vy * vy)
            if d < 0.5 or d > max_dist:
                continue
            dot = (vx * ux + vy * uy) / d
            if dot >= cos_half:
                # Check solid walls block the cone (simplified: skip solid tiles)
                if floor and floor.flags and floor.flags.solid[cy][cx]:
                    continue
                cells.add((cx, cy))
    return cells


class WandOfRegrowth(Wand):
    kind: Literal["wand_regrowth"] = "wand_regrowth"
    name: str = "Wand of Regrowth"
    type: str = "wand"
    damage: int = 0
    projectile_type: str = "foliage"
    wand_sound: str = "ATTACK_MAGIC"
    staff_name: str = "Staff of Regrowth"
    DESC: ClassVar[str] = "A wand that causes vegetation to spring forth."

    # SPD degradation tracking
    _tot_chrg_used: int = 0
    _charges_over_limit: int = 0

    def _charge_limit(self, hero_lvl: int, wand_lvl: int) -> int:
        """SPD WandOfRegrowth.chargeLimit()."""
        if wand_lvl >= 10:
            return 999999
        return round(20 + hero_lvl * (2 + wand_lvl) * (1.0 + wand_lvl / (50.0 - 5.0 * wand_lvl)))

    def charges_per_cast(self) -> int:
        consumed = (self.charges * 3 + 9) // 10
        return max(1, min(3, consumed))

    def on_hit(self, attacker, defender, damage, floor_mobs=None, tile_x=None, tile_y=None, floor=None, add_event=None):
        """Staff proc: heal on grass (SPD herbal healing)."""
        if attacker is None or damage <= 0:
            return
        from app.engine.dungeon.constants import TileType
        on_grass = False
        if floor:
            for pos in [(attacker.pos.x, attacker.pos.y), (tile_x, tile_y)]:
                px, py = pos
                if 0 <= py < floor.height and 0 <= px < floor.width:
                    if floor.grid[py][px] in (TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.FURROWED_GRASS):
                        on_grass = True
                        break
        if on_grass:
            from app.engine.entities.buffs import get_buff
            lvl = max(0, self.level)
            healing = round(damage * (lvl + 2) / (lvl + 6) / 2)
            if healing <= 0:
                return
            max_hp = attacker.get_total_max_hp() if hasattr(attacker, "get_total_max_hp") else getattr(attacker, "max_hp", 20)
            attacker_pos = getattr(attacker, "pos", None)
            subclass_info = getattr(attacker, "subclass_info", None)
            is_warden = getattr(subclass_info, "subclass", None) == "warden"
            source_id = None if is_warden else (f"{attacker_pos.x},{attacker_pos.y}" if attacker_pos else None)
            existing_buff = get_buff(getattr(attacker, "buffs", []), "sungrass_health")
            if existing_buff is not None:
                existing_buff.level = min(max_hp, existing_buff.level + healing)
                if existing_buff.source_id is not None and not is_warden:
                    existing_buff.source_id = source_id
                existing_buff.remaining = 999999.0
            else:
                attacker.add_buff(
                    "sungrass_health",
                    duration=999999.0,
                    level=min(max_hp, healing),
                    source_id=source_id,
                )

    def handle_zap(self, ctx):
        from app.engine.dungeon.constants import TileType
        floor = ctx.floor
        if floor is None:
            return
        lvl = self.buffed_lvl()
        cpc = self.charges_per_cast()
        grass_to_place = round((3.67 + lvl / 3.0) * cpc)
        tx, ty = ctx.target_x, ctx.target_y

        # Degradation
        hero_lvl = getattr(ctx.attacker, "level", 1)
        charge_limit = self._charge_limit(hero_lvl, lvl)
        furrowed_chance = 0.0
        if self._tot_chrg_used >= charge_limit:
            furrowed_chance = (self._charges_over_limit + 1) / 5.0

        # Compute cone cells (SPD: maxDist=2+2*cpc, angle=20+10*cpc degrees)
        max_dist = 2 + 2 * cpc
        angle = 20.0 + 10.0 * cpc
        src_x, src_y = ctx.attacker.pos.x, ctx.attacker.pos.y
        cells = list(_cone_cells(src_x, src_y, tx, ty, max_dist, angle, floor))

        # Filter: skip cells that can't grow or have plants/mobs
        from app.engine.dungeon.constants import TileType
        filtered = []
        for cx, cy in cells:
            if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                continue
            tile = floor.grid[cy][cx]
            if not _is_growable(tile):
                continue
            # Skip cells with plants
            if hasattr(floor, "plants") and floor.plants.get((cx, cy)):
                continue
            # Skip cells with immovable chars
            skip = False
            for m in floor.mobs.values():
                if m.is_alive and m.pos.x == cx and m.pos.y == cy:
                    props = getattr(m, "properties", None) or []
                    if "IMMOVABLE" in props:
                        skip = True
                        break
            if skip:
                continue
            # Upgrade tile to GRASS if not already high/furrowed
            if tile not in (TileType.HIGH_GRASS, TileType.FURROWED_GRASS):
                floor.grid[cy][cx] = TileType.FLOOR_GRASS
                ctx.add_event("TERRAIN_CHANGE", {"x": cx, "y": cy, "tile": TileType.FLOOR_GRASS},
                              floor_id=ctx.floor_id)
            # Root chars
            for m in floor.mobs.values():
                if m.is_alive and m.pos.x == cx and m.pos.y == cy:
                    m.add_buff("roots", duration=4.0 * cpc, level=1)
            for p in (getattr(floor, "players", {}) or {}).values():
                if getattr(p, "is_alive", True) and p.pos.x == cx and p.pos.y == cy:
                    p.add_buff("roots", duration=4.0 * cpc, level=1)
            filtered.append((cx, cy))

        _random.shuffle(filtered)

        # 3-charge: spawn Lotus (simplified: just a ward-like mob with healing)
        if cpc >= 3 and filtered:
            lotus_pos = None
            if (tx, ty) in filtered:
                lotus_pos = (tx, ty)
            else:
                # Find cell closest to target along bolt
                for cx, cy in reversed(filtered):
                    if not any(m.is_alive and m.pos.x == cx and m.pos.y == cy
                               for m in floor.mobs.values()):
                        lotus_pos = (cx, cy)
                        break
            if lotus_pos:
                filtered.remove(lotus_pos)
                lotus_id = str(_uuid.uuid4())
                from app.engine.entities.player import Mob as MobEntity
                lotus = MobEntity(
                    id=lotus_id, type="mob", mob_type="lotus",
                    name="Lotus",
                    pos=Position(x=lotus_pos[0], y=lotus_pos[1]),
                    hp=25 + 3 * lvl, max_hp=25 + 3 * lvl,
                    attack=0, defense=999,
                    damage_min=0, damage_max=0,
                    faction=ctx.attacker.faction, view_distance=1 + lvl,
                )
                lotus._wand_level = lvl
                floor.mobs[lotus.id] = lotus
                ctx.add_event("SUMMON", {"id": lotus.id, "x": lotus_pos[0],
                                          "y": lotus_pos[1], "name": "Lotus"},
                              floor_id=ctx.floor_id)

        # Chance to spawn Dewcatcher/Seedpod (16%/33%/50% for cpc 1/2/3)
        if filtered and _random.random() > furrowed_chance and _random.randint(0, 5) < cpc:
            sx, sy = filtered.pop(0)
            # Drop a seed item as simplified Dewcatcher/Seedpod
            from app.engine.entities.items.consumables import Seed
            seed_kind = _random.choice(("dewcatcher_seed", "seedpod_seed"))
            seed = Seed(id=str(_uuid.uuid4()), pos=Position(x=sx, y=sy), name=seed_kind)
            floor.items[seed.id] = seed
            ctx.add_event("ITEM_DROP", {"x": sx, "y": sy, "item": seed.id, "kind": seed.kind},
                          floor_id=ctx.floor_id)

        # Chance to spawn random seed plant (33%/66%/100% for cpc 1/2/3)
        if filtered and _random.random() > furrowed_chance and _random.randint(0, 2) < cpc:
            sx, sy = filtered.pop(0)
            from app.engine.entities.items.consumables import Seed, STANDARD_SEEDS
            seed_name = _random.choice(STANDARD_SEEDS)
            seed = Seed(id=str(_uuid.uuid4()), pos=Position(x=sx, y=sy), plant_type=seed_name)
            floor.items[seed.id] = seed
            ctx.add_event("ITEM_DROP", {"x": sx, "y": sy, "item": seed.id, "kind": seed.kind},
                          floor_id=ctx.floor_id)

        # Fill remaining grass
        for cx, cy in filtered:
            if placed >= grass_to_place:
                break
            if floor.grid[cy][cx] == TileType.HIGH_GRASS:
                continue
            if _random.random() > furrowed_chance:
                floor.grid[cy][cx] = TileType.HIGH_GRASS
            else:
                floor.grid[cy][cx] = TileType.FURROWED_GRASS
            ctx.add_event("TERRAIN_CHANGE",
                          {"x": cx, "y": cy, "tile": floor.grid[cy][cx]},
                          floor_id=ctx.floor_id)
            placed += 1

        # Track degradation
        if self._tot_chrg_used < charge_limit:
            self._charges_over_limit = 0
            self._tot_chrg_used += cpc
            if self._tot_chrg_used > charge_limit:
                self._charges_over_limit = self._tot_chrg_used - charge_limit
                self._tot_chrg_used = charge_limit
        else:
            self._charges_over_limit += cpc

        floor.rebuild_flags()
        ctx.add_event("PLAY_SOUND", {"sound": "ATTACK_MAGIC"}, floor_id=ctx.floor_id)
