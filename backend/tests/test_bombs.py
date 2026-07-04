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
