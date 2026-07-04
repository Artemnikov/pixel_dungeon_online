import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.items_artifacts import ChaliceOfBlood
from app.engine.manager import GameInstance
import app.engine.entities.artifact_actions as aa
import app.engine.game.artifacts as ga


def _game():
    g = GameInstance("t")
    p = g.add_player("p1", "Hero", "warrior")
    return g, p


# --- prick damage formula --------------------------------------------------

def test_prick_damage_formula():
    assert (aa._min_prick_dmg(0), aa._max_prick_dmg(0)) == (3, 7)
    assert (aa._min_prick_dmg(3), aa._max_prick_dmg(3)) == (26, 38)
    assert (aa._min_prick_dmg(10), aa._max_prick_dmg(10)) == (253, 357)


# --- prick behaviour -------------------------------------------------------

def test_prick_upgrades_on_survival(monkeypatch):
    g, p = _game()
    p.max_hp = 100
    p.hp = 100
    ch = ChaliceOfBlood(id="ch")
    monkeypatch.setattr(aa, "_roll_prick_damage", lambda level: 5)
    aa.action_prick(g, p, ch)
    assert ch.level == 1
    assert not p.is_downed
    assert p.hp < 100


def test_prick_downs_on_lethal(monkeypatch):
    g, p = _game()
    p.max_hp = 20
    p.hp = 10
    ch = ChaliceOfBlood(id="ch")
    monkeypatch.setattr(aa, "_roll_prick_damage", lambda level: 999)
    aa.action_prick(g, p, ch)
    assert p.is_downed
    assert ch.level == 0            # no upgrade on death


def test_prick_noop_when_cursed(monkeypatch):
    g, p = _game()
    p.max_hp = 100; p.hp = 100
    ch = ChaliceOfBlood(id="ch", cursed=True)
    monkeypatch.setattr(aa, "_roll_prick_damage", lambda level: 5)
    aa.action_prick(g, p, ch)
    assert ch.level == 0
    assert p.hp == 100


def test_prick_noop_at_level_cap(monkeypatch):
    g, p = _game()
    p.max_hp = 100; p.hp = 100
    ch = ChaliceOfBlood(id="ch", level=10)
    monkeypatch.setattr(aa, "_roll_prick_damage", lambda level: 5)
    aa.action_prick(g, p, ch)
    assert p.hp == 100              # unchanged


# --- passive heal ----------------------------------------------------------

def test_chalice_heal_rate_formula():
    assert abs(ga._chalice_heal_rate(0) - 5/8.67) < 0.01
    assert abs(ga._chalice_heal_rate(10) - 2.5) < 0.01


def test_passive_heal_when_hurt():
    g, p = _game()
    p.max_hp = 100; p.hp = 50
    ch = ChaliceOfBlood(id="ch")
    ga.ArtifactsMixin._tick_chalice(g, p, ch, 20.0)   # ~0.577*20 ≈ 11 HP
    assert p.hp > 50


def test_no_heal_at_full_hp():
    g, p = _game()
    p.max_hp = 100; p.hp = 100
    ch = ChaliceOfBlood(id="ch")
    ga.ArtifactsMixin._tick_chalice(g, p, ch, 20.0)
    assert p.hp == 100


def test_no_heal_when_starving():
    g, p = _game()
    p.max_hp = 100; p.hp = 50
    p.hunger = 450
    ch = ChaliceOfBlood(id="ch")
    ga.ArtifactsMixin._tick_chalice(g, p, ch, 20.0)
    assert p.hp == 50
