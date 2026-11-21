# Copyright (C) 2026 ArtemNikov
#
"""Boss countdowns that used to stall in turn rooms (Tengu bomb, DM-300 rocks)."""

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction, Position
from app.engine.entities.mobs import DM300, Tengu
from app.engine.game.ai_dm300 import _dm300_drop_rocks, _tick_dm300_pending_rockfall
from app.engine.game.constants import TENGU_BOMB_STEP_TICKS
from app.engine.turn.instance import TurnBasedGameInstance


def _room(depth):
    g = TurnBasedGameInstance("timers")
    g.players = {}
    floor = g._get_or_create_floor(depth)
    floor.grid = [[TileType.FLOOR for _ in range(16)] for _ in range(16)]
    floor.mobs.clear()
    floor.rebuild_flags()
    hero = g.add_player("p1", "Hero")
    hero.floor_id = depth
    hero.pos = Position(x=5, y=4)
    hero.hp = hero.max_hp = 500
    return g, hero, floor


def test_tengu_bomb_counts_down_one_step_per_turn_and_detonates():
    g, hero, floor = _room(10)
    tengu = Tengu(id="t1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    floor.mobs[tengu.id] = tengu
    assert g._tengu_throw_bomb(tengu, hero, floor, 10)
    assert tengu.bomb_timer == 3 * TENGU_BOMB_STEP_TICKS
    counts = []
    for _ in range(3):
        g.flush_events()
        g._update_tengu(tengu, floor, 10)
        events = g.flush_events()
        counts += [e["data"]["count"] for e in events if e["type"] == "TENGU_BOMB_COUNTDOWN"]
    assert counts == [2, 1]
    assert tengu.bomb_timer == 0


def test_dm300_rocks_land_on_the_targets_next_action():
    g, hero, floor = _room(15)
    dm = DM300(id="dm", pos=Position(x=8, y=8), faction=Faction.DUNGEON)
    floor.mobs[dm.id] = dm
    hero._last_turn_cost = 1.0
    _dm300_drop_rocks(g, dm, hero, floor, 15)
    assert dm.pending_rockfall is not None
    _tick_dm300_pending_rockfall(g, dm, floor, 15)
    assert dm.pending_rockfall is None


def test_bomb_fuse_advances_a_turn_per_turn():
    from app.engine.entities.items.bombs import Bomb
    g, hero, floor = _room(3)
    bomb = Bomb(pos=Position(x=2, y=2))
    bomb.fuse_ticks = 2 * 40
    floor.items[bomb.id] = bomb
    exploded = []
    g.explode_bomb = lambda f, fid, b: exploded.append(b.id)
    g.tick_bombs(floor, 3)
    assert not exploded
    g.tick_bombs(floor, 3)
    assert exploded == [bomb.id]
