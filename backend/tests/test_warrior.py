"""Warrior talent tree: tier-gating formula, T1/T2 talent effects, Berserk,
Combo (Gladiator) mechanics + finisher moves, and armor abilities."""

import random

from app.engine.manager import GameInstance
from app.engine.entities.base import Position, Action
from app.engine.entities.items.consumables import KingsCrown, TenguMask
from app.engine.entities.items.equip import Armor
from app.engine.entities.player import Mob as MobEntity
from app.engine.entities.subclasses import Subclass, Talent, ArmorAbilityType, CLASS_ARMOR_ABILITIES
from app.engine.systems.loot import _make_item


def _warrior(game, pid="w"):
    return game.add_player(pid, "Warrior", "warrior")


def _mob(hp=20, max_hp=20, x=2, y=1, **kw):
    kw.setdefault("dr_min", 0)
    kw.setdefault("dr_max", 0)
    return MobEntity(id="m", name="Rat", pos=Position(x=x, y=y),
                     hp=hp, max_hp=max_hp, attack=2, defense=0,
                     defense_skill=0, **kw)


def _grant_mask(p):
    """Simulate wearing Tengu's Mask (grants the subclass choice)."""
    p._tengu_mask_worn = True
    return p


def _grant_crown(p):
    """Simulate wearing the King's Crown (grants the armor ability choice)."""
    p._kings_crown_worn = True
    return p


def _level_up(game, player, level):
    player.level = level
    game.on_talent_level_up(player)


# --- talent_points_available formula ---------------------------------------

def test_tier1_points_available_at_level_2():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 2)
    assert g.talent_points_available(p, 1) == 1


def test_tier1_points_capped_at_5_after_level_7():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 7)
    assert g.talent_points_available(p, 1) == 5


def test_tier1_points_increase_every_level():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 2)
    assert g.talent_points_available(p, 1) == 1
    _level_up(g, p, 3)
    assert g.talent_points_available(p, 1) == 2
    _level_up(g, p, 4)
    assert g.talent_points_available(p, 1) == 3
    _level_up(g, p, 5)
    assert g.talent_points_available(p, 1) == 4
    _level_up(g, p, 6)
    assert g.talent_points_available(p, 1) == 5


def test_tier3_locked_without_subclass():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 13)
    assert g.talent_points_available(p, 3) == 0


def test_tier3_unlocked_with_subclass():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 13)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.GLADIATOR)
    assert g.talent_points_available(p, 3) == 1


def test_tier4_locked_without_armor_ability():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 21)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.GLADIATOR)
    assert g.talent_points_available(p, 4) == 0


def test_tier4_unlocked_with_armor_ability():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 21)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.GLADIATOR)
    _grant_crown(p)
    assert g.choose_armor_ability(p.id, ArmorAbilityType.SHOCKWAVE) is True
    assert g.talent_points_available(p, 4) == 1
    _level_up(g, p, 25)
    assert g.talent_points_available(p, 4) == 5


# --- choose_armor_ability gating --------------------------------------------

def test_choose_armor_ability_requires_crown_not_level_or_subclass():
    # Matches SPD: King's Crown gates the choice, not level/subclass.
    g = GameInstance("t")
    p = _warrior(g)
    # Without the crown, no choice can be made regardless of level.
    assert g.choose_armor_ability(p.id, ArmorAbilityType.ENDURE) is False
    _grant_crown(p)
    assert g.choose_armor_ability(p.id, ArmorAbilityType.ENDURE) is True
    assert p.armor_ability == ArmorAbilityType.ENDURE
    # cannot pick again
    assert g.choose_armor_ability(p.id, ArmorAbilityType.HEROIC_LEAP) is False


def test_choose_armor_ability_rejects_invalid_choice():
    g = GameInstance("t")
    p = _warrior(g)
    _grant_crown(p)
    assert g.choose_armor_ability(p.id, "spectral_blades") is False


# --- King's Crown (WEAR -> ARMOR_ABILITY_CHOICE_AVAILABLE) -------------------

def test_make_item_kings_crown():
    item = _make_item("kings_crown")
    assert isinstance(item, KingsCrown)
    assert item.kind == "kings_crown"


def test_wear_kings_crown_with_armor_emits_choice_event():
    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.armor = Armor(name="Cloth Armor", tier=1, strength_requirement=10)
    crown = KingsCrown(id="crown", name="King's Crown")
    p.belongings.backpack.collect(crown)

    g.execute_item_action(p.id, crown.id, Action.WEAR)

    raw_events = g.flush_events()
    events = [e for e in raw_events if e["type"] == "ARMOR_ABILITY_CHOICE_AVAILABLE"]
    assert len(events) == 1
    assert events[0]["data"]["player"] == p.id
    assert events[0]["data"]["options"] == list(CLASS_ARMOR_ABILITIES.get(p.class_type, ()))
    filtered = [e for e in g.filter_events_for_player(raw_events, p.id) if e["type"] == "ARMOR_ABILITY_CHOICE_AVAILABLE"]
    assert len(filtered) == 1
    # Wearing opens the choice window but does NOT consume the crown (SPD:
    # it is only detached once an ability is actually picked), so the choice
    # can be re-opened by re-wearing after dismissing.
    assert p.belongings.get_item(crown.id) is not None
    assert p._kings_crown_worn is True


def test_wear_kings_crown_then_pick_consumes_crown():
    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.armor = Armor(name="Cloth Armor", tier=1, strength_requirement=10)
    crown = KingsCrown(id="crown", name="King's Crown")
    p.belongings.backpack.collect(crown)

    g.execute_item_action(p.id, crown.id, Action.WEAR)
    g.flush_events()
    assert g.choose_armor_ability(p.id, ArmorAbilityType.ENDURE) is True
    assert p.armor_ability == ArmorAbilityType.ENDURE
    # The pick consumed the crown and closed the window.
    assert p.belongings.get_item(crown.id) is None
    assert p._kings_crown_worn is False


def test_wear_kings_crown_without_armor_is_noop():
    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.armor = None
    crown = KingsCrown(id="crown", name="King's Crown")
    p.belongings.backpack.collect(crown)

    g.execute_item_action(p.id, crown.id, Action.WEAR)

    events = [e for e in g.flush_events() if e["type"] == "ARMOR_ABILITY_CHOICE_AVAILABLE"]
    assert events == []
    assert p.belongings.get_item(crown.id) is not None
    assert p._kings_crown_worn is False


def test_wear_kings_crown_without_armor_emits_message():
    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.armor = None
    crown = KingsCrown(id="crown", name="King's Crown")
    p.belongings.backpack.collect(crown)

    g.execute_item_action(p.id, crown.id, Action.WEAR)

    messages = [e for e in g.flush_events()
                if e["type"] == "MESSAGE" and e.get("_player_id") == p.id]
    assert any("wearing armor" in m["data"]["text"] for m in messages)


def test_wear_tengu_mask_opens_choice_without_consuming():
    g = GameInstance("t")
    p = _warrior(g)
    mask = TenguMask(id="mask", name="Tengu's Mask")
    p.belongings.backpack.collect(mask)

    g.execute_item_action(p.id, mask.id, Action.WEAR)

    raw_events = g.flush_events()
    events = [e for e in raw_events if e["type"] == "SUBCLASS_CHOICE_AVAILABLE"]
    assert len(events) == 1
    assert events[0]["data"]["player"] == p.id
    filtered = [e for e in g.filter_events_for_player(raw_events, p.id) if e["type"] == "SUBCLASS_CHOICE_AVAILABLE"]
    assert len(filtered) == 1
    # Still in the backpack: dismissing the window keeps the choice re-openable.
    assert p.belongings.get_item(mask.id) is not None
    assert p._tengu_mask_worn is True
    # The mask must be worn before a subclass can be chosen.
    assert g.choose_subclass(p.id, Subclass.GLADIATOR) is True
    assert p.subclass_info.subclass == Subclass.GLADIATOR
    assert p.belongings.get_item(mask.id) is None
    assert p._tengu_mask_worn is False


def test_wear_tengu_mask_dismiss_keeps_choice_reopenable():
    g = GameInstance("t")
    p = _warrior(g)
    mask = TenguMask(id="mask", name="Tengu's Mask")
    p.belongings.backpack.collect(mask)

    # Wear (choice window opens), then "dismiss" (client just closes the modal).
    g.execute_item_action(p.id, mask.id, Action.WEAR)
    g.flush_events()
    # Re-wearing re-opens the window; the choice still works afterwards.
    g.execute_item_action(p.id, mask.id, Action.WEAR)
    events = [e for e in g.flush_events() if e["type"] == "SUBCLASS_CHOICE_AVAILABLE"]
    assert len(events) == 1
    assert g.choose_subclass(p.id, Subclass.GLADIATOR) is True


def test_wear_kings_crown_after_ability_chosen_is_noop():
    g = GameInstance("t")
    p = _warrior(g)
    p.belongings.armor = Armor(name="Cloth Armor", tier=1, strength_requirement=10)
    _grant_crown(p)
    g.choose_armor_ability(p.id, ArmorAbilityType.ENDURE)
    crown = KingsCrown(id="crown", name="King's Crown")
    p.belongings.backpack.collect(crown)

    g.execute_item_action(p.id, crown.id, Action.WEAR)

    events = [e for e in g.flush_events() if e["type"] == "ARMOR_ABILITY_CHOICE_AVAILABLE"]
    assert events == []
    assert p.belongings.get_item(crown.id) is not None


# --- upgrade_talent gating ---------------------------------------------------

def test_upgrade_talent_t3_requires_subclass():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 13)
    assert g.upgrade_talent(p.id, Talent.HOLD_FAST) is False
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.GLADIATOR)
    assert g.upgrade_talent(p.id, Talent.HOLD_FAST) is True


def test_upgrade_talent_t3_subclass_specific_requires_match():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 13)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.GLADIATOR)
    # Berserker-only talent, player is Gladiator
    assert g.upgrade_talent(p.id, Talent.ENDLESS_RAGE) is False
    assert g.upgrade_talent(p.id, Talent.CLEAVE) is True


def test_upgrade_talent_t4_requires_matching_armor_ability():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 24)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.GLADIATOR)
    _grant_crown(p)
    g.choose_armor_ability(p.id, ArmorAbilityType.HEROIC_LEAP)
    # Shockwave talent gated out
    assert g.upgrade_talent(p.id, Talent.EXPANDING_WAVE) is False
    # Heroic Leap talent allowed
    assert g.upgrade_talent(p.id, Talent.BODY_SLAM) is True
    # Universal HEROIC_ENERGY available regardless of chosen ability
    assert g.upgrade_talent(p.id, Talent.HEROIC_ENERGY) is True


# --- T1/T2 talent effect hooks -----------------------------------------------

def test_hearty_meal_heals_when_low_hp():
    g = GameInstance("t")
    p = _warrior(g)
    p.subclass_info.talent_info.talents[Talent.HEARTY_MEAL] = 1
    p.hp = 1
    p.max_hp = 30
    from app.engine.entities.items.consumables import Food
    food = Food(id="f", name="Mango", energy=8)
    g.on_food_eaten(p, food)
    assert p.hp == 1 + 2 + 2 * 1


def test_iron_stomach_grants_hunger_immunity_buff():
    g = GameInstance("t")
    p = _warrior(g)
    p.subclass_info.talent_info.talents[Talent.IRON_STOMACH] = 2
    from app.engine.entities.items.consumables import Food
    food = Food(id="f", name="Mango", energy=8)
    g.on_food_eaten(p, food)
    assert p.has_buff("iron_stomach_immunity")


def test_liquid_willpower_grants_shield_on_potion():
    g = GameInstance("t")
    p = _warrior(g)
    p.subclass_info.talent_info.talents[Talent.LIQUID_WILLPOWER] = 1
    p.max_hp = 100
    from app.engine.entities.items.potions import Potion
    potion = Potion(id="pot", name="Potion")
    g.on_potion_drunk(p, potion)
    shield = p.get_shield("liquid_willpower")
    assert shield is not None
    assert shield.amount == round(100 * (0.030 + 0.035 * 1))


def test_provoked_anger_grants_bonus_on_next_attack():
    g = GameInstance("t")
    p = _warrior(g)
    p.subclass_info.talent_info.talents[Talent.PROVOKED_ANGER] = 2
    p.hp = 50
    p.max_hp = 50

    # No shield: taking damage must NOT prime the tracker (SPD only procs when
    # a shield buff is broken by damage).
    p.take_damage(5)
    assert not p.has_buff("provoked_anger_tracker")

    # Shield that survives the hit: no proc.
    p.add_shield("barrier", 10, priority=0, decay=0)
    p.take_damage(4)
    assert not p.has_buff("provoked_anger_tracker")
    barrier = p.get_shield("barrier")
    assert barrier is not None and barrier.amount == 6

    # Shield destroyed by the hit: tracker primed.
    p.take_damage(6)
    assert p.has_buff("provoked_anger_tracker")
    assert p.get_talent_damage_bonus() == 1 + 2 * 2
    # consumed
    assert not p.has_buff("provoked_anger_tracker")
    assert p.get_talent_damage_bonus() == 0.0


def test_lethal_momentum_on_kill_chance(monkeypatch):
    g = GameInstance("t")
    p = _warrior(g)
    p.subclass_info.talent_info.talents[Talent.LETHAL_MOMENTUM] = 4  # 100% chance
    monkeypatch.setattr(random, "random", lambda: 0.0)
    g.on_kill(p, _mob(), {}, p.floor_id)
    assert p.has_buff("lethal_momentum_tracker")


# --- Berserk -----------------------------------------------------------------

def test_endless_rage_raises_berserk_power_cap():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 6)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.BERSERKER)
    p.subclass_info.talent_info.talents[Talent.ENDLESS_RAGE] = 3
    p.berserk_power = 0.95
    g.trigger_berserk(p.id)
    p.berserk_power = 1.0 + 0.1667 * 3 - 0.001
    g.add_berserk_power(p, p.get_total_max_hp() * 4)
    assert p.berserk_power <= 1.0 + 0.1667 * 3


def test_deathless_fury_cheats_death():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 6)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.BERSERKER)
    p.subclass_info.talent_info.talents[Talent.DEATHLESS_FURY] = 1
    p.berserk_power = 1.0
    p.berserk_active = False
    p.hp = 5
    p.max_hp = 50
    dealt = p.take_damage(100)
    assert dealt == 0
    assert p.hp == 1
    assert p.is_alive
    assert p.berserk_active
    assert p.berserk_cooldown == 200 - 50 * 1


# --- Combo (Gladiator) --------------------------------------------------------

def test_combo_count_increments_on_attack_proc():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 6)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.GLADIATOR)
    target = _mob()
    p.attack_proc(target)
    assert p.combo_count == 1
    assert p.combo_timer == 5.0


def test_cleave_resets_combo_timer_on_kill():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 6)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.GLADIATOR)
    p.subclass_info.talent_info.talents[Talent.CLEAVE] = 2
    p.combo_count = 3
    g.on_kill(p, _mob(), {}, p.floor_id)
    assert p.combo_timer == 15.0 + 15.0 * 2


def test_combo_decays_and_resets_use_flags():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 6)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.GLADIATOR)
    p.combo_count = 5
    p.combo_timer = 0.1
    p.clobber_used = True
    p.parry_used = True
    g.update_combo(p, 0.2)
    assert p.combo_count == 0
    assert not p.clobber_used
    assert not p.parry_used


def test_clobber_combo_move_knocks_back_target():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 6)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.GLADIATOR)
    floor = g._get_or_create_floor(p.floor_id)
    floor.mobs.clear()
    # Place target below player; knock goes down through open floor.
    target = _mob(x=p.pos.x, y=p.pos.y + 1)
    floor.mobs[target.id] = target
    orig_y = target.pos.y
    p.combo_count = 2
    p.combo_timer = 5.0
    assert g.use_combo_move(p.id, "clobber", target.pos.x, target.pos.y) is True
    assert target.pos.y > orig_y  # knocked back at least 1 tile
    assert p.clobber_used
    assert p.combo_count == 0


def test_slam_combo_move_deals_damage():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 6)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.GLADIATOR)
    floor = g._get_or_create_floor(p.floor_id)
    floor.mobs.clear()
    target = _mob(hp=100, max_hp=100, x=p.pos.x + 1, y=p.pos.y, dr_min=0, dr_max=0)
    floor.mobs[target.id] = target
    p.combo_count = 4
    p.combo_timer = 5.0
    assert g.use_combo_move(p.id, "slam", target.pos.x, target.pos.y) is True
    assert target.hp < 100
    assert p.combo_count == 0


def test_fury_combo_move_repeats_attack():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 6)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.GLADIATOR)
    floor = g._get_or_create_floor(p.floor_id)
    floor.mobs.clear()
    target = _mob(hp=1000, max_hp=1000, x=p.pos.x + 1, y=p.pos.y, dr_min=0, dr_max=0)
    floor.mobs[target.id] = target
    p.combo_count = 10
    p.combo_timer = 5.0
    hp_before = target.hp
    assert g.use_combo_move(p.id, "fury", target.pos.x, target.pos.y) is True
    assert target.hp < hp_before
    assert p.combo_count == 0


def test_combo_move_rejected_below_threshold():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 6)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.GLADIATOR)
    p.combo_count = 1
    assert g.use_combo_move(p.id, "slam", 0, 0) is False


# --- Armor abilities -----------------------------------------------------------

def test_heroic_energy_reduces_charge_cost():
    from app.engine.game.armor_abilities import _heroic_energy_mult
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 6)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.GLADIATOR)
    p.subclass_info.talent_info.talents[Talent.HEROIC_ENERGY] = 4
    assert _heroic_energy_mult(p) == 0.60


def test_endure_banks_and_reduces_incoming_damage():
    g = GameInstance("t")
    p = _warrior(g)
    _level_up(g, p, 13)
    _grant_mask(p)
    g.choose_subclass(p.id, Subclass.BERSERKER)
    _grant_crown(p)
    g.choose_armor_ability(p.id, ArmorAbilityType.ENDURE)
    from app.engine.entities.buffs import add_buff
    add_buff(p.buffs, "endure_tracker", duration=12.0, level=1)
    mob = _mob()
    reduced = p.defense_proc(10, mob, {}, p.pos.x, p.pos.y)
    assert reduced == int(10 * 0.5)
    assert p.endure_banked == 5.0
