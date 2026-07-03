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
