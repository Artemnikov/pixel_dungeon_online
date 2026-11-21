# Copyright (C) 2026 ArtemNikov
#
"""Yog-Dzewa (YogDzewa.java / HallsBossLevel.java) driven turn by turn."""

import pytest

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.buffs import add_buff
from app.engine.entities.mobs import Larva, YogRipper
from app.engine.game import yog_arena
from app.engine.game.ai_yog_dzewa import (
    FIST_CLASSES, build_fist_schedule, build_regular_summons, process_fist_death, yog_act, yog_flush,
)
from app.engine.game.constants import YOG_FIST_SPAWN_DELAY
from app.engine.turn.instance import TurnBasedGameInstance


def _room(players=1):
    g = TurnBasedGameInstance("yog-turn")
    g.players = {}
    floor = g.generate_floor(25)
    ex, ey = floor.entrance_pos
    heroes = []
    for i in range(players):
        p = g.add_player(f"p{i + 1}", f"Hero{i + 1}")
        p.floor_id = 25
        p.pos = Position(x=ex, y=ey)
        p.hp = p.max_hp = 10_000
        heroes.append(p)
    return g, floor, heroes


def _sealed(players=1):
    g, floor, heroes = _room(players)
    yog_arena.seal(g, floor, 25)
    yog = yog_arena.find_yog(floor)
    return g, floor, heroes, yog


def _noticed(players=1):
    g, floor, heroes, yog = _sealed(players)
    for h in heroes:
        h.pos = Position(x=yog.pos.x, y=yog.pos.y + 3)
    g._invalidate_fov_cache()
    yog_act(g, yog, floor, 25)
    assert yog.phase == 1
    return g, floor, heroes, yog


# --- seal and notice ---------------------------------------------------------

def test_arena_starts_without_yog_and_seals_two_tiles_from_entrance():
    g, floor, (hero,) = _room()
    assert yog_arena.find_yog(floor) is None
    ex, ey = floor.entrance_pos
    hero.pos = Position(x=ex, y=ey - 1)
    yog_arena.maybe_seal(g, hero, floor, 25)
    assert yog_arena.find_yog(floor) is None
    hero.pos = Position(x=ex, y=ey - 2)
    yog_arena.maybe_seal(g, hero, floor, 25)
    yog = yog_arena.find_yog(floor)
    assert yog is not None and (yog.pos.x, yog.pos.y) == floor.yog_pos
    assert yog.phase == 0
    assert floor.grid[ey][ex] == TileType.FLOOR_WOOD
    assert hero.locked_floor_left == 50.0
    assert floor.view_distance == 4


def test_yog_notices_only_when_a_hero_sees_it():
    g, floor, (hero,), yog = _sealed()
    assert yog_act(g, yog, floor, 25) == 1.0
    assert yog.phase == 0
    hero.pos = Position(x=yog.pos.x, y=yog.pos.y + 3)
    g._invalidate_fov_cache()
    g.flush_events()
    yog_act(g, yog, floor, 25)
    assert yog.phase == 1 and yog.fight_started
    assert 9 <= yog.ability_cooldown < 15 and 9 <= yog.summon_cooldown < 15
    yells = [e for e in g.flush_events() if e["type"] == "BOSS_YELL"]
    assert yells and yells[0]["data"]["key"] == "mob.yog_dzewa.notice"


def test_party_prompt_holds_initiator_then_seals_on_approval():
    g, floor, (a, b) = _room(players=2)
    ex, ey = floor.entrance_pos
    a.pos = Position(x=ex, y=ey - 2)
    yog_arena.maybe_seal(g, a, floor, 25)
    assert yog_arena.find_yog(floor) is None
    assert (a.pos.x, a.pos.y) == (ex, ey - 1)
    events = g.flush_events()
    assert any(e["type"] == "YOG_JOIN_PROMPT" for e in events)
    yog_arena.respond_yog_join(g, b.id, True)
    assert yog_arena.find_yog(floor) is not None
    assert a.locked_floor_left == 50.0 and b.locked_floor_left == 50.0


def test_start_without_sends_decliners_back_up():
    g, floor, (a, b) = _room(players=2)
    ex, ey = floor.entrance_pos
    a.pos = Position(x=ex, y=ey - 2)
    yog_arena.maybe_seal(g, a, floor, 25)
    yog_arena.respond_yog_join(g, b.id, False)
    assert yog_arena.find_yog(floor) is None
    yog_arena.decide_yog_start(g, a.id, "start_without")
    assert yog_arena.find_yog(floor) is not None
    assert b.floor_id == 24
    assert a.floor_id == 25


def test_late_arrival_is_sealed_in():
    g, floor, (a,), yog = _sealed()
    late = g.add_player("p9", "Late")
    late.floor_id = 25
    late.pos = Position(x=floor.entrance_pos[0], y=floor.entrance_pos[1])
    yog_flush(g, yog, floor, 25)
    assert late.locked_floor_left == 50.0


# --- death ray -----------------------------------------------------------------

def test_ray_telegraphs_then_fires_on_next_act():
    g, floor, (hero,), yog = _noticed()
    yog.ability_cooldown = 0
    yog.summon_cooldown = 99
    g.flush_events()
    spent = yog_act(g, yog, floor, 25)
    assert spent == 1.0
    assert yog.targeted_cells == [(hero.pos.x, hero.pos.y)]
    assert any(e["type"] == "YOG_TARGETED_CELLS" for e in g.flush_events())
    assert 9 <= yog.ability_cooldown <= 15
    hp = hero.hp
    yog_act(g, yog, floor, 25)
    assert yog.targeted_cells == []
    assert 20 <= hp - hero.hp <= 30
    assert g.boss_scores[4] == -500


def test_ray_waits_while_target_rooted():
    g, floor, (hero,), yog = _noticed()
    yog.ability_cooldown = 0
    yog.summon_cooldown = 99
    yog_act(g, yog, floor, 25)
    add_buff(hero.buffs, "roots", duration=5.0)
    hp = hero.hp
    yog_act(g, yog, floor, 25)
    assert hero.hp == hp and yog.targeted_cells


def test_ray_spares_yogs_own_minions():
    g, floor, (hero,), yog = _noticed()
    larva = g._spawn_mob_at(Larva, yog.pos.x, yog.pos.y + 2, 25)
    floor.mobs[larva.id] = larva
    yog.targeted_cells = [(hero.pos.x, hero.pos.y)]
    yog.beam_target_id = hero.id
    yog.summon_cooldown = 99
    yog.ability_cooldown = 99
    yog_act(g, yog, floor, 25)
    assert larva.hp == larva.max_hp
    assert hero.hp < hero.max_hp


def test_extra_beams_scale_with_lost_hp():
    g, floor, (hero,), yog = _noticed()
    yog.hp = 500
    yog.phase = 2
    yog.ability_cooldown = 0
    yog.summon_cooldown = 99
    yog_act(g, yog, floor, 25)
    assert len(yog.targeted_cells) in (1, 2)
    assert yog.targeted_cells[0] == (hero.pos.x, hero.pos.y)


def test_charge_spend_gated_by_target_cooldown():
    g, floor, (hero,), yog = _noticed()
    yog.ability_cooldown = 0
    yog.summon_cooldown = 99
    hero._last_turn_cost = 2.0
    assert yog_act(g, yog, floor, 25) == 2.0
    yog.ability_cooldown = 0
    hero._last_turn_cost = 9.0
    assert yog_act(g, yog, floor, 25) == 3.0


# --- summons -------------------------------------------------------------------

def test_summon_spawns_next_to_yog_nearest_target():
    g, floor, (hero,), yog = _noticed()
    yog.regular_summons = ["Larva"]
    yog.summon_cooldown = 0
    yog.ability_cooldown = 99
    yog_act(g, yog, floor, 25)
    larvae = [m for m in floor.mobs.values() if isinstance(m, Larva)]
    assert len(larvae) == 1
    assert (larvae[0].pos.x, larvae[0].pos.y) == (yog.pos.x, yog.pos.y + 1)
    assert 8 <= yog.summon_cooldown <= 15


def test_final_phase_burst_summons_several_at_once():
    g, floor, (hero,), yog = _noticed()
    yog.phase = 5
    yog.summon_cooldown = -15
    yog.ability_cooldown = 99
    yog_act(g, yog, floor, 25)
    minions = [m for m in floor.mobs.values() if isinstance(m, (Larva, YogRipper))]
    assert len(minions) >= 2
    assert yog.summon_cooldown <= 3
    assert yog.ability_cooldown <= 2


def test_regular_deck_follows_spawners_alive():
    assert all(c is Larva for c in build_regular_summons(0, False))
    two = build_regular_summons(2, False)
    assert two.count(YogRipper) == 2 and two.count(Larva) == 2


def test_fist_schedule_pairs_never_repeat():
    fists, challenge = build_fist_schedule(True)
    assert len(set(fists)) == 3 and len(set(challenge)) == 3
    assert not set(fists) & set(challenge)


# --- damage and phases ---------------------------------------------------------

def test_yog_is_invulnerable_before_notice_and_while_fists_live():
    g, floor, (hero,), yog = _sealed()
    assert yog.take_damage(50) == 0 and yog.hp == 1000
    yog.phase = 1
    yog.fists_alive = 1
    assert yog.take_damage(50) == 0


def test_damage_shortens_cooldowns_and_crossing_700_adds_a_fist():
    g, floor, (hero,), yog = _noticed()
    yog.ability_cooldown = 12
    yog.summon_cooldown = 12
    yog.take_damage(100)
    assert yog.ability_cooldown == pytest.approx(2.0)
    yog.take_damage(250)
    assert yog.hp == 700 and yog.phase == 2 and yog.fists_alive == 1
    assert yog.take_damage(50) == 0
    yog_flush(g, yog, floor, 25)
    fist = floor.mobs[yog.fist_ids[0]]
    ex, ey = floor.exit_pos
    assert (fist.pos.x, fist.pos.y) == (ex, ey + 1)
    assert type(fist) is FIST_CLASSES[fist.__class__.__name__]
    assert floor.view_distance == 3
    assert fist.spawn_delay == YOG_FIST_SPAWN_DELAY


def test_last_fist_death_starts_final_phase():
    g, floor, (hero,), yog = _noticed()
    yog.phase = 4
    yog.hp = 100
    yog.fists_alive = 1
    fist = FIST_CLASSES["BurningFist"](pos=Position(x=3, y=3))
    fist.yog_id = yog.id
    floor.mobs[fist.id] = fist
    yog.fist_ids.append(fist.id)
    fist.is_alive = False
    process_fist_death(g, fist, floor, 25)
    assert yog.phase == 5 and yog.summon_cooldown == -15
    assert yog.take_damage(150) == 100 and not yog.is_alive


def test_yog_death_unseals_and_scores():
    g, floor, (hero,), yog = _noticed()
    larva = g._spawn_mob_at(Larva, 5, 5, 25)
    floor.mobs[larva.id] = larva
    yog.phase = 5
    yog.take_damage(2000)
    g.handle_mob_death(yog, floor, 25)
    ex, ey = floor.entrance_pos
    xx, xy = floor.exit_pos
    assert floor.grid[ey][ex] == TileType.STAIRS_UP
    assert floor.grid[xy][xx] == TileType.STAIRS_DOWN
    assert not larva.is_alive
    assert hero.locked_floor_left is None
    assert g.boss_scores[4] == 5000
    assert floor.view_distance == 4


# --- turn-room cadence ---------------------------------------------------------

def test_turn_room_rays_and_summons_keep_coming():
    g, floor, (hero,), yog = _noticed()
    hero.pos = Position(x=yog.pos.x, y=yog.pos.y + 6)
    rays = summons = 0
    for _ in range(60):
        g._players_acted.add(hero.id)
        g._resolve_dungeon_phase()
        for e in g.flush_events():
            rays += e["type"] == "YOG_DEATH_RAY"
            summons += e["type"] == "MOB_SPAWN"
    assert 3 <= rays <= 7
    assert summons >= 3


def test_hitting_yog_turns_nearby_minions_on_the_attacker():
    g, floor, (hero,), yog = _noticed()
    near = g._spawn_mob_at(Larva, yog.pos.x + 2, yog.pos.y, 25)
    far = g._spawn_mob_at(Larva, yog.pos.x + 8, yog.pos.y, 25)
    for m in (near, far):
        m.ai_state = "wandering"
        floor.mobs[m.id] = m
    yog.defense_proc(10, hero, floor.mobs, yog.pos.x, yog.pos.y)
    assert near.aggro_target_id == hero.id and near.ai_state == "hunting"
    assert far.aggro_target_id is None
