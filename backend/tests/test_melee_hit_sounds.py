"""The attacker's own melee hit/miss sounds come from the server outcome.

The client no longer plays a hit sound when the hero swings, so every landed
hit must reach the attacker as a PLAY_SOUND, every miss must not, and the
sounds observers hear must be the same ones.
"""

import random

import pytest

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.mobs.sewers import Rat
from app.engine.game.constants import TICK_DURATION
from app.engine.game.movement import melee as melee_module
from app.engine.manager import GameInstance
from app.engine.turn.instance import TurnBasedGameInstance
from app.schemas import messages as msg
from app.schemas.common import Direction

from conftest import open_floor_on_game

HIT_SOUNDS = {"HIT_SLASH", "HIT_STAB", "HIT_CRUSH", "HIT_BODY", "HIT", "HIT_PARRY", "HIT_ARROW"}


def _sounds(events):
    return [e["data"]["sound"] for e in events if e["type"] == "PLAY_SOUND"]


def _spawn_rat(game, x, y):
    floor = game._get_or_create_floor(1)
    rat = game._spawn_mob_at(Rat, x, y)
    rat.pos = Position(x=x, y=y)
    rat.floor_id = 1
    floor.mobs[rat.id] = rat
    return rat


def _realtime_duel():
    game = GameInstance("melee-sounds")
    game.players = {}
    open_floor_on_game(game)
    hero = game.add_player("p1", "Hero")
    hero.pos = Position(x=5, y=5)
    hero.floor_id = 1
    observer = game.add_player("p2", "Observer")
    observer.pos = Position(x=5, y=7)
    observer.floor_id = 1
    rat = _spawn_rat(game, 6, 5)
    game.flush_events()
    return game, hero, observer, rat


def _attack_with(monkeypatch, game, hero, rat, result):
    monkeypatch.setattr(melee_module, "resolve_melee_attack", lambda *a, **kw: dict(result))
    hero.last_attack_time = 0.0
    game.move_entity(hero.id, 1, 0)
    return game.flush_events()


def test_echo_to_source_reaches_source_and_keeps_los_scope():
    game = GameInstance("echo")
    game.players = {}
    floor = open_floor_on_game(game)
    src = game.add_player("p1", "Src")
    src.pos = Position(x=2, y=2)
    near = game.add_player("p2", "Near")
    near.pos = Position(x=4, y=2)
    far = game.add_player("p3", "Far")
    far.pos = Position(x=10, y=2)
    for y in range(20):
        floor.grid[y][7] = TileType.WALL
    floor.rebuild_flags()

    game.add_event("PLAY_SOUND", {"sound": "HIT_SLASH"}, floor_id=1, source_player_id=src.id, echo_to_source=True)
    game.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=1, source_player_id=src.id)
    events = game.flush_events()

    assert _sounds(game.filter_events_for_player(events, src.id)) == ["HIT_SLASH"]
    assert _sounds(game.filter_events_for_player(events, near.id)) == ["HIT_SLASH", "PUFF"]
    assert _sounds(game.filter_events_for_player(events, far.id)) == []


def test_landed_hit_sound_reaches_attacker_and_observer_alike(monkeypatch):
    game, hero, observer, rat = _realtime_duel()
    events = _attack_with(monkeypatch, game, hero, rat, {
        "missed": False, "damage": 1, "surprise": False, "crit": False, "grim_proc": False,
    })
    mine = _sounds(game.filter_events_for_player(events, hero.id))
    theirs = _sounds(game.filter_events_for_player(events, observer.id))
    assert len(mine) == 1 and mine[0] in HIT_SOUNDS
    assert mine == theirs


def test_missed_swing_sends_no_hit_sound(monkeypatch):
    game, hero, observer, rat = _realtime_duel()
    events = _attack_with(monkeypatch, game, hero, rat, {
        "missed": True, "damage": 0, "defense_verb": "dodged",
    })
    mine = game.filter_events_for_player(events, hero.id)
    assert [e["type"] for e in mine if e["type"] in ("MISS", "ATTACK")] == ["MISS", "ATTACK"]
    assert not HIT_SOUNDS.intersection(_sounds(mine))


def test_surprise_hit_plays_weapon_sound_and_hit_strong(monkeypatch):
    game, hero, observer, rat = _realtime_duel()
    events = _attack_with(monkeypatch, game, hero, rat, {
        "missed": False, "damage": 1, "surprise": True, "crit": True, "grim_proc": False,
    })
    mine = _sounds(game.filter_events_for_player(events, hero.id))
    assert len(mine) == 2 and mine[0] in HIT_SOUNDS and mine[1] == "HIT_STRONG"
    assert _sounds(game.filter_events_for_player(events, observer.id)) == mine


def test_grim_proc_adds_no_extra_sound(monkeypatch):
    game, hero, observer, rat = _realtime_duel()
    events = _attack_with(monkeypatch, game, hero, rat, {
        "missed": False, "damage": 1, "surprise": False, "crit": False, "grim_proc": True,
    })
    mine = _sounds(game.filter_events_for_player(events, hero.id))
    assert len(mine) == 1 and mine[0] in HIT_SOUNDS


def test_events_from_melee_resolution_reach_the_attacker(monkeypatch):
    game, hero, observer, rat = _realtime_duel()

    def fake_resolve(*args, add_event, **kwargs):
        add_event("SHOCKING_PROC", {"source": hero.id, "defender": rat.id, "defender_x": 6, "defender_y": 5, "chain_targets": []})
        return {"missed": False, "damage": 1, "surprise": False, "crit": False, "grim_proc": False}

    monkeypatch.setattr(melee_module, "resolve_melee_attack", fake_resolve)
    game.move_entity(hero.id, 1, 0)
    events = game.flush_events()
    for pid in (hero.id, observer.id):
        assert any(e["type"] == "SHOCKING_PROC" for e in game.filter_events_for_player(events, pid))


def test_combo_strike_plays_server_hit_sound_for_attacker(monkeypatch):
    game, hero, observer, rat = _realtime_duel()
    from app.engine.systems import combat

    monkeypatch.setattr(combat, "resolve_melee_attack", lambda *a, **kw: {
        "missed": False, "damage": 1, "surprise": True, "crit": True, "grim_proc": False,
    })
    floor = game._get_or_create_floor(1)
    game._combo_strike(hero, rat, floor, 1, "clobber")
    events = game.flush_events()
    mine = _sounds(game.filter_events_for_player(events, hero.id))
    assert len(mine) == 2 and mine[0] in HIT_SOUNDS and mine[1] == "HIT_STRONG"


@pytest.mark.parametrize("seed", range(8))
def test_turn_based_every_attack_outcome_matches_its_sound(seed):
    """End to end in a turn room: each resolved hero swing gives the hero a
    hit sound exactly when it landed (including the killing blow)."""
    random.seed(seed)
    game = TurnBasedGameInstance("turn-sounds")
    game.players = {}
    open_floor_on_game(game)
    hero = game.add_player("p1", "Hero")
    hero.pos = Position(x=5, y=5)
    hero.floor_id = 1
    rat = _spawn_rat(game, 6, 5)
    rat.ai_state = "hunting"

    def pump():
        out = []
        for _ in range(40):
            hero.movement._cooldown_until = 0.0
            game.update_tick(TICK_DURATION)
            out += game.filter_events_for_player(game.flush_events(), hero.id)
        return out

    pump()
    weapon_sound = hero.belongings.weapon.hit_sound
    swings = 0
    while rat.is_alive and swings < 40:
        assert game.submit_turn_action(hero.id, msg.Move(type="MOVE", direction=Direction.RIGHT))
        events = pump()
        assert any(e["type"] == "ATTACK" and e["data"]["source"] == hero.id for e in events)
        missed = any(e["type"] == "MISS" and e["data"]["source"] == hero.id for e in events)
        expected = [] if missed else [weapon_sound]
        assert [s for s in _sounds(events) if s == weapon_sound] == expected
        swings += 1
    assert not rat.is_alive


def test_duelist_ability_hit_sounds_reach_attacker():
    from app.engine.game.duelist_weapon_skills import WeaponSkill

    game, hero, observer, rat = _realtime_duel()
    res = {"missed": False, "damage": 1, "surprise": False, "grim_proc": False}
    WeaponSkill._emit_attack_events(None, game, hero, rat, res, hero.belongings.weapon, hit_sound="HIT_STAB")
    events = game.flush_events()
    mine = _sounds(game.filter_events_for_player(events, hero.id))
    assert mine == ["HIT_STAB", "HIT_STRONG"]
    assert _sounds(game.filter_events_for_player(events, observer.id)) == mine
