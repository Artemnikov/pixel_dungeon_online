import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.items_artifacts import TimekeepersHourglass
from app.engine.entities.mobs import Rat
from app.engine.entities.base import Position
from app.engine.manager import GameInstance
import app.engine.entities.artifact_actions as aa


def _upgrade(h, times):
    for _ in range(times):
        h.level += 1
        h.on_upgrade()


def _game():
    g = GameInstance("t")
    p = g.add_player("p1", "Hero", "warrior")
    return g, p


def _add_mob(g, p, dx=2):
    floor = g._get_or_create_floor(p.floor_id)
    rat = Rat(id="rat1", pos=Position(x=p.pos.x + dx, y=p.pos.y))
    floor.mobs[rat.id] = rat
    return rat


# --- model -----------------------------------------------------------------

def test_charge_cap_formula_level_cap_5():
    h = TimekeepersHourglass()
    assert h.level_cap == 5
    assert h.charge == 5 and h.charge_cap == 5    # 5 + 0
    _upgrade(h, 5)
    assert h.level == 5
    assert h.charge_cap == 10                      # 5 + 5


# --- FREEZE ----------------------------------------------------------------

def test_freeze_consumes_two_charges_and_freezes_hostiles():
    g, p = _game()
    rat = _add_mob(g, p)
    h = TimekeepersHourglass(id="hg")
    h.charge = 5
    aa.action_freeze(g, p, h)
    assert h.charge == 3                            # min(charge, 2) consumed
    assert rat.freeze_ticks > 0


def test_freeze_cursed_is_noop():
    g, p = _game()
    _add_mob(g, p)
    h = TimekeepersHourglass(id="hg", cursed=True)
    h.charge = 5
    aa.action_freeze(g, p, h)
    assert h.charge == 5


# --- STASIS ----------------------------------------------------------------

def test_stasis_consumes_two_charges_and_buffs_player():
    g, p = _game()
    h = TimekeepersHourglass(id="hg")
    h.charge = 5
    aa.action_stasis(g, p, h)
    assert h.charge == 3
    assert p.has_buff("time_stasis")


def test_stasised_player_is_untargetable():
    g, p = _game()
    rat = _add_mob(g, p)
    p.add_buff("time_stasis", duration=5.0)
    assert g._find_nearest_player(rat.pos, p.floor_id) is None


def test_stasised_player_is_invulnerable():
    g, p = _game()
    p.add_buff("time_stasis", duration=5.0)
    hp0 = p.hp
    dealt = p.take_damage(5)
    assert dealt == 0
    assert p.hp == hp0


# --- recharge --------------------------------------------------------------

def test_recharge_accrues_to_cap():
    from app.engine.game.artifacts import ArtifactsMixin, _SLOW_RECHARGE
    h = TimekeepersHourglass(id="hg")
    h.charge = 0
    ArtifactsMixin._tick_hourglass(None, None, h, _SLOW_RECHARGE + 0.01)
    assert h.charge == 1
    ArtifactsMixin._tick_hourglass(None, None, h, _SLOW_RECHARGE * 20)
    assert h.charge == h.charge_cap
