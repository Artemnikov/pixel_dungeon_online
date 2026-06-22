"""Regression test for a real-time pacing bug in YogDzewa/DwarfKing's AI.

This engine's mob AI runs once per server tick (20Hz, see main.py's
global_game_loop / GameInstance.update_tick). Cooldown counters decremented
by 1 per tick call must be expressed in ticks, not in the original game's
turn counts -- the established idiom elsewhere in this codebase scales by
~20 (see OOZE_TICK_INTERVAL/GOO_WATER_HEAL_INTERVAL in constants.py, both
"20 ticks (~1s at 20Hz)").

ai_yog_dzewa.py and ai_dwarf_king.py ported their summon/ability cooldowns
as raw, unscaled Java turn-count constants (e.g. YogDzewa.java's
MIN/MAX_SUMMON_CD = 10/15), so they resolved in 10-15 *ticks* (0.5-0.75
real seconds) instead of an equivalent number of real seconds -- a
relentless, "infinite-looking" flood of summoned minions.
"""

import random

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import Faction, Player, Position
from app.engine.entities.mobs import DwarfKing, YogDzewa
from app.engine.game.floor_state import FloorState
from app.engine.manager import GameInstance


def make_floor(floor_id, w=10, h=10):
    grid = [[TileType.FLOOR for _ in range(w)] for _ in range(h)]
    floor = FloorState(floor_id=floor_id, grid=grid, rooms=[], mobs={}, items={}, region="halls")
    floor.rebuild_flags()
    floor.mob_limit = 99
    return floor


def make_game(floor):
    game = GameInstance(f"test-boss-pacing-{floor.floor_id}")
    game.players = {}
    game.floors[floor.floor_id] = floor
    game.depth = floor.floor_id
    return game


def make_player(x, y):
    return Player(id="p1", name="Hero", pos=Position(x=x, y=y), hp=100, max_hp=100,
                  attack=10, defense=0, floor_id=25)


def test_yog_summon_cooldown_is_tick_scaled(monkeypatch):
    floor = make_floor(25)
    game = make_game(floor)

    yog = YogDzewa(id="yog1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    yog.fight_started = True
    yog.phase = 1
    yog.summon_cooldown = 0  # ready to summon this tick
    yog.ability_cooldown = 999  # keep the death-ray branch from firing too
    floor.mobs[yog.id] = yog

    target = make_player(x=5, y=7)
    game.players[target.id] = target

    monkeypatch.setattr(random, "randint", lambda a, b: 10)

    game._update_yog_dzewa(yog, floor, floor.floor_id)

    # phase=1 -> raw cooldown = randint(10,15)-(1-1) = 10 "turns".
    # Tick-scaled (x20, matching OOZE_TICK_INTERVAL/GOO_WATER_HEAL_INTERVAL) = 200 ticks (10s).
    assert yog.summon_cooldown == 200


def test_yog_ability_cooldown_is_tick_scaled(monkeypatch):
    floor = make_floor(25)
    game = make_game(floor)

    yog = YogDzewa(id="yog1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    yog.fight_started = True
    yog.phase = 1
    yog.ability_cooldown = 0  # ready to fire this tick
    yog.summon_cooldown = 999  # keep the summon branch from firing too
    floor.mobs[yog.id] = yog

    target = make_player(x=5, y=7)
    game.players[target.id] = target

    monkeypatch.setattr(random, "randint", lambda a, b: 10)
    monkeypatch.setattr(random, "random", lambda: 0.0)  # acu=0 <= df=0 -> beam misses, deterministic

    game._update_yog_dzewa(yog, floor, floor.floor_id)

    # phase=1 -> raw cooldown = randint(10,15)-(1-1) = 10 "turns" -> 200 ticks.
    assert yog.ability_cooldown == 200


def test_dwarf_king_summon_cooldown_is_tick_scaled(monkeypatch):
    floor = make_floor(20)
    floor.dk_summon_spots = [(5, 6), (5, 4), (6, 5), (4, 5)]
    game = make_game(floor)

    dk = DwarfKing(id="dk1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    dk.fight_started = True
    dk.phase = 1
    dk.summon_cooldown = 0  # ready to summon this tick
    floor.mobs[dk.id] = dk

    target = make_player(x=5, y=8)
    game.players[target.id] = target

    monkeypatch.setattr(random, "randint", lambda a, b: 10)

    game._update_dwarf_king(dk, floor, floor.floor_id)

    # phase != 3 -> raw cooldown = randint(10,14) = 10 "turns" -> 200 ticks (10s).
    assert dk.summon_cooldown == 200
