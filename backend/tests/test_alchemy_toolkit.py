"""AlchemistsToolkit: charge-first brewing, exp charging, energize upgrades."""
import pytest

from app.engine.dungeon.generator import TileType
from app.engine.entities.items_artifacts import AlchemistsToolkit
from app.engine.entities.items_consumable import GooBlob
from app.engine.entities.items_potions import HealthPotion
from app.engine.manager import GameInstance


@pytest.fixture
def game_with_kit():
    g = GameInstance("t-toolkit")
    p = g.add_player("p1", "Bob")
    kit = AlchemistsToolkit(id="kit1")
    p.add_to_inventory(kit)
    p.equip_item("kit1")
    return g, p, p.belongings.artifact


def test_consume_energy_charge_first():
    kit = AlchemistsToolkit(charge=4)
    assert kit.consume_energy(6) == 2      # remainder from player energy
    assert kit.charge == 0
    kit.charge = 5
    assert kit.consume_energy(3) == 0
    assert kit.charge == 2


def test_toolkit_acts_as_portable_pot_and_pays_first(game_with_kit):
    g, p, kit = game_with_kit
    kit.charge = 4
    p.energy = 3
    g.identified_kinds.add("health_potion")
    p.add_to_inventory(GooBlob(id="b1"))
    p.add_to_inventory(HealthPotion(id="hp1"))
    assert g.alchemy_gate_ok(p)            # no pot anywhere near
    assert g.alchemy_available_energy(p) == 7
    g.alchemy_brew("p1", ["b1", "hp1"], 0)  # elixir costs 6
    assert kit.charge == 0
    assert p.energy == 1


def test_earn_exp_charges_equipped_kit(game_with_kit):
    g, p, kit = game_with_kit
    # (2 + level) energy per hero level: a full level at kit level 0 -> +2.
    p.earn_exp(p.max_exp())
    assert kit.charge == 2


def test_earn_exp_no_charge_when_unequipped():
    g = GameInstance("t-kit-uneq")
    p = g.add_player("p1", "Bob")
    kit = AlchemistsToolkit(id="kit1")
    p.add_to_inventory(kit)
    p.earn_exp(p.max_exp())
    assert kit.charge == 0


def test_toolkit_energize_prompt_and_upgrade(game_with_kit):
    g, p, kit = game_with_kit
    p.energy = 14
    g.execute_item_action("p1", "kit1", "ENERGIZE")
    prompt = [e for e in g.events if e["type"] == "TOOLKIT_ENERGIZE_PROMPT"][-1]["data"]
    assert prompt["max_levels"] == 2       # min(10-0, 14//6)

    g.toolkit_energize("p1", "kit1", 2)
    assert kit.level == 2
    assert kit.charge_cap == 12
    assert p.energy == 2
    done = [e for e in g.events if e["type"] == "TOOLKIT_ENERGIZED"][-1]["data"]
    assert done["levels"] == 2 and done["level"] == 2


def test_toolkit_energize_clamps_levels(game_with_kit):
    g, p, kit = game_with_kit
    p.energy = 6
    g.toolkit_energize("p1", "kit1", 99)
    assert kit.level == 1 and p.energy == 0


def test_brew_action_emits_open_event(game_with_kit):
    g, p, kit = game_with_kit
    g.execute_item_action("p1", "kit1", "BREW")
    assert any(e["type"] == "TOOLKIT_BREW" for e in g.events)


def test_exp_charge_accum_isolated_from_tick_timer(game_with_kit):
    g, p, kit = game_with_kit
    # The passive tick uses _charge_accum as a seconds timer; exp-based
    # charging must not drain it as if it were energy points.
    kit._charge_accum = 9.95
    p.earn_exp(p.max_exp())
    assert kit.charge == 2          # (2 + level 0) * 1.0 full level
    assert kit._charge_accum == 9.95  # tick timer untouched
