"""AlchemyMixin: gates, preview round-trip, atomic brew, energize."""
import pytest

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import Position
from app.engine.entities.items_consumable import GooBlob, MysteryMeat
from app.engine.entities.items_potions import ElixirOfAquaticRejuvenation, HealthPotion
from app.engine.entities.trinkets import TrinketCatalyst
from app.engine.manager import GameInstance


@pytest.fixture
def game_at_pot():
    g = GameInstance("t-brew")
    p = g.add_player("p1", "Bob")
    floor = g._get_or_create_floor(p.floor_id)
    floor.grid[p.pos.y][p.pos.x + 1] = TileType.ALCHEMY
    return g, p


def _events(g, etype):
    return [e for e in g.events if e["type"] == etype]


def _find_by_id(items, item_id):
    # Recurse into sub-bags (e.g. the starting VelvetPouch auto-sorts
    # runestones out of the top-level backpack list).
    for i in items:
        if i["id"] == item_id:
            return i
        found = _find_by_id(i.get("items") or [], item_id)
        if found is not None:
            return found
    return None


def test_gate_rejects_away_from_pot():
    g = GameInstance("t-gate")
    p = g.add_player("p1", "Bob")
    blob = GooBlob(id="b1")
    p.add_to_inventory(blob)
    g.alchemy_brew("p1", ["b1"], 0)
    assert _events(g, "TOAST")
    assert p.belongings.get_item("b1") is not None


def test_preview_and_brew_elixir(game_at_pot):
    g, p = game_at_pot
    g.identified_kinds.add("health_potion")
    p.add_to_inventory(GooBlob(id="b1"))
    p.add_to_inventory(HealthPotion(id="hp1"))
    p.energy = 6

    g.alchemy_preview("p1", ["b1", "hp1"])
    pv = _events(g, "ALCHEMY_PREVIEW_RESULT")[-1]["data"]
    assert pv["available_energy"] == 6
    assert len(pv["recipes"]) == 1
    entry = pv["recipes"][0]
    assert entry["output_kind"] == "elixir_aqua_rejuv"
    assert entry["cost"] == 6 and entry["affordable"]

    g.alchemy_brew("p1", ["b1", "hp1"], entry["recipe_index"])
    assert p.energy == 0
    assert p.belongings.get_item("b1") is None
    assert p.belongings.get_item("hp1") is None
    elixirs = [i for i in p.inventory if isinstance(i, ElixirOfAquaticRejuvenation)]
    assert len(elixirs) == 1 and elixirs[0].id
    brewed = _events(g, "ALCHEMY_BREWED")[-1]["data"]
    assert brewed["item_kind"] == "elixir_aqua_rejuv" and brewed["cost"] == 6


def test_brew_insufficient_energy_no_mutation(game_at_pot):
    g, p = game_at_pot
    g.identified_kinds.add("health_potion")
    p.add_to_inventory(GooBlob(id="b1"))
    p.add_to_inventory(HealthPotion(id="hp1"))
    p.energy = 5
    g.alchemy_brew("p1", ["b1", "hp1"], 0)
    assert _events(g, "TOAST")
    assert p.energy == 5
    assert p.belongings.get_item("b1") is not None


def test_brew_repeated_id_consumes_stack_units(game_at_pot):
    g, p = game_at_pot
    p.add_to_inventory(MysteryMeat(id="m1", quantity=3))
    p.energy = 2
    # 3 slots from the same stack -> threeMeat (cost 2, 3x stewed meat)
    g.alchemy_preview("p1", ["m1", "m1", "m1"])
    pv = _events(g, "ALCHEMY_PREVIEW_RESULT")[-1]["data"]
    idx = next(r["recipe_index"] for r in pv["recipes"]
               if r["output_kind"] == "stewed_meat" and r["output_quantity"] == 3)
    g.alchemy_brew("p1", ["m1", "m1", "m1"], idx)
    assert p.belongings.get_item("m1") is None
    assert p.energy == 0


def test_brew_rejects_overdrawn_stack(game_at_pot):
    g, p = game_at_pot
    p.add_to_inventory(MysteryMeat(id="m1", quantity=2))
    p.energy = 5
    g.alchemy_brew("p1", ["m1", "m1", "m1"], 0)
    assert _events(g, "TOAST")
    assert p.belongings.get_item("m1").quantity == 2


def test_trinket_catalyst_choice_flow(game_at_pot):
    g, p = game_at_pot
    p.add_to_inventory(TrinketCatalyst(id="cat1"))
    p.energy = 6
    g.alchemy_preview("p1", ["cat1"])
    pv = _events(g, "ALCHEMY_PREVIEW_RESULT")[-1]["data"]
    g.alchemy_brew("p1", ["cat1"], pv["recipes"][0]["recipe_index"])
    assert p.energy == 0
    cata = p.belongings.get_item("cat1")
    assert cata is not None and len(cata.rolled_kinds) == 4
    choice = _events(g, "TRINKET_CHOICE")[-1]["data"]
    assert choice["kinds"] == cata.rolled_kinds

    g.alchemy_trinket_choose("p1", "cat1", cata.rolled_kinds[2])
    assert p.belongings.get_item("cat1") is None
    assert any(i.kind == choice["kinds"][2] for i in p.inventory)


def test_energize_at_pot(game_at_pot):
    g, p = game_at_pot
    from app.engine.entities.runestones import StoneOfBlast
    p.add_to_inventory(StoneOfBlast(id="s1", quantity=3))
    g.alchemy_energize("p1", "s1", all_items=False)
    assert p.energy == 3
    assert p.belongings.get_item("s1").quantity == 2
    g.alchemy_energize("p1", "s1", all_items=True)
    assert p.energy == 9
    assert p.belongings.get_item("s1") is None
    assert _events(g, "ALCHEMY_ENERGIZED")[-1]["data"]["energy"] == 9


def test_energize_rejects_worthless(game_at_pot):
    g, p = game_at_pot
    # MysteryMeat has energy_val 0 (unlike GooBlob, whose energyVal() is
    # 3*quantity per GooBlob.java — see test_alchemy_recipes.py's energy_val
    # table); it's the correctly "worthless" fixture for this gate.
    p.add_to_inventory(MysteryMeat(id="b1"))
    g.alchemy_energize("p1", "b1", all_items=False)
    assert p.energy == 0
    assert p.belongings.get_item("b1") is not None


def test_trinket_catalyst_rebrew_does_not_respend(game_at_pot):
    g, p = game_at_pot
    p.add_to_inventory(TrinketCatalyst(id="cat1"))
    p.energy = 12
    g.alchemy_brew("p1", ["cat1"], 0)
    assert p.energy == 6
    first = list(p.belongings.get_item("cat1").rolled_kinds)
    g.alchemy_brew("p1", ["cat1"], 0)          # retry/double-click
    assert p.energy == 6                        # no second charge
    assert p.belongings.get_item("cat1").rolled_kinds == first


def test_paid_catalyst_reopens_choice_without_energy(game_at_pot):
    g, p = game_at_pot
    p.add_to_inventory(TrinketCatalyst(id="cat1"))
    p.energy = 6
    g.alchemy_brew("p1", ["cat1"], 0)
    assert p.energy == 0
    kinds = list(p.belongings.get_item("cat1").rolled_kinds)
    # broke: 0 energy — the already-paid choice must still re-open
    g.alchemy_brew("p1", ["cat1"], 0)
    choices = [e for e in g.events if e["type"] == "TRINKET_CHOICE"]
    assert len(choices) == 2 and choices[-1]["data"]["kinds"] == kinds
    assert p.energy == 0


def test_preview_exotic_known_when_base_identified(game_at_pot):
    g, p = game_at_pot
    g.identified_kinds.add("health_potion")
    p.add_to_inventory(HealthPotion(id="hp1"))
    p.energy = 10
    g.alchemy_preview("p1", ["hp1"])
    pv = _events(g, "ALCHEMY_PREVIEW_RESULT")[-1]["data"]
    exotic = next(r for r in pv["recipes"] if r["cost"] == 4)
    assert exotic["known"] is True
    assert exotic["output_kind"] == "potion_of_shielding"
    assert exotic["output_name"] == "Potion of Shielding"


def test_brewed_elixir_serializes_unmasked(game_at_pot):
    g, p = game_at_pot
    g.identified_kinds.add("health_potion")
    p.add_to_inventory(GooBlob(id="b1"))
    p.add_to_inventory(HealthPotion(id="hp1"))
    p.energy = 6
    g.alchemy_brew("p1", ["b1", "hp1"], 0)
    d = g._serialize_player(p)
    nodes = [i for i in d["inventory"] if i["kind"] == "elixir_aqua_rejuv"]
    assert nodes, "elixir masked or missing from serialized inventory"
    assert nodes[0]["name"] == "Elixir of Aquatic Rejuvenation"
    assert "appearance" not in nodes[0]


def test_serialized_energy_values_per_unit(game_at_pot):
    g, p = game_at_pot
    from app.engine.entities.items_potions import ElixirOfHoneyedHealing
    from app.engine.entities.runestones import StoneOfBlast
    p.add_to_inventory(ElixirOfHoneyedHealing(id="hh1", quantity=2))
    p.add_to_inventory(StoneOfBlast(id="s1", quantity=3))
    d = g._serialize_player(p)
    # StoneOfBlast (a Runestone) auto-sorts into the starting VelvetPouch, so
    # it isn't a top-level d["inventory"] entry -- search recursively.
    hh = _find_by_id(d["inventory"], "hh1")
    st = _find_by_id(d["inventory"], "s1")
    assert (hh["energy_value"], hh["energy_value_one"]) == (8, 8)   # flat SPD override
    assert (st["energy_value"], st["energy_value_one"]) == (9, 3)   # linear 3*q
