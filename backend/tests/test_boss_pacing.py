"""Real-time pacing of the Dwarf King's once-per-turn act.

The Dwarf King's AI runs every 40 Hz tick but acts once per SPD turn
(`act_ticks` reaching TICKS_PER_TURN), so its turn-denominated cooldowns
keep their SPD length in real time. (Yog-Dzewa runs on the shared SPD act
clock instead; see test_yog_boss_fight.py.)
"""

from app.engine.entities.base import Faction, Position
from app.engine.entities.player import Player
from app.engine.entities.mobs import DwarfKing
from app.engine.game.constants import TICKS_PER_TURN
from app.engine.game.ai_dwarf_king import _update_dwarf_king

from conftest import make_game_with_floors, make_open_floor, partial

make_floor = partial(make_open_floor, region="halls", mob_limit=99)
make_game = make_game_with_floors


def make_player(x, y):
    return Player(id="p1", name="Hero", pos=Position(x=x, y=y), hp=100, max_hp=100,
                  attack=10, defense=0, floor_id=25)


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

    import app.engine.game.ai_dwarf_king as ai
    monkeypatch.setattr(ai, "normal_int_range", lambda a, b: 10)

    # DwarfKing.act() runs once per game turn, so its 10-turn cooldown spans
    # 10 * TICKS_PER_TURN ticks rather than 10 ticks.
    for _ in range(TICKS_PER_TURN):
        _update_dwarf_king(game, dk, floor, floor.floor_id)
    assert dk.summon_cooldown == 10

    for _ in range(TICKS_PER_TURN * 9):
        _update_dwarf_king(game, dk, floor, floor.floor_id)
    assert dk.summon_cooldown == 1
    assert dk.summons_made == 1
