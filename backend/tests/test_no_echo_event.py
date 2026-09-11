from app.engine.manager import GameInstance, Position
from app.engine.dungeon.constants import TileType
from app.engine.game.floor_state import FloorState
from app.engine.entities.subclasses import Talent

def test_events_not_echoed_to_source_player():
    game = GameInstance("test_no_echo")
    grid = [[TileType.FLOOR for _ in range(10)] for _ in range(10)]
    game.floors[1] = FloorState(floor_id=1, grid=grid, rooms=[], mobs={}, items={})
    
    p1 = game.add_player("p1", "Player 1")
    p2 = game.add_player("p2", "Player 2")
    p1.pos = Position(x=2, y=2)
    p2.pos = Position(x=3, y=2)
    
    # Emit an event with source_player_id="p1"
    game.add_event("SEARCH", {"x": 2, "y": 2}, source_player_id="p1")
    events = game.flush_events()
    
    # p1 (originating player) MUST NOT receive the event
    p1_events = game.filter_events_for_player(events, "p1")
    assert not any(e["type"] == "SEARCH" for e in p1_events)
    
    # p2 (other connected player in same room/floor/LOS) MUST receive the event
    p2_events = game.filter_events_for_player(events, "p2")
    assert any(e["type"] == "SEARCH" for e in p2_events)


def test_targeted_talent_upgraded_delivered_to_actor_only():
    """Actor-directed UI events are delivered via player_id targeting: the
    acting player receives them (the no-echo suppression must NOT apply when
    the event is explicitly targeted), and peers on the same floor never see
    them (targeted events are not broadcast)."""
    game = GameInstance("test_targeted_talent")
    grid = [[TileType.FLOOR for _ in range(10)] for _ in range(10)]
    game.floors[1] = FloorState(floor_id=1, grid=grid, rooms=[], mobs={}, items={})

    p1 = game.add_player("p1", "Player 1", "warrior")
    p2 = game.add_player("p2", "Player 2", "warrior")
    p1.pos = Position(x=2, y=2)
    p2.pos = Position(x=3, y=2)

    # Grant p1 a tier-1 talent point and upgrade a talent
    p1.level = 2
    game.on_talent_level_up(p1)
    assert game.upgrade_talent(p1.id, Talent.HEARTY_MEAL) is True

    events = game.flush_events()

    # The acting player receives their own TALENT_UPGRADED confirmation
    actor_events = [e for e in game.filter_events_for_player(events, p1.id) if e["type"] == "TALENT_UPGRADED"]
    assert len(actor_events) == 1
    assert actor_events[0]["data"]["player"] == p1.id
    assert actor_events[0]["data"]["talent"] == Talent.HEARTY_MEAL
    assert actor_events[0]["data"]["level"] == 1

    # A peer on the same floor must NOT receive the targeted event
    peer_events = [e for e in game.filter_events_for_player(events, p2.id) if e["type"] == "TALENT_UPGRADED"]
    assert peer_events == []


def test_wear_tengu_mask_choice_event_delivered_to_wearer_filtered():
    from app.engine.entities.base import Action
    from app.engine.entities.items.consumables import TenguMask

    game = GameInstance("test_mask_filter")
    grid = [[TileType.FLOOR for _ in range(10)] for _ in range(10)]
    game.floors[1] = FloorState(floor_id=1, grid=grid, rooms=[], mobs={}, items={})

    p1 = game.add_player("p1", "Player 1", "warrior")
    p2 = game.add_player("p2", "Player 2", "warrior")
    p1.pos = Position(x=2, y=2)
    p2.pos = Position(x=3, y=2)

    mask = TenguMask(id="mask1", name="Tengu's Mask")
    p1.belongings.backpack.collect(mask)

    game.execute_item_action(p1.id, mask.id, Action.WEAR)
    events = game.flush_events()

    # The wearing player MUST receive the SUBCLASS_CHOICE_AVAILABLE event in their broadcast
    p1_events = [e for e in game.filter_events_for_player(events, p1.id) if e["type"] == "SUBCLASS_CHOICE_AVAILABLE"]
    assert len(p1_events) == 1
    assert p1_events[0]["data"]["player"] == p1.id
    assert p1_events[0]["data"]["options"] == ["berserker", "gladiator"]

    # Other players on the same floor MUST NOT receive the private subclass choice dialog
    p2_events = [e for e in game.filter_events_for_player(events, p2.id) if e["type"] == "SUBCLASS_CHOICE_AVAILABLE"]
    assert p2_events == []


def test_wear_kings_crown_choice_event_delivered_to_wearer_filtered():
    from app.engine.entities.base import Action
    from app.engine.entities.items.consumables import KingsCrown
    from app.engine.entities.items.equip import Armor

    game = GameInstance("test_crown_filter")
    grid = [[TileType.FLOOR for _ in range(10)] for _ in range(10)]
    game.floors[1] = FloorState(floor_id=1, grid=grid, rooms=[], mobs={}, items={})

    p1 = game.add_player("p1", "Player 1", "warrior")
    p2 = game.add_player("p2", "Player 2", "warrior")
    p1.pos = Position(x=2, y=2)
    p2.pos = Position(x=3, y=2)

    p1.belongings.armor = Armor(name="Cloth Armor", tier=1, strength_requirement=10)
    crown = KingsCrown(id="crown1", name="King's Crown")
    p1.belongings.backpack.collect(crown)

    game.execute_item_action(p1.id, crown.id, Action.WEAR)
    events = game.flush_events()

    p1_events = [e for e in game.filter_events_for_player(events, p1.id) if e["type"] == "ARMOR_ABILITY_CHOICE_AVAILABLE"]
    assert len(p1_events) == 1
    assert p1_events[0]["data"]["player"] == p1.id

    p2_events = [e for e in game.filter_events_for_player(events, p2.id) if e["type"] == "ARMOR_ABILITY_CHOICE_AVAILABLE"]
    assert p2_events == []


def test_reemit_pending_choices_delivered_to_reconnecting_player_only():
    game = GameInstance("test_reemit_filter")
    grid = [[TileType.FLOOR for _ in range(10)] for _ in range(10)]
    game.floors[1] = FloorState(floor_id=1, grid=grid, rooms=[], mobs={}, items={})

    p1 = game.add_player("p1", "Player 1", "warrior")
    p2 = game.add_player("p2", "Player 2", "warrior")
    p1._tengu_mask_worn = True

    game.reemit_pending_choices(p1.id)
    events = game.flush_events()

    p1_events = [e for e in game.filter_events_for_player(events, p1.id) if e["type"] == "SUBCLASS_CHOICE_AVAILABLE"]
    assert len(p1_events) == 1
    assert p1_events[0]["data"]["player"] == p1.id

    p2_events = [e for e in game.filter_events_for_player(events, p2.id) if e["type"] == "SUBCLASS_CHOICE_AVAILABLE"]
    assert p2_events == []
