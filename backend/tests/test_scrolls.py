from app.engine.entities.base import Position, Faction, is_immune
from app.engine.entities.items_consumable import Seed, Gold
from app.engine.entities.items_equip import Dagger
from app.engine.entities.items_potions import HealthPotion, PotionOfLiquidFlame
from app.engine.entities.items_scrolls import ScrollOfTeleportation, ScrollOfRecharging, ScrollOfLullaby, ScrollOfTerror, ScrollOfRage, ScrollOfRetribution, ScrollOfIdentify, ScrollOfRemoveCurse, ScrollOfTransmutation, ScrollOfMirrorImage, ScrollOfMagicMapping, ScrollOfMetamorphosis, ScrollOfUpgrade
from app.engine.entities.items_wands import Wand
from app.engine.entities.player import Mob
from app.engine.entities.mobs import Tengu, MirrorImage
from app.engine.entities.scroll_actions import action_read
from app.engine.entities.scroll_predicates import player_inventory_items
from app.engine.entities.subclasses import Talent
from app.engine.dungeon.constants import TileType
from app.engine.manager import GameInstance


def _detach_starter_scroll(p):
    for it in list(p.belongings.backpack.items):
        if it.kind == "scroll_of_identify":
            p.belongings.backpack.detach(it.id)
            return


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


def test_scroll_of_recharging_grants_regen_buff():
    g = GameInstance("t")
    p = _player(g)

    wand = Wand(id="wand1", name="Wand of Test", charges=0, max_charges=3)
    p.belongings.backpack.items.append(wand)

    scroll = ScrollOfRecharging(id="scroll2")
    p.belongings.backpack.items.append(scroll)

    action_read(g, p, scroll)

    assert wand.charges == 0  # SPD: no instant refill, only regen-speed buff
    assert p.has_buff("recharging")


def test_recharging_buff_regenerates_wand_charges_over_time():
    g = GameInstance("t")
    p = _player(g)

    wand = Wand(id="wand1", name="Wand of Test", charges=0, max_charges=3)
    p.belongings.backpack.items.append(wand)

    scroll = ScrollOfRecharging(id="scroll2")
    p.belongings.backpack.items.append(scroll)

    action_read(g, p, scroll)
    assert wand.charges == 0  # SPD: no instant refill

    # With 3x recharging rate: 1st charge takes ~12.3s, 2nd takes ~13.5s more.
    # 700 ticks = 35s → enough for 2 charges.
    for _ in range(700):
        g.update_tick()

    assert wand.charges == 2


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
    assert p.has_buff("drowsy")  # SPD also drowses the reader

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

    # SPD: all mobs (including allies) are beckoned to player, but allies
    # are NOT amok'd (include_allies=False by default for amok).
    assert ally_mob.ai_state == "hunting"
    assert not ally_mob.has_buff("amok")

    # Out of FOV mob: beckoned (hunting) but no amok.
    assert far_mob.ai_state == "hunting"
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


# --- Scroll of Identify -----------------------------------------------------------

def test_scroll_of_identify_lists_unidentified_identifiable_items():
    g = GameInstance("t")
    p = _player(g)

    potion = HealthPotion(id="potion1")
    p.belongings.backpack.collect(potion)
    seed = Seed(id="seed1", name="Seed")
    p.belongings.backpack.collect(seed)

    _detach_starter_scroll(p)
    scroll = ScrollOfIdentify(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    assert len(select_events) == 1
    data = select_events[0]["data"]
    assert data["scroll_kind"] == "scroll_of_identify"
    assert potion.id in data["candidates"]
    assert seed.id not in data["candidates"]


def test_scroll_of_identify_excludes_already_identified_kind():
    g = GameInstance("t")
    p = _player(g)

    known_potion = HealthPotion(id="potion1")
    p.belongings.backpack.collect(known_potion)
    g.identified_kinds.add(known_potion.kind)

    # A second potion of a different kind, unidentified, ensures ≥1 candidate.
    unknown_potion = PotionOfLiquidFlame(id="potion2", level_known=False, cursed_known=False)
    p.belongings.backpack.collect(unknown_potion)

    _detach_starter_scroll(p)
    scroll = ScrollOfIdentify(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    assert len(select_events) == 1
    assert known_potion.id not in select_events[0]["data"]["candidates"]


def test_scroll_of_identify_select_target_reveals_kind():
    g = GameInstance("t")
    p = _player(g)

    potion = HealthPotion(id="potion1")
    potion.level_known = False
    potion.cursed_known = False
    p.belongings.backpack.collect(potion)

    _detach_starter_scroll(p)
    scroll = ScrollOfIdentify(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    assert len(select_events) == 1
    assert potion.id in select_events[0]["data"]["candidates"]

    g.select_scroll_target(p.id, scroll.id, potion.id)

    assert potion.kind in g.identified_kinds
    assert potion.level_known is True
    assert potion.cursed_known is True


def test_scroll_of_identify_no_candidates_does_not_consume_scroll():
    from app.engine.entities.scroll_predicates import player_inventory_items

    g = GameInstance("t")
    p = _player(g)

    # Mark every starting item's kind as already identified so none qualify.
    for it in player_inventory_items(p):
        g.identified_kinds.add(it.kind)

    _detach_starter_scroll(p)

    # Only other item present besides the scroll itself is a seed (not identifiable).
    seed = Seed(id="seed1", name="Seed")
    p.belongings.backpack.collect(seed)

    scroll = ScrollOfIdentify(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    assert len(select_events) == 1  # dialog always opens (SPD)
    assert select_events[0]["data"]["candidates"] == []

    assert p.belongings.get_item(scroll.id) is not None  # not consumed (already identified)


# --- Scroll of Remove Curse -------------------------------------------------------

def test_scroll_of_remove_curse_lists_cursed_item_as_candidate():
    g = GameInstance("t")
    p = _player(g)

    weapon = Dagger(id="weapon1")
    weapon.cursed = True
    weapon.cursed_known = True
    p.belongings.backpack.collect(weapon)

    scroll = ScrollOfRemoveCurse(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    assert len(select_events) == 1
    data = select_events[0]["data"]
    assert data["scroll_kind"] == "scroll_of_remove_curse"
    assert weapon.id in data["candidates"]

    g.select_scroll_target(p.id, scroll.id, weapon.id)

    assert weapon.cursed is False
    assert weapon.cursed_known is True


def test_scroll_of_remove_curse_lists_cursed_weapon_enchant_as_candidate():
    g = GameInstance("t")
    p = _player(g)

    weapon = Dagger(id="weapon1")
    weapon.cursed = False
    weapon.cursed_known = True
    weapon.enchantment = "annoying"
    p.belongings.backpack.collect(weapon)

    scroll = ScrollOfRemoveCurse(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    assert len(select_events) == 1
    assert weapon.id in select_events[0]["data"]["candidates"]


def test_scroll_of_remove_curse_strips_weapon_curse_enchant():
    g = GameInstance("t")
    p = _player(g)

    weapon = Dagger(id="weapon1")
    weapon.cursed = True
    weapon.cursed_known = True
    weapon.enchantment = "annoying"
    p.belongings.backpack.collect(weapon)

    scroll = ScrollOfRemoveCurse(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    assert weapon.id in select_events[0]["data"]["candidates"]

    g.select_scroll_target(p.id, scroll.id, weapon.id)

    assert weapon.cursed is False
    assert weapon.enchantment is None


def test_scroll_of_remove_curse_on_wand_sets_level_known():
    g = GameInstance("t")
    p = _player(g)

    wand = Wand(id="wand1", name="Wand of Test")
    wand.cursed = True
    wand.cursed_known = True
    wand.level_known = False
    p.belongings.backpack.collect(wand)

    scroll = ScrollOfRemoveCurse(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    assert wand.id in select_events[0]["data"]["candidates"]

    g.select_scroll_target(p.id, scroll.id, wand.id)

    assert wand.cursed is False
    assert wand.level_known is True


def test_scroll_of_remove_curse_ignores_non_equipable_categories():
    g = GameInstance("t")
    p = _player(g)

    potion = HealthPotion(id="potion1")
    potion.cursed = True  # not meaningful for potions, but set anyway
    p.belongings.backpack.collect(potion)

    scroll = ScrollOfRemoveCurse(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    if select_events:
        assert potion.id not in select_events[0]["data"]["candidates"]


def test_scroll_of_remove_curse_no_candidates_does_not_consume_scroll():
    g = GameInstance("t")
    p = _player(g)

    # Strip all equipable items so none qualify as a Remove Curse candidate.
    p.belongings.weapon = None
    p.belongings.armor = None
    p.belongings.artifact = None
    if p.belongings.ring is not None:
        p.belongings.ring = None
    if p.belongings.misc is not None:
        p.belongings.misc = None

    scroll = ScrollOfRemoveCurse(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    assert len(select_events) == 1  # dialog always opens
    assert select_events[0]["data"]["candidates"] == []

    # Scroll was unidentified → consumed immediately (SPD).
    assert p.belongings.get_item(scroll.id) is None


# --- Scroll of Transmutation -------------------------------------------------------

def test_scroll_of_transmutation_lists_expected_candidates():
    from app.engine.entities.item_catalog import TRANSMUTE_GROUPS

    g = GameInstance("t")
    p = _player(g)

    potion = HealthPotion(id="potion1")
    p.belongings.backpack.collect(potion)

    extra_scroll = ScrollOfTeleportation(id="otherscroll1")
    p.belongings.backpack.collect(extra_scroll)

    seed = Seed(id="seed1", name="Seed")
    p.belongings.backpack.collect(seed)

    gold = Gold(id="gold1", name="Gold", quantity=50)
    p.belongings.backpack.collect(gold)

    scroll = ScrollOfTransmutation(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    assert len(select_events) == 1
    candidates = select_events[0]["data"]["candidates"]

    # The starting melee weapon is transmutable as input.
    # worn_shortsword is no longer in the output pool (Bug 4 fix).
    assert p.belongings.weapon.id in candidates

    assert potion.id in candidates
    assert extra_scroll.id in candidates

    # Seed is now transmutable (SPD allows it).
    assert seed.id in candidates
    # Not transmutable: the transmutation scroll itself, gold.
    assert scroll.id not in candidates
    assert gold.id not in candidates


def test_scroll_of_transmutation_equipped_weapon_changes_kind_keeps_id_and_flags():
    from app.engine.entities.item_catalog import TRANSMUTE_GROUPS

    g = GameInstance("t")
    p = _player(g)

    weapon = p.belongings.weapon
    weapon.level = 2
    weapon.level_known = True
    weapon.cursed = True
    weapon.cursed_known = True
    original_id = weapon.id
    original_kind = weapon.kind

    scroll = ScrollOfTransmutation(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)
    g.select_scroll_target(p.id, scroll.id, original_id)

    new_weapon = p.belongings.weapon
    assert new_weapon.id == original_id
    assert new_weapon.kind != original_kind
    assert new_weapon.kind in TRANSMUTE_GROUPS["weapon_melee"]
    assert new_weapon.level == 2
    assert new_weapon.level_known is True
    assert new_weapon.cursed is True
    assert new_weapon.cursed_known is True


def test_scroll_of_transmutation_equipped_weapon_preserves_enchantment():
    g = GameInstance("t")
    p = _player(g)

    weapon = p.belongings.weapon
    weapon.cursed = True
    weapon.cursed_known = True
    weapon.enchantment = "vampiric"
    original_id = weapon.id

    scroll = ScrollOfTransmutation(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)
    g.select_scroll_target(p.id, scroll.id, original_id)

    new_weapon = p.belongings.weapon
    assert new_weapon.id == original_id
    assert new_weapon.enchantment == "vampiric"


def test_scroll_of_transmutation_armor_preserves_enchantment():
    g = GameInstance("t")
    p = _player(g)

    armor = p.belongings.armor
    armor.cursed = True
    armor.cursed_known = True
    armor.enchantment.type = "warding"
    original_id = armor.id

    scroll = ScrollOfTransmutation(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)
    g.select_scroll_target(p.id, scroll.id, original_id)

    new_armor = p.belongings.armor
    assert new_armor.id == original_id
    assert new_armor.enchantment.type == "warding"
    # Deep-copied, not the same object as the original armor's enchantment.
    assert new_armor.enchantment is not armor.enchantment


def test_scroll_of_transmutation_wand_preserves_charges():
    g = GameInstance("t")
    p = _player(g)

    wand = Wand(id="wand1", name="Wand", charges=1, max_charges=5)
    p.belongings.backpack.collect(wand)

    scroll = ScrollOfTransmutation(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)
    g.select_scroll_target(p.id, scroll.id, wand.id)

    new_wand = p.belongings.get_item(wand.id)
    assert new_wand.id == wand.id
    assert new_wand.charges == 1
    assert new_wand.max_charges == 5


def test_scroll_of_transmutation_potion_stack_splits_off_new_kind():
    g = GameInstance("t")
    p = _player(g)

    potions = HealthPotion(id="potions1", quantity=3)
    p.belongings.backpack.collect(potions)

    scroll = ScrollOfTransmutation(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)
    g.select_scroll_target(p.id, scroll.id, potions.id)

    # Original stack lost one unit.
    remaining = p.belongings.get_item(potions.id)
    assert remaining is not None
    assert remaining.quantity == 2

    # A new 1-quantity item of a different potion kind appears in the backpack.
    new_items = [
        it for it in player_inventory_items(p)
        if it.category == "potion" and it.id != potions.id
    ]
    assert len(new_items) == 1
    assert new_items[0].kind != "health_potion"
    assert new_items[0].quantity == 1


def test_scroll_of_transmutation_armor_group_fallback_does_not_crash():
    g = GameInstance("t")
    p = _player(g)

    armor = p.belongings.armor
    armor.level = 1
    armor.level_known = True
    armor.cursed = True
    armor.cursed_known = True
    original_id = armor.id

    scroll = ScrollOfTransmutation(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)
    g.select_scroll_target(p.id, scroll.id, original_id)

    new_armor = p.belongings.armor
    assert new_armor.id == original_id
    assert new_armor.category == "armor"
    assert new_armor.level == 1
    assert new_armor.level_known is True
    assert new_armor.cursed is True
    assert new_armor.cursed_known is True


def test_scroll_of_transmutation_no_candidates_does_not_consume_scroll():
    g = GameInstance("t")
    p = _player(g)

    # Strip the player down to non-transmutable items only: the
    # transmutation scroll itself, a Seed, and Gold.
    p.belongings.weapon = None
    p.belongings.armor = None
    p.belongings.artifact = None
    p.belongings.misc = None
    p.belongings.ring = None
    p.belongings.backpack.items = []

    gold = Gold(id="gold1", name="Gold", quantity=50)
    p.belongings.backpack.collect(gold)

    scroll = ScrollOfTransmutation(id="scroll1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    assert len(select_events) == 1  # dialog always opens
    assert select_events[0]["data"]["candidates"] == []

    # Scroll was unidentified → consumed immediately (SPD).
    assert p.belongings.get_item(scroll.id) is None


def test_scroll_of_mirror_image_spawns_two_invisible_player_allies():
    g = GameInstance("t")
    p = _player(g)
    floor = g._get_or_create_floor(p.floor_id)

    scroll = ScrollOfMirrorImage(id="scroll_mi1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    mirror_events = [e for e in g.events if e["type"] == "MIRROR_IMAGE"]
    assert len(mirror_events) == 1
    clone_data = mirror_events[0]["data"]["clones"]
    assert mirror_events[0]["data"]["player"] == p.id
    assert len(clone_data) == 2

    clones = [floor.mobs[c["id"]] for c in clone_data]
    for clone in clones:
        assert isinstance(clone, MirrorImage)
        assert clone.faction == Faction.PLAYER
        assert clone.invisible >= 1
        assert clone.hp == 1
        assert clone.max_hp == 1
        assert clone.damage_min == max(1, (p.get_damage_min() + 1) // 2)
        assert clone.damage_max == max(1, (p.get_damage_max() + 1) // 2)
        # SPD: attackSkill = (9 + hero.lvl) * accuracyMultiplier — with no ring
        # this is just the owner's base attack_skill.
        from app.engine.entities.rings import accuracy_multiplier
        assert clone.attack_skill == int(p.attack_skill * accuracy_multiplier(p))
        # SPD: defenseSkill = super.defenseSkill * (baseEvasion + heroEvasion) / 2
        base_ev = 4 + p.level
        hero_ev = int(base_ev * 1.0)  # no Ring of Evasion
        assert clone.defense_skill == (base_ev + hero_ev) // 2
        dist = max(abs(clone.pos.x - p.pos.x), abs(clone.pos.y - p.pos.y))
        assert dist == 1

    # Scroll consumed.
    assert p.belongings.get_item(scroll.id) is None

    read_events = [e for e in g.events if e["type"] == "READ"]
    assert len(read_events) == 1


def test_mirror_image_clone_dies_from_single_point_of_damage():
    g = GameInstance("t")
    p = _player(g)
    floor = g._get_or_create_floor(p.floor_id)

    scroll = ScrollOfMirrorImage(id="scroll_mi2")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    mirror_events = [e for e in g.events if e["type"] == "MIRROR_IMAGE"]
    clone = floor.mobs[mirror_events[0]["data"]["clones"][0]["id"]]

    clone.take_damage(1)
    assert clone.is_alive is False
    assert clone.hp == 0


def test_is_immune_helper():
    g = GameInstance("t")
    p = _player(g)
    floor = g._get_or_create_floor(p.floor_id)

    scroll = ScrollOfMirrorImage(id="scroll_mi3")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)
    mirror_events = [e for e in g.events if e["type"] == "MIRROR_IMAGE"]
    clone = floor.mobs[mirror_events[0]["data"]["clones"][0]["id"]]

    assert is_immune(clone, "burning") is True

    other_mob = Mob(
        id="m_other", name="Rat", pos=Position(x=p.pos.x + 5, y=p.pos.y),
        hp=10, max_hp=10, attack=1, defense=0, faction="dungeon")
    assert is_immune(other_mob, "burning") is False


def test_refresh_mirror_image_stats_removes_clone_when_owner_left_floor():
    g = GameInstance("t")
    p = _player(g)
    floor = g._get_or_create_floor(p.floor_id)

    scroll = ScrollOfMirrorImage(id="scroll_mi4")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)
    mirror_events = [e for e in g.events if e["type"] == "MIRROR_IMAGE"]
    clone = floor.mobs[mirror_events[0]["data"]["clones"][0]["id"]]

    # Owner leaves the floor.
    p.floor_id = p.floor_id + 1

    g._refresh_mirror_image_stats(clone, p, floor, floor.floor_id)

    assert clone.is_alive is False
    assert clone.hp == 0
    assert clone.id not in floor.mobs

    death_events = [e for e in g.events if e["type"] == "DEATH" and e["data"]["target"] == clone.id]
    assert len(death_events) == 1


def test_scroll_of_magic_mapping_marks_floor_mapped_and_consumes_scroll():
    g = GameInstance("t")
    p = _player(g)
    floor = g._get_or_create_floor(p.floor_id)

    scroll = ScrollOfMagicMapping(id="scroll_mm1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    assert floor.mapped is True
    assert p.belongings.get_item(scroll.id) is None


def test_scroll_of_magic_mapping_reveals_hidden_door_and_emits_map_patch():
    g = GameInstance("t")
    p = _player(g)
    floor = g._get_or_create_floor(p.floor_id)

    # Pick a cell far from the player and stash a hidden door there.
    tx, ty = 1, 1
    if (tx, ty) == (p.pos.x, p.pos.y):
        tx, ty = 2, 2
    actual_tile = floor.grid[ty][tx]
    floor.grid[ty][tx] = TileType.SECRET_DOOR
    floor.hidden_doors[(tx, ty)] = actual_tile

    scroll = ScrollOfMagicMapping(id="scroll_mm2")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    assert (tx, ty) not in floor.hidden_doors
    assert floor.grid[ty][tx] == actual_tile

    patch_events = [e for e in g.events if e["type"] == "MAP_PATCH"]
    assert len(patch_events) == 1
    patched = patch_events[0]["data"]["tiles"]
    assert any(t["x"] == tx and t["y"] == ty and t["tile"] == actual_tile for t in patched)


def test_scroll_of_magic_mapping_populates_mapped_tiles_in_state():
    g = GameInstance("t")
    p = _player(g)
    floor = g._get_or_create_floor(p.floor_id)

    scroll = ScrollOfMagicMapping(id="scroll_mm3")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    state = g.get_state(p.id)
    mapped = state["mapped_tiles"]
    # SPD: only discoverable tiles (non-{VOID, WALL, WALL_DECO}) are mapped.
    assert len(mapped) > 0
    assert len(mapped) < floor.width * floor.height  # not every tile
    for x, y in mapped:
        t = floor.grid[y][x]
        assert t not in (0, 1, 17)  # not VOID, WALL, or WALL_DECO


def test_inscribed_stealth_not_granted_when_predicate_scroll_has_no_candidates():
    """Stealth procs when scroll is read (always opens dialog)."""
    from app.engine.entities.subclasses import Talent

    g = GameInstance("t")
    p = _player(g)

    # Give player inscribed_stealth talent (Rogue T2).
    p.subclass_info.talent_info.talents[Talent.INSCRIBED_STEALTH] = 1

    _detach_starter_scroll(p)

    # Mark every item as identified so Scroll of Identify finds no candidates.
    for it in player_inventory_items(p):
        g.identified_kinds.add(it.kind)

    scroll = ScrollOfIdentify(id="scroll_is1")
    g.identified_kinds.add(scroll.kind)
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    assert len(select_events) == 1  # dialog always opens
    assert scroll.kind in g.identified_kinds
    # Stealth procs because the scroll was read (dialog opened).
    assert p.has_buff("invisibility")
    # Scroll is NOT consumed (was already identified).
    assert p.belongings.get_item(scroll.id) is not None


def test_predicate_scroll_not_identified_when_no_candidates():
    """Reading an unidentified predicate scroll reveals its kind (SPD), even with no candidates."""
    g = GameInstance("t")
    p = _player(g)

    p.belongings.weapon = None
    p.belongings.armor = None
    p.belongings.artifact = None
    p.belongings.misc = None
    p.belongings.ring = None
    p.belongings.backpack.items = []

    scroll = ScrollOfUpgrade(id="scroll_pu1")
    p.belongings.backpack.collect(scroll)

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    assert len(select_events) == 1  # dialog always opens
    assert scroll.kind in g.identified_kinds, "scroll kind is revealed on read (SPD)"


def test_predicate_scroll_identified_when_candidates_exist():
    """Reading with valid candidates reveals kind immediately."""
    g = GameInstance("t")
    p = _player(g)

    scroll = ScrollOfUpgrade(id="scroll_pu2")
    p.belongings.backpack.collect(scroll)
    assert p.belongings.weapon is not None  # player has an upgradable weapon

    action_read(g, p, scroll)

    select_events = [e for e in g.events if e["type"] == "SCROLL_SELECT_TARGET"]
    assert len(select_events) == 1
    assert scroll.kind in g.identified_kinds


def test_floor_scroll_pool_includes_scroll_of_transmutation():
    """Bug 3 fix: FLOOR_SCROLL_KINDS must include scroll_of_transmutation."""
    from app.engine.entities.item_catalog import FLOOR_SCROLL_KINDS
    assert "scroll_of_transmutation" in FLOOR_SCROLL_KINDS


def test_transmutation_output_never_worn_shortsword():
    """Bug 4 fix: worn_shortsword must not appear as transmutation output."""
    from app.engine.entities.item_catalog import TRANSMUTE_GROUPS
    assert "worn_shortsword" not in TRANSMUTE_GROUPS["weapon_melee"]


def test_scroll_of_metamorphosis_opens_then_replaces_talent():
    g = GameInstance("t")
    p = _player(g)
    p.subclass_info.talent_info.talents[Talent.HEARTY_MEAL] = 1

    scroll = ScrollOfMetamorphosis(id="scroll1")
    p.belongings.backpack.items.append(scroll)

    action_read(g, p, scroll)

    open_events = [e for e in g.events if e["type"] == "METAMORPH_OPEN"]
    assert len(open_events) == 1
    assert open_events[0]["data"]["player"] == p.id
    assert p.belongings.get_item("scroll1") is None

    assert g.metamorph_choose(p.id, Talent.HEARTY_MEAL) is True
    options_events = [e for e in g.events if e["type"] == "METAMORPH_OPTIONS"]
    assert len(options_events) == 1
    options = options_events[0]["data"]["options"]
    assert options
    assert Talent.HEARTY_MEAL not in options

    new_talent = options[0]
    assert g.metamorph_replace(p.id, Talent.HEARTY_MEAL, new_talent) is True
    assert Talent.HEARTY_MEAL not in p.subclass_info.talent_info.talents
    assert p.subclass_info.talent_info.talents[new_talent] == 1
    assert p.subclass_info.metamorphed_talents[Talent.HEARTY_MEAL] == new_talent

    replaced_events = [e for e in g.events if e["type"] == "TALENT_METAMORPHED"]
    assert len(replaced_events) == 1
    assert replaced_events[0]["data"]["old_talent"] == Talent.HEARTY_MEAL
    assert replaced_events[0]["data"]["new_talent"] == new_talent
