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
