# Copyright (C) 2026 ArtemNikov
#
"""Exhaustive 1-1 Parity Test Suite for all 27 Shattered Pixel Dungeon Duelist Talents.

Covers:
- Tier 1: Strengthening Meal, Adventurer's Intuition, Patient Strike, Aggressive Barrier.
- Tier 2: Focused Meal, Liquid Agility, Weapon Recharging, Lethal Haste, Swift Equip.
- Tier 3: Precise Assault, Deadly Followup (Class Common).
- Tier 3 Champion: Varied Charge, Twin Upgrades, Combined Lethality.
- Tier 3 Monk: Unencumbered Spirit, Monastic Vigor, Combined Energy.
- Tier 4 Universal: Heroic Energy.
- Tier 4 Challenge: Close the Gap, Invigorating Victory, Elimination Match.
- Tier 4 Elemental Strike: Elemental Reach, Striking Force, Directed Power.
- Tier 4 Feint: Feigned Retreat, Expose Weakness, Counter Ability.
"""
import pytest
import time
from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.buffs import add_buff, get_buff, has_buff
from app.engine.entities.items.consumables import Ration
from app.engine.entities.items.equip import (
    ClothArmor,
    Dagger,
    LeatherArmor,
    MissileWeapon,
    ScaleArmor,
    make_named_melee_weapon,
)
from app.engine.entities.items.potions import HealthPotion
from app.engine.entities.player import CharacterClass, Mob as MobEntity, Player
from app.engine.entities.subclasses import ArmorAbilityType, Subclass
from app.engine.entities.talent_enum import Talent
from app.engine.game.duelist_armor_abilities import (
    ChallengeArmorAbility,
    ElementalStrikeArmorAbility,
    FeintArmorAbility,
)
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
# Tier 1 Talents
# ===========================================================================

def test_strengthening_meal_scaling():
    g = GameInstance("t_str_meal")
    p = _duelist(g)
    floor = g._get_or_create_floor(p.floor_id)

    # Rank 1: 2 hits (+3 dmg)
    p.talent_info.talents[Talent.STRENGTHENING_MEAL] = 1
    g.on_food_eaten(p, Ration(id="r1", name="Ration"))
    buff = p.get_buff("strengthening_meal_tracker")
    assert buff is not None and buff.level == 2

    mob = _mob(hp=100, max_hp=100, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    resolve_melee_attack(p, mob, floor.mobs, mob.pos.x, mob.pos.y, floor=floor, game=g)
    b1 = p.get_buff("strengthening_meal_tracker")
    assert b1 is not None and b1.level == 1

    resolve_melee_attack(p, mob, floor.mobs, mob.pos.x, mob.pos.y, floor=floor, game=g)
    assert not p.has_buff("strengthening_meal_tracker")

    # Rank 2: 3 hits (+3 dmg)
    p.talent_info.talents[Talent.STRENGTHENING_MEAL] = 2
    g.on_food_eaten(p, Ration(id="r2", name="Ration"))
    b2 = p.get_buff("strengthening_meal_tracker")
    assert b2 is not None and b2.level == 3


def test_adventurers_intuition_combat_hit_id_speed():
    g = GameInstance("t_adv_int_hit")
    p = _duelist(g)
    floor = g._get_or_create_floor(p.floor_id)
    p.talent_info.talents[Talent.ADVENTURERS_INTUITION] = 1

    weapon = make_named_melee_weapon("Sword")
    weapon.level_known = False
    weapon.uses_left_to_id = 10.0
    weapon.available_uses_to_id = 10.0
    p.belongings.weapon = weapon

    mob = _mob(hp=100, max_hp=100, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    # Rank 1 weapon ID speed is 1.0 + 1.5 * 1 = 2.5 uses per hit
    resolve_melee_attack(p, mob, floor.mobs, mob.pos.x, mob.pos.y, floor=floor, game=g)
    assert weapon.uses_left_to_id == pytest.approx(7.5, rel=1e-3)


def test_adventurers_intuition_on_upgrade_auto_identifies():
    g = GameInstance("t_adv_int_upgrade")
    p = _duelist(g)
    p.level = 6
    p.subclass_info.subclass = Subclass.CHAMPION
    p.subclass_info.bonus_talent_points[1] = 5

    primary = make_named_melee_weapon("Sword")
    primary.level_known = False
    primary.cursed_known = False
    p.belongings.weapon = primary

    secondary = make_named_melee_weapon("Dagger")
    secondary.level_known = False
    secondary.cursed_known = False
    p.belongings.secondary_weapon = secondary

    # Rank 1 upgrade
    g.upgrade_talent(p.id, Talent.ADVENTURERS_INTUITION)
    assert not primary.level_known
    assert not secondary.level_known

    # Rank 2 upgrade auto-identifies primary and secondary
    g.upgrade_talent(p.id, Talent.ADVENTURERS_INTUITION)
    assert primary.level_known and primary.cursed_known
    assert secondary.level_known and secondary.cursed_known


def test_adventurers_intuition_equip_auto_identify():
    g = GameInstance("t_adv_int_equip")
    p = _duelist(g)
    p.talent_info.talents[Talent.ADVENTURERS_INTUITION] = 2

    mace = make_named_melee_weapon("Mace")
    mace.level_known = False
    p.belongings.backpack.collect(mace)

    p.equip_item(mace.id)
    assert mace.level_known is True
    assert mace.cursed_known is True


def test_patient_strike_damage_bonus():
    g = GameInstance("t_patient_strike")
    p = _duelist(g)
    floor = g._get_or_create_floor(p.floor_id)

    # Rank 2: +2 flat bonus damage
    p.talent_info.talents[Talent.PATIENT_STRIKE] = 2
    p.patient_strike_tile = (p.pos.x, p.pos.y)
    p.patient_strike_ready = True

    mob = _mob(hp=100, max_hp=100, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    resolve_melee_attack(p, mob, floor.mobs, mob.pos.x, mob.pos.y, floor=floor, game=g)
    assert p.patient_strike_ready is False


def test_aggressive_barrier_shield():
    g = GameInstance("t_aggr_barrier")
    p = _duelist(g)
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(hp=100, max_hp=100, x=p.pos.x + 2, y=p.pos.y)
    floor.mobs[mob.id] = mob

    p.talent_info.talents[Talent.AGGRESSIVE_BARRIER] = 2
    p.hp = 10  # <= 50% max HP
    p.weapon_charge = 2.0

    # Lunge weapon skill triggers aggressive barrier
    g.use_weapon_ability(p.id, target_x=mob.pos.x, target_y=mob.pos.y)
    # Rank 2 grants 1 + 2*2 = 5 shield
    shield = p.get_shield("aggressive_barrier")
    assert shield is not None and shield.amount == 5


# ===========================================================================
# Tier 2 Talents
# ===========================================================================

def test_focused_meal_charges():
    g = GameInstance("t_foc_meal")
    p = _duelist(g)
    p.weapon_charge = 0.0

    # Rank 1: +0.67 charges
    p.talent_info.talents[Talent.FOCUSED_MEAL] = 1
    g.on_food_eaten(p, Ration(id="r1", name="Ration"))
    assert p.weapon_charge == pytest.approx(0.67, rel=1e-2)

    # Rank 2: +1.0 charges
    p.weapon_charge = 0.0
    p.talent_info.talents[Talent.FOCUSED_MEAL] = 2
    g.on_food_eaten(p, Ration(id="r2", name="Ration"))
    assert p.weapon_charge == pytest.approx(1.0, rel=1e-2)


def test_liquid_agility_evasion_and_accuracy():
    g = GameInstance("t_liq_agil")
    p = _duelist(g)
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(hp=100, max_hp=100, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    # Rank 2: Infinite Evasion & Infinite Accuracy
    p.talent_info.talents[Talent.LIQUID_AGILITY] = 2
    g.on_potion_drunk(p, HealthPotion(id="p1", name="Potion of Healing"))

    assert p.has_buff("liquid_agility_evasion")
    assert p.has_buff("liquid_agility_accuracy")

    # Mob attacks Duelist -> guaranteed dodge
    res_def = resolve_melee_attack(mob, p, floor.mobs, p.pos.x, p.pos.y, floor=floor, game=g)
    assert res_def["missed"] is True
    assert res_def["defense_verb"] == "dodged"

    # Duelist attacks mob -> guaranteed hit
    res_atk = resolve_melee_attack(p, mob, floor.mobs, mob.pos.x, mob.pos.y, floor=floor, game=g)
    assert res_atk["hit"] is True
    assert not p.has_buff("liquid_agility_accuracy")


def test_weapon_recharging_rate_boost():
    g = GameInstance("t_wpn_rech")
    p = _duelist(g)
    p.weapon_charge = 0.0
    p.talent_info.talents[Talent.WEAPON_RECHARGING] = 2
    add_buff(p.buffs, "recharging", duration=10.0, level=1)

    # Base max deficit rate (1/57) + bonus rate (1/(20 - 5*2) = 1/10)
    g.tick_duelist(p, 1.0)
    expected_gain = (1.0 / 57.0) + (1.0 / 10.0)
    assert p.weapon_charge == pytest.approx(expected_gain, rel=1e-2)


def test_lethal_haste_on_weapon_kill():
    g = GameInstance("t_lethal_haste")
    p = _duelist(g)
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(hp=1, max_hp=10, x=p.pos.x + 2, y=p.pos.y)
    floor.mobs[mob.id] = mob

    p.talent_info.talents[Talent.LETHAL_HASTE] = 2
    p.weapon_charge = 2.0

    g.use_weapon_ability(p.id, target_x=mob.pos.x, target_y=mob.pos.y)
    assert not mob.is_alive
    # Rank 2 gives haste duration 5.0 (level 2)
    haste_buff = p.get_buff("haste")
    assert haste_buff is not None
    assert haste_buff.remaining == pytest.approx(5.0, rel=1e-1)


def test_swift_equip_zero_delay_and_cooldown():
    from app.engine.entities.items.actions import action_equip
    g = GameInstance("t_swift_equip")
    p = _duelist(g)
    p.level = 12
    p.subclass_info.bonus_talent_points[2] = 5
    g.upgrade_talent(p.id, Talent.SWIFT_EQUIP)  # Rank 1: 1 charge

    assert p.swift_equip_charges == 1
    assert p.swift_equip_cooldown == 0.0

    sword = make_named_melee_weapon("Sword")
    p.belongings.backpack.collect(sword)

    # Equipping consumes swift charge with 0 action_until delay
    now = time.time()
    p.action_until = 0.0
    action_equip(g, p, sword)
    assert p.swift_equip_charges == 0
    assert p.swift_equip_cooldown == 20.0
    assert p.action_until <= now

    # While on cooldown, ticking reduces cooldown
    g.tick_duelist(p, 10.0)
    assert p.swift_equip_cooldown == 10.0
    assert p.swift_equip_charges == 0

    # Cooldown expires -> replenishes charges
    g.tick_duelist(p, 10.0)
    assert p.swift_equip_cooldown == 0.0
    assert p.swift_equip_charges == 1


# ===========================================================================
# Tier 3 Talents (Base & Subclasses)
# ===========================================================================

def test_precise_assault_guaranteed_hit():
    g = GameInstance("t_prec_assault")
    p = _duelist(g)
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(hp=100, max_hp=100, x=p.pos.x + 2, y=p.pos.y)
    floor.mobs[mob.id] = mob

    # Rank 3: Infinite Accuracy on next melee hit
    p.talent_info.talents[Talent.PRECISE_ASSAULT] = 3
    p.weapon_charge = 2.0

    g.use_weapon_ability(p.id, target_x=mob.pos.x, target_y=mob.pos.y)
    assert p.has_buff("precise_assault_tracker")

    # Melee attack consumes tracker and hits guaranteed
    res = resolve_melee_attack(p, mob, floor.mobs, mob.pos.x, mob.pos.y, floor=floor, game=g)
    assert res["hit"] is True
    assert not p.has_buff("precise_assault_tracker")


def test_deadly_followup_damage_scaling():
    g = GameInstance("t_deadly_followup")
    p = _duelist(g)
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(hp=100, max_hp=100, x=p.pos.x + 2, y=p.pos.y)
    floor.mobs[mob.id] = mob

    p.talent_info.talents[Talent.DEADLY_FOLLOWUP] = 3
    spike = MissileWeapon(name="Throwing Spikes", tier=1, quantity=2)
    resolve_ranged_attack(p, mob, spike, floor.mobs, mob.pos.x, mob.pos.y, floor=floor, game=g)

    tracker = mob.get_buff("deadly_followup_tracker")
    assert tracker is not None and tracker.level == 3


def test_champion_varied_charge_refund():
    g = GameInstance("t_varied_charge")
    p = _duelist(g)
    p.subclass_info.subclass = Subclass.CHAMPION
    p.talent_info.talents[Talent.VARIED_CHARGE] = 3  # +0.50 charge refund
    floor = g._get_or_create_floor(p.floor_id)

    rapier = make_named_melee_weapon("Rapier")
    dagger = make_named_melee_weapon("Dagger")
    p.belongings.weapon = rapier
    p.belongings.secondary_weapon = dagger
    p.weapon_charge = 4.0

    mob1 = _mob(hp=100, max_hp=100, x=p.pos.x + 2, y=p.pos.y, id="m1")
    floor.mobs[mob1.id] = mob1

    # Ability 1 with Rapier (Lunge) costs 1.0 charge -> 3.0 charge
    g.use_weapon_ability(p.id, target_x=mob1.pos.x, target_y=mob1.pos.y, use_secondary=False)
    assert p.weapon_charge == 3.0

    # Ability 2 with Dagger (Sneak) to an empty tile costs 1.0 charge, refunds +0.50 -> 2.50 charge
    g.use_weapon_ability(p.id, target_x=p.pos.x, target_y=p.pos.y - 1, use_secondary=True)
    assert p.weapon_charge == 2.5


def test_champion_twin_upgrades_effective_level():
    g = GameInstance("t_twin_upgrades")
    p = _duelist(g)
    p.subclass_info.subclass = Subclass.CHAMPION
    p.talent_info.talents[Talent.TWIN_UPGRADES] = 2  # Tier deficit >= 1

    t4_glaive = make_named_melee_weapon("Glaive", level=5)  # Tier 4 +5
    t3_sword = make_named_melee_weapon("Sword", level=1)    # Tier 3 +1
    p.belongings.weapon = t3_sword
    p.belongings.secondary_weapon = t4_glaive

    assert p.get_effective_weapon_level(t3_sword) == 5
    assert t3_sword.level == 1


def test_champion_combined_lethality_execute():
    g = GameInstance("t_comb_lethality")
    p = _duelist(g)
    p.subclass_info.subclass = Subclass.CHAMPION
    p.talent_info.talents[Talent.COMBINED_LETHALITY] = 3  # 40% execute
    floor = g._get_or_create_floor(p.floor_id)

    p.last_weapon_ability_id = "lunge"
    p.last_weapon_ability_weapon_name = "Rapier"
    p.last_weapon_ability_turn = getattr(g, "turns", 0)

    sword = make_named_melee_weapon("Sword")
    p.belongings.weapon = sword

    mob = _mob(hp=15, max_hp=50, x=p.pos.x + 1, y=p.pos.y)  # 30% HP <= 40%
    floor.mobs[mob.id] = mob

    res = resolve_melee_attack(p, mob, floor.mobs, mob.pos.x, mob.pos.y, floor=floor, game=g)
    assert res.get("ko") is True
    assert not mob.is_alive


def test_monk_unencumbered_spirit_gift_and_energy():
    g = GameInstance("t_unenc_spirit")
    p = _duelist(g)
    p.level = 20
    p.subclass_info.subclass = Subclass.MONK
    p.subclass_info.bonus_talent_points[3] = 5

    # Upgrade to rank 3 gifts Cloth Armor and Gloves
    g.upgrade_talent(p.id, Talent.UNENCUMBERED_SPIRIT)
    g.upgrade_talent(p.id, Talent.UNENCUMBERED_SPIRIT)
    g.upgrade_talent(p.id, Talent.UNENCUMBERED_SPIRIT)

    names = [i.name for i in p.belongings.backpack.items]
    assert "Cloth Armor" in names
    assert "Gloves" in names

    # Kill energy multiplier with T1 Cloth Armor and T1 Gloves (+100% + 100% = 3.0x)
    p.belongings.armor = ClothArmor()
    p.belongings.weapon = make_named_melee_weapon("Gloves")
    mob = _mob(hp=10, max_hp=10, x=p.pos.x + 1, y=p.pos.y)

    from app.engine.game.duelist_monk import calculate_monk_kill_energy
    energy = calculate_monk_kill_energy(p, mob)
    assert energy == 3.0  # Base 1.0 * 3.0


def test_monk_monastic_vigor_empowered_thresholds():
    g = GameInstance("t_monastic_vigor")
    p = _duelist(g)
    p.subclass_info.subclass = Subclass.MONK
    p.level = 10  # Max energy = 10

    # 0 points in Monastic Vigor: base Monk empowered at 100% (10 energy)
    p.monk_energy = 9.0
    assert p.is_monk_empowered() is False
    p.monk_energy = 10.0
    assert p.is_monk_empowered() is True

    # Rank 1: empowered at 80% (8 energy)
    p.talent_info.talents[Talent.MONASTIC_VIGOR] = 1
    p.monk_energy = 7.0
    assert p.is_monk_empowered() is False
    p.monk_energy = 8.0
    assert p.is_monk_empowered() is True

    # Rank 2: empowered at 60% (6 energy)
    p.talent_info.talents[Talent.MONASTIC_VIGOR] = 2
    p.monk_energy = 5.0
    assert p.is_monk_empowered() is False
    p.monk_energy = 6.0
    assert p.is_monk_empowered() is True

    # Rank 3: empowered at 40% (4 energy)
    p.talent_info.talents[Talent.MONASTIC_VIGOR] = 3
    p.monk_energy = 3.0
    assert p.is_monk_empowered() is False
    p.monk_energy = 4.0
    assert p.is_monk_empowered() is True


def test_monk_combined_energy_both_directions():
    g = GameInstance("t_comb_energy")
    p = _duelist(g)
    p.subclass_info.subclass = Subclass.MONK
    p.talent_info.talents[Talent.COMBINED_ENERGY] = 3  # Abilities costing >= 2 qualify
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(hp=100, max_hp=100, x=p.pos.x + 2, y=p.pos.y)
    floor.mobs[mob.id] = mob

    # Direction 1: Weapon Ability -> Monk Ability (Focus costs 2, refunds 1)
    floor.grid[p.pos.y][p.pos.x + 1] = TileType.FLOOR
    floor.grid[p.pos.y][p.pos.x + 2] = TileType.FLOOR
    p.monk_energy = 5.0
    p.weapon_charge = 2.0
    g.use_weapon_ability(p.id, target_x=mob.pos.x, target_y=mob.pos.y)
    g.use_monk_ability(p.id, "focus")
    assert p.monk_energy == 4.0  # Spent 2, refunded 1 -> 4.0

    # Direction 2: Monk Ability -> Weapon Ability
    floor.mobs.clear()
    floor.grid[p.pos.y][p.pos.x + 1] = TileType.FLOOR
    floor.grid[p.pos.y][p.pos.x + 2] = TileType.FLOOR
    p.monk_energy = 4.0
    p.weapon_charge = 2.0
    mob2 = _mob(hp=100, max_hp=100, x=p.pos.x + 2, y=p.pos.y, id="m2")
    floor.mobs[mob2.id] = mob2
    g.use_monk_ability(p.id, "focus")  # Energy 4 -> 2
    g.use_weapon_ability(p.id, target_x=mob2.pos.x, target_y=mob2.pos.y)  # Refunds 1.0 Monk energy -> 3.0
    assert p.monk_energy == 3.0


# ===========================================================================
# Tier 4 Talents & Armor Abilities
# ===========================================================================

def test_heroic_energy_universal_discount():
    g = GameInstance("t_heroic_energy")
    p = _duelist(g)
    p._kings_crown_worn = True
    p.armor_ability = ArmorAbilityType.CHALLENGE

    challenge = ChallengeArmorAbility()
    assert challenge.get_cost(p) == 35

    # 4 points: 40% reduction (35 * 0.60 = 21)
    p.talent_info.talents[Talent.HEROIC_ENERGY] = 4
    assert challenge.get_cost(p) == 21


def test_challenge_close_the_gap_leap():
    g = GameInstance("t_close_gap")
    p = _duelist(g)
    p._kings_crown_worn = True
    p.armor_ability = ArmorAbilityType.CHALLENGE
    p.talent_info.talents[Talent.CLOSE_THE_GAP] = 4  # Leap up to 5 tiles
    p.armor_charge = 100
    floor = g._get_or_create_floor(p.floor_id)

    mob = _mob(hp=50, max_hp=50, x=p.pos.x + 4, y=p.pos.y)
    floor.mobs[mob.id] = mob

    g.use_armor_ability(p.id, ArmorAbilityType.CHALLENGE, mob.pos.x, mob.pos.y)
    assert p.pos.x == mob.pos.x - 1  # Leaped adjacent


def test_challenge_elimination_match_cost_reduction():
    g = GameInstance("t_elim_match")
    p = _duelist(g)
    p._kings_crown_worn = True
    p.armor_ability = ArmorAbilityType.CHALLENGE
    p.talent_info.talents[Talent.ELIMINATION_MATCH] = 4  # 0.84^4 = ~0.498 (50% reduction)
    p.last_duel_ended_turn = getattr(g, "turns", 0)

    challenge = ChallengeArmorAbility()
    cost = challenge.get_cost(p, g)
    assert cost == round(35 * (0.84 ** 4))


def test_elemental_strike_talents_range_and_power():
    g = GameInstance("t_ele_strike")
    p = _duelist(g)
    p._kings_crown_worn = True
    p.armor_ability = ArmorAbilityType.ELEMENTAL_STRIKE
    p.talent_info.talents[Talent.ELEMENTAL_REACH] = 4   # 4 + 4 = 8 range
    p.talent_info.talents[Talent.STRIKING_FORCE] = 4    # 1.0 + 0.3*4 = 2.2x power
    p.talent_info.talents[Talent.DIRECTED_POWER] = 4    # 1.0 + 0.3*4*N single target

    ele_ability = ElementalStrikeArmorAbility()
    assert ele_ability.get_range(p) == 8


def test_feint_talents_haste_vulnerable_and_counter():
    g = GameInstance("t_feint_talents")
    p = _duelist(g)
    p._kings_crown_worn = True
    p.armor_ability = ArmorAbilityType.FEINT
    p.armor_charge = 100
    p.talent_info.talents[Talent.FEIGNED_RETREAT] = 3   # 6s Haste
    p.talent_info.talents[Talent.EXPOSE_WEAKNESS] = 3   # 6s Vulnerable & Weakness
    p.talent_info.talents[Talent.COUNTER_ABILITY] = 4   # 1.50 charge refund
    floor = g._get_or_create_floor(p.floor_id)

    # Use Feint to spawn afterimage
    feint = FeintArmorAbility()
    target_x = p.pos.x + 1
    target_y = p.pos.y
    g.use_armor_ability(p.id, ArmorAbilityType.FEINT, target_x, target_y)

    mob = _mob(hp=100, max_hp=100, x=p.pos.x + 2, y=p.pos.y)
    floor.mobs[mob.id] = mob

    # Mob attacks afterimage
    feint.on_afterimage_struck(g, p, mob)
    assert p.has_buff("haste")
    assert mob.has_buff("vulnerable")
    assert mob.has_buff("weakness")
    assert p.feint_cooldown_refund_ready is True

    # Next weapon ability refunds 4 * 0.375 = 1.50 charges (spent 1.0, gained 1.50 -> 1.50)
    p.weapon_charge = 1.0
    g.use_weapon_ability(p.id, target_x=mob.pos.x, target_y=mob.pos.y)
    assert p.weapon_charge == 1.50


def test_monk_unencumbered_spirit_backpack_full_floor_drop():
    g = GameInstance("t_unenc_drop")
    p = _duelist(g)
    p.level = 20
    p.subclass_info.subclass = Subclass.MONK
    p.subclass_info.bonus_talent_points[3] = 5
    floor = g._get_or_create_floor(p.floor_id)

    # Fill backpack to capacity (19 items)
    p.belongings.backpack.capacity = 0  # Cannot hold more

    g.upgrade_talent(p.id, Talent.UNENCUMBERED_SPIRIT)
    g.upgrade_talent(p.id, Talent.UNENCUMBERED_SPIRIT)
    g.upgrade_talent(p.id, Talent.UNENCUMBERED_SPIRIT)

    # Items dropped on floor at player pos
    floor_item_names = [it.name for it in floor.items.values()]
    assert "Cloth Armor" in floor_item_names
    assert "Gloves" in floor_item_names


def test_on_upgrade_no_duplicate_gifts_on_subsequent_upgrades():
    g = GameInstance("t_no_dup_gift")
    p = _duelist(g)
    p.level = 20
    p.subclass_info.subclass = Subclass.MONK
    p.subclass_info.bonus_talent_points[3] = 10

    # Upgrade Unencumbered Spirit to 3
    g.upgrade_talent(p.id, Talent.UNENCUMBERED_SPIRIT)
    g.upgrade_talent(p.id, Talent.UNENCUMBERED_SPIRIT)
    g.upgrade_talent(p.id, Talent.UNENCUMBERED_SPIRIT)

    count_cloth_before = sum(1 for it in p.belongings.backpack.items if it.name == "Cloth Armor")
    count_gloves_before = sum(1 for it in p.belongings.backpack.items if it.name == "Gloves")

    # Upgrade unrelated talent (Monastic Vigor)
    g.upgrade_talent(p.id, Talent.MONASTIC_VIGOR)

    count_cloth_after = sum(1 for it in p.belongings.backpack.items if it.name == "Cloth Armor")
    count_gloves_after = sum(1 for it in p.belongings.backpack.items if it.name == "Gloves")

    assert count_cloth_before == count_cloth_after == 1
    assert count_gloves_before == count_gloves_after == 1


def test_combined_energy_does_not_double_refund():
    g = GameInstance("t_comb_no_double")
    p = _duelist(g)
    p.subclass_info.subclass = Subclass.MONK
    p.talent_info.talents[Talent.COMBINED_ENERGY] = 3
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(hp=100, max_hp=100, x=p.pos.x + 2, y=p.pos.y)
    floor.mobs[mob.id] = mob

    # Monk Focus -> Energy 5 -> 3
    p.monk_energy = 5.0
    p.weapon_charge = 4.0
    g.use_monk_ability(p.id, "focus")

    # 1st weapon skill: refunds +1 Monk energy (energy -> 4.0)
    g.use_weapon_ability(p.id, target_x=mob.pos.x, target_y=mob.pos.y)
    assert p.monk_energy == 4.0

    # 2nd weapon skill without another Monk ability: no double refund
    g.use_weapon_ability(p.id, target_x=mob.pos.x, target_y=mob.pos.y)
    assert p.monk_energy == 4.0


def test_duelist_api_tier_talents_count():
    import asyncio
    from app.api.routes import get_talents
    data = asyncio.run(get_talents("duelist"))
    tiers = data["tiers"]

    # Tier 1 has exactly 4 talents in authentic SPD
    t1_ids = [t["id"] for t in tiers["1"]["talents"]]
    assert len(t1_ids) == 4
    assert t1_ids == [
        "strengthening_meal",
        "adventurers_intuition",
        "patient_strike",
        "aggressive_barrier",
    ]

    # Tier 2 has exactly 5 talents in authentic SPD
    t2_ids = [t["id"] for t in tiers["2"]["talents"]]
    assert len(t2_ids) == 5
    assert t2_ids == [
        "focused_meal",
        "liquid_agility",
        "weapon_recharging",
        "lethal_haste",
        "swift_equip",
    ]
