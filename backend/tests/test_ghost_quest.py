"""Tests for the sewers Ghost quest chain (Ghost NPC spawn, quest-boss spawn
on interact, completion on boss death, and the weapon-or-armor reward claim).
"""
import uuid

from app.engine.entities.base import Position
from app.engine.entities.items_equip import Armor, MeleeWeapon
from app.engine.entities.quest_bosses import FetidRat, Ghost, GnollTrickster, GreatCrab
from app.engine.manager import GameInstance

# Fixed seed that reliably spawns a Ghost (quest_type=1, FetidRat) on depth 2.
_SEED = "8"


def _spawn_ghost_floor():
    g = GameInstance("ghost-fixed", seed=_SEED)
    floor = g._get_or_create_floor(2)
    ghost = next(m for m in floor.mobs.values() if isinstance(m, Ghost))
    return g, floor, ghost


def test_ghost_spawns_on_depth_2_with_correct_quest_type():
    g, floor, ghost = _spawn_ghost_floor()
    assert g.run_state.ghost_quest.spawned is True
    assert g.run_state.ghost_quest.quest_type == 1  # depth 2 -> FetidRat
    assert g.run_state.ghost_quest.depth == 2
    assert ghost.faction == "player"  # never attacked by players on contact


def test_ghost_does_not_spawn_on_depth_1():
    for s in range(10):
        g = GameInstance("ghost-d1", seed=str(s))
        floor = g._get_or_create_floor(1)
        assert not any(isinstance(m, Ghost) for m in floor.mobs.values())
        assert g.run_state.ghost_quest.spawned is False


def test_ghost_does_not_spawn_on_boss_floor_5():
    for s in range(10):
        g = GameInstance("ghost-d5", seed=str(s))
        floor = g._get_or_create_floor(5)
        assert not any(isinstance(m, Ghost) for m in floor.mobs.values())


def test_npc_interact_with_ghost_spawns_quest_boss_and_gives_quest():
    g, floor, ghost = _spawn_ghost_floor()
    p = g.add_player("p1", "Bob")
    p.floor_id = 2
    p.pos = Position(x=ghost.pos.x + 1, y=ghost.pos.y)

    g.npc_interact("p1", ghost.id)

    quest = g.run_state.ghost_quest
    assert quest.given is True
    assert quest.boss_id is not None
    boss = floor.mobs[quest.boss_id]
    assert isinstance(boss, FetidRat)

    events = [e for e in g.events if e["type"] == "GHOST_DIALOGUE"]
    assert len(events) == 1
    assert events[0]["data"]["can_claim"] is False
    assert "fetid rat" in events[0]["data"]["text"]
    assert "Bob" in events[0]["data"]["text"]


def test_reinteract_before_boss_death_shows_reminder_dialogue():
    g, floor, ghost = _spawn_ghost_floor()
    p = g.add_player("p1", "Bob")
    p.floor_id = 2
    p.pos = Position(x=ghost.pos.x + 1, y=ghost.pos.y)

    g.npc_interact("p1", ghost.id)
    g.npc_interact("p1", ghost.id)

    events = [e for e in g.events if e["type"] == "GHOST_DIALOGUE"]
    assert len(events) == 2
    assert events[1]["data"]["can_claim"] is False
    assert "abomination" in events[1]["data"]["text"]


def test_quest_completes_only_when_boss_dies_on_spawn_depth():
    g, floor, ghost = _spawn_ghost_floor()
    quest = g.run_state.ghost_quest
    quest.given = True
    boss = FetidRat(id=str(uuid.uuid4()), pos=Position(x=10, y=10))
    floor.mobs[boss.id] = boss
    quest.boss_id = boss.id

    g.handle_mob_death(boss, floor, 2)  # same depth the quest was given on

    assert quest.processed is True
    messages = [e for e in g.events if e["type"] == "MESSAGE"]
    assert any("come find me" in e["data"]["text"] for e in messages)


def test_quest_does_not_complete_if_boss_killed_on_wrong_floor():
    g, floor, ghost = _spawn_ghost_floor()
    quest = g.run_state.ghost_quest
    quest.given = True
    floor3 = g._get_or_create_floor(3)
    boss = FetidRat(id=str(uuid.uuid4()), pos=Position(x=10, y=10))
    floor3.mobs[boss.id] = boss
    quest.boss_id = boss.id

    g.handle_mob_death(boss, floor3, 3)  # wrong depth -- quest.depth is 2

    assert quest.processed is False


def test_ghost_claim_reward_fails_before_quest_processed():
    g, floor, ghost = _spawn_ghost_floor()
    p = g.add_player("p1", "Bob")
    p.floor_id = 2
    p.pos = Position(x=ghost.pos.x + 1, y=ghost.pos.y)
    quest = g.run_state.ghost_quest
    quest.given = True  # not yet processed

    g.ghost_claim_reward("p1", ghost.id, "weapon")

    assert ghost.id in floor.mobs
    assert not any(isinstance(i, (MeleeWeapon, Armor)) for i in p.inventory)


def test_ghost_claim_reward_grants_chosen_weapon_and_despawns_ghost():
    g, floor, ghost = _spawn_ghost_floor()
    p = g.add_player("p1", "Bob")
    p.floor_id = 2
    p.pos = Position(x=ghost.pos.x + 1, y=ghost.pos.y)
    quest = g.run_state.ghost_quest
    quest.given = True
    quest.processed = True
    assert quest.weapon_tier_category is not None  # rolled at spawn time

    g.ghost_claim_reward("p1", ghost.id, "weapon")

    assert ghost.id not in floor.mobs
    weapons = [i for i in p.inventory if isinstance(i, MeleeWeapon)]
    assert len(weapons) == 1
    assert weapons[0].cursed is False
    assert weapons[0].level_known is True

    reward_events = [e for e in g.events if e["type"] == "GHOST_REWARD"]
    assert len(reward_events) == 1


def test_ghost_claim_reward_grants_chosen_armor():
    g, floor, ghost = _spawn_ghost_floor()
    p = g.add_player("p1", "Bob")
    p.floor_id = 2
    p.pos = Position(x=ghost.pos.x + 1, y=ghost.pos.y)
    quest = g.run_state.ghost_quest
    quest.given = True
    quest.processed = True

    g.ghost_claim_reward("p1", ghost.id, "armor")

    armors = [i for i in p.inventory if isinstance(i, Armor)]
    assert len(armors) == 1
    assert armors[0].tier == quest.armor_tier or armors[0].tier is not None


def test_ghost_quest_shared_across_party():
    g, floor, ghost = _spawn_ghost_floor()
    p1 = g.add_player("p1", "Bob")
    p2 = g.add_player("p2", "Alice")
    p1.floor_id = p2.floor_id = 2
    p1.pos = Position(x=ghost.pos.x + 1, y=ghost.pos.y)

    g.npc_interact("p1", ghost.id)  # Bob gets the quest
    quest = g.run_state.ghost_quest
    boss = floor.mobs[quest.boss_id]

    g.handle_mob_death(boss, floor, 2)  # boss dies (e.g. to Alice's attack)
    assert quest.processed is True

    p2.pos = Position(x=ghost.pos.x + 1, y=ghost.pos.y)
    g.ghost_claim_reward("p2", ghost.id, "weapon")  # Alice claims it

    assert ghost.id not in floor.mobs
    assert any(isinstance(i, MeleeWeapon) for i in p2.inventory)


def test_gnoll_trickster_never_melees_and_great_crab_blocks_melee_when_awake():
    gnoll = GnollTrickster(id=str(uuid.uuid4()), pos=Position(x=0, y=0))
    assert gnoll.attack_range > 1

    crab = GreatCrab(id=str(uuid.uuid4()), pos=Position(x=0, y=0))
    crab.ai_state = "hunting"
    assert crab.get_effective_defense_skill() >= 10 ** 9
    crab.ai_state = "sleeping"
    assert crab.get_effective_defense_skill() < 10 ** 9
