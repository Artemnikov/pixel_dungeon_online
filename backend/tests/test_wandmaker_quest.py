"""Tests for the Wandmaker quest chain, Corpse Dust variant (MassGraveRoom,
CorpseDust pickup/buff, DustWraith spawner, WandmakerClaimReward).

Seed "2" is used for the levelgen-integration tests: it's a known seed where
WandmakerQuestState rolls quest_type == 1 (Corpse Dust) by depth 7 -- see
run_state.WandmakerQuestState / wandmaker_quest.py's module docstring for why
only type 1 is implemented in phase 1 (types 2/3 still consume the same RNG
draw but silently produce no room)."""
import uuid

from app.engine.entities.base import Position
from app.engine.entities.item_union import Chest
from app.engine.entities.items_consumable import CorpseDust
from app.engine.entities.items_wands import Wand
from app.engine.entities.wandmaker_quest import DustWraith, Wandmaker
from app.engine.manager import GameInstance


def _place_corpse_dust(floor, pos: Position) -> CorpseDust:
    dust = CorpseDust(id=str(uuid.uuid4()), pos=pos)
    floor.items[dust.id] = dust
    return dust


def test_mass_grave_room_spawns_wandmaker_and_corpse_dust_chest():
    g = GameInstance("wandmaker-spawn", seed="2")
    wandmaker = None
    dust_chest = None
    for depth in (6, 7, 8, 9):
        floor = g._get_or_create_floor(depth)
        found = next((m for m in floor.mobs.values() if isinstance(m, Wandmaker)), None)
        if found:
            wandmaker = found
        chest = next(
            (i for i in floor.items.values()
             if isinstance(i, Chest) and any(isinstance(c, CorpseDust) for c in i.contents)),
            None,
        )
        if chest:
            dust_chest = chest

    assert wandmaker is not None
    assert dust_chest is not None
    quest = g.run_state.wandmaker_quest
    assert quest.spawned is True
    assert quest.wand1_index is not None
    assert quest.wand2_index is not None
    assert quest.wand1_index != quest.wand2_index


def test_npc_interact_with_wandmaker_gives_quest():
    g = GameInstance("wandmaker-give")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)
    npc = Wandmaker(id="wm1", pos=Position(x=p.pos.x + 1, y=p.pos.y))
    floor.mobs[npc.id] = npc

    g.npc_interact("p1", npc.id)

    quest = g.run_state.wandmaker_quest
    assert quest.given is True
    events = [e for e in g.events if e["type"] == "WANDMAKER_DIALOGUE"]
    assert len(events) == 1
    assert events[0]["data"]["can_claim"] is False


def test_npc_interact_wandmaker_reminder_without_dust():
    g = GameInstance("wandmaker-reminder")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)
    npc = Wandmaker(id="wm1", pos=Position(x=p.pos.x + 1, y=p.pos.y))
    floor.mobs[npc.id] = npc
    g.run_state.wandmaker_quest.given = True

    g.npc_interact("p1", npc.id)

    events = [e for e in g.events if e["type"] == "WANDMAKER_DIALOGUE"]
    assert events[-1]["data"]["can_claim"] is False
    assert "corpse dust" in events[-1]["data"]["text"].lower()


def test_npc_interact_wandmaker_offers_wands_with_dust():
    g = GameInstance("wandmaker-offer")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)
    npc = Wandmaker(id="wm1", pos=Position(x=p.pos.x + 1, y=p.pos.y))
    floor.mobs[npc.id] = npc
    quest = g.run_state.wandmaker_quest
    quest.given = True
    quest.wand1_index = 0
    quest.wand1_level = 2
    quest.wand2_index = 3
    quest.wand2_level = 1
    p.inventory.append(CorpseDust(id="dust1"))

    g.npc_interact("p1", npc.id)

    events = [e for e in g.events if e["type"] == "WANDMAKER_DIALOGUE"]
    assert events[-1]["data"]["can_claim"] is True
    assert events[-1]["data"]["wand1"] is not None
    assert events[-1]["data"]["wand2"] is not None


def test_wandmaker_claim_reward_grants_wand_and_clears_dust():
    g = GameInstance("wandmaker-claim")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)
    npc = Wandmaker(id="wm1", pos=Position(x=p.pos.x + 1, y=p.pos.y))
    floor.mobs[npc.id] = npc
    quest = g.run_state.wandmaker_quest
    quest.given = True
    quest.wand1_index = 0
    quest.wand1_level = 2
    quest.wand2_index = 3
    quest.wand2_level = 1
    dust = CorpseDust(id="dust1")
    p.inventory.append(dust)
    p.add_buff("dust_ghost_spawner", duration=999999.0)
    wraith = DustWraith(id="wraith1", pos=Position(x=5, y=5))
    floor.mobs[wraith.id] = wraith

    g.wandmaker_claim_reward("p1", npc.id, "wand1")

    assert not any(isinstance(i, CorpseDust) for i in p.inventory)
    assert not p.has_buff("dust_ghost_spawner")
    assert wraith.id not in floor.mobs
    assert npc.id in floor.mobs  # Wandmaker persists, unlike Ghost

    wands = [i for i in p.inventory if isinstance(i, Wand)]
    assert len(wands) == 1
    assert wands[0].cursed is False
    assert wands[0].level == 2

    reward_events = [e for e in g.events if e["type"] == "WANDMAKER_REWARD"]
    assert len(reward_events) == 1


def test_wandmaker_claim_reward_fails_without_dust():
    g = GameInstance("wandmaker-claim-fail")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)
    npc = Wandmaker(id="wm1", pos=Position(x=p.pos.x + 1, y=p.pos.y))
    floor.mobs[npc.id] = npc
    quest = g.run_state.wandmaker_quest
    quest.given = True
    quest.wand1_index = 0
    quest.wand1_level = 2

    g.wandmaker_claim_reward("p1", npc.id, "wand1")

    assert not any(isinstance(i, Wand) for i in p.inventory)
    reward_events = [e for e in g.events if e["type"] == "WANDMAKER_REWARD"]
    assert len(reward_events) == 0


def test_corpse_dust_pickup_attaches_buff():
    g = GameInstance("wandmaker-pickup")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)
    _place_corpse_dust(floor, Position(x=p.pos.x + 1, y=p.pos.y))

    g.move_entity("p1", 1, 0)

    assert any(isinstance(i, CorpseDust) for i in p.inventory)
    assert p.has_buff("dust_ghost_spawner")


def test_dust_ghost_spawner_summons_wraith_once_power_threshold_reached():
    g = GameInstance("wandmaker-spawner")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)
    p.inventory.append(CorpseDust(id="dust1"))
    buff = p.add_buff("dust_ghost_spawner", duration=999999.0)
    buff.level = 10  # comfortably above the 1-wraith power_needed of 1

    g._tick_dust_ghost_spawner(p)

    wraiths = [m for m in floor.mobs.values() if isinstance(m, DustWraith)]
    assert len(wraiths) == 1
    assert wraiths[0].ai_state == "hunting"
    assert buff.level == 10  # 10 + 1 (tick increment) - 1 (power_needed for the first wraith)


def test_dust_ghost_spawner_resets_power_when_dust_dropped():
    g = GameInstance("wandmaker-spawner-reset")
    p = g.add_player("p1", "Bob")
    g._get_or_create_floor(p.floor_id)
    buff = p.add_buff("dust_ghost_spawner", duration=999999.0)
    buff.level = 5

    g._tick_dust_ghost_spawner(p)  # no CorpseDust in inventory

    assert buff.level == 0
