import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.base import Position
from app.engine.entities.mobs import Tengu
from app.engine.dungeon.spd_levelgen import prison_boss_layout as layout
from app.engine.manager import GameInstance
from app.engine.game.constants import BOSS_RESPAWN_TICKS, PUBLIC_ROOM_ID


def make_public_game():
    game = GameInstance(PUBLIC_ROOM_ID)
    game.players = {}
    floor = game.generate_floor(10)
    player = game.add_player("p1", "Hero")
    player.floor_id = 10
    player.pos = Position(x=layout.TENGU_CELL_CENTER.x, y=layout.TENGU_CELL.top + 2)
    return game, floor


def to_fight_pause(game, floor):
    """Drive the state machine START -> FIGHT_START -> FIGHT_PAUSE."""
    game._update_prison_boss(floor, 10)          # -> FIGHT_START
    tengu = next(m for m in floor.mobs.values() if isinstance(m, Tengu))
    tengu.hp = tengu.max_hp // 2                 # is_enraged() == True
    game._update_prison_boss(floor, 10)          # -> FIGHT_PAUSE (Tengu removed)


def alive_tengus(game, floor):
    return [m for m in floor.mobs.values() if isinstance(m, Tengu) and m.is_alive]


def test_no_respawn_before_trigger_start_state():
    """Before the fight is triggered (tengu_state == START), generic cooldown
    respawn must not spawn a Tengu."""
    game = GameInstance(PUBLIC_ROOM_ID)
    game.players = {}
    floor = game.generate_floor(10)
    player = game.add_player("p1", "Hero")
    player.floor_id = 10
    # Player is in entrance room, hasn't stepped into cell yet
    player.pos = Position(x=layout.ENTRANCE_ROOM.left + 1, y=layout.ENTRANCE_ROOM.top + 1)

    assert floor.tengu_state == "START"
    assert not alive_tengus(game, floor)

    floor.boss_dead_ticks = BOSS_RESPAWN_TICKS + 1
    game._process_boss_respawns(10, floor, [player])

    assert floor.tengu_state == "START"
    assert not alive_tengus(game, floor)


def test_no_respawn_during_fight_pause_between_stages():
    """The 'between stages' FIGHT_PAUSE must NOT trigger a boss respawn even
    after the cooldown elapses -- only a full defeat (WON) may be resurrected."""
    game, floor = make_public_game()
    to_fight_pause(game, floor)

    assert floor.tengu_state == "FIGHT_PAUSE"
    assert not alive_tengus(game, floor)          # Tengu left the world for the pause

    # Force the cooldown past its threshold and let the generic respawn path run.
    floor.boss_dead_ticks = BOSS_RESPAWN_TICKS + 1
    game._process_boss_respawns(10, floor, [game.players["p1"]])

    assert floor.tengu_state == "FIGHT_PAUSE"     # unchanged: still between stages
    assert not alive_tengus(game, floor)          # no stray/extra Tengu spawned


def test_no_double_tengu_after_arena_restore():
    """Regression for the race where a respawn during FIGHT_PAUSE leaves two
    Tengus once pause->arena restores the stashed original."""
    game, floor = make_public_game()
    to_fight_pause(game, floor)

    player = game.players["p1"]
    player.pos = Position(x=layout.START_HALLWAY.left + 2, y=layout.START_HALLWAY.top)
    game._update_prison_boss(floor, 10)           # -> FIGHT_ARENA (restores original)

    assert floor.tengu_state == "FIGHT_ARENA"
    tengus = alive_tengus(game, floor)
    assert len(tengus) == 1                        # exactly one Tengu, no duplicate


def test_respawn_after_full_defeat_won():
    """Positive control: once the boss is fully defeated (WON), the public-room
    cooldown respawn path must bring a fresh Tengu back."""
    game, floor = make_public_game()
    to_fight_pause(game, floor)

    player = game.players["p1"]
    player.pos = Position(x=layout.START_HALLWAY.left + 2, y=layout.START_HALLWAY.top)
    game._update_prison_boss(floor, 10)           # -> FIGHT_ARENA
    tengu_id = tengus_id(game, floor)
    del floor.mobs[tengu_id]                       # simulate full defeat
    game._update_prison_boss(floor, 10)           # arena->WON on death

    assert floor.tengu_state == "WON"
    assert not alive_tengus(game, floor)

    floor.boss_dead_ticks = BOSS_RESPAWN_TICKS + 1
    game._process_boss_respawns(10, floor, [game.players["p1"]])

    tengus = alive_tengus(game, floor)
    assert len(tengus) == 1                        # respawned exactly once
    assert tengus[0].pos.x == layout.TENGU_CELL_CENTER.x
    assert tengus[0].pos.y == layout.TENGU_CELL_CENTER.y


def tengus_id(game, floor):
    return next(m.id for m in floor.mobs.values() if isinstance(m, Tengu))
