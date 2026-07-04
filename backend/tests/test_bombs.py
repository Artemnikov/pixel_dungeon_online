"""Bombs (SPD items/bombs): items, fuse lifecycle, explosions, recipes."""
import pytest

from app.engine.alchemy.energy import energy_val
from app.engine.entities.items_bombs import (
    ArcaneBomb, Bomb, Firebomb, FlashBangBomb, FrostBomb, HolyBomb,
    MetalShard, Noisemaker, RegrowthBomb, ShrapnelBomb, SmokeBomb, WoollyBomb,
)
from app.engine.game.spd_adapter import _descriptor_to_item
from app.engine.manager import GameInstance


@pytest.fixture
def game():
    return GameInstance("t-bombs")


def test_bomb_item_basics():
    b = Bomb()
    assert b.kind == "bomb" and b.stackable
    assert b.is_identified()                      # always identified (SPD)
    assert b.fuse_ticks is None and b.armed is False
    assert b.value() == 15 and Bomb(quantity=3).value() == 45
    assert (Bomb.EXPLOSION_RANGE, Bomb.DESTRUCTIVE, Bomb.FUSE_TICKS) == (1, True, 40)


def test_enhanced_bomb_flags_match_java():
    # (cls, range, destructive, pierces) per items/bombs/*.java
    table = [
        (Firebomb, 2, True, False), (FrostBomb, 2, True, False),
        (SmokeBomb, 2, True, False), (FlashBangBomb, 2, True, False),
        (HolyBomb, 2, True, False), (WoollyBomb, 2, True, False),
        (Noisemaker, 2, True, False),
        (RegrowthBomb, 3, False, False),
        (ArcaneBomb, 2, False, True),
        (ShrapnelBomb, 8, False, False),
    ]
    for cls, rng, destr, pierce in table:
        assert (cls.EXPLOSION_RANGE, cls.DESTRUCTIVE, cls.PIERCES_ARMOR) == (rng, destr, pierce), cls.__name__


def test_bomb_prices_match_java():
    # value() overrides in items/bombs/*.java: 20+30=50 default,
    # SmokeBomb/Noisemaker 20+40=60, ShrapnelBomb 20+50=70.
    prices = {
        Firebomb: 50, FrostBomb: 50, FlashBangBomb: 50, HolyBomb: 50,
        RegrowthBomb: 50, WoollyBomb: 50, ArcaneBomb: 50,
        SmokeBomb: 60, Noisemaker: 60,
        ShrapnelBomb: 70,
    }
    for cls, price in prices.items():
        assert cls().value() == price, cls.__name__
        assert cls(quantity=2).value() == 2 * price, cls.__name__


def test_lit_and_unlit_bombs_do_not_merge():
    lit = Bomb(fuse_ticks=40)
    unlit = Bomb()
    assert not lit.is_similar(unlit)
    assert Bomb().is_similar(Bomb())


def test_metal_shard(game):
    s = MetalShard(quantity=2)
    assert s.kind == "metal_shard" and s.stackable
    assert s.value() == 100
    assert energy_val(game, s) == 6                # 3*q (MetalShard.java)


def test_adapter_maps_bomb_and_shard():
    b = _descriptor_to_item(frozenset({"Bomb"}), 1, 1)
    assert isinstance(b, Bomb) and b.quantity == 1
    b2 = _descriptor_to_item(frozenset({"Bomb", "qty:2"}), 1, 1)
    assert b2.quantity == 2
    s = _descriptor_to_item(frozenset({"MetalShard"}), 1, 1)
    assert isinstance(s, MetalShard)


from app.engine.entities.base import Position


@pytest.fixture
def game_with_player():
    g = GameInstance("t-bombs-run")
    p = g.add_player("p1", "Bob")
    return g, p, g._get_or_create_floor(p.floor_id)


def _events(g, etype):
    return [e for e in g.events if e["type"] == etype]


def test_throw_lights_bomb_on_floor(game_with_player):
    g, p, floor = game_with_player
    p.add_to_inventory(Bomb(id="b1", quantity=2))
    tx, ty = p.pos.x + 1, p.pos.y
    g.execute_item_action("p1", "b1", "THROW", tx, ty)
    lit = [i for i in floor.items.values() if isinstance(i, Bomb) and i.fuse_ticks]
    assert len(lit) == 1
    assert lit[0].fuse_ticks == Bomb.FUSE_TICKS and lit[0].quantity == 1
    assert p.belongings.get_item("b1").quantity == 1     # one unit detached
    assert _events(g, "BOMB_LIT")[-1]["data"]["kind"] == "bomb"


def test_fuse_ticks_down_and_explodes(game_with_player):
    g, p, floor = game_with_player
    bomb = Bomb(id="bf", fuse_ticks=2, pos=Position(x=p.pos.x + 2, y=p.pos.y))
    floor.items["bf"] = bomb
    g.tick_bombs(floor, p.floor_id)
    assert floor.items["bf"].fuse_ticks == 1
    g.tick_bombs(floor, p.floor_id)
    assert "bf" not in floor.items                        # exploded, consumed
    assert _events(g, "BOMB_BLAST")


def test_pickup_snuffs_lit_bomb(game_with_player):
    g, p, floor = game_with_player
    floor.items["bl"] = Bomb(id="bl", fuse_ticks=30, pos=Position(x=p.pos.x + 1, y=p.pos.y))
    g.move_entity("p1", 1, 0)
    assert "bl" not in floor.items
    picked = next(i for i in p.inventory if isinstance(i, Bomb))
    assert picked.fuse_ticks is None                      # snuffed (SPD)


from app.engine.dungeon.generator import TileType


def _place(floor, item):
    floor.items[item.id] = item
    return item


def test_explosion_damages_entities_in_radius(game_with_player):
    g, p, floor = game_with_player
    # Force open floor at the bomb/mob cells: procedural gen is seeded from
    # the fixture's fixed game_id, so it's not guaranteed open by default.
    floor.grid[p.pos.y][p.pos.x + 2] = TileType.FLOOR
    floor.grid[p.pos.y][p.pos.x + 3] = TileType.FLOOR
    floor.rebuild_flags()
    from app.engine.entities.player import Mob
    m = Mob(id="m1", name="Rat", pos=Position(x=p.pos.x + 3, y=p.pos.y),
            hp=100, max_hp=100, faction="dungeon")
    floor.mobs["m1"] = m
    bomb = _place(floor, Bomb(id="bx", fuse_ticks=1,
                              pos=Position(x=p.pos.x + 2, y=p.pos.y)))
    p_hp = p.hp
    g.tick_bombs(floor, p.floor_id)
    # depth 1: dmg in [5..15] mean-biased, mob has no DR
    assert 100 - m.hp >= 5
    # player 2 tiles away from center with base range 1 -> untouched
    assert p.hp == p_hp


def test_explosion_destroys_floor_items_and_chains(game_with_player):
    g, p, floor = game_with_player
    cx, cy = p.pos.x + 3, p.pos.y
    # Force open floor across the blast neighborhood (see comment in the
    # radius-damage test above re: fixed fixture seed).
    floor.grid[cy][cx - 1] = TileType.FLOOR
    floor.grid[cy][cx] = TileType.FLOOR
    floor.grid[cy][cx + 1] = TileType.FLOOR
    floor.rebuild_flags()
    _place(floor, Bomb(id="bA", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    _place(floor, Bomb(id="bB", pos=Position(x=cx + 1, y=cy)))      # unlit neighbor
    from app.engine.entities.items_consumable import GooBlob
    _place(floor, GooBlob(id="loot", pos=Position(x=cx - 1, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    assert "bA" not in floor.items
    assert "bB" not in floor.items          # chain-detonated
    assert "loot" not in floor.items        # destroyed
    assert len(_events(g, "BOMB_BLAST")) == 2


def test_explosion_destroys_flammable_terrain(game_with_player):
    g, p, floor = game_with_player
    cx, cy = p.pos.x + 3, p.pos.y
    floor.grid[cy][cx + 1] = TileType.BARRICADE
    floor.grid[cy - 1][cx] = TileType.HIGH_GRASS
    floor.rebuild_flags()
    _place(floor, Bomb(id="bt", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    assert floor.grid[cy][cx + 1] != TileType.BARRICADE
    assert floor.grid[cy - 1][cx] != TileType.HIGH_GRASS
    assert _events(g, "MAP_PATCH")


def test_non_destructive_bomb_spares_items_and_terrain(game_with_player):
    g, p, floor = game_with_player
    cx, cy = p.pos.x + 3, p.pos.y
    floor.grid[cy][cx + 1] = TileType.BARRICADE
    floor.rebuild_flags()
    from app.engine.entities.items_consumable import GooBlob
    _place(floor, GooBlob(id="loot2", pos=Position(x=cx - 1, y=cy)))
    _place(floor, RegrowthBomb(id="br", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    assert "loot2" in floor.items
    assert floor.grid[cy][cx + 1] == TileType.BARRICADE


def test_regrowth_bomb_deals_no_damage(game_with_player):
    g, p, floor = game_with_player
    from app.engine.entities.player import Mob
    cx, cy = p.pos.x + 3, p.pos.y
    from app.engine.dungeon.generator import TileType
    for x in range(cx - 3, cx + 4):
        for y in range(cy - 3, cy + 4):
            if 0 <= x < floor.width and 0 <= y < floor.height:
                floor.grid[y][x] = TileType.FLOOR
    floor.rebuild_flags()
    m = Mob(id="mr", name="Rat", pos=Position(x=cx + 1, y=cy), hp=100, max_hp=100, faction="dungeon")
    floor.mobs["mr"] = m
    _place(floor, RegrowthBomb(id="rnd", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    assert m.hp == 100                      # SPD: regrowth bomb never harms


def test_explosion_spares_equipment_and_uniques(game_with_player):
    g, p, floor = game_with_player
    from app.engine.dungeon.generator import TileType
    cx, cy = p.pos.x + 3, p.pos.y
    for x in range(cx - 2, cx + 3):
        floor.grid[cy][x] = TileType.FLOOR
    floor.rebuild_flags()
    from app.engine.entities.items_equip import Dagger
    from app.engine.entities.items_wands import WandOfMagicMissile
    _place(floor, Dagger(id="dg", pos=Position(x=cx - 1, y=cy)))
    _place(floor, WandOfMagicMissile(id="wd", pos=Position(x=cx + 1, y=cy)))
    _place(floor, Bomb(id="beq", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    assert "dg" in floor.items and "wd" in floor.items


def _force_open_block(floor, cx, cy, radius=2):
    # Force open floor around the blast: procedural gen is seeded from the
    # fixture's fixed game_id, so it's not guaranteed open by default (see
    # comment in the radius-damage test above re: the same fixture quirk).
    for x in range(cx - radius, cx + radius + 1):
        for y in range(cy - radius, cy + radius + 1):
            if 0 <= x < floor.width and 0 <= y < floor.height:
                floor.grid[y][x] = TileType.FLOOR
    floor.rebuild_flags()


def test_firebomb_seeds_fire_blob(game_with_player):
    g, p, floor = game_with_player
    cx, cy = p.pos.x + 4, p.pos.y
    _force_open_block(floor, cx, cy)
    _place(floor, Firebomb(id="fb", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    fires = [b for b in floor.blob_areas.values() if b["type"] == "fire"]
    assert fires and len(fires[0]["cells"]) >= 5


def test_frost_bomb_freezes_and_douses(game_with_player):
    g, p, floor = game_with_player
    from app.engine.entities.player import Mob
    cx, cy = p.pos.x + 4, p.pos.y
    _force_open_block(floor, cx, cy)
    m = Mob(id="mf", name="Rat", pos=Position(x=cx + 1, y=cy), hp=100, max_hp=100, faction="dungeon")
    floor.mobs["mf"] = m
    floor.blob_areas["firez"] = {"type": "fire", "cells": {(cx, cy)}, "volume": {(cx, cy): 5}}
    _place(floor, FrostBomb(id="frb", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    assert m.has_buff("frozen")
    assert not any(b["type"] == "fire" and b["cells"] & {(cx, cy)}
                   for b in floor.blob_areas.values())


def test_holy_bomb_bonus_vs_undead_only(game_with_player):
    g, p, floor = game_with_player
    from app.engine.entities.player import Mob
    import random
    random.seed(0)  # deterministic rolls (both mobs' base+bonus draw from
                     # the shared RNG; see tests/test_goo_boss.py for precedent)
    cx, cy = p.pos.x + 4, p.pos.y
    _force_open_block(floor, cx, cy)
    undead = Mob(id="mu", name="Skeleton", pos=Position(x=cx + 1, y=cy),
                 hp=1000, max_hp=1000, faction="dungeon", properties=["UNDEAD"])
    living = Mob(id="ml", name="Rat", pos=Position(x=cx - 1, y=cy),
                 hp=1000, max_hp=1000, faction="dungeon")
    floor.mobs.update({"mu": undead, "ml": living})
    _place(floor, HolyBomb(id="hb", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    # undead take the base roll plus a separate 50% holy roll
    assert (1000 - undead.hp) > (1000 - living.hp)


def test_smoke_bomb_seeds_smoke_blob(game_with_player):
    g, p, floor = game_with_player
    cx, cy = p.pos.x + 4, p.pos.y
    _force_open_block(floor, cx, cy, 3)
    _place(floor, SmokeBomb(id="sb", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    fog = [b for b in floor.blob_areas.values() if b["type"] == "shrouding_fog"]
    assert fog
    vol = fog[0]["volume"]
    # Every reachable cell holds 40; unspent budget (1000-40*cells) piles onto
    # the center so the fog lingers (SmokeBomb.java centerVolume).
    assert all(v >= 40 for v in vol.values())
    assert vol[(cx, cy)] == 40 + (1000 - 40 * len(vol))
    # the blob must actually tick: a mob standing in it gets blinded
    from app.engine.entities.player import Mob
    m = Mob(id="ms", name="Rat", pos=Position(x=cx, y=cy), hp=100, max_hp=100, faction="dungeon")
    floor.mobs["ms"] = m
    from app.engine.game.blobs import tick_blob_areas, GAS_TICK_INTERVAL
    for _ in range(GAS_TICK_INTERVAL + 1):
        tick_blob_areas({p.floor_id: floor}, {"p1": p})
    assert m.has_buff("blindness")


def test_woolly_bomb_spawns_sheep(game_with_player):
    g, p, floor = game_with_player
    cx, cy = p.pos.x + 4, p.pos.y
    # Sheep placement reaches EXPLOSION_RANGE+2 == 4 tiles out; force that
    # whole neighborhood open (fixed fixture seed puts walls here otherwise,
    # see comment on _force_open_block above).
    _force_open_block(floor, cx, cy, 4)
    _place(floor, WoollyBomb(id="wb", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    sheep = [m for m in floor.mobs.values() if m.name == "Sheep"]
    assert len(sheep) >= 3
    assert all(s.has_buff("sheep_timer") for s in sheep)
    # Depth 1 (non-boss): Sheep.initialize(200) +/- 2 jitter, far longer than a
    # Stone of Flock sheep (8) -- woolly bombs make lasting barriers.
    assert all(197 <= s.get_buff("sheep_timer").remaining <= 202 for s in sheep)


def test_flashbang_quarter_damage_plus_paralysis(game_with_player):
    g, p, floor = game_with_player
    from app.engine.entities.player import Mob
    cx, cy = p.pos.x + 4, p.pos.y
    _force_open_block(floor, cx, cy)
    m = Mob(id="mz", name="Rat", pos=Position(x=cx + 1, y=cy), hp=1000, max_hp=1000, faction="dungeon")
    floor.mobs["mz"] = m
    _place(floor, FlashBangBomb(id="fl", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    assert m.has_buff("paralysis")
    # base blast + quarter bonus: at depth 1 total stays well under 40
    assert 0 < (1000 - m.hp) < 40


def test_shrapnel_bomb_blocked_by_line_of_sight(game_with_player):
    # ShrapnelBomb hits by LOS, not flood-fill BFS: a wall directly between the
    # blast and a target spares it, even though a BFS path wraps around the wall.
    g, p, floor = game_with_player
    from app.engine.entities.player import Mob
    cx, cy = p.pos.x + 6, p.pos.y
    _force_open_block(floor, cx, cy, 3)
    floor.grid[cy][cx + 1] = TileType.WALL          # wall on the sightline
    floor.rebuild_flags()
    walled = Mob(id="mw", name="Rat", pos=Position(x=cx + 2, y=cy),
                 hp=100, max_hp=100, faction="dungeon")
    seen = Mob(id="ms", name="Rat", pos=Position(x=cx, y=cy + 2),
               hp=100, max_hp=100, faction="dungeon")
    floor.mobs.update({"mw": walled, "ms": seen})
    _place(floor, ShrapnelBomb(id="shr", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    assert walled.hp == 100                          # behind the wall: spared
    assert seen.hp < 100                             # open line of sight: hit


def test_dm300_drops_metal_shards():
    # DM-300.die() drops 2-4 MetalShards (Random.chances{0,0,6,3,1}), the
    # Shrapnel Bomb reagent -- confirm the loot lands in that range and hits
    # every count across seeds.
    import random
    from app.engine.entities.mobs import DM300
    from app.engine.systems.loot import roll_drops
    seen = set()
    for seed in range(60):
        random.seed(seed)
        dm = DM300(id=f"dm{seed}", pos=Position(x=1, y=1))
        shards = [d for d in roll_drops(dm, {}, 1, 1) if isinstance(d, MetalShard)]
        seen.add(len(shards))
    assert seen == {2, 3, 4}


def test_noisemaker_arms_then_triggers_on_contact(game_with_player):
    g, p, floor = game_with_player
    from app.engine.entities.player import Mob
    cx, cy = p.pos.x + 4, p.pos.y
    nm = _place(floor, Noisemaker(id="nm", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    assert nm.armed and "nm" in floor.items          # armed, not exploded
    m = Mob(id="mn", name="Rat", pos=Position(x=cx + 3, y=cy), hp=100, max_hp=100, faction="dungeon")
    floor.mobs["mn"] = m
    for _ in range(120):                              # alert period
        g.tick_bombs(floor, p.floor_id)
    assert m.last_known_target_pos is not None        # beckoned
    m.pos = Position(x=cx, y=cy)                      # steps onto it
    g.tick_bombs(floor, p.floor_id)
    assert "nm" not in floor.items                    # detonated
    assert m.hp < 100


def test_armed_noisemaker_detonates_on_pickup(game_with_player):
    g, p, floor = game_with_player
    nm = _place(floor, Noisemaker(id="nm2", armed=True, fuse_ticks=50,
                                  pos=Position(x=p.pos.x + 1, y=p.pos.y)))
    g.move_entity("p1", 1, 0)
    assert "nm2" not in floor.items
    assert not any(isinstance(i, Noisemaker) for i in p.inventory)


def test_regrowth_bomb_grows_grass_and_heals_allies(game_with_player):
    g, p, floor = game_with_player
    from app.engine.entities.player import Mob
    from app.engine.entities.base import Faction
    cx, cy = p.pos.x + 4, p.pos.y
    _force_open_block(floor, cx, cy, 3)                    # FLOOR is grass-able
    # Injured, poisoned player and an injured allied mob within blast range.
    p.pos = Position(x=cx + 1, y=cy)
    p.hp = 1
    p.add_buff("poison", duration=5.0, level=1)
    ally = Mob(id="al", name="Ghost", pos=Position(x=cx - 1, y=cy),
               hp=1, max_hp=50, faction=Faction.PLAYER)
    ally.add_buff("bleeding", duration=5.0, level=1)
    floor.mobs["al"] = ally
    _place(floor, RegrowthBomb(id="rg", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    assert p.heal_left > 0 and not p.has_buff("poison")    # healed + cured
    assert ally.hp == ally.max_hp and not ally.has_buff("bleeding")
    assert floor.grid[cy][cx] == TileType.HIGH_GRASS       # blanketed in grass
    assert _events(g, "MAP_PATCH")


def test_regrowth_bomb_leaves_enemies_unhealed(game_with_player):
    g, p, floor = game_with_player
    from app.engine.entities.player import Mob
    cx, cy = p.pos.x + 4, p.pos.y
    _force_open_block(floor, cx, cy, 3)
    enemy = Mob(id="en", name="Rat", pos=Position(x=cx + 1, y=cy),
                hp=1, max_hp=100, faction="dungeon")
    floor.mobs["en"] = enemy
    _place(floor, RegrowthBomb(id="rg2", fuse_ticks=1, pos=Position(x=cx, y=cy)))
    g.tick_bombs(floor, p.floor_id)
    assert enemy.hp == 1                                   # dungeon faction: no heal


# --- Bomb.EnhanceBomb recipe (Bomb.java) ------------------------------------
from app.engine.alchemy.recipes import ENHANCE_BOMB_INGREDIENTS, EnhanceBombRecipe
from app.engine.entities.items_consumable import GooBlob
from app.engine.entities.items_potions import (
    HealthPotion, PotionOfFrost, PotionOfInvisibility, PotionOfLiquidFlame,
)
from app.engine.entities.items_scrolls import (
    ScrollOfMirrorImage, ScrollOfRage, ScrollOfRecharging, ScrollOfRemoveCurse,
)


def _rec_units(*items):
    out = []
    for it in items:
        u = it.model_copy(deep=True)
        u.quantity = 1
        out.append(u)
    return out


def test_enhance_bomb_maps_every_ingredient(game):
    r = EnhanceBombRecipe()
    for ing_cls, (bomb_cls, energy) in ENHANCE_BOMB_INGREDIENTS.items():
        ing = ing_cls()
        game.identified_kinds.add(ing.kind)               # always-identified reqs
        units = _rec_units(Bomb(), ing)
        assert r.test_ingredients(game, units), ing_cls.__name__
        assert r.cost(units) == energy, ing_cls.__name__
        out = r.brew(game, units)
        assert isinstance(out, bomb_cls) and out.quantity == 1, ing_cls.__name__


def test_enhance_bomb_needs_identified_ingredient(game):
    r = EnhanceBombRecipe()
    units = _rec_units(Bomb(), PotionOfFrost())           # frost potion unknown
    assert not r.test_ingredients(game, units)
    game.identified_kinds.add(PotionOfFrost().kind)
    assert r.test_ingredients(game, _rec_units(Bomb(), PotionOfFrost()))


def test_enhance_bomb_requires_plain_base_bomb(game):
    # SPD getClass().equals(Bomb.class): an already-enhanced bomb can't be a base.
    r = EnhanceBombRecipe()
    game.identified_kinds.add(PotionOfLiquidFlame().kind)
    assert not r.test_ingredients(game, _rec_units(Firebomb(), PotionOfLiquidFlame()))
    assert r.test_ingredients(game, _rec_units(Bomb(), PotionOfLiquidFlame()))


def test_enhance_bomb_found_via_registry(game):
    from app.engine.alchemy.registry import find_recipes
    units = _rec_units(Bomb(), GooBlob())                 # GooBlob always identified
    recipes = find_recipes(game, units)
    assert any(isinstance(r, EnhanceBombRecipe) for r in recipes)
    out = next(r for r in recipes if isinstance(r, EnhanceBombRecipe)).brew(game, units)
    assert isinstance(out, ArcaneBomb)
