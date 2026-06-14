"""Weapon enchantments and curses (docs/spd_items/01-weapons-bombs.md §6-7):
proc-chance formulas, random generation rolls, combat dispatch, and
Scroll of Upgrade."""

import random

from app.engine.entities.base import Mob as MobEntity, Position, Dagger
from app.engine.entities.weapon_enchants import (
    ALL_SPD_CURSES,
    CURSES,
    ENCHANTS,
    blocking_chance,
    elastic_chance,
    grim_chance,
    missing_hp_pct,
    polarized_roll,
    roll_weapon_enchant,
    roll_weapon_level,
    vampiric_chance,
)
from app.engine.manager import GameInstance
from app.engine.systems.combat import resolve_melee_attack


def _warrior(game, pid="w"):
    return game.add_player(pid, "Warrior", "warrior")


def _mob(hp=20, max_hp=20, x=2, y=1, **kw):
    kw.setdefault("dr_min", 0)
    kw.setdefault("dr_max", 0)
    return MobEntity(id="m", name="Rat", pos=Position(x=x, y=y),
                     hp=hp, max_hp=max_hp, attack=2, defense=0,
                     defense_skill=0, **kw)


# --- proc-chance formulas ----------------------------------------------------

def test_missing_hp_pct():
    e = _mob(hp=5, max_hp=20)
    assert missing_hp_pct(e) == 0.75


def test_vampiric_chance_scales_with_missing_hp():
    assert vampiric_chance(0.0) == 0.05
    assert vampiric_chance(1.0) == 0.30


def test_blocking_chance_formula():
    assert blocking_chance(0) == 4 / 40
    assert blocking_chance(5) == 9 / 45


def test_elastic_chance_formula():
    assert elastic_chance(0) == 1 / 5
    assert elastic_chance(5) == 6 / 10


def test_grim_chance_capped_at_one():
    assert grim_chance(0) == 0.5
    assert grim_chance(20) == 1.0


def test_polarized_roll_only_returns_known_values():
    rolls = {polarized_roll() for _ in range(200)}
    assert rolls <= {0.0, 1.5}
    assert len(rolls) == 2


# --- random generation --------------------------------------------------------

def test_roll_weapon_level_distribution():
    rng = random.Random(1)
    counts = {0: 0, 1: 0, 2: 0}
    for _ in range(20000):
        counts[roll_weapon_level(rng)] += 1
    assert 0.70 < counts[0] / 20000 < 0.80
    assert 0.15 < counts[1] / 20000 < 0.25
    assert 0.02 < counts[2] / 20000 < 0.08


def test_roll_weapon_enchant_only_returns_known_names():
    rng = random.Random(2)
    for _ in range(2000):
        name, cursed = roll_weapon_enchant(rng)
        if name is None:
            assert cursed is False
        elif cursed:
            assert name in CURSES
            assert name in ALL_SPD_CURSES
        else:
            assert name in ENCHANTS


# --- combat dispatch -----------------------------------------------------------

def test_vampiric_heals_attacker_on_hit(monkeypatch):
    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.weapon.enchantment = "vampiric"
    p.hp = 1
    p.max_hp = 50
    p.attack_skill = 1000
    target = _mob(hp=100, max_hp=100, dr_min=0, dr_max=0)

    monkeypatch.setattr(random, "random", lambda: 0.0)  # always proc
    monkeypatch.setattr(random, "randint", lambda a, b: b)  # max damage roll
    floor = g._get_or_create_floor(p.floor_id)
    result = resolve_melee_attack(p, target, floor.mobs, p.pos.x, p.pos.y, floor=floor)
    assert result["damage"] > 0
    assert p.hp > 1


def test_blocking_adds_shield_on_hit(monkeypatch):
    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.weapon.enchantment = "blocking"
    p.attack_skill = 1000
    target = _mob(hp=100, max_hp=100, dr_min=0, dr_max=0)

    monkeypatch.setattr(random, "random", lambda: 0.0)
    floor = g._get_or_create_floor(p.floor_id)
    result = resolve_melee_attack(p, target, floor.mobs, p.pos.x, p.pos.y, floor=floor)
    assert result["damage"] > 0
    assert p.get_shield("block") is not None


def test_shocking_damages_nearby_hostile_mobs(monkeypatch):
    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.weapon.enchantment = "shocking"
    p.attack_skill = 1000
    floor = g._get_or_create_floor(p.floor_id)
    floor.mobs.clear()

    target = _mob(hp=100, max_hp=100, x=p.pos.x + 1, y=p.pos.y, dr_min=0, dr_max=0)
    bystander = _mob(hp=100, max_hp=100, x=p.pos.x + 2, y=p.pos.y, dr_min=0, dr_max=0)
    bystander.id = "bystander"
    floor.mobs[target.id] = target
    floor.mobs[bystander.id] = bystander

    monkeypatch.setattr(random, "random", lambda: 0.0)  # proc + max damage rolls
    result = resolve_melee_attack(p, target, floor.mobs, p.pos.x, p.pos.y, floor=floor)
    assert result["damage"] > 0
    assert bystander.hp < 100


def test_kinetic_conserves_overflow_damage_on_kill(monkeypatch):
    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.weapon.enchantment = "kinetic"
    p.attack_skill = 1000
    target = _mob(hp=1, max_hp=20, dr_min=0, dr_max=0)

    monkeypatch.setattr(random, "random", lambda: 0.999)
    monkeypatch.setattr(random, "randint", lambda a, b: b)  # max damage roll
    floor = g._get_or_create_floor(p.floor_id)
    resolve_melee_attack(p, target, floor.mobs, p.pos.x, p.pos.y, floor=floor)
    assert not target.is_alive
    assert p.conserved_damage > 0


def test_grim_executes_only_with_grim_enchant(monkeypatch):
    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.weapon.enchantment = "grim"
    p.attack_skill = 1000
    target = _mob(hp=1000, max_hp=1000, dr_min=0, dr_max=0)
    target.hp = 500  # 50% missing -> grim_chance(0)*(1-0.5)**2 = 0.125

    monkeypatch.setattr(random, "random", lambda: 0.0)
    floor = g._get_or_create_floor(p.floor_id)
    result = resolve_melee_attack(p, target, floor.mobs, p.pos.x, p.pos.y, floor=floor)
    assert result["grim_proc"] is True
    # grim_max_chance is reset after the hit, not left mutated
    assert p.grim_max_chance == 0.0


def test_grim_does_not_proc_without_enchant(monkeypatch):
    g = GameInstance("t")
    p = _warrior(g)
    p.attack_skill = 1000
    target = _mob(hp=100, max_hp=100, dr_min=0, dr_max=0)
    target.hp = 10

    monkeypatch.setattr(random, "random", lambda: 0.0)
    floor = g._get_or_create_floor(p.floor_id)
    result = resolve_melee_attack(p, target, floor.mobs, p.pos.x, p.pos.y, floor=floor)
    assert result["grim_proc"] is False


def test_polarized_curse_replaces_damage_with_1_5x_or_0(monkeypatch):
    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.weapon.enchantment = "polarized"
    p.belongings.weapon.cursed = True
    p.attack_skill = 1000
    target = _mob(hp=100, max_hp=100, dr_min=0, dr_max=0)
    floor = g._get_or_create_floor(p.floor_id)

    # First call: hit/dmg rolls "random" but polarized_roll forced to 0.0
    calls = iter([0.0, 0.0, 0.6])  # acu_roll, dmg_roll selection..., polarized roll>=0.5 -> 0x
    monkeypatch.setattr(random, "random", lambda: next(calls, 0.6))
    result = resolve_melee_attack(p, target, floor.mobs, p.pos.x, p.pos.y, floor=floor)
    assert result["damage"] == 0


def test_sacrificial_curse_costs_attacker_hp(monkeypatch):
    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.weapon.enchantment = "sacrificial"
    p.belongings.weapon.cursed = True
    p.attack_skill = 1000
    p.hp = 10
    p.max_hp = 50
    target = _mob(hp=100, max_hp=100, dr_min=0, dr_max=0)

    monkeypatch.setattr(random, "random", lambda: 0.0)  # proc + max sacrifice
    floor = g._get_or_create_floor(p.floor_id)
    hp_before = p.hp
    resolve_melee_attack(p, target, floor.mobs, p.pos.x, p.pos.y, floor=floor)
    assert p.hp <= hp_before


def test_annoying_curse_makes_mobs_hunt_attacker(monkeypatch):
    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.weapon.enchantment = "annoying"
    p.belongings.weapon.cursed = True
    p.attack_skill = 1000
    floor = g._get_or_create_floor(p.floor_id)
    floor.mobs.clear()
    target = _mob(hp=100, max_hp=100, dr_min=0, dr_max=0)
    other = _mob(hp=100, max_hp=100, x=5, y=5, dr_min=0, dr_max=0)
    other.id = "other"
    floor.mobs[target.id] = target
    floor.mobs[other.id] = other

    monkeypatch.setattr(random, "random", lambda: 0.0)
    resolve_melee_attack(p, target, floor.mobs, p.pos.x, p.pos.y, floor=floor)
    assert other.ai_state == "hunting"
    assert other.target_id == p.id


# --- DR bonus wiring -----------------------------------------------------------

def test_weapon_dr_bonus_applies_to_player_dr():
    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.weapon.dr_bonus_base = 1
    p.belongings.weapon.dr_bonus_per_lvl = 2
    p.belongings.weapon.level = 3
    base_min, base_max = p.get_dr_min(), p.get_dr_max()
    p.belongings.weapon.level = 0
    no_bonus_min, no_bonus_max = p.get_dr_min(), p.get_dr_max()
    assert base_min - no_bonus_min == 6
    assert base_max - no_bonus_max == 6


# --- Scroll of Upgrade -----------------------------------------------------------

def test_scroll_of_upgrade_levels_up_equipped_weapon():
    from app.engine.entities.base import ScrollOfUpgrade
    from app.engine.entities.item_actions import action_read

    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.weapon.level = 0
    p.belongings.weapon.level_known = False
    scroll = ScrollOfUpgrade(id="scroll1", name="Scroll of Upgrade")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)
    assert p.belongings.weapon.level == 1
    assert p.belongings.weapon.level_known is True


def test_scroll_of_upgrade_removes_curse():
    from app.engine.entities.base import ScrollOfUpgrade
    from app.engine.entities.item_actions import action_read

    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.weapon.cursed = True
    p.belongings.weapon.cursed_known = False
    scroll = ScrollOfUpgrade(id="scroll2", name="Scroll of Upgrade")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)
    assert p.belongings.weapon.cursed is False
    assert p.belongings.weapon.cursed_known is True
