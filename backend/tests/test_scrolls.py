from app.engine.entities.base import ScrollOfTeleportation, ScrollOfRecharging, ScrollOfLullaby, ScrollOfTerror, ScrollOfRage, ScrollOfRetribution, Wand, Position, Mob, Faction
from app.engine.entities.mobs import Tengu
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


def test_scroll_of_lullaby_drowses_mobs_in_fov_and_eventually_sleeps_them():
    g = GameInstance("t")
    p = _player(g)
    floor = g._get_or_create_floor(p.floor_id)

    near_mob = Mob(
        id="m1", name="Rat1", pos=Position(x=p.pos.x + 1, y=p.pos.y),
        hp=10, max_hp=10, attack=1, defense=0, faction="dungeon", ai_state="wandering")
    far_mob = Mob(
        id="m2", name="Rat2", pos=Position(x=p.pos.x + 50, y=p.pos.y),
        hp=10, max_hp=10, attack=1, defense=0, faction="dungeon", ai_state="wandering")
    floor.mobs["m1"] = near_mob
    floor.mobs["m2"] = far_mob

    scroll = ScrollOfLullaby(id="scroll3")
    p.belongings.backpack.items.append(scroll)

    action_read(g, p, scroll)

    assert near_mob.has_buff("drowsy")
    assert not far_mob.has_buff("drowsy")

    # Move the player out of the mob's view distance so it can't re-aggro
    # while the drowsy buff is ticking down.
    p.pos = Position(x=p.pos.x + 50, y=p.pos.y)

    # Advance ~5 seconds (100 ticks at dt=0.05) so the drowsy buff expires.
    for _ in range(101):
        g.update_tick()

    assert not near_mob.has_buff("drowsy")
    assert near_mob.ai_state == "sleeping"


def test_scroll_of_terror_makes_mobs_flee_then_revert_to_hunting():
    g = GameInstance("t")
    p = _player(g)
    floor = g._get_or_create_floor(p.floor_id)

    near_mob = Mob(
        id="m1", name="Rat1", pos=Position(x=p.pos.x + 1, y=p.pos.y),
        hp=10, max_hp=10, attack=1, defense=0, faction="dungeon", ai_state="hunting")
    far_mob = Mob(
        id="m2", name="Rat2", pos=Position(x=p.pos.x + 50, y=p.pos.y),
        hp=10, max_hp=10, attack=1, defense=0, faction="dungeon", ai_state="hunting")
    tengu = Tengu(id="m3", pos=Position(x=p.pos.x - 1, y=p.pos.y))
    floor.mobs["m1"] = near_mob
    floor.mobs["m2"] = far_mob
    floor.mobs["m3"] = tengu

    scroll = ScrollOfTerror(id="scroll4")
    p.belongings.backpack.items.append(scroll)

    action_read(g, p, scroll)

    assert near_mob.has_buff("terror")
    assert near_mob.ai_state == "fleeing"

    assert not far_mob.has_buff("terror")

    # Tengu is immune to terror.
    assert not tengu.has_buff("terror")
    assert tengu.ai_state != "fleeing"

    # Advance 20 seconds (400 ticks at dt=0.05) so the terror buff expires.
    for _ in range(401):
        g.update_tick()

    assert not near_mob.has_buff("terror")
    assert near_mob.ai_state == "hunting"


def test_scroll_of_retribution_damages_fov_mobs_and_debuffs_reader():
    g = GameInstance("t")
    p = _player(g)
    floor = g._get_or_create_floor(p.floor_id)

    p.hp = p.max_hp // 2  # partial HP -> power > 0

    near_mob = Mob(
        id="m1", name="Rat1", pos=Position(x=p.pos.x + 1, y=p.pos.y),
        hp=10, max_hp=10, attack=1, defense=0, faction="dungeon", ai_state="wandering")
    weak_mob = Mob(
        id="m2", name="Rat2", pos=Position(x=p.pos.x - 1, y=p.pos.y),
        hp=1, max_hp=10, attack=1, defense=0, faction="dungeon", ai_state="wandering")
    far_mob = Mob(
        id="m3", name="Rat3", pos=Position(x=p.pos.x + 50, y=p.pos.y),
        hp=10, max_hp=10, attack=1, defense=0, faction="dungeon", ai_state="wandering")
    floor.mobs["m1"] = near_mob
    floor.mobs["m2"] = weak_mob
    floor.mobs["m3"] = far_mob

    scroll = ScrollOfRetribution(id="scroll5")
    p.belongings.backpack.items.append(scroll)

    action_read(g, p, scroll)

    max_hp = max(1, p.max_hp)
    power = min(4.0, 4.45 * (max_hp - (p.max_hp // 2)) / max_hp)

    expected_near_dmg = round(near_mob.max_hp / 10 + 10 * power * 0.225)
    assert near_mob.hp == max(0, 10 - expected_near_dmg)
    if near_mob.hp > 0:
        assert near_mob.has_buff("blindness")

    # Weak mob (hp=1) should die from retribution damage.
    expected_weak_dmg = round(weak_mob.max_hp / 10 + 1 * power * 0.225)
    assert expected_weak_dmg >= 1
    assert weak_mob.is_alive is False
    assert weak_mob.hp == 0
    death_events = [e for e in g.events if e["type"] == "DEATH" and e["data"]["target"] == "m2"]
    assert len(death_events) == 1

    # Mob outside FOV is unaffected.
    assert far_mob.hp == 10
    assert not far_mob.has_buff("blindness")

    # Reader gets weakness + blindness debuffs.
    assert p.has_buff("weakness")
    assert p.has_buff("blindness")


def test_scroll_of_rage_sets_amok_and_hunting_on_fov_mobs():
    g = GameInstance("t")
    p = _player(g)
    floor = g._get_or_create_floor(p.floor_id)

    near_mob = Mob(
        id="m1", name="Rat1", pos=Position(x=p.pos.x + 1, y=p.pos.y),
        hp=10, max_hp=10, attack=1, defense=0, faction="dungeon", ai_state="wandering")
    ally_mob = Mob(
        id="m2", name="Clone", pos=Position(x=p.pos.x - 1, y=p.pos.y),
        hp=10, max_hp=10, attack=1, defense=0, faction=Faction.PLAYER, ai_state="wandering")
    far_mob = Mob(
        id="m3", name="Rat3", pos=Position(x=p.pos.x + 50, y=p.pos.y),
        hp=10, max_hp=10, attack=1, defense=0, faction="dungeon", ai_state="wandering")
    floor.mobs["m1"] = near_mob
    floor.mobs["m2"] = ally_mob
    floor.mobs["m3"] = far_mob

    scroll = ScrollOfRage(id="scroll6")
    p.belongings.backpack.items.append(scroll)

    action_read(g, p, scroll)

    assert near_mob.ai_state == "hunting"
    assert near_mob.has_buff("amok")

    # include_allies=True -> ally (Faction.PLAYER) mob in FOV is also affected.
    assert ally_mob.ai_state == "hunting"
    assert ally_mob.has_buff("amok")

    # Out of FOV mob unaffected.
    assert far_mob.ai_state == "wandering"
    assert not far_mob.has_buff("amok")


def test_find_nearest_entity_returns_nearest_of_mixed_players_and_mobs_excluding_self():
    g = GameInstance("t")
    p = _player(g)
    floor = g._get_or_create_floor(p.floor_id)

    self_mob = Mob(
        id="self", name="Self", pos=Position(x=p.pos.x + 5, y=p.pos.y),
        hp=10, max_hp=10, attack=1, defense=0, faction="dungeon", ai_state="hunting")
    near_mob = Mob(
        id="m1", name="Near", pos=Position(x=self_mob.pos.x + 1, y=self_mob.pos.y),
        hp=10, max_hp=10, attack=1, defense=0, faction=Faction.PLAYER, ai_state="wandering")
    floor.mobs["self"] = self_mob
    floor.mobs["m1"] = near_mob

    # Player is further away than near_mob.
    p.pos = Position(x=self_mob.pos.x + 10, y=self_mob.pos.y)

    nearest = g._find_nearest_entity(self_mob.pos, p.floor_id, exclude_id="self")

    assert nearest is near_mob
