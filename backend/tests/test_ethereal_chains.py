import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.items_artifacts import EtherealChains
from app.engine.entities.mobs import Rat
from app.engine.entities.base import Position
from app.engine.manager import GameInstance
from app.engine.systems.ballistica import ballistica_path
import app.engine.entities.artifact_actions as aa


def _game_corridor(px=15, py=15, length=8):
    g = GameInstance("t")
    p = g.add_player("p1", "Hero", "warrior")
    floor = g._get_or_create_floor(p.floor_id)
    floor.mobs.clear()
    p.pos = Position(x=px, y=py)
    # clear a horizontal open strip (and its vertical neighbours) around the row
    for x in range(px - 1, px + length + 2):
        for y in (py - 1, py, py + 1):
            floor.flags.solid[y][x] = False
            floor.flags.passable[y][x] = True
    return g, p, floor


# --- model -----------------------------------------------------------------

def test_charge_cap_formula_level_cap_5():
    c = EtherealChains()
    assert c.level_cap == 5
    assert c.charge == 5 and c.charge_cap == 5           # 5 + 0*2
    for _ in range(5):
        c.level += 1
        c.on_upgrade()
    assert c.charge_cap == 15                            # 5 + 5*2


# --- ballistica ------------------------------------------------------------

class _Flags:
    def __init__(self, w, h):
        self.solid = [[False] * w for _ in range(h)]
        self.passable = [[True] * w for _ in range(h)]


def test_ballistica_stops_before_wall():
    f = _Flags(20, 5)
    f.solid[2][6] = True
    path = ballistica_path(2, 2, 10, 2, f, 20, 5)
    assert path[-1] == (5, 2)                            # cell before the wall


# --- chainEnemy ------------------------------------------------------------

def test_pull_enemy_down_corridor():
    g, p, floor = _game_corridor()
    rat = Rat(id="r", pos=Position(x=19, y=15))
    floor.mobs[rat.id] = rat
    c = EtherealChains(id="c"); c.charge = 10
    aa.action_cast_chains(g, p, c, 19, 15)
    assert (rat.pos.x, rat.pos.y) == (16, 15)            # earliest open cell
    assert c.charge == 10 - 3                            # chebyshev(19,16)=3


def test_adjacent_enemy_is_noop():
    g, p, floor = _game_corridor()
    rat = Rat(id="r", pos=Position(x=16, y=15))
    floor.mobs[rat.id] = rat
    c = EtherealChains(id="c"); c.charge = 10
    aa.action_cast_chains(g, p, c, 16, 15)
    assert (rat.pos.x, rat.pos.y) == (16, 15)            # nowhere closer to go
    assert c.charge == 10


def test_pull_enemy_costs_more_than_charge_is_noop():
    g, p, floor = _game_corridor()
    rat = Rat(id="r", pos=Position(x=21, y=15))
    floor.mobs[rat.id] = rat
    c = EtherealChains(id="c"); c.charge = 1             # need 5, have 1
    aa.action_cast_chains(g, p, c, 21, 15)
    assert (rat.pos.x, rat.pos.y) == (21, 15)
    assert c.charge == 1


# --- chainLocation ---------------------------------------------------------

def test_chain_to_wall_pulls_hero():
    g, p, floor = _game_corridor()
    floor.flags.solid[15][20] = True                     # wall just past target
    floor.flags.passable[15][20] = False
    c = EtherealChains(id="c"); c.charge = 10
    aa.action_cast_chains(g, p, c, 19, 15)               # target beside the wall
    assert (p.pos.x, p.pos.y) == (19, 15)
    assert c.charge == 10 - 4                            # chebyshev(15,19)=4


def test_chain_to_open_space_without_grab_is_noop():
    g, p, floor = _game_corridor()
    c = EtherealChains(id="c"); c.charge = 10
    aa.action_cast_chains(g, p, c, 19, 15)               # no solid neighbour
    assert (p.pos.x, p.pos.y) == (15, 15)
    assert c.charge == 10
