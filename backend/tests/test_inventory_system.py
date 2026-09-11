"""Unit tests for the ported SPD inventory system: stacking, nested category
bags, equip slots, quickslot placeholders, and curse handling."""
import pytest
from app.engine.entities.base import Position, Action
from app.engine.entities.items.union import Bag, PotionBandolier, ScrollHolder, VelvetPouch
from app.engine.entities.items.consumables import Seed, GooBlob, Stone
from app.engine.entities.wands.wandmaker_quest_items import RotberrySeed
from app.engine.entities.items.equip import MeleeWeapon, Armor, Ring
from app.engine.entities.items.potions import HealthPotion, RevivingPotion
from app.engine.entities.items.scrolls import Scroll
from app.engine.entities.items.wands import Wand
from app.engine.entities.player import Player, Belongings, QuickSlot


def make_player(strength=10):
    return Player(id="p", type="player", name="T", pos=Position(x=0, y=0),
                  hp=20, max_hp=20, attack=5, defense=1, faction="player", strength=strength)


# --- stacking --------------------------------------------------------------
def test_stackable_potions_merge():
    p = make_player()
    assert p.add_to_inventory(HealthPotion(id="h1"))
    assert p.add_to_inventory(HealthPotion(id="h2"))
    pots = [i for i in p.inventory if i.kind == "health_potion"]
    assert len(pots) == 1 and pots[0].quantity == 2


def test_different_potions_do_not_merge():
    p = make_player()
    p.add_to_inventory(HealthPotion(id="h1"))
    p.add_to_inventory(RevivingPotion(id="r1"))
    assert len({i.kind for i in p.inventory}) == 2


def test_split_creates_fresh_id():
    stack = HealthPotion(id="h1", quantity=3)
    piece = stack.split(1)
    assert piece is not None
    assert piece.quantity == 1 and stack.quantity == 2
    assert piece.id != "h1"  # id-addressed protocol must not collide


def test_split_invalid_amounts():
    stack = HealthPotion(id="h1", quantity=2)
    assert stack.split(0) is None
    assert stack.split(2) is None  # can't split the whole stack


def test_detach_decrements_stack():
    p = make_player()
    p.add_to_inventory(HealthPotion(id="h1", quantity=3))
    one = p.belongings.backpack.detach("h1")
    assert one.quantity == 1
    assert [i for i in p.inventory if i.kind == "health_potion"][0].quantity == 2


# --- nested category bags --------------------------------------------------
def test_subbag_autosorts_items():
    p = make_player()
    p.add_to_inventory(PotionBandolier(id="band"))
    p.add_to_inventory(HealthPotion(id="h1"))
    band = p.belongings.backpack.find("band")
    assert band.find("h1") is not None  # potion auto-routed into the bandolier
    # the potion should not also sit at backpack top level
    assert all(i.id != "h1" for i in p.belongings.backpack.items)


def test_subbag_rejects_wrong_category():
    band = PotionBandolier(id="band")
    assert band.can_hold(HealthPotion(id="h")) is True
    assert band.can_hold(Scroll(id="s", name="Scroll")) is False


def test_grab_items_pulls_matching():
    p = make_player()
    # distinct names so they don't stack into one entry
    p.add_to_inventory(Scroll(id="s1", name="Scroll of A"))
    p.add_to_inventory(Scroll(id="s2", name="Scroll of B"))
    holder = ScrollHolder(id="holder")
    holder.grab_items(p.belongings.backpack)
    assert holder.contains("s1") and holder.contains("s2")
    assert all(i.type != "scroll" for i in p.belongings.backpack.items)


def test_collecting_bag_grabs_existing_matching_items():
    # SPD Bag.collect -> grabItems(container): acquiring a specialised bag
    # pulls every matching item already sitting in the backpack.
    p = make_player()
    p.add_to_inventory(Scroll(id="s1", name="Scroll of A"))
    p.add_to_inventory(HealthPotion(id="h1"))
    p.add_to_inventory(ScrollHolder(id="holder"))
    holder = p.belongings.backpack.find("holder")
    assert holder.contains("s1")
    assert not holder.contains("h1")
    # scroll gone from backpack top level, potion stays
    assert all(i.id != "s1" for i in p.belongings.backpack.items)
    assert any(i.id == "h1" for i in p.belongings.backpack.items)


def test_velvet_pouch_capacity_is_19():
    assert VelvetPouch(id="vp").capacity == 19


def test_velvet_pouch_holds_seeds_and_goo_blob_not_throwables():
    p = make_player()
    p.add_to_inventory(VelvetPouch(id="vp"))
    p.add_to_inventory(Seed(id="seed1", name="Seed"))
    p.add_to_inventory(GooBlob(id="goo1"))
    p.add_to_inventory(Stone(id="stone1"))

    pouch = p.belongings.backpack.find("vp")
    assert pouch.contains("seed1") and pouch.contains("goo1")
    # Throwables share SPD's old "stone" naming but are a different category
    # here (Throwable weapons, not Runestones) -- they must stay in the
    # backpack, not get swept into the seed pouch.
    assert not pouch.contains("stone1")
    assert any(i.id == "stone1" for i in p.belongings.backpack.items)


def test_velvet_pouch_holds_rotberry_seed():
    p = make_player()
    p.add_to_inventory(VelvetPouch(id="vp"))
    p.add_to_inventory(RotberrySeed(id="rot1"))
    pouch = p.belongings.backpack.find("vp")
    assert pouch.contains("rot1")


def test_seeds_merge_by_plant_type_in_velvet_pouch():
    p = make_player()
    p.add_to_inventory(VelvetPouch(id="vp"))
    p.add_to_inventory(Seed(id="s1", plant_type="sungrass", quantity=1))
    p.add_to_inventory(Seed(id="s2", plant_type="sungrass", quantity=2))
    pouch = p.belongings.backpack.find("vp")
    assert len(pouch.items) == 1
    assert pouch.items[0].plant_type == "sungrass"
    assert pouch.items[0].quantity == 3


def test_different_plant_type_seeds_do_not_merge():
    p = make_player()
    p.add_to_inventory(VelvetPouch(id="vp"))
    p.add_to_inventory(Seed(id="s1", plant_type="sungrass", quantity=1))
    p.add_to_inventory(Seed(id="s2", plant_type="earthroot", quantity=1))
    pouch = p.belongings.backpack.find("vp")
    assert len(pouch.items) == 2
    types = {i.plant_type for i in pouch.items}
    assert types == {"sungrass", "earthroot"}


def test_auto_pickup_seed_and_rotberry_into_velvet_pouch():
    from app.engine.manager import GameInstance
    from app.engine.game.terrain_effects import _drop_seed
    g = GameInstance("test-seed-pickup")
    p = g.add_player("p1", "Hero")
    floor = g._get_or_create_floor(1)

    _drop_seed(floor, (p.pos.x, p.pos.y), "firebloom")
    g._auto_pickup_on_step(p, floor)

    pouch = next(i for i in p.belongings.backpack.items if isinstance(i, VelvetPouch))
    assert any(getattr(i, "plant_type", None) == "firebloom" for i in pouch.items)

    rot_seed = RotberrySeed(id="rot_floor", pos=Position(x=p.pos.x, y=p.pos.y))
    floor.items[rot_seed.id] = rot_seed
    g._auto_pickup_on_step(p, floor)
    assert pouch.contains("rot_floor")


def test_capacity_limit():
    bag = Bag(id="b", name="B", capacity=2)
    assert bag.collect(MeleeWeapon(id="w1", name="a", damage=1))
    assert bag.collect(MeleeWeapon(id="w2", name="b", damage=1))
    assert not bag.collect(MeleeWeapon(id="w3", name="c", damage=1))


# --- equip slots -----------------------------------------------------------
def test_equip_routes_to_correct_slot():
    p = make_player()
    p.add_to_inventory(MeleeWeapon(id="w", name="Sword", damage=3, strength_requirement=0))
    p.add_to_inventory(Armor(id="a", name="Mail", tier=3, strength_requirement=0))
    p.add_to_inventory(Ring(id="r", name="Ring", strength_requirement=0))
    assert p.equip_item("w") and p.belongings.weapon.id == "w"
    assert p.equip_item("a") and p.belongings.armor.id == "a"
    assert p.equip_item("r") and p.belongings.ring.id == "r"
    # equipped items leave the backpack
    assert len(p.belongings.backpack.items) == 0


def test_equip_swaps_previous():
    p = make_player()
    p.add_to_inventory(MeleeWeapon(id="w1", name="A", damage=3, strength_requirement=0))
    p.add_to_inventory(MeleeWeapon(id="w2", name="B", damage=5, strength_requirement=0))
    p.equip_item("w1")
    p.equip_item("w2")
    assert p.belongings.weapon.id == "w2"
    assert any(i.id == "w1" for i in p.belongings.backpack.items)  # swapped back


# --- curses ----------------------------------------------------------------
def test_cursed_known_blocks_unequip():
    p = make_player()
    p.add_to_inventory(MeleeWeapon(id="w", name="Sword", damage=3, strength_requirement=0,
                                   cursed=True, cursed_known=True))
    p.equip_item("w")
    assert p.unequip_item("w") is False
    assert p.belongings.weapon is not None


def test_unknown_curse_allows_unequip():
    p = make_player()
    p.add_to_inventory(MeleeWeapon(id="w", name="Sword", damage=3, strength_requirement=0,
                                   cursed=True, cursed_known=False))
    p.equip_item("w")
    # Equipping sets cursed_known = True, which blocks unequipped unless uncursed
    assert p.unequip_item("w") is False
    assert p.belongings.weapon is not None


# --- quickslot placeholders ------------------------------------------------
def test_quickslot_placeholder_lifecycle():
    p = make_player()
    pot = HealthPotion(id="h1", quantity=1)
    p.add_to_inventory(pot)
    p.quickslot.set_slot(0, pot)
    assert p.quickslot.slots[0].item_id == "h1"
    # deplete -> becomes a placeholder reserved by kind
    p.quickslot.convert_to_placeholder(pot)
    assert p.quickslot.slots[0].is_placeholder
    assert p.quickslot.slots[0].placeholder_kind == "health_potion"
    # collecting a like item re-binds the slot
    newpot = HealthPotion(id="h2")
    p.add_to_inventory(newpot)
    assert p.quickslot.slots[0].item_id == "h2"
    assert not p.quickslot.slots[0].is_placeholder


# --- actions list ----------------------------------------------------------
def test_actions_reflect_equipped_state():
    p = make_player()
    w = MeleeWeapon(id="w", name="Sword", damage=3, strength_requirement=0)
    p.add_to_inventory(w)
    assert Action.EQUIP in w.actions(p)
    p.equip_item("w")
    assert Action.UNEQUIP in p.belongings.weapon.actions(p)


def test_potion_default_action():
    assert HealthPotion(id="h").default_action() == Action.DRINK
    assert Wand(id="x", name="W").default_action() == Action.ZAP


# --- generic action dispatch (via GameInstance) ----------------------------
from app.engine.manager import GameInstance


def test_dispatch_drink_consumes_and_heals():
    g = GameInstance("t1")
    p = g.add_player("p1", "Bob")
    p.add_to_inventory(HealthPotion(id="h1"))
    g.execute_item_action("p1", "h1", Action.DRINK)
    assert p.heal_left > 0
    assert p.belongings.get_item("h1") is None


def test_dispatch_drop_equipped_to_floor():
    g = GameInstance("t2")
    p = g.add_player("p1", "Bob")
    wid = p.belongings.weapon.id
    g.execute_item_action("p1", wid, Action.DROP)
    assert p.belongings.weapon is None
    assert wid in g._get_or_create_floor(p.floor_id).items


def test_dispatch_rejects_illegal_action():
    g = GameInstance("t3")
    p = g.add_player("p1", "Bob")
    p.add_to_inventory(MeleeWeapon(id="w9", name="S", damage=2, strength_requirement=0))
    g.execute_item_action("p1", "w9", Action.DRINK)  # weapons can't be drunk
    assert p.belongings.get_item("w9") is not None


def test_unidentified_potion_masked_then_revealed():
    g = GameInstance("m1")
    p = g.add_player("p1", "Bob")
    p.add_to_inventory(HealthPotion(id="h1"))
    me = g.get_state("p1")["self_player"]
    pot = next(i for i in me["belongings"]["backpack"]["items"] if i["id"] == "h1")
    assert pot["kind"] == "potion"            # subtype collapsed
    assert "Potion" in pot["name"]            # scrambled label, not "Health Potion"
    assert pot["name"] != "Health Potion"
    assert "effect" not in pot

    # drinking identifies the kind for the whole party
    g.execute_item_action("p1", "h1", Action.DRINK)
    p.add_to_inventory(HealthPotion(id="h2"))
    me2 = g.get_state("p1")["self_player"]
    pot2 = next(i for i in me2["belongings"]["backpack"]["items"] if i["id"] == "h2")
    assert pot2["kind"] == "health_potion"
    assert pot2["name"] == "Health Potion"


def test_quickslot_set_and_use():
    g = GameInstance("t4")
    p = g.add_player("p1", "Bob")
    p.add_to_inventory(HealthPotion(id="h1"))
    g.set_quickslot("p1", 0, "h1")
    assert p.quickslot.slots[0].item_id == "h1"
    g.use_quickslot("p1", 0)  # default action = DRINK
    assert p.heal_left > 0


def test_floor_pickup_updates_serialized_state():
    g = GameInstance("t_pickup")
    p = g.add_player("p1", "Alice")
    floor = g._get_or_create_floor(p.floor_id)

    # Initial serialization (tick 0)
    s1 = g.get_state("p1")["self_player"]
    initial_count = len(s1["belongings"]["backpack"]["items"])

    # Spawn weapon on floor at player pos
    sword = MeleeWeapon(id="w_test", name="Super Sword", tier=1, pos=Position(x=p.pos.x, y=p.pos.y))
    floor.items["w_test"] = sword

    # Explicit floor pickup
    g.pickup_floor_items("p1")
    assert "w_test" not in floor.items
    assert p.belongings.get_item("w_test") is not None

    # Subsequent serialization must include the picked-up item
    s2 = g.get_state("p1")["self_player"]
    items2 = s2["belongings"]["backpack"]["items"]
    assert len(items2) == initial_count + 1
    assert any(i["id"] == "w_test" and i["name"] == "Super Sword" for i in items2)


def test_polymorphic_pickups():
    from app.engine.entities.items.consumables import Gold, EnergyCrystal, Key
    g = GameInstance("t_poly")
    p = g.add_player("p1", "Alice")
    floor = g._get_or_create_floor(p.floor_id)

    # Test Gold pickup
    floor.items["g1"] = Gold(id="g1", name="Gold", quantity=25, pos=Position(x=p.pos.x, y=p.pos.y))
    g.pickup_floor_items("p1")
    assert "g1" not in floor.items
    assert p.gold == 25

    # Test EnergyCrystal pickup
    floor.items["e1"] = EnergyCrystal(id="e1", quantity=10, pos=Position(x=p.pos.x, y=p.pos.y))
    g.pickup_floor_items("p1")
    assert "e1" not in floor.items
    assert p.energy == 10

    # Test Key pickup
    floor.items["k1"] = Key(id="k1", key_id="iron", name="Iron Key", pos=Position(x=p.pos.x, y=p.pos.y))
    g.pickup_floor_items("p1")
    assert "k1" not in floor.items
    assert p.key_count("iron", p.floor_id) == 1

