"""Frost buff/debuff: SPD Frost roots the char (paralysed++), douses fire, and
leaves Chill when thawing on water. Mirrors items/../buffs/Frost.java."""
import pytest

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import Position
from app.engine.entities.buffs import add_buff, has_buff, is_frozen
from app.engine.entities.player import Mob
from app.engine.manager import GameInstance


@pytest.fixture
def game():
    g = GameInstance("t-frost")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)
    return g, p, floor


def _open(floor, x, y):
    floor.grid[y][x] = TileType.FLOOR
    floor.rebuild_flags()


def test_frost_douses_burning_and_chill():
    # Frost.attachTo: cold detaches Burning and overrides Chill.
    buffs = []
    add_buff(buffs, "burning", duration=8.0, level=1)
    add_buff(buffs, "chill", duration=5.0, level=1)
    add_buff(buffs, "frozen", duration=2.0, level=1)
    assert is_frozen(buffs)
    assert not has_buff(buffs, "burning")
    assert not has_buff(buffs, "chill")


def test_fire_does_not_thaw_frost():
    # Burning.attachTo only detaches Chill, never Frost -- a frozen char that
    # catches fire stays frozen (and now also burns).
    buffs = []
    add_buff(buffs, "frozen", duration=5.0, level=1)
    add_buff(buffs, "burning", duration=8.0, level=1)
    assert is_frozen(buffs) and has_buff(buffs, "burning")


def test_frozen_player_cannot_move(game):
    g, p, floor = game
    _open(floor, p.pos.x + 1, p.pos.y)
    p.add_buff("frost", duration=5.0, level=1)
    start = (p.pos.x, p.pos.y)
    g.move_entity("p1", 1, 0)
    assert (p.pos.x, p.pos.y) == start          # rooted


def test_frozen_mob_cannot_step_or_attack(game):
    g, p, floor = game
    mx, my = p.pos.x + 1, p.pos.y
    _open(floor, mx, my)
    m = Mob(id="m1", name="Rat", pos=Position(x=mx, y=my), hp=50, max_hp=50,
            faction="dungeon", last_attack_time=0.0)
    m.add_buff("frozen", duration=5.0, level=1)
    floor.mobs["m1"] = m
    hp0 = p.hp
    g.move_entity("m1", -1, 0)                   # step into player = attack
    assert (m.pos.x, m.pos.y) == (mx, my)        # didn't step
    assert m.last_attack_time == 0.0             # never reached combat
    assert p.hp == hp0
    g.move_entity("m1", 1, 0)                     # step away
    assert (m.pos.x, m.pos.y) == (mx, my)


def test_unfrozen_mob_still_attacks(game):
    # Control: without frost the same bump reaches combat (last_attack_time set),
    # proving the freeze -- not some unrelated guard -- blocked it above.
    g, p, floor = game
    mx, my = p.pos.x + 1, p.pos.y
    _open(floor, mx, my)
    m = Mob(id="m2", name="Rat", pos=Position(x=mx, y=my), hp=50, max_hp=50,
            faction="dungeon", last_attack_time=0.0)
    floor.mobs["m2"] = m
    g.move_entity("m2", -1, 0)
    assert m.last_attack_time > 0.0              # attack was resolved


def test_frost_thaw_on_water_leaves_chill(game):
    g, p, floor = game
    floor.grid[p.pos.y][p.pos.x] = TileType.FLOOR_WATER
    g._frost_thaw(p, floor)
    assert p.has_buff("chill")


def test_frost_thaw_on_dry_land_no_chill(game):
    g, p, floor = game
    floor.grid[p.pos.y][p.pos.x] = TileType.FLOOR
    g._frost_thaw(p, floor)
    assert not p.has_buff("chill")
