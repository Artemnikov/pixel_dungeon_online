# Copyright (C) 2026 ArtemNikov
#
"""Wand of Disintegration (SPD WandOfDisintegration.java)."""
from __future__ import annotations

import random as _random
from typing import ClassVar, Literal

from app.engine.entities.base import *  # noqa: F401,F403
from app.engine.entities.wands.base import DamageWand


class WandOfDisintegration(DamageWand):
    kind: Literal["wand_disintegration"] = "wand_disintegration"
    name: str = "Wand of Disintegration"
    type: str = "wand"
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
        lvl = self.buffed_lvl()
        floor = ctx.floor
        if floor is None:
            return
        from app.engine.systems.ballistica import bresenham
        path = bresenham(ctx.attacker.pos.x, ctx.attacker.pos.y, ctx.target_x, ctx.target_y)
        hit_entities = []
        terrain_passed = 2
        terrain_bonus = 0
        terrain_changed = False
        for i, (cx, cy) in enumerate(path):
            if i == 0:
                continue
            if 0 <= cy < floor.height and 0 <= cx < floor.width:
                tile = floor.grid[cy][cx]
                if tile in (TileType.BARRICADE, TileType.BOOKSHELF):
                    floor.grid[cy][cx] = TileType.FLOOR_GRASS
                    terrain_changed = True
            # Find entities at this cell
            cell_hit = False
            for m in list(floor.mobs.values()):
                if m.is_alive and m.pos.x == cx and m.pos.y == cy and m.faction != ctx.attacker.faction:
                    if m.id not in {e.id for e in hit_entities}:
                        hit_entities.append(m)
                        cell_hit = True
            for p in (ctx.floor_players or []):
                if p.id != ctx.attacker.id and p.pos.x == cx and p.pos.y == cy:
                    if p.id not in {e.id for e in hit_entities}:
                        hit_entities.append(p)
                        cell_hit = True
            # SPD: convert terrain_passed on first char hit at this cell
            if cell_hit:
                terrain_bonus += terrain_passed // 3
                terrain_passed = terrain_passed % 3
            # SPD: solid tile increments terrain_passed (after char conversion)
            if 0 <= cy < floor.height and 0 <= cx < floor.width:
                if floor.flags and floor.flags.solid[cy][cx]:
                    terrain_passed += 1

        if terrain_changed:
            floor.rebuild_flags()

        if not hit_entities and ctx.target_entity and ctx.target_entity.is_alive:
            hit_entities.append(ctx.target_entity)

        for idx, ent in enumerate(hit_entities):
            if getattr(ent, "name", "") == "Dwarf King" and ctx.game is not None:
                ctx.game.qualified_for_boss_challenge = False
            extra_hits = idx
            eff_lvl = lvl + terrain_bonus + extra_hits
            dmg = _random.randint(self.min(eff_lvl), self.max(eff_lvl))
            if dmg > 0:
                ent.take_damage(dmg)
                ctx.add_event("DAMAGE", {
                    "target": ent.id,
                    "amount": dmg,
                    "projectile": "beam",
                    "beam_type": "death_ray",
                    "source_x": ctx.attacker.pos.x,
                    "source_y": ctx.attacker.pos.y,
                }, floor_id=ctx.floor_id)
