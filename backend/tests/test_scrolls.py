from app.engine.entities.base import ScrollOfTeleportation, ScrollOfRecharging, Wand, Position
from app.engine.entities.item_actions import action_read
from app.engine.manager import GameInstance


def _player(g):
    return g.add_player("p1", "Hero", "warrior")


def test_scroll_of_teleportation_moves_player_to_passable_unoccupied_cell():
    g = GameInstance("t")
    p = _player(g)
    floor = g._get_or_create_floor(p.floor_id)

    scroll = ScrollOfTeleportation(id="scroll1")
    p.belongings.backpack.items.append(scroll)

    action_read(g, p, scroll)

    assert 0 <= p.pos.x < floor.width
    assert 0 <= p.pos.y < floor.height
    assert floor.flags.passable[p.pos.y][p.pos.x]
    assert not any(
        m.is_alive and m.pos.x == p.pos.x and m.pos.y == p.pos.y
        for m in floor.mobs.values()
    )

    teleport_events = [e for e in g.events if e["type"] == "TELEPORT"]
    assert len(teleport_events) == 1
    assert teleport_events[0]["data"]["player"] == p.id
    assert teleport_events[0]["data"]["x"] == p.pos.x
    assert teleport_events[0]["data"]["y"] == p.pos.y


def test_scroll_of_recharging_fully_refills_wands_and_grants_buff():
    g = GameInstance("t")
    p = _player(g)

    wand = Wand(id="wand1", name="Wand of Test", charges=0, max_charges=3)
    p.belongings.backpack.items.append(wand)

    scroll = ScrollOfRecharging(id="scroll2")
    p.belongings.backpack.items.append(scroll)

    action_read(g, p, scroll)

    assert wand.charges == wand.max_charges
    assert p.has_buff("recharging")


def test_recharging_buff_regenerates_wand_charges_over_time():
    g = GameInstance("t")
    p = _player(g)

    wand = Wand(id="wand1", name="Wand of Test", charges=0, max_charges=3)
    p.belongings.backpack.items.append(wand)

    scroll = ScrollOfRecharging(id="scroll2")
    p.belongings.backpack.items.append(scroll)

    action_read(g, p, scroll)
    assert wand.charges == wand.max_charges  # instant full refill

    # Drain it back down to test the regen-over-time path.
    wand.charges = 0

    # 8 seconds / 0.05s per tick = 160 ticks.
    for _ in range(161):
        g.update_tick()

    assert wand.charges == 1
