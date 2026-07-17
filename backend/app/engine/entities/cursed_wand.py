# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
"""CursedWand random effect dispatcher.

SPD CursedWand uses weighted tiers (common/uncommon/rare/very_rare).
Wondrous Resin trinket restricts pool to positive-only effects.
"""
import random

_COMMON = [
    "magic_missile", "slow", "knockback", "toxic_gas", "regrowth",
    "blindness", "teleport_other", "recharge", "summon_monsters",
]
_UNCOMMON = [
    "fire_blast", "frost_blast", "prismatic", "corruption",
    "blink", "disintegrate", "transfusion",
]
_RARE = [
    "summon_elemental", "warp_beacon", "living_earth",
]
_VERY_RARE = [
    "polymorph", "wish",
]

_POSITIVE_EFFECTS = {
    "magic_missile", "recharge", "regrowth", "transfusion",
    "blink", "warp_beacon", "wish", "summon_monsters",
}

_TIER_WEIGHTS = [60, 30, 9, 1]
_TIERS = [_COMMON, _UNCOMMON, _RARE, _VERY_RARE]


def _pick_effect(positive_only: bool = False) -> str:
    if positive_only:
        pool = [e for tier in _TIERS for e in tier if e in _POSITIVE_EFFECTS]
        return random.choice(pool) if pool else "magic_missile"
    tier = random.choices(range(4), weights=_TIER_WEIGHTS, k=1)[0]
    return random.choice(_TIERS[tier])


def fire_cursed_wand(game, player, item, tx: int, ty: int) -> None:
    from app.engine.entities.base import Position
    from app.engine.entities.trinkets import WondrousResin
    floor = game._get_or_create_floor(player.floor_id)

    positive_only = any(isinstance(it, WondrousResin) for it in player.belongings.all_items())
    effect = _pick_effect(positive_only)

    # Reduce charges
    item.charges = max(0, item.charges - 1)
    game.add_event("ZAP", {"player": player.id, "item": item.id, "cursed_effect": effect},
                   floor_id=player.floor_id, source_player_id=player.id)

    target_mob = next(
        (m for m in floor.mobs.values() if m.is_alive and m.pos.x == tx and m.pos.y == ty),
        None)

    if effect == "magic_missile":
        if target_mob:
            dmg = max(1, random.randint(6, 10) + item.level * 2)
            dealt = target_mob.take_damage(dmg)
            game.add_event("DAMAGE", {"target": target_mob.id, "amount": dealt}, floor_id=player.floor_id)
    elif effect == "slow":
        if target_mob:
            target_mob.add_buff("slow", duration=10.0)
    elif effect == "knockback":
        if target_mob:
            for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
                nx, ny = target_mob.pos.x+dx*2, target_mob.pos.y+dy*2
                if 0<=nx<floor.width and 0<=ny<floor.height and floor.flags and floor.flags.passable[ny][nx]:
                    target_mob.pos = Position(x=nx, y=ny)
                    game.add_event("PUSH", {"target": target_mob.id, "x": nx, "y": ny}, floor_id=player.floor_id)
                    break
    elif effect == "toxic_gas":
        from app.engine.game.terrain_effects import _create_gas
        _create_gas(floor, (tx, ty), 5, "toxic_gas")
    elif effect == "regrowth":
        from app.engine.dungeon.generator import TileType
        count = 0
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                nx, ny = tx+dx, ty+dy
                if 0<=nx<floor.width and 0<=ny<floor.height:
                    if floor.flags and floor.flags.passable[ny][nx] and floor.grid[ny][nx] == TileType.FLOOR:
                        floor.grid[ny][nx] = TileType.HIGH_GRASS
                        count += 1
        if count:
            game.add_event("MAP_PATCH", {"region": [tx-2, ty-2, tx+2, ty+2]}, floor_id=player.floor_id)
    elif effect == "blindness":
        if target_mob:
            target_mob.add_buff("blindness", duration=10.0)
        else:
            player.add_buff("blindness", duration=10.0)
    elif effect == "teleport_other":
        if target_mob:
            pool = [(x, y) for y in range(floor.height) for x in range(floor.width)
                    if floor.flags and floor.flags.passable[y][x]]
            if pool:
                nx, ny = random.choice(pool)
                target_mob.pos = Position(x=nx, y=ny)
                game.add_event("TELEPORT", {"target": target_mob.id, "x": nx, "y": ny}, floor_id=player.floor_id)
    elif effect == "recharge":
        player.add_buff("recharging", duration=20.0)
    elif effect == "fire_blast":
        if target_mob:
            dmg = max(1, random.randint(8, 16) + item.level * 3)
            dealt = target_mob.take_damage(dmg)
            target_mob.add_buff("burning", duration=8.0, level=1, stack_mode="extend")
            game.add_event("DAMAGE", {"target": target_mob.id, "amount": dealt, "fire": True}, floor_id=player.floor_id)
    elif effect == "frost_blast":
        if target_mob:
            dmg = max(1, random.randint(6, 12) + item.level * 2)
            dealt = target_mob.take_damage(dmg)
            target_mob.add_buff("frost", duration=10.0, level=1)
            game.add_event("DAMAGE", {"target": target_mob.id, "amount": dealt, "frost": True}, floor_id=player.floor_id)
    elif effect == "prismatic":
        if target_mob:
            buffs = ["burning", "frost", "blindness", "slow", "poison"]
            target_mob.add_buff(random.choice(buffs), duration=10.0, level=1)
    elif effect == "corruption":
        if target_mob and target_mob.faction != "player":
            target_mob.faction = "player"
            target_mob.ai_state = "hunting"
            game.add_event("CORRUPTED", {"target": target_mob.id}, floor_id=player.floor_id)
    elif effect == "blink":
        pool = [(x, y) for y in range(floor.height) for x in range(floor.width)
                if floor.flags and floor.flags.passable[y][x]
                and abs(x-player.pos.x) <= 8 and abs(y-player.pos.y) <= 8]
        if pool:
            nx, ny = random.choice(pool)
            player.pos = Position(x=nx, y=ny)
            game._invalidate_fov_cache()
            game.add_event("TELEPORT", {"player": player.id, "x": nx, "y": ny}, floor_id=player.floor_id)
    elif effect == "disintegrate":
        for mob in list(floor.mobs.values()):
            if not mob.is_alive or mob.faction == "player":
                continue
            if mob.pos.x == tx or mob.pos.y == ty:
                dmg = max(1, random.randint(10, 20) + item.level * 4)
                dealt = mob.take_damage(dmg)
                game.add_event("DAMAGE", {"target": mob.id, "amount": dealt}, floor_id=player.floor_id)
    elif effect == "transfusion":
        if target_mob:
            heal = max(1, random.randint(5, 15))
            target_mob.hp = min(target_mob.max_hp, target_mob.hp + heal)
            player.take_damage(max(1, heal // 2))
    elif effect == "summon_monsters":
        # SPD CursedWand.SummonMonsters: positive-only + user is hero →
        # spawn 2 mirror images at bolt collision pos. Otherwise →
        # summon hostile mobs (simplified: random enemy for the floor).
        if positive_only:
            from app.engine.entities.base import Position
            spawn_pos = Position(x=tx, y=ty)
            clone_ids = game._spawn_mirror_images(
                player, floor, player.floor_id, spawn_pos=spawn_pos,
            )
            clone_data = [
                {"id": cid, "x": floor.mobs[cid].pos.x, "y": floor.mobs[cid].pos.y}
                for cid in clone_ids if cid in floor.mobs
            ]
            game.add_event("MIRROR_IMAGE", {"player": player.id, "clones": clone_data},
                           floor_id=player.floor_id)
        else:
            from app.engine.entities.armor_glyphs import _spawn_random_enemy
            for _ in range(random.randint(1, 3)):
                mob = _spawn_random_enemy(floor, player.floor_id)
                if mob is not None:
                    floor.mobs[mob.id] = mob
                    game.add_event("SPAWN", {"mob": mob.id, "x": mob.pos.x, "y": mob.pos.y},
                                   floor_id=player.floor_id)
    elif effect in ("summon_elemental", "living_earth", "warp_beacon", "polymorph", "wish"):
        # Stub: complex effects emit a placeholder event
        game.add_event("CURSED_WAND_STUB", {"effect": effect, "player": player.id},
                       floor_id=player.floor_id, player_id=player.id)
