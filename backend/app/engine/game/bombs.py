# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
"""BombsMixin: real-time fuses for floor bombs + the shared explosion core.

A lit bomb is just a floor item with fuse_ticks set — serialized with the
floor, so reconnects can't lose a fuse. update_tick calls tick_bombs per
active floor (tengu bomb-timer pattern)."""
import random as _random
import uuid as _uuid
from typing import List, Tuple

from app.engine.entities.base import Position
from app.engine.entities.items_bombs import Bomb, Noisemaker
from app.engine.entities.items_equip import EquipableItem
from app.engine.entities.items_wands import Wand


def _normal_int_range(lo: int, hi: int) -> int:
    # SPD Random.NormalIntRange: mean-biased average of two uniforms.
    return round((_random.randint(lo, hi) + _random.randint(lo, hi)) / 2)


class BombsMixin:
    def tick_bombs(self, floor, floor_id: int) -> None:
        for item_id in list(floor.items.keys()):
            item = floor.items.get(item_id)
            if not isinstance(item, Bomb) or item.fuse_ticks is None:
                continue
            if isinstance(item, Noisemaker) and item.armed:
                self._noisemaker_tick(floor, floor_id, item)
                continue
            item.fuse_ticks -= 1
            if item.fuse_ticks > 0:
                continue
            if isinstance(item, Noisemaker) and not item.armed:
                self._arm_noisemaker(floor, floor_id, item)
            else:
                self.explode_bomb(floor, floor_id, item)

    def _arm_noisemaker(self, floor, floor_id: int, bomb) -> None:
        bomb.armed = True
        bomb.fuse_ticks = 120  # 6 SPD turns between alerts
        self.add_event("PLAY_SOUND", {"sound": "ALERT"}, floor_id=floor_id)

    def _noisemaker_tick(self, floor, floor_id: int, bomb) -> None:
        # Armed: detonate when any char stands on our cell; otherwise count
        # down to the next alert that beckons every mob (Noisemaker.java).
        bx, by = bomb.pos.x, bomb.pos.y
        occupied = any(m.is_alive and m.pos.x == bx and m.pos.y == by
                       for m in floor.mobs.values())
        occupied = occupied or any(
            p.is_alive and not p.is_downed and p.pos.x == bx and p.pos.y == by
            for p in self._players_on_floor(floor_id))
        if occupied:
            self.explode_bomb(floor, floor_id, bomb)
            return
        bomb.fuse_ticks -= 1
        if bomb.fuse_ticks <= 0:
            bomb.fuse_ticks = 120
            self.add_event("PLAY_SOUND", {"sound": "ALERT"}, floor_id=floor_id)
            self.add_event("BOMB_LIT", {"x": bx, "y": by, "kind": bomb.kind},
                           floor_id=floor_id)
            for m in floor.mobs.values():
                if m.is_alive and m.faction == "dungeon":
                    m.last_known_target_pos = Position(x=bx, y=by)
                    m.ai_state = "hunting"

    def explode_bomb(self, floor, floor_id: int, bomb) -> None:
        # Remove first: chain detonations must never recurse into this bomb.
        floor.items.pop(bomb.id, None)
        cx, cy = bomb.pos.x, bomb.pos.y
        cells = set(self._explosion_cells(floor, cx, cy, bomb))
        self.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)
        self.add_event("BOMB_BLAST", {
            "x": cx, "y": cy, "kind": bomb.kind,
            "cells": [[x, y] for x, y in sorted(cells)],
        }, floor_id=floor_id)

        chained = []
        if bomb.DESTRUCTIVE:
            self._explosion_destroy(floor, floor_id, cells, chained)

        depth = floor_id
        victims = [e for e in self._explosion_victims(floor, floor_id, cells)]
        if bomb.DEALS_BASE_DAMAGE:
            for ch in victims:
                if not ch.is_alive:
                    continue
                dmg = _normal_int_range(4 + depth, 12 + 3 * depth)
                if not bomb.PIERCES_ARMOR:
                    dmg -= _random.randint(ch.get_dr_min(), ch.get_dr_max())
                if dmg > 0:
                    taken = ch.take_damage(dmg)
                    self.add_event("DAMAGE", {"target": ch.id, "amount": taken},
                                   floor_id=floor_id)
                    if not ch.is_alive and ch.id in floor.mobs:
                        # Mirrors _blast_effect (runestone_actions.py): die() ->
                        # DEATH event -> handle_mob_death -> roll_drops, exactly.
                        from app.engine.systems.loot import roll_drops
                        ch.die(floor_mobs=floor.mobs, tile_x=ch.pos.x, tile_y=ch.pos.y,
                               players=list(self._players_on_floor(floor_id)))
                        self.add_event("DEATH", {"target": ch.id}, floor_id=floor_id)
                        self.handle_mob_death(ch, floor, floor_id)
                        for drop in roll_drops(ch, self.drop_counters, ch.pos.x, ch.pos.y,
                                                players=list(self._players_on_floor(floor_id))):
                            floor.items[drop.id] = drop

        self._bomb_effect(floor, floor_id, bomb, cells, victims)

        for other in chained:
            if other.id in floor.items:
                self.explode_bomb(floor, floor_id, other)

    def _explosion_victims(self, floor, floor_id: int, cells):
        for m in floor.mobs.values():
            if m.is_alive and (m.pos.x, m.pos.y) in cells:
                yield m
        for p in self._players_on_floor(floor_id):
            if p.is_alive and not p.is_downed and (p.pos.x, p.pos.y) in cells:
                yield p

    def _explosion_destroy(self, floor, floor_id: int, cells, chained: list) -> None:
        from app.engine.game.blobs import _BURN_RESULT  # underscore-private; repo precedent for cross-module reuse
        from app.engine.dungeon.constants import TileType
        patches = []
        for (x, y) in cells:
            if floor.flags and floor.flags.flamable[y][x]:
                new_tile = _BURN_RESULT.get(floor.grid[y][x], TileType.EMBERS)
                floor.grid[y][x] = new_tile
                patches.append({"x": x, "y": y, "tile": new_tile})
        destroyed = []
        for item_id in list(floor.items.keys()):
            item = floor.items[item_id]
            if item.pos is None or (item.pos.x, item.pos.y) not in cells:
                continue
            if getattr(item, "for_sale", False) or item.type in ("grave", "chest", "scenery"):
                continue
            # Heap.explode: unique/upgradable/equipable items survive explosions.
            if item.unique or isinstance(item, (EquipableItem, Wand)):
                continue
            if isinstance(item, Bomb):
                chained.append(item)      # detonated after this blast resolves
                continue
            del floor.items[item_id]
            destroyed.append({"x": item.pos.x, "y": item.pos.y})
        if patches:
            floor.rebuild_flags()
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)
        if destroyed:
            self.add_event("ITEMS_DESTROYED", {"tiles": destroyed}, floor_id=floor_id)

    def _bomb_effect(self, floor, floor_id: int, bomb, cells, victims) -> None:
        # Per-kind effects: Tasks 4-6 dispatch on bomb.kind here.
        handler = {
            "firebomb": self._effect_firebomb,
            "frost_bomb": self._effect_frost_bomb,
            "smoke_bomb": self._effect_smoke_bomb,
            "holy_bomb": self._effect_holy_bomb,
            "woolly_bomb": self._effect_woolly_bomb,
            "flashbang_bomb": self._effect_flashbang,
            "regrowth_bomb": self._effect_regrowth_bomb,
        }.get(bomb.kind)
        if handler:
            handler(floor, floor_id, bomb, cells, victims)

    def _effect_firebomb(self, floor, floor_id, bomb, cells, victims) -> None:
        # Firebomb.java: Fire blob vol 10 per open cell + BURNING sound.
        open_cells = {c for c in cells
                      if floor.flags and not floor.flags.solid[c[1]][c[0]]}
        if not open_cells:
            return
        for bid in list(floor.blob_areas.keys()):
            b = floor.blob_areas[bid]
            if b.get("type") == "fire" and b.get("cells", set()) & open_cells:
                del floor.blob_areas[bid]
        floor.blob_areas[f"firebomb_{bomb.id}"] = {
            "type": "fire", "cells": set(open_cells),
            "volume": {c: 10 for c in open_cells},
        }
        self.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)

    def _effect_frost_bomb(self, floor, floor_id, bomb, cells, victims) -> None:
        # FrostBomb.java: Freezing blob + Frost 2 turns on chars. Remake:
        # frozen buff + douse overlapping fire blob cells.
        for ch in victims:
            if ch.is_alive:
                ch.add_buff("frozen", duration=2.0, level=1)
        for bid in list(floor.blob_areas.keys()):
            b = floor.blob_areas[bid]
            if b.get("type") == "fire":
                b["cells"] = set(b["cells"]) - set(cells)
                for c in list(b.get("volume", {})):
                    if c in cells:
                        del b["volume"][c]
                if not b["cells"]:
                    del floor.blob_areas[bid]

    def _effect_smoke_bomb(self, floor, floor_id, bomb, cells, victims) -> None:
        # SmokeBomb.java: SmokeScreen vol 40 per cell, then whatever of the
        # 1000-unit (40*25) budget is left unspent when fewer than 25 cells are
        # reachable gets dumped onto the center so the fog lingers there.
        # Blob type mirrors _shatter_gas's gas_type for the Shrouding Fog
        # potion (item_actions.py: item.effect == "shrouding_fog") so this
        # blob is indistinguishable from a thrown potion's, for blobs.py.
        cx, cy = bomb.pos.x, bomb.pos.y
        open_cells = {c for c in cells
                      if floor.flags and not floor.flags.solid[c[1]][c[0]]}
        if not open_cells:
            return
        volume = {c: 40 for c in open_cells}
        excess = 1000 - 40 * len(open_cells)
        if excess > 0 and (cx, cy) in volume:
            volume[(cx, cy)] += excess
        floor.blob_areas[f"smoke_{bomb.id}"] = {
            "type": "shrouding_fog", "cells": set(open_cells),
            "volume": volume,
        }
        self.add_event("PLAY_SOUND", {"sound": "GAS"}, floor_id=floor_id)

    def _effect_holy_bomb(self, floor, floor_id, bomb, cells, victims) -> None:
        # HolyBomb.java: +50% of a fresh base roll to UNDEAD/DEMONIC, no DR.
        depth = floor_id
        for ch in victims:
            props = getattr(ch, "properties", [])
            if not ch.is_alive or not ("UNDEAD" in props or "DEMONIC" in props):
                continue
            bonus = round(_normal_int_range(4 + depth, 12 + 3 * depth) * 0.5)
            taken = ch.take_damage(bonus)
            self.add_event("DAMAGE", {"target": ch.id, "amount": taken},
                           floor_id=floor_id)
            if not ch.is_alive and ch.id in floor.mobs:
                # Mirrors explode_bomb's own death sequence (Task 3):
                # die() -> DEATH event -> handle_mob_death -> roll_drops.
                from app.engine.systems.loot import roll_drops
                ch.die(floor_mobs=floor.mobs, tile_x=ch.pos.x, tile_y=ch.pos.y,
                       players=list(self._players_on_floor(floor_id)))
                self.add_event("DEATH", {"target": ch.id}, floor_id=floor_id)
                self.handle_mob_death(ch, floor, floor_id)
                for drop in roll_drops(ch, self.drop_counters, ch.pos.x, ch.pos.y,
                                        players=list(self._players_on_floor(floor_id))):
                    floor.items[drop.id] = drop
        self.add_event("PLAY_SOUND", {"sound": "READ"}, floor_id=floor_id)

    def _effect_woolly_bomb(self, floor, floor_id, bomb, cells, victims) -> None:
        # WoollyBomb.java: sheep on every reachable cell within range+2. Uses
        # the blast's own BFS connectivity (via _explosion_cells_radius)
        # rather than a raw diamond so sheep don't appear through walls.
        from app.engine.dungeon.spd_levelgen.run_state import is_boss_level
        cx, cy = bomb.pos.x, bomb.pos.y
        cells4 = self._explosion_cells_radius(floor, cx, cy, bomb.EXPLOSION_RANGE + 2)
        # Sheep.initialize(bossLevel ? 20 : 200) + Random.Float(-2, 2) jitter.
        base_life = 20.0 if is_boss_level(floor_id) else 200.0
        placed = []
        for nx, ny in cells4:
            if floor.flags and (floor.flags.solid[ny][nx] or floor.flags.pit[ny][nx]):
                continue
            if any(m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values()):
                continue
            if any(pl.pos.x == nx and pl.pos.y == ny
                   for pl in self._players_on_floor(floor_id)):
                continue
            sheep_id = str(_uuid.uuid4())
            from app.engine.entities.base import Faction
            from app.engine.entities.player import Mob as MobEntity
            sheep = MobEntity(id=sheep_id, name="Sheep", type="npc",
                              pos=Position(x=nx, y=ny), hp=0, max_hp=0,
                              speed=0, faction=Faction.PLAYER)
            sheep.add_buff("sheep_timer", duration=base_life + _random.uniform(-2, 2), level=1)
            floor.mobs[sheep_id] = sheep
            placed.append({"id": sheep_id, "x": nx, "y": ny})
            self.add_event("WOOL_BURST", {"x": nx, "y": ny}, floor_id=floor_id)
        if placed:
            self.add_event("FLOCK", {"sheep": placed}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "SHEEP"}, floor_id=floor_id)

    def _effect_flashbang(self, floor, floor_id, bomb, cells, victims) -> None:
        # FlashBangBomb.java: extra quarter-roll electric damage + 10-turn
        # paralysis + lightning arcs.
        depth = floor_id
        for ch in victims:
            if not ch.is_alive:
                continue
            dmg = round(_normal_int_range(4 + depth, 12 + 3 * depth) / 4)
            taken = ch.take_damage(dmg)
            ch.add_buff("paralysis", duration=10.0, level=1)
            self.add_event("DAMAGE", {"target": ch.id, "amount": taken,
                                      "projectile": "lightning"}, floor_id=floor_id)
            if not ch.is_alive and ch.id in floor.mobs:
                # Mirrors explode_bomb's own death sequence (Task 3):
                # die() -> DEATH event -> handle_mob_death -> roll_drops.
                from app.engine.systems.loot import roll_drops
                ch.die(floor_mobs=floor.mobs, tile_x=ch.pos.x, tile_y=ch.pos.y,
                       players=list(self._players_on_floor(floor_id)))
                self.add_event("DEATH", {"target": ch.id}, floor_id=floor_id)
                self.handle_mob_death(ch, floor, floor_id)
                for drop in roll_drops(ch, self.drop_counters, ch.pos.x, ch.pos.y,
                                        players=list(self._players_on_floor(floor_id))):
                    floor.items[drop.id] = drop
        self.add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=floor_id)

    # PotionOfHealing.cure debuff set (PotionOfHealing.java): cleared from every
    # player-aligned char caught in a Regrowth Bomb.
    _REGROWTH_CURES = ("poison", "cripple", "weakness", "vulnerable", "bleeding",
                       "blindness", "drowsy", "slow", "vertigo")

    def _effect_regrowth_bomb(self, floor, floor_id, bomb, cells, victims) -> None:
        # RegrowthBomb.java: heal + cure allies caught in the blast, blanket the
        # reachable area in grass, and plant a few random seeds. SPD seeds a
        # Regrowth blob that grows grass over time; the remake grows it directly
        # (WandOfRegrowth parity). SPD's grass candidate set includes EMPTY
        # (== remake FLOOR), so grow there too rather than reuse plant_grass,
        # whose GRASS_TILES excludes plain floor.
        from app.engine.entities.base import Faction
        from app.engine.entities.player import Player
        from app.engine.dungeon.constants import TileType
        from app.engine.game.terrain_effects import _plant_seed_at

        for ch in victims:
            if not ch.is_alive or getattr(ch, "faction", None) != Faction.PLAYER:
                continue
            for b in self._REGROWTH_CURES:
                ch.remove_buff(b)
            if isinstance(ch, Player):
                ch.set_heal(round(0.8 * ch.get_total_max_hp() + 14), 0.25, 0.0)
            elif ch.max_hp > 0:
                ch.hp = ch.max_hp

        growable = {TileType.FLOOR, TileType.FLOOR_GRASS, TileType.EMPTY_DECO,
                    TileType.EMBERS, TileType.HIGH_GRASS, TileType.FURROWED_GRASS}
        patches, candidates = [], []
        for (x, y) in cells:
            if floor.grid[y][x] not in growable or (x, y) in floor.plants:
                continue
            occupied = any(m.is_alive and m.pos.x == x and m.pos.y == y
                           for m in floor.mobs.values()) or any(
                pl.pos.x == x and pl.pos.y == y
                for pl in self._players_on_floor(floor_id))
            if not occupied:
                candidates.append((x, y))
            if floor.grid[y][x] != TileType.HIGH_GRASS:
                floor.grid[y][x] = TileType.HIGH_GRASS
                patches.append({"x": x, "y": y, "tile": TileType.HIGH_GRASS})
        if patches:
            floor.rebuild_flags()
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)

        # 2-3 random seeds (SPD Random.chances{0,0,2,1}: index 2 w=2, index 3 w=1).
        seed_types = ("sungrass", "earthroot", "firebloom", "icecap", "sorrowmoss",
                      "dreamfoil", "fadeleaf", "rotberry", "starflower", "stormvine",
                      "blindweed", "swiftthistle")
        n_plants = _random.choices([2, 3], weights=[2, 1])[0]
        _random.shuffle(candidates)
        for pos in candidates[:n_plants]:
            _plant_seed_at(floor, pos, _random.choice(seed_types))
        self.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=floor_id)

    def _explosion_cells(self, floor, cx: int, cy: int, bomb) -> List[Tuple[int, int]]:
        if getattr(bomb, "USES_LOS", False):
            return self._los_explosion_cells(floor, cx, cy, bomb.EXPLOSION_RANGE)
        return self._explosion_cells_radius(floor, cx, cy, bomb.EXPLOSION_RANGE)

    def _los_explosion_cells(self, floor, cx: int, cy: int, radius: int) -> List[Tuple[int, int]]:
        # ShrapnelBomb.java: cast a losBlocking field of view from the blast and
        # hit everything in line of sight up to `radius` — unlike the flood-fill
        # BFS, shrapnel does not wrap around walls/corners.
        from app.engine.mechanics import shadowcaster
        blocking = self._effective_blocking(floor)
        fov = shadowcaster.compute_fov(blocking, floor.width, floor.height, cx, cy, radius)
        w = floor.width
        x0, x1 = max(0, cx - radius), min(floor.width - 1, cx + radius)
        y0, y1 = max(0, cy - radius), min(floor.height - 1, cy + radius)
        return [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
                if fov[y * w + x]]

    def _explosion_cells_radius(self, floor, cx: int, cy: int, radius: int) -> List[Tuple[int, int]]:
        # BFS distance map over non-solid cells (SPD also lets the blast
        # reach flammable solids like doors — handled with the destruction
        # pass in Task 3 by including flamable cells as traversable).
        seen = {(cx, cy)}
        frontier = [(cx, cy)]
        for _ in range(radius):
            nxt = []
            for x, y in frontier:
                for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0),
                               (-1, -1), (1, -1), (-1, 1), (1, 1)):
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                        continue
                    if (nx, ny) in seen:
                        continue
                    solid = floor.flags.solid[ny][nx] if floor.flags else False
                    flamable = floor.flags.flamable[ny][nx] if floor.flags else False
                    if solid and not flamable:
                        continue
                    seen.add((nx, ny))
                    if not solid:
                        nxt.append((nx, ny))
            frontier = nxt
        return sorted(seen)

    def light_bomb(self, player, floor, floor_id: int, bomb_cls_instance, tx: int, ty: int) -> None:
        unit = bomb_cls_instance
        unit.id = unit.id or str(_uuid.uuid4())
        unit.pos = Position(x=tx, y=ty)
        unit.fuse_ticks = unit.FUSE_TICKS
        floor.items[unit.id] = unit
        self.add_event("BOMB_LIT", {"x": tx, "y": ty, "kind": unit.kind},
                       floor_id=floor_id)

    def handle_bomb_pickup(self, player, floor, floor_id: int, item_id: str, bomb) -> bool:
        """Lit-bomb pickup: snuff the fuse (SPD), or detonate an armed
        Noisemaker. Returns True when this handled the pickup."""
        if bomb.fuse_ticks is None:
            return False
        if isinstance(bomb, Noisemaker) and bomb.armed:
            self.explode_bomb(floor, floor_id, bomb)
            return True
        bomb.fuse_ticks = None
        self.add_event("MESSAGE", {"text": "You quickly snuff the bomb's fuse."},
                       floor_id=floor_id, player_id=player.id)
        return False  # continue with the normal collect path
