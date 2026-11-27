# Copyright (C) 2026 ArtemNikov
#
"""SPD Ratmogrify: the Rat King's crown trade, the armor ability and its
TransmogRat, the Ratmogrify talents and rat neutrality."""

import pytest

from app.engine.entities.base import Faction, Position
from app.engine.entities.mobs import Gnoll, Goo, Rat, AlbinoRat, RatKing, TransmogRat
from app.engine.entities.subclasses import ArmorAbilityType, Talent
from app.engine.entities.talent_enum import ArmorAbilityType as AAT
from app.engine.game.ai_spd_common import attack_delay, mob_attack_cooldown, move_cost
from app.engine.game.constants import TRANSMOG_RAT_DURATION
from app.engine.systems.combat import _roll_damage
from tests.conftest import make_open_game


def _setup(width=12, height=12, cls="warrior"):
    g = make_open_game(width, height)
    p = g.add_player("p1", "Hero", cls)
    p.floor_id = 1
    p.pos = Position(x=2, y=2)
    g._invalidate_fov_cache()
    floor = g._get_or_create_floor(1)
    return g, p, floor


def _rat_hero(g, p, **talents):
    p.armor_ability = ArmorAbilityType.RATMOGRIFY
    p.armor_charge = 100
    for name, pts in talents.items():
        p.talent_info.talents[name] = pts


def _place(floor, mob, x, y):
    mob.pos = Position(x=x, y=y)
    mob.floor_id = 1
    floor.mobs[mob.id] = mob
    return mob


def _messages(g, player_id):
    return [e for e in g.flush_events()
            if e["type"] == "MESSAGE" and e.get("_player_id") == player_id]


# ---------------------------------------------------------------- ability --

def test_ratmogrify_transforms_enemy_in_place_with_its_stats():
    g, p, floor = _setup()
    _rat_hero(g, p)
    gnoll = _place(floor, Gnoll(ai_state="hunting"), 4, 2)
    gnoll.hp = 7

    g.use_armor_ability(p.id, "ratmogrify", 4, 2)

    assert gnoll.id not in floor.mobs
    rats = [m for m in floor.mobs.values() if isinstance(m, TransmogRat)]
    assert len(rats) == 1
    rat = rats[0]
    assert (rat.pos.x, rat.pos.y) == (4, 2)
    assert (rat.hp, rat.max_hp) == (7, gnoll.max_hp)
    assert rat.attack_skill == gnoll.attack_skill
    assert rat.defense_skill == gnoll.defense_skill
    assert rat.exp == gnoll.exp and rat.max_lvl == gnoll.max_lvl
    assert (rat.get_damage_min(), rat.get_damage_max()) == (gnoll.damage_min, gnoll.damage_max)
    assert rat.loot_table == gnoll.loot_table
    assert rat.ai_state == "hunting"
    assert rat.faction == Faction.DUNGEON
    assert rat.original_name == "Gnoll"
    assert p.armor_charge == 50


def test_transmog_rat_reverts_after_six_turns_with_its_hp():
    g, p, floor = _setup()
    _rat_hero(g, p)
    gnoll = _place(floor, Gnoll(), 4, 2)
    g.use_armor_ability(p.id, "ratmogrify", 4, 2)
    rat = next(m for m in floor.mobs.values() if isinstance(m, TransmogRat))
    rat.hp = 3
    rat.pos = Position(x=5, y=3)

    from app.engine.game.tick_steps import run_buff_upkeep
    assert run_buff_upkeep(g, rat, floor, 1, False, TRANSMOG_RAT_DURATION - 0.5) is True
    assert rat.id in floor.mobs
    assert run_buff_upkeep(g, rat, floor, 1, False, 1.0) is False

    assert rat.id not in floor.mobs
    assert floor.mobs[gnoll.id] is gnoll
    assert gnoll.hp == 3 and (gnoll.pos.x, gnoll.pos.y) == (5, 3)


@pytest.mark.parametrize("make_target,expected", [
    (lambda: Rat(), "cant_transform"),
    (lambda: AlbinoRat(), "cant_transform"),
    (lambda: Gnoll(faction=Faction.PLAYER), "cant_transform"),
    (lambda: Goo(), "too_strong"),
])
def test_ratmogrify_refusals_cost_no_charge(make_target, expected):
    g, p, floor = _setup()
    _rat_hero(g, p)
    target = _place(floor, make_target(), 4, 2)
    g.flush_events()

    g.use_armor_ability(p.id, "ratmogrify", 4, 2)

    assert p.armor_charge == 100
    assert target.id in floor.mobs
    keys = [m["data"].get("key") for m in _messages(g, p.id)]
    assert f"ability.ratmogrify.{expected}" in keys


def test_ratmogrify_empty_cell_and_self_without_ratforcements():
    g, p, floor = _setup()
    _rat_hero(g, p)
    g.flush_events()
    g.use_armor_ability(p.id, "ratmogrify", 6, 6)
    g.use_armor_ability(p.id, "ratmogrify", p.pos.x, p.pos.y)
    keys = [m["data"].get("key") for m in _messages(g, p.id)]
    assert keys == ["ability.target.no_target", "ability.target.self_target"]
    assert p.armor_charge == 100


def test_ratmogrify_needs_the_ability():
    g, p, floor = _setup()
    p.armor_charge = 100
    p.armor_ability = ArmorAbilityType.ENDURE
    gnoll = _place(floor, Gnoll(), 4, 2)
    g.use_armor_ability(p.id, "ratmogrify", 4, 2)
    assert gnoll.id in floor.mobs and p.armor_charge == 100


def test_heroic_energy_discounts_ratmogrify():
    g, p, floor = _setup()
    _rat_hero(g, p, **{Talent.HEROIC_ENERGY: 4})
    _place(floor, Gnoll(), 4, 2)
    g.use_armor_ability(p.id, "ratmogrify", 4, 2)
    assert p.armor_charge == 100 - 30


def test_ratsistance_scales_hostile_rat_damage():
    g, p, floor = _setup()
    _rat_hero(g, p, **{Talent.RATSISTANCE: 2})
    gnoll = _place(floor, Gnoll(damage_min=10, damage_max=10), 4, 2)
    g.use_armor_ability(p.id, "ratmogrify", 4, 2)
    rat = next(m for m in floor.mobs.values() if isinstance(m, TransmogRat))
    assert gnoll.id not in floor.mobs
    assert _roll_damage(rat, {}) == int(10 * 0.9 ** 2)
    rat.make_ally()
    assert _roll_damage(rat, {}) == 10


def test_ratlomacy_befriends_a_transmog_rat_permanently_with_adrenaline():
    g, p, floor = _setup()
    _rat_hero(g, p, **{Talent.RATLOMACY: 3})
    _place(floor, Gnoll(), 4, 2)
    g.use_armor_ability(p.id, "ratmogrify", 4, 2)
    rat = next(m for m in floor.mobs.values() if isinstance(m, TransmogRat))
    p.armor_charge = 100

    g.use_armor_ability(p.id, "ratmogrify", rat.pos.x, rat.pos.y)

    assert rat.allied and rat.faction == Faction.PLAYER and rat.owner_id == p.id
    assert not rat.has_buff("transmog_timer")
    assert rat.get_buff("adrenaline").remaining == pytest.approx(4.0)
    assert p.armor_charge == 50

    p.armor_charge = 100
    g.use_armor_ability(p.id, "ratmogrify", rat.pos.x, rat.pos.y)
    assert p.armor_charge == 100


def test_ratmogrify_on_transmog_rat_without_ratlomacy_is_refused():
    g, p, floor = _setup()
    _rat_hero(g, p)
    _place(floor, Gnoll(), 4, 2)
    g.use_armor_ability(p.id, "ratmogrify", 4, 2)
    p.armor_charge = 100
    g.use_armor_ability(p.id, "ratmogrify", 4, 2)
    assert p.armor_charge == 100


def test_ratforcements_spawns_allied_rats_next_to_the_hero():
    g, p, floor = _setup()
    _rat_hero(g, p, **{Talent.RATFORCEMENTS: 3})
    g.use_armor_ability(p.id, "ratmogrify", p.pos.x, p.pos.y)
    rats = [m for m in floor.mobs.values() if type(m) is Rat]
    assert len(rats) == 3
    for r in rats:
        assert r.faction == Faction.PLAYER and r.owner_id == p.id
        assert max(abs(r.pos.x - p.pos.x), abs(r.pos.y - p.pos.y)) == 1
    assert len({(r.pos.x, r.pos.y) for r in rats}) == 3
    assert p.armor_charge == 50


def test_killing_a_transmog_rat_awards_the_originals_xp():
    g, p, floor = _setup()
    _rat_hero(g, p)
    _place(floor, Gnoll(), 3, 2)
    g.use_armor_ability(p.id, "ratmogrify", 3, 2)
    rat = next(m for m in floor.mobs.values() if isinstance(m, TransmogRat))
    before = p.experience
    rat.hp = 1
    rat.defense_skill = 0
    for _ in range(50):
        if not rat.is_alive:
            break
        p.last_attack_time = 0
        g.move_entity(p.id, 1, 0)
    assert not rat.is_alive
    assert p.experience == before + Gnoll().exp


# ---------------------------------------------------------------- neutral --

def test_rat_seen_by_a_ratmogrify_player_turns_neutral_and_wakes():
    g, p, floor = _setup()
    _rat_hero(g, p)
    rat = _place(floor, Rat(ai_state="sleeping"), 5, 2)
    albino = _place(floor, AlbinoRat(), 6, 3)
    g._tick_mob(rat, floor, 1)
    g._tick_mob(albino, floor, 1)
    assert rat.faction == Faction.NEUTRAL and rat.ai_state == "wandering"
    assert albino.faction == Faction.NEUTRAL


def test_rat_stays_hostile_without_a_ratmogrify_player():
    g, p, floor = _setup()
    rat = _place(floor, Rat(), 5, 2)
    g._tick_mob(rat, floor, 1)
    assert rat.faction == Faction.DUNGEON


def test_neutral_mobs_neither_target_nor_get_targeted():
    g, p, floor = _setup()
    sheep = _place(floor, Rat(faction=Faction.NEUTRAL), 3, 2)
    assert g._find_nearest_hostile(sheep.pos, 1, faction=Faction.NEUTRAL, exclude_id=sheep.id) is None
    gnoll = _place(floor, Gnoll(), 3, 3)
    assert g._find_nearest_hostile(gnoll.pos, 1, faction=Faction.DUNGEON, exclude_id=gnoll.id) is p
    p.pos = Position(x=11, y=11)
    assert g._find_nearest_hostile(gnoll.pos, 1, faction=Faction.DUNGEON, exclude_id=gnoll.id) is p


# ------------------------------------------------------------- adrenaline --

def test_mob_adrenaline_speeds_attacks_and_movement():
    gnoll = Gnoll()
    base_delay, base_cd, base_move = attack_delay(gnoll), mob_attack_cooldown(gnoll), move_cost(gnoll)
    gnoll.add_buff("adrenaline", duration=5.0, level=1)
    assert attack_delay(gnoll) == pytest.approx(base_delay / 1.5)
    assert mob_attack_cooldown(gnoll) == pytest.approx(base_cd / 1.5)
    assert move_cost(gnoll) == pytest.approx(base_move / 2)


# ---------------------------------------------------------------- talents --

def test_ratmogrify_talents_need_ratmogrify():
    g, p, floor = _setup()
    p.level = 25
    p.armor_ability = ArmorAbilityType.ENDURE
    assert g.upgrade_talent(p.id, Talent.RATSISTANCE) is False
    p.armor_ability = AAT.RATMOGRIFY
    assert g.upgrade_talent(p.id, Talent.RATSISTANCE) is True
    assert g.upgrade_talent(p.id, Talent.HEROIC_ENERGY) is True
    assert g.upgrade_talent(p.id, Talent.SUSTAINED_RETRIBUTION) is False


# --------------------------------------------------------------- rat king --

def _with_king(g, floor):
    return _place(floor, RatKing(), 3, 2)


def _give_crown(p, armor=True):
    from app.engine.entities.items.consumables import KingsCrown
    from app.engine.entities.items.equip import Armor
    if armor:
        p.belongings.armor = Armor(name="Cloth Armor", tier=1, strength_requirement=10)
    crown = KingsCrown(id="crown", name="King's Crown")
    p.belongings.backpack.collect(crown)
    return crown


def _yells(events):
    return [e["data"]["key"] for e in events if e["type"] == "BOSS_YELL"]


def test_first_talk_wakes_the_rat_king_for_everyone():
    g, p, floor = _setup()
    king = _with_king(g, floor)
    _give_crown(p)
    g.flush_events()

    g.npc_interact(p.id, king.id)

    events = g.flush_events()
    assert _yells(events) == ["mobText.rat_king_not_sleeping"]
    assert any(e["type"] == "MOB_NOTICE" for e in events)
    assert not any(e["type"] == "RAT_KING_DIALOGUE" for e in events)
    assert king.ai_state == "wandering"


def test_awake_rat_king_offers_ratmogrify_for_the_crown_to_that_player():
    g, p, floor = _setup()
    king = _with_king(g, floor)
    king.ai_state = "wandering"
    _give_crown(p)
    g.flush_events()

    g.npc_interact(p.id, king.id)

    events = [e for e in g.flush_events() if e["type"] == "RAT_KING_DIALOGUE"]
    assert len(events) == 1
    assert events[0]["_player_id"] == p.id
    assert events[0]["data"] == {"player": p.id, "npc": king.id}


def test_rat_king_refuses_a_hero_without_armor():
    g, p, floor = _setup()
    king = _with_king(g, floor)
    king.ai_state = "wandering"
    _give_crown(p, armor=False)
    p.belongings.armor = None
    g.flush_events()
    g.npc_interact(p.id, king.id)
    assert _yells(g.flush_events()) == ["mobText.rat_king_crown_clothes"]


def test_accepting_trades_the_crown_for_ratmogrify():
    g, p, floor = _setup()
    king = _with_king(g, floor)
    king.ai_state = "wandering"
    crown = _give_crown(p)
    g.flush_events()

    g.rat_king_crown_choice(p.id, king.id, True)

    assert p.armor_ability == AAT.RATMOGRIFY
    assert p.belongings.get_item(crown.id) is None
    events = g.flush_events()
    assert _yells(events) == ["mobText.rat_king_crown_thankyou"]
    assert any(e["type"] == "MESSAGE" and e["data"]["key"] == "ability.ratmogrify.ratgraded" for e in events)
    assert any(e["type"] == "ARMOR_ABILITY_CHOSEN" and e["data"]["ability"] == "ratmogrify" for e in events)

    g.npc_interact(p.id, king.id)
    assert _yells(g.flush_events()) == ["mobText.rat_king_crown_after"]


def test_declining_keeps_the_crown():
    g, p, floor = _setup()
    king = _with_king(g, floor)
    king.ai_state = "wandering"
    crown = _give_crown(p)
    g.flush_events()
    g.rat_king_crown_choice(p.id, king.id, False)
    assert p.armor_ability == ""
    assert p.belongings.get_item(crown.id) is not None
    assert _yells(g.flush_events()) == ["mobText.rat_king_crown_fine"]


def test_crown_choice_needs_adjacency_and_the_crown():
    g, p, floor = _setup()
    king = _with_king(g, floor)
    king.ai_state = "wandering"
    _give_crown(p)
    king.pos = Position(x=8, y=8)
    g.rat_king_crown_choice(p.id, king.id, True)
    assert p.armor_ability == ""

    g2, p2, floor2 = _setup()
    king2 = _with_king(g2, floor2)
    _give_crown(p2)
    p2.belongings.backpack.detach("crown")
    g2.rat_king_crown_choice(p2.id, king2.id, True)
    assert p2.armor_ability == ""


def test_rat_king_without_a_crown_has_no_time():
    g, p, floor = _setup()
    king = _with_king(g, floor)
    king.ai_state = "wandering"
    g.flush_events()
    g.npc_interact(p.id, king.id)
    assert _yells(g.flush_events()) == ["mobText.rat_king_what_is_it"]


def test_awake_rat_king_wanders_and_never_attacks():
    g, p, floor = _setup()
    king = _with_king(g, floor)
    gnoll = _place(floor, Gnoll(), 4, 3)
    king.ai_state = "wandering"
    g._mob_move_times = {}
    for _ in range(5):
        g._mob_move_times[king.id] = 0.0
        g._mob_wander_pause_until = {}
        g._tick_mob(king, floor, 1)
    assert gnoll.hp == gnoll.max_hp
    assert king.ai_state == "wandering"
