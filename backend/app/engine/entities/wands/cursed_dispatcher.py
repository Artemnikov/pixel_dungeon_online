# Copyright (C) 2026 ArtemNikov
#
"""CursedWand random effect dispatcher — 32 effects across 4 tiers."""
from __future__ import annotations
import random as R
from app.engine.game.terrain_primitives import _create_gas
from app.engine.entities.base import Position

# ── Tier lists (SPD CursedWand.java) ────────────────────────────────
COMMON = [
    "burn_and_freeze", "spawn_regrowth", "random_teleport", "random_gas",
    "random_area_effect", "bubbles", "random_wand", "self_ooze",
]
UNCOMMON = [
    "random_plant", "health_transfer", "explosion", "lightning_bolt",
    "geyser", "summon_sheep", "levitate", "alarm",
]
RARE = [
    "sheep_polymorph", "curse_equipment", "interfloor_teleport",
    "summon_monsters", "fireball", "cone_of_colors", "mass_invuln", "petrify",
]
VERY_RARE = [
    "forest_fire", "spawn_golden_mimic", "abort_retry_fail",
    "random_transmogrify", "hero_shape_shift", "super_nova",
    "sinkhole", "gravity_chaos",
]
TIER_WEIGHTS = [60, 30, 9, 1]
TIERS = [COMMON, UNCOMMON, RARE, VERY_RARE]
POSITIVE_EFFECTS = {
    "spawn_regrowth", "random_teleport", "health_transfer", "bubbles",
    "random_plant", "summon_sheep", "levitate", "sheep_polymorph",
    "mass_invuln", "hero_shape_shift", "forest_fire", "abort_retry_fail",
}


def _pick_effect(positive_only: bool = False) -> str:
    if positive_only:
        pool = [e for tier in TIERS for e in tier if e in POSITIVE_EFFECTS]
        return R.choice(pool) if pool else "spawn_regrowth"
    tier = R.choices(range(4), weights=TIER_WEIGHTS, k=1)[0]
    return R.choice(TIERS[tier])


def fire_cursed_wand(game, player, item, tx: int, ty: int,
                     consume_charge: bool = True) -> None:
    from app.engine.entities.trinkets import WondrousResin
    floor = game._get_or_create_floor(player.floor_id)
    positive_only = any(isinstance(it, WondrousResin) for it in player.belongings.all_items())
    effect = _pick_effect(positive_only)
    if consume_charge:
        item.charges = max(0, item.charges - 1)
    game.add_event("ZAP", {"player": player.id, "item": item.id, "cursed_effect": effect},
                   floor_id=player.floor_id, source_player_id=player.id)
    _EFFECTS[effect](game, player, item, tx, ty, floor, positive_only)


def _target(floor, tx, ty):
    return next((m for m in floor.mobs.values() if m.is_alive and m.pos.x == tx and m.pos.y == ty), None)


def _passable_cells(floor, max_d=999, cx=None, cy=None):
    return [(x, y) for y in range(floor.height) for x in range(floor.width)
            if floor.flags and floor.flags.passable[y][x]
            and (cx is None or abs(x - cx) <= max_d)]


def _e(game, floor, ev, data):
    game.add_event(ev, data, floor_id=floor.floor_id)


# ── Common effects ──────────────────────────────────────────────────
def _burn_and_freeze(g, p, item, tx, ty, f, pos):
    t = _target(f, tx, ty)
    if R.int(2) == 0:
        if t: t.add_buff("burning", duration=4.0)
        if not pos: p.add_buff("frost", duration=3.0)
    else:
        if not pos: p.add_buff("burning", duration=4.0)
        if t: t.add_buff("frost", duration=3.0)

def _spawn_regrowth(g, p, item, tx, ty, f, pos):
    _create_gas(f, (tx, ty), 30, "foliage")

def _random_teleport(g, p, item, tx, ty, f, pos):
    t = _target(f, tx, ty)
    pool = _passable_cells(f)
    if not pool: return
    if t and (pos or R.int(2) == 0):
        nx, ny = R.choice(pool)
        t.pos = Position(x=nx, y=ny)
        _e(g, f, "TELEPORT", {"target": t.id, "x": nx, "y": ny})
    elif not pos:
        nx, ny = R.choice(pool)
        p.pos = Position(x=nx, y=ny)
        g._invalidate_fov_cache()
        _e(g, f, "TELEPORT", {"player": p.id, "x": nx, "y": ny})

def _random_gas(g, p, item, tx, ty, f, pos):
    gas = R.choice(["confusion_gas", "toxic_gas", "paralytic_gas"])
    vol = {"confusion_gas": 800, "toxic_gas": 500, "paralytic_gas": 200}[gas]
    _create_gas(f, (tx, ty), vol, gas)

def _random_area_effect(g, p, item, tx, ty, f, pos):
    _create_gas(f, (tx, ty), 10, "fire")

def _bubbles(g, p, item, tx, ty, f, pos):
    _e(g, f, "PLAY_SOUND", {"sound": "ZAP"})

def _random_wand(g, p, item, tx, ty, f, pos):
    from app.engine.entities.items.catalog import item_catalog
    _e(g, f, "ZAP", {"effect": "random_wand", "player": p.id})

def _self_ooze(g, p, item, tx, ty, f, pos):
    t = _target(f, tx, ty)
    for ch in ([t] if t else []):
        ch.add_buff("ooze", duration=10.0)
    if not pos:
        p.add_buff("ooze", duration=10.0)

# ── Uncommon effects ────────────────────────────────────────────────
def _random_plant(g, p, item, tx, ty, f, pos):
    from app.engine.entities.items.consumables import Seed, STANDARD_SEEDS
    s = Seed(id=str(R.getrandbits(64)), pos=Position(x=tx, y=ty), plant_type=R.choice(STANDARD_SEEDS))
    f.items[s.id] = s
    _e(g, f, "ITEM_DROP", {"x": tx, "y": ty, "item": s.id, "kind": s.kind})

def _health_transfer(g, p, item, tx, ty, f, pos):
    t = _target(f, tx, ty)
    if t is None: return
    dmg = max(2, f.floor_id * 2) if hasattr(f, "floor_id") else 10
    if pos or R.int(2) == 0:
        p.hp = min(p.get_total_max_hp(), p.hp + dmg // 2)
        t.take_damage(dmg)
    else:
        t.hp = min(t.get_total_max_hp(), t.hp + dmg // 2)
        p.take_damage(dmg)

def _explosion(g, p, item, tx, ty, f, pos):
    _create_gas(f, (tx, ty), 20, "fire")
    t = _target(f, tx, ty)
    if t: t.take_damage(R.randint(15, 30))
    _e(g, f, "PLAY_SOUND", {"sound": "BLAST"})

def _lightning_bolt(g, p, item, tx, ty, f, pos):
    affected = set()
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for bx, by in [(p.pos.x + dx, p.pos.y + dy), (tx + dx, ty + dy)]:
                if 0 <= bx < f.width and 0 <= by < f.height:
                    for m in f.mobs.values():
                        if m.is_alive and m.pos.x == bx and m.pos.y == by and m.id not in affected:
                            m.take_damage(R.randint(5, 10))
                            m.add_buff("paralysis", duration=2.0)
                            affected.add(m.id)
    g.add_event("PLAY_SOUND", {"sound": "LIGHTNING",
                               "x": p.pos.x, "y": p.pos.y},
                floor_id=f.floor_id, source_player_id=p.id)

def _geyser(g, p, item, tx, ty, f, pos):
    t = _target(f, tx, ty)
    if t: t.take_damage(R.randint(5, 15))
    _e(g, f, "PLAY_SOUND", {"sound": "BLAST"})

def _summon_sheep(g, p, item, tx, ty, f, pos):
    from app.engine.entities.player import Mob as MobEntity
    sid = str(R.getrandbits(64))
    sheep = MobEntity(id=sid, type="mob", mob_type="sheep", name="Sheep",
                      pos=Position(x=tx, y=ty), hp=1, max_hp=1,
                      attack=0, defense=0, damage_min=0, damage_max=0,
                      faction="neutral", view_distance=4)
    f.mobs[sid] = sheep
    _e(g, f, "SUMMON", {"id": sid, "x": tx, "y": ty, "name": "Sheep"})

def _levitate(g, p, item, tx, ty, f, pos):
    t = _target(f, tx, ty)
    if t and (pos or R.int(2) == 0):
        t.add_buff("levitation", duration=10.0)
    elif not pos:
        p.add_buff("levitation", duration=10.0)

def _alarm(g, p, item, tx, ty, f, pos):
    for m in f.mobs.values():
        if m.is_alive and hasattr(m, "aggro"):
            m.aggro(p)
    _e(g, f, "PLAY_SOUND", {"sound": "ALERT"})

# ── Rare effects ────────────────────────────────────────────────────
def _sheep_polymorph(g, p, item, tx, ty, f, pos):
    t = _target(f, tx, ty)
    if t is None: return
    props = getattr(t, "properties", None) or []
    if "BOSS" in props or "MINIBOSS" in props: return
    from app.engine.entities.player import Mob as MobEntity
    sid = str(R.getrandbits(64))
    sheep = MobEntity(id=sid, type="mob", mob_type="sheep", name="Sheep",
                      pos=Position(x=t.pos.x, y=t.pos.y), hp=1, max_hp=1,
                      attack=0, defense=0, damage_min=0, damage_max=0,
                      faction="neutral", view_distance=4)
    del f.mobs[t.id]
    f.mobs[sid] = sheep
    _e(g, f, "SUMMON", {"id": sid, "x": sheep.pos.x, "y": sheep.pos.y, "name": "Sheep"})

def _curse_equipment(g, p, item, tx, ty, f, pos):
    if pos:
        t = _target(f, tx, ty)
        if t: t.add_buff("hex", duration=10.0)
    else:
        p.add_buff("hex", duration=10.0)

def _interfloor_teleport(g, p, item, tx, ty, f, pos):
    if not pos:
        pool = _passable_cells(f)
        if pool:
            nx, ny = R.choice(pool)
            p.pos = Position(x=nx, y=ny)
            g._invalidate_fov_cache()
            _e(g, f, "TELEPORT", {"player": p.id, "x": nx, "y": ny})

def _summon_monsters(g, p, item, tx, ty, f, pos):
    if pos:
        from app.engine.entities.armors.armor_glyphs import _spawn_random_enemy
        for _ in range(R.randint(1, 3)):
            mob = _spawn_random_enemy(f, f.floor_id)
            if mob:
                f.mobs[mob.id] = mob
                _e(g, f, "SUMMON", {"id": mob.id, "x": mob.pos.x, "y": mob.pos.y, "name": mob.name})
    else:
        from app.engine.game.ai_mirror_image import _spawn_mirror_images
        _spawn_mirror_images(g, p, f, f.floor_id)

def _fireball(g, p, item, tx, ty, f, pos):
    from app.engine.dungeon.constants import TileType
    fire_cells = set()
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            nx, ny = tx + dx, ty + dy
            if 0 <= nx < f.width and 0 <= ny < f.height:
                tile = f.grid[ny][nx]
                if tile in (TileType.FLOOR_GRASS, TileType.HIGH_GRASS):
                    fire_cells.add((nx, ny))
    if fire_cells:
        bid = f"fireball_{p.id}"
        f.blob_areas[bid] = {
            "type": "fire", "cells": fire_cells,
            "volume": {c: 4 for c in fire_cells},
        }
    t = _target(f, tx, ty)
    if t: t.take_damage(R.randint(15, 30))
    _e(g, f, "PLAY_SOUND", {"sound": "BLAST"})

def _cone_of_colors(g, p, item, tx, ty, f, pos):
    for m in list(f.mobs.values()):
        if not m.is_alive or m.faction == p.faction: continue
        dx = m.pos.x - p.pos.x
        dy = m.pos.y - p.pos.y
        if abs(dx) + abs(dy) > 8: continue
        buff = R.choice(["burning", "frost", "poison", "ooze", "paralysis"])
        m.add_buff(buff, duration=5.0)
        m.take_damage(R.randint(5, 15))
    _e(g, f, "PLAY_SOUND", {"sound": "ZAP"})

def _mass_invuln(g, p, item, tx, ty, f, pos):
    p.add_buff("invulnerability", duration=10.0)
    p.add_buff("bless", duration=10.0)
    for m in f.mobs.values():
        if m.is_alive and m.faction == p.faction:
            m.add_buff("invulnerability", duration=10.0)
    _e(g, f, "PLAY_SOUND", {"sound": "TELEPORT"})

def _petrify(g, p, item, tx, ty, f, pos):
    if not pos:
        p.add_buff("time_stasis", duration=10.0)
        _e(g, f, "PLAY_SOUND", {"sound": "TELEPORT"})

# ── Very rare effects ───────────────────────────────────────────────
def _forest_fire(g, p, item, tx, ty, f, pos):
    from app.engine.dungeon.constants import TileType
    patches = []
    for y in range(f.height):
        for x in range(f.width):
            if f.flags and f.flags.passable[y][x] and f.grid[y][x] == TileType.FLOOR:
                f.grid[y][x] = TileType.HIGH_GRASS
                patches.append({"x": x, "y": y, "tile": TileType.HIGH_GRASS})
    if patches:
        _e(g, f, "MAP_PATCH", {"tiles": patches})
        f.rebuild_flags()
    if not pos:
        fire_cells = set()
        for _ in range(R.randint(3, 8)):
            bx, by = R.randint(0, f.width - 1), R.randint(0, f.height - 1)
            fire_cells.add((bx, by))
        if fire_cells:
            f.blob_areas[f"ff_{p.id}"] = {
                "type": "fire", "cells": fire_cells,
                "volume": {c: 10 for c in fire_cells},
            }

def _spawn_golden_mimic(g, p, item, tx, ty, f, pos):
    from app.engine.entities.player import Mob as MobEntity
    mid = str(R.getrandbits(64))
    mimic = MobEntity(id=mid, type="mob", mob_type="golden_mimic", name="Golden Mimic",
                      pos=Position(x=tx, y=ty), hp=30, max_hp=30,
                      attack=12, defense=4, damage_min=5, damage_max=15,
                      faction="enemy", view_distance=6)
    f.mobs[mid] = mimic
    _e(g, f, "SUMMON", {"id": mid, "x": tx, "y": ty, "name": "Golden Mimic"})

def _abort_retry_fail(g, p, item, tx, ty, f, pos):
    _e(g, f, "PLAY_SOUND", {"sound": "CURSED"})

def _random_transmogrify(g, p, item, tx, ty, f, pos):
    if pos: return
    _e(g, f, "ZAP", {"effect": "transmogrify", "player": p.id})

def _hero_shape_shift(g, p, item, tx, ty, f, pos):
    p.add_buff("disguise", duration=20.0)
    _e(g, f, "PLAY_SOUND", {"sound": "CURSED"})

def _super_nova(g, p, item, tx, ty, f, pos):
    for m in list(f.mobs.values()):
        if not m.is_alive: continue
        dx = m.pos.x - p.pos.x
        dy = m.pos.y - p.pos.y
        dist = abs(dx) + abs(dy)
        if dist <= 6:
            m.take_damage(R.randint(10, 20))
            m.add_buff("burning", duration=4.0)
    _e(g, f, "PLAY_SOUND", {"sound": "BLAST"})

def _sinkhole(g, p, item, tx, ty, f, pos):
    from app.engine.dungeon.constants import TileType
    patches = []
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            nx, ny = tx + dx, ty + dy
            if 0 <= nx < f.width and 0 <= ny < f.height:
                if f.flags and f.flags.passable[ny][nx]:
                    f.grid[ny][nx] = TileType.CHASM
                    patches.append({"x": nx, "y": ny, "tile": TileType.CHASM})
    if patches:
        _e(g, f, "MAP_PATCH", {"tiles": patches})
        f.rebuild_flags()

def _gravity_chaos(g, p, item, tx, ty, f, pos):
    occupied = set()
    for m in list(f.mobs.values()):
        if not m.is_alive or m.faction == p.faction: continue
        pool = _passable_cells(f)
        occupied.add((m.pos.x, m.pos.y))
        free = [(x, y) for x, y in pool if (x, y) not in occupied]
        if free:
            nx, ny = R.choice(free)
            m.pos = Position(x=nx, y=ny)
            occupied.add((nx, ny))
    _e(g, f, "PLAY_SOUND", {"sound": "TELEPORT"})


# ── Dispatch table ──────────────────────────────────────────────────
_EFFECTS = {
    "burn_and_freeze": _burn_and_freeze, "spawn_regrowth": _spawn_regrowth,
    "random_teleport": _random_teleport, "random_gas": _random_gas,
    "random_area_effect": _random_area_effect, "bubbles": _bubbles,
    "random_wand": _random_wand, "self_ooze": _self_ooze,
    "random_plant": _random_plant, "health_transfer": _health_transfer,
    "explosion": _explosion, "lightning_bolt": _lightning_bolt,
    "geyser": _geyser, "summon_sheep": _summon_sheep,
    "levitate": _levitate, "alarm": _alarm,
    "sheep_polymorph": _sheep_polymorph, "curse_equipment": _curse_equipment,
    "interfloor_teleport": _interfloor_teleport, "summon_monsters": _summon_monsters,
    "fireball": _fireball, "cone_of_colors": _cone_of_colors,
    "mass_invuln": _mass_invuln, "petrify": _petrify,
    "forest_fire": _forest_fire, "spawn_golden_mimic": _spawn_golden_mimic,
    "abort_retry_fail": _abort_retry_fail, "random_transmogrify": _random_transmogrify,
    "hero_shape_shift": _hero_shape_shift, "super_nova": _super_nova,
    "sinkhole": _sinkhole, "gravity_chaos": _gravity_chaos,
}
