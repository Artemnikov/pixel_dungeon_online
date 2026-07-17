import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.base import Position
from app.engine.entities.mobs import Swarm, Rat
from app.engine.systems.combat import resolve_melee_attack


def test_swarm_defense_proc_returns_damage():
    """defense_proc is contracted to return the (possibly modified) damage so
    the combat resolver can keep applying it. Swarm must not return None."""
    swarm = Swarm(id="s1", pos=Position(x=5, y=5))
    floor_mobs = {swarm.id: swarm}
    out = swarm.defense_proc(5, attacker=None, floor_mobs=floor_mobs, tile_x=5, tile_y=5)
    assert out == 5


def test_attacking_swarm_does_not_crash():
    """Regression: hitting a Swarm used to raise
    TypeError: '<=' not supported between 'NoneType' and 'int' because
    defense_proc returned None into combat.py's `if raw_damage <= 0`."""
    swarm = Swarm(id="s1", pos=Position(x=5, y=5), defense_skill=0)
    attacker = Rat(id="r1", pos=Position(x=4, y=5), attack_skill=100)
    floor_mobs = {swarm.id: swarm, attacker.id: attacker}

    result = resolve_melee_attack(attacker, swarm, floor_mobs, 5, 5, is_in_los=None)
    assert isinstance(result["damage"], int)
    assert result["hit"] is True


def _split_clone(floor_mobs, exclude_ids):
    return next(m for k, m in floor_mobs.items() if k not in exclude_ids)


def test_swarm_split_spawns_adjacent_to_swarm_not_attacker():
    """Regression: defense_proc used to build candidate cells around
    tile_x/tile_y, which callers pass as the *attacker's* position, not the
    Swarm's. A clone could then appear next to (or behind) the player instead
    of next to the Swarm itself. Candidates must be adjacent to swarm.pos."""
    swarm = Swarm(id="s1", pos=Position(x=5, y=5), hp=50, max_hp=50, defense_skill=0)
    attacker = Rat(id="r1", pos=Position(x=4, y=5), attack_skill=100)
    floor_mobs = {swarm.id: swarm, attacker.id: attacker}

    # tile_x/tile_y deliberately point somewhere else entirely (as a stray
    # caller might pass) to prove they're no longer used as the spawn center.
    out = swarm.defense_proc(2, attacker=attacker, floor_mobs=floor_mobs, tile_x=0, tile_y=0)
    assert out == 2

    clone = _split_clone(floor_mobs, {swarm.id, attacker.id})
    assert abs(clone.pos.x - swarm.pos.x) + abs(clone.pos.y - swarm.pos.y) == 1
    # Never on the attacker's own tile.
    assert (clone.pos.x, clone.pos.y) != (attacker.pos.x, attacker.pos.y)


def test_swarm_split_redistributes_hp():
    """SPD Swarm.java: clone.HP = (HP - damage) / 2; HP -= clone.HP. The
    split must redistribute the parent's existing HP, never manufacture new
    HP: right after defense_proc returns (before the resolver's separate
    take_damage call), parent+clone HP must still equal the pre-split HP."""
    swarm = Swarm(id="s1", pos=Position(x=5, y=5), hp=50, max_hp=50, defense_skill=0)
    attacker = Rat(id="r1", pos=Position(x=4, y=5), attack_skill=100)
    floor_mobs = {swarm.id: swarm, attacker.id: attacker}
    hp_before = swarm.hp
    damage = 2

    swarm.defense_proc(damage, attacker=attacker, floor_mobs=floor_mobs, tile_x=4, tile_y=5)

    clone = _split_clone(floor_mobs, {swarm.id, attacker.id})
    assert clone.hp == (hp_before - damage) // 2
    assert swarm.hp + clone.hp == hp_before
    assert clone.max_hp == swarm.max_hp


def test_swarm_split_hp_conserved_end_to_end():
    """Full combat pipeline: total Swarm HP after a hit-that-splits must
    equal pre-hit HP minus the damage dealt, exactly as if the Swarm hadn't
    split at all. Total HP must shrink with each hit, never grow -- growth
    is what made splitting feel unbounded."""
    swarm = Swarm(id="s1", pos=Position(x=5, y=5), hp=50, max_hp=50, defense_skill=0)
    attacker = Rat(id="r1", pos=Position(x=4, y=5), attack_skill=100, damage_min=2, damage_max=2)
    floor_mobs = {swarm.id: swarm, attacker.id: attacker}
    hp_before = swarm.hp

    result = resolve_melee_attack(
        attacker, swarm, floor_mobs, swarm.pos.x, swarm.pos.y,
        is_in_los=None, guaranteed_hit=True,
    )

    clone = _split_clone(floor_mobs, {swarm.id, attacker.id})
    assert swarm.hp + clone.hp == hp_before - result["damage"]


def test_swarm_wont_split_forever():
    """Repeatedly hitting a Swarm must eventually stop producing splits once
    HP drops below the damage+2 gate -- population growth must not be
    unbounded."""
    swarm = Swarm(id="s1", pos=Position(x=5, y=5), hp=50, max_hp=50, defense_skill=0)
    attacker = Rat(id="r1", pos=Position(x=4, y=5), attack_skill=100)
    floor_mobs = {swarm.id: swarm, attacker.id: attacker}

    for _ in range(200):
        if not swarm.is_alive:
            break
        swarm.defense_proc(3, attacker=attacker, floor_mobs=floor_mobs, tile_x=4, tile_y=5)
        swarm.hp -= 3
        if swarm.hp <= 0:
            swarm.hp = 0
            swarm.is_alive = False

    total_clones = len(floor_mobs) - 2  # minus swarm + attacker
    # 4 cardinal neighbours of a single tile is a hard ceiling on simultaneous
    # splits from one Swarm regardless of how many hits land.
    assert total_clones <= 4
