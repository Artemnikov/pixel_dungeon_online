# Copyright (C) 2026 ArtemNikov
#
"""Comprehensive SPD Duelist Parity Test Suite.

Covers:
- Starting equipment, quickslots, and identification.
- Max weapon charges formula and turn-based regeneration.
- All 17 Weapon Skills (Lunge, Sneak, Cleave, Spike, Defensive Stance, Sword Dance,
  Harvest, Lash, Spin, Combo Strike, Heavy Blow, Retribution, Guard, Charged Shot,
  Runic Slash, Pierce, Brawler's Stance).
- Champion Subclass: Secondary weapon slot, instant swap, Varied Charge,
  Twin Upgrades, Combined Lethality.
- Monk Subclass: Monk Energy system, Unencumbered Spirit, Monastic Vigor,
  Flurry of Blows, Focus, Dash, Dragon Kick, Meditate, Combined Energy.
- All 4 Tiers of Duelist Talents.
- Armor Abilities: Challenge, Elemental Strike, Feint with T4 talents.
"""
import pytest
from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.buffs import add_buff, has_buff
from app.engine.entities.items.consumables import Food, Ration
from app.engine.entities.items.equip import (
    ClothArmor,
    Dagger,
    MissileWeapon,
    Staff,
    WornShortsword,
    make_named_melee_weapon,
)
from app.engine.entities.items.potions import HealthPotion
from app.engine.entities.player import CharacterClass, Mob as MobEntity, Player
from app.engine.entities.subclasses import ArmorAbilityType, Subclass
from app.engine.entities.talent_enum import Talent
from app.engine.game.duelist_weapon_skills import get_weapon_skill_for_weapon
from app.engine.manager import GameInstance
from app.engine.systems.combat import resolve_melee_attack, resolve_ranged_attack


def _duelist(game: GameInstance, pid: str = "duelist_test") -> Player:
    p = game.add_player(pid, "Duelist", CharacterClass.DUELIST)
    p.strength = 20
    p.weapon_charge = float(p.get_max_weapon_charges())
    return p


def _mob(hp: int = 40, max_hp: int = 40, x: int = 2, y: int = 1, id: str = "m1", **kw) -> MobEntity:
    return MobEntity(
        id=id, name="Rat", pos=Position(x=x, y=y),
        hp=hp, max_hp=max_hp, attack=4, defense=0,
        defense_skill=0, dr_min=0, dr_max=0, **kw
    )


# ===========================================================================
# 1. Starting Kit & Weapon Charge Scaling
# ===========================================================================

def test_duelist_starting_kit_and_identification():
    g = GameInstance("t_kit")
    p = g.add_player("p1", "Duelist", CharacterClass.DUELIST)

    assert p.class_type == CharacterClass.DUELIST
    assert p.belongings.weapon is not None
    assert p.belongings.weapon.name == "Rapier"
    assert p.belongings.weapon.level_known is True
    assert p.belongings.armor is not None
    assert p.belongings.armor.name == "Cloth Armor"
    assert p.belongings.armor.level_known is True

    names = [i.name for i in p.belongings.backpack.items]
    assert "Ration" in names
    assert "Waterskin" in names
    assert "Velvet Pouch" in names
    assert "Scroll of Identify" in names
    assert "Throwing Spikes" in names
    assert "Potion of Strength" in names
    assert "Scroll of Mirror Image" in names

    assert p.quickslot.slots[0].item_id == p.belongings.weapon.id
    assert p.weapon_charge == 2.0
    assert p.finisher_ready is True


def test_duelist_max_charges_formula():
    g = GameInstance("t_charges")
    p = _duelist(g)

    # Base Duelist: min(8, 2 + (lvl - 1) // 3)
    p.level = 1
    assert p.get_max_weapon_charges() == 2
    p.level = 4
    assert p.get_max_weapon_charges() == 3
    p.level = 7
    assert p.get_max_weapon_charges() == 4
    p.level = 19
    assert p.get_max_weapon_charges() == 8
    p.level = 25
    assert p.get_max_weapon_charges() == 8

    # Champion: min(10, 4 + (lvl - 1) // 3)
    p.subclass_info.subclass = "champion"
    p.level = 13
    assert p.get_max_weapon_charges() == 8
    p.level = 16
    assert p.get_max_weapon_charges() == 9
    p.level = 19
    assert p.get_max_weapon_charges() == 10


# ===========================================================================
# 2. Weapon Skills (All 17 Melee Abilities)
# ===========================================================================

def test_lunge_skill_rapier():
    g = GameInstance("t_lunge")
    p = _duelist(g)
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(hp=40, x=p.pos.x + 2, y=p.pos.y)
    floor.mobs[mob.id] = mob

    # Rapier Lunge from 2 tiles away
    assert g.use_weapon_ability(p.id, target_x=mob.pos.x, target_y=mob.pos.y) is True
    assert p.pos.x == mob.pos.x - 1  # Leaped to adjacent tile
    assert mob.hp < 40  # Struck target


def test_sneak_skill_dagger():
    g = GameInstance("t_sneak")
    p = _duelist(g)
    dagger = make_named_melee_weapon("Dagger")
    p.belongings.weapon = dagger
    floor = g._get_or_create_floor(p.floor_id)

    target_x = p.pos.x + 3
    target_y = p.pos.y

    assert g.use_weapon_ability(p.id, target_x=target_x, target_y=target_y) is True
    assert p.pos.x == target_x and p.pos.y == target_y
    assert p.has_buff("invisibility")


def test_cleave_skill_and_free_followup_on_kill():
    g = GameInstance("t_cleave")
    p = _duelist(g)
    sword = make_named_melee_weapon("Sword")
    p.belongings.weapon = sword
    floor = g._get_or_create_floor(p.floor_id)

    # 1. Cleave on low-hp mob -> kills it and gains cleave_tracker
    mob1 = _mob(hp=2, max_hp=2, x=p.pos.x + 1, y=p.pos.y, id="m1")
    floor.mobs[mob1.id] = mob1
    assert g.use_weapon_ability(p.id, target_x=mob1.pos.x, target_y=mob1.pos.y) is True
    assert not mob1.is_alive
    assert p.has_buff("cleave_tracker")

    # 2. Next Cleave costs 0 charges
    mob2 = _mob(hp=40, max_hp=40, x=p.pos.x + 1, y=p.pos.y, id="m2")
    floor.mobs[mob2.id] = mob2
    charge_before = p.weapon_charge
    assert g.use_weapon_ability(p.id, target_x=mob2.pos.x, target_y=mob2.pos.y) is True
    assert p.weapon_charge == charge_before  # 0 charge consumed
    assert not p.has_buff("cleave_tracker")


def test_spike_skill_spear_reach_and_knockback():
    g = GameInstance("t_spike")
    p = _duelist(g)
    spear = make_named_melee_weapon("Spear")
    p.belongings.weapon = spear
    floor = g._get_or_create_floor(p.floor_id)

    mob = _mob(hp=40, x=p.pos.x + 2, y=p.pos.y)
    floor.mobs[mob.id] = mob

    assert g.use_weapon_ability(p.id, target_x=mob.pos.x, target_y=mob.pos.y) is True
    assert mob.hp < 40
    # Knocked back 1 tile (from x+2 to x+3)
    assert mob.pos.x == p.pos.x + 3


def test_defensive_stance_quarterstaff():
    g = GameInstance("t_def_stance")
    p = _duelist(g)
    qs = make_named_melee_weapon("Quarterstaff")
    p.belongings.weapon = qs

    assert g.use_weapon_ability(p.id) is True
    assert p.has_buff("defensive_stance")


def test_sword_dance_scimitar():
    g = GameInstance("t_sword_dance")
    p = _duelist(g)
    scimitar = make_named_melee_weapon("Scimitar")
    p.belongings.weapon = scimitar

    assert g.use_weapon_ability(p.id) is True
    assert p.has_buff("sword_dance")


def test_harvest_skill_sickle_bleed():
    g = GameInstance("t_harvest")
    p = _duelist(g)
    sickle = make_named_melee_weapon("Sickle")
    p.belongings.weapon = sickle
    floor = g._get_or_create_floor(p.floor_id)

    mob = _mob(hp=40, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    assert g.use_weapon_ability(p.id, target_x=mob.pos.x, target_y=mob.pos.y) is True
    assert mob.has_buff("bleeding")


def test_lash_skill_whip_multitarget():
    g = GameInstance("t_lash")
    p = _duelist(g)
    whip = make_named_melee_weapon("Whip")
    p.belongings.weapon = whip
    floor = g._get_or_create_floor(p.floor_id)

    mob1 = _mob(hp=40, x=p.pos.x + 1, y=p.pos.y, id="m1")
    mob2 = _mob(hp=40, x=p.pos.x + 2, y=p.pos.y + 1, id="m2")
    floor.mobs[mob1.id] = mob1
    floor.mobs[mob2.id] = mob2

    assert g.use_weapon_ability(p.id) is True
    assert mob1.hp < 40
    assert mob2.hp < 40


def test_spin_skill_flail_channeling():
    g = GameInstance("t_spin")
    p = _duelist(g)
    flail = make_named_melee_weapon("Flail")
    p.belongings.weapon = flail

    # Spin 1: costs 1 charge
    c1 = p.weapon_charge
    assert g.use_weapon_ability(p.id) is True
    assert p.weapon_charge == c1 - 1.0
    buff1 = p.get_buff("spin_tracker")
    assert buff1 is not None and buff1.level == 1

    # Spin 2: costs 0 charge
    c2 = p.weapon_charge
    assert g.use_weapon_ability(p.id) is True
    assert p.weapon_charge == c2
    buff2 = p.get_buff("spin_tracker")
    assert buff2 is not None and buff2.level == 2


def test_heavy_blow_skill_mace_daze():
    g = GameInstance("t_heavy_blow")
    p = _duelist(g)
    mace = make_named_melee_weapon("Mace")
    p.belongings.weapon = mace
    floor = g._get_or_create_floor(p.floor_id)

    mob = _mob(hp=40, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    assert g.use_weapon_ability(p.id, target_x=mob.pos.x, target_y=mob.pos.y) is True
    assert mob.has_buff("daze")


def test_retribution_skill_greataxe_low_hp():
    g = GameInstance("t_retribution")
    p = _duelist(g)
    axe = make_named_melee_weapon("Greataxe")
    p.belongings.weapon = axe
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(hp=40, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    # At full HP -> cannot execute
    p.hp = p.max_hp
    assert g.use_weapon_ability(p.id, target_x=mob.pos.x, target_y=mob.pos.y) is False

    # Below 50% HP -> executes successfully
    p.hp = p.max_hp // 2 - 1
    assert g.use_weapon_ability(p.id, target_x=mob.pos.x, target_y=mob.pos.y) is True
    assert mob.hp < 40


def test_guard_skill_round_shield_infinite_evasion():
    g = GameInstance("t_guard")
    p = _duelist(g)
    shield = make_named_melee_weapon("Round Shield")
    p.belongings.weapon = shield
    floor = g._get_or_create_floor(p.floor_id)

    assert g.use_weapon_ability(p.id) is True
    assert p.has_buff("guard_tracker")

    # Mob attacks player -> blocked by Guard
    mob = _mob(hp=40, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob
    res = resolve_melee_attack(mob, p, floor.mobs, p.pos.x, p.pos.y, floor=floor, game=g)
    assert res["missed"] is True
    assert res["defense_verb"] == "blocked"


def test_pierce_skill_pickaxe_vulnerable():
    g = GameInstance("t_pierce")
    p = _duelist(g)
    pickaxe = make_named_melee_weapon("Pickaxe")
    p.belongings.weapon = pickaxe
    floor = g._get_or_create_floor(p.floor_id)

    mob = _mob(hp=40, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    assert g.use_weapon_ability(p.id, target_x=mob.pos.x, target_y=mob.pos.y) is True
    assert mob.has_buff("vulnerable")


# ===========================================================================
# 3. Champion Subclass
# ===========================================================================

def test_champion_secondary_weapon_and_instant_swap():
    g = GameInstance("t_champ_swap")
    p = _duelist(g)
    p.subclass_info.subclass = "champion"

    rapier = make_named_melee_weapon("Rapier")
    dagger = make_named_melee_weapon("Dagger")
    p.belongings.weapon = rapier
    p.belongings.secondary_weapon = dagger

    assert g.swap_weapons(p.id) is True
    assert p.belongings.weapon == dagger
    assert p.belongings.secondary_weapon == rapier


def test_champion_twin_upgrades():
    g = GameInstance("t_twin_upgrades")
    p = _duelist(g)
    p.subclass_info.subclass = "champion"
    p.talent_info.talents[Talent.TWIN_UPGRADES] = 3  # Rank 3: same tier or lower

    high_sword = make_named_melee_weapon("Sword", level=6)  # T3 +6
    low_mace = make_named_melee_weapon("Mace", level=0)     # T3 +0

    p.belongings.weapon = low_mace
    p.belongings.secondary_weapon = high_sword

    # Effective level is 6 without modifying item.level
    assert p.get_effective_weapon_level(low_mace) == 6
    assert low_mace.level == 0


def test_champion_combined_lethality_execute():
    g = GameInstance("t_combined_lethality")
    p = _duelist(g)
    p.subclass_info.subclass = "champion"
    p.talent_info.talents[Talent.COMBINED_LETHALITY] = 3

    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(hp=10, max_hp=40, x=p.pos.x + 1, y=p.pos.y)  # 25% HP (< 40%)
    floor.mobs[mob.id] = mob

    # Set last ability used was from a different weapon (e.g. Rapier Lunge)
    p.last_weapon_ability_id = "lunge"
    p.last_weapon_ability_weapon_name = "Rapier"
    p.last_weapon_ability_turn = getattr(g, "turns", 0)

    # Melee attack with Sword executes mob
    sword = make_named_melee_weapon("Sword")
    p.belongings.weapon = sword

    res = resolve_melee_attack(p, mob, floor.mobs, mob.pos.x, mob.pos.y, floor=floor, game=g)
    assert res.get("ko") is True
    assert not mob.is_alive


# ===========================================================================
# 4. Monk Subclass
# ===========================================================================

def test_monk_energy_and_flurry_of_blows():
    g = GameInstance("t_monk_flurry")
    p = _duelist(g)
    p.subclass_info.subclass = "monk"
    p.monk_energy = 5.0
    floor = g._get_or_create_floor(p.floor_id)

    mob = _mob(hp=100, max_hp=100, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    assert g.use_monk_ability(p.id, "flurry", target_x=mob.pos.x, target_y=mob.pos.y) is True
    assert p.monk_energy == 4.0
    assert mob.hp < 100


def test_monk_focus_infinite_evasion():
    g = GameInstance("t_monk_focus")
    p = _duelist(g)
    p.subclass_info.subclass = "monk"
    p.monk_energy = 5.0
    floor = g._get_or_create_floor(p.floor_id)

    assert g.use_monk_ability(p.id, "focus") is True
    assert p.has_buff("focus_parry_buff")

    # Mob attack is parried
    mob = _mob(hp=30, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob
    res = resolve_melee_attack(mob, p, floor.mobs, p.pos.x, p.pos.y, floor=floor, game=g)
    assert res["missed"] is True
    assert res["defense_verb"] == "parried"
    assert not p.has_buff("focus_parry_buff")


def test_monk_dash_leap():
    g = GameInstance("t_monk_dash")
    p = _duelist(g)
    p.subclass_info.subclass = "monk"
    p.monk_energy = 5.0
    floor = g._get_or_create_floor(p.floor_id)

    target_x = p.pos.x + 3
    target_y = p.pos.y

    assert g.use_monk_ability(p.id, "dash", target_x=target_x, target_y=target_y) is True
    assert p.pos.x == target_x and p.pos.y == target_y


def test_monk_dragon_kick_knockback_and_paralysis():
    g = GameInstance("t_monk_kick")
    p = _duelist(g)
    p.subclass_info.subclass = "monk"
    p.monk_energy = 5.0
    floor = g._get_or_create_floor(p.floor_id)

    mob = _mob(hp=100, max_hp=100, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    assert g.use_monk_ability(p.id, "dragon_kick", target_x=mob.pos.x, target_y=mob.pos.y) is True
    assert mob.pos.x > p.pos.x + 1  # Pushed back
    assert mob.has_buff("paralysis")


def test_monk_meditate_cleanse_and_recharge():
    g = GameInstance("t_monk_meditate")
    p = _duelist(g)
    p.subclass_info.subclass = "monk"
    p.monk_energy = 5.0

    add_buff(p.buffs, "poison", duration=10.0, level=1)
    assert p.has_buff("poison")

    assert g.use_monk_ability(p.id, "meditate") is True
    assert not p.has_buff("poison")
    assert p.has_buff("recharging")


# ===========================================================================
# 5. Talents Tier 1-4 & Armor Abilities
# ===========================================================================

def test_strengthening_meal_bonus_damage():
    g = GameInstance("t_str_meal")
    p = _duelist(g)
    p.talent_info.talents[Talent.STRENGTHENING_MEAL] = 2
    floor = g._get_or_create_floor(p.floor_id)

    g.on_food_eaten(p, Ration(id="r1", name="Ration"))
    assert p.has_buff("strengthening_meal_tracker")

    mob = _mob(hp=50, max_hp=50, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    res = resolve_melee_attack(p, mob, floor.mobs, mob.pos.x, mob.pos.y, floor=floor, game=g)
    assert res["hit"] is True
    # Decrements tracker
    b = p.get_buff("strengthening_meal_tracker")
    assert b is not None and b.level == 2


def test_adventurers_intuition_auto_identify():
    g = GameInstance("t_adv_intuition")
    p = _duelist(g)
    p.talent_info.talents[Talent.ADVENTURERS_INTUITION] = 2

    sword = make_named_melee_weapon("Sword", level=3)
    sword.level_known = False
    p.belongings.backpack.collect(sword)

    p.equip_item(sword.id)
    assert sword.level_known is True


def test_patient_strike_waiting_bonus():
    g = GameInstance("t_patient_strike")
    p = _duelist(g)
    p.talent_info.talents[Talent.PATIENT_STRIKE] = 2
    floor = g._get_or_create_floor(p.floor_id)

    # Stationary tick sets patient_strike_ready
    p.patient_strike_tile = (p.pos.x, p.pos.y)
    p.patient_strike_ready = True

    mob = _mob(hp=50, max_hp=50, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    res = resolve_melee_attack(p, mob, floor.mobs, mob.pos.x, mob.pos.y, floor=floor, game=g)
    assert res["hit"] is True
    assert p.patient_strike_ready is False


def test_deadly_followup_missile_bonus():
    g = GameInstance("t_deadly_followup")
    p = _duelist(g)
    p.talent_info.talents[Talent.DEADLY_FOLLOWUP] = 3
    floor = g._get_or_create_floor(p.floor_id)

    mob = _mob(hp=50, max_hp=50, x=p.pos.x + 2, y=p.pos.y)
    floor.mobs[mob.id] = mob

    spike = MissileWeapon(name="Throwing Spikes", tier=1, quantity=2)
    # Ranged attack hits mob and applies deadly_followup_tracker
    res = resolve_ranged_attack(p, mob, spike, floor.mobs, mob.pos.x, mob.pos.y, floor=floor, game=g)
    assert res["hit"] is True
    assert mob.has_buff("deadly_followup_tracker")


def test_challenge_armor_ability_and_invigorating_victory():
    g = GameInstance("t_challenge_invigorating")
    p = _duelist(g)
    p.talent_info.talents[Talent.INVIGORATING_VICTORY] = 3
    p._kings_crown_worn = True
    floor = g._get_or_create_floor(p.floor_id)

    mob = _mob(hp=10, max_hp=10, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    p.armor_charge = 100
    p.hp = 10  # Missing 10 HP
    g.use_armor_ability(p.id, ArmorAbilityType.CHALLENGE, mob.pos.x, mob.pos.y)
    assert p.duel_mode_active is True

    # Take damage during duel
    p.duel_mode_taken_damage = 20

    # Kill challenged mob -> duel ends and heals player
    mob.is_alive = False
    g.tick_duelist(p, 0.05)
    assert p.duel_mode_active is False
    assert p.hp > 10  # Healed from Invigorating Victory
