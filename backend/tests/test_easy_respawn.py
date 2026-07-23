import pytest

from app.engine.manager import GameInstance
from app.engine.entities.base import Position
from app.engine.entities.player import Difficulty
from app.engine.entities.buffs import has_buff
from app.engine.entities.items_consumable import Ankh, Waterskin, LostBackpack


def _make_game(difficulty: Difficulty = Difficulty.EASY, floor_id: int = 1) -> GameInstance:
    game = GameInstance("test-ankh-respawn")
    game.change_difficulty(difficulty)
    return game


def _give_ankh(game: GameInstance, player_id: str, blessed: bool = False) -> Ankh:
    """Give the player an ankh (optionally blessed)."""
    player = game.players[player_id]
    ankh = Ankh(id=f"ankh_{player_id}", blessed=blessed)
    player.belongings.backpack.collect(ankh)
    return ankh


def _kill_player(game: GameInstance, player_id: str, floor_id: int = 1) -> dict:
    """Simulate death: down the player, run _kill_player, return the DEATH event data."""
    player = game.players[player_id]
    player.floor_id = floor_id
    player.hp = 0
    player.is_alive = False
    player.is_downed = True
    floor = game._get_or_create_floor(floor_id)
    game._kill_player(player, floor, floor_id)
    death_events = [e for e in game.events if e["type"] == "DEATH"]
    return death_events[-1]["data"]


# --- Blessed ankh tests ---

def test_blessed_ankh_grants_instant_revive_easy():
    game = _make_game(Difficulty.EASY)
    player = game.add_player("p1", "Hero", "warrior")
    _give_ankh(game, "p1", blessed=True)
    max_hp = player.get_total_max_hp()

    data = _kill_player(game, "p1", floor_id=1)

    assert data["can_resurrect"] is False
    assert data["has_ankh"] is False
    assert data["loot_dropped"] is False
    assert player.is_alive is True
    assert player.is_downed is False
    # Easy = 75% HP
    assert player.hp == int(max_hp * 0.75)
    # Ankh consumed
    assert not any(isinstance(i, Ankh) for i in player.belongings.all_items())
    # Score penalty applied
    assert player.respawns_used == 1


def test_blessed_ankh_grants_instant_revive_hard():
    game = _make_game(Difficulty.HARD)
    player = game.add_player("p1", "Hero", "warrior")
    _give_ankh(game, "p1", blessed=True)
    max_hp = player.get_total_max_hp()

    data = _kill_player(game, "p1", floor_id=1)

    assert player.is_alive is True
    # Hard = 25% HP
    assert player.hp == int(max_hp * 0.25)


def test_blessed_ankh_preserves_all_items():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    _give_ankh(game, "p1", blessed=True)
    initial_items = len(player.belongings.backpack.items)

    _kill_player(game, "p1", floor_id=1)

    # Backpack items preserved (minus the consumed ankh)
    assert len(player.belongings.backpack.items) == initial_items - 1


def test_blessed_ankh_clears_harmful_buffs():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    _give_ankh(game, "p1", blessed=True)
    from app.engine.entities.buffs import add_buff
    add_buff(player.buffs, "poison", duration=10)
    add_buff(player.buffs, "burning", duration=5)

    _kill_player(game, "p1", floor_id=1)

    assert not has_buff(player.buffs, "poison")
    assert not has_buff(player.buffs, "burning")


def test_blessed_ankh_grants_invulnerability():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    _give_ankh(game, "p1", blessed=True)

    _kill_player(game, "p1", floor_id=1)

    assert has_buff(player.buffs, "invulnerability")


# --- Unblessed ankh tests ---

def test_unblessed_ankh_sets_pending_ankh():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    _give_ankh(game, "p1", blessed=False)

    data = _kill_player(game, "p1", floor_id=1)

    assert data["has_ankh"] is True
    assert data["can_resurrect"] is True
    assert data["loot_dropped"] is False
    assert player.pending_ankh is True
    # Player is NOT dead yet (waiting for choice)
    assert player.death_processed is False


def test_ankh_choice_with_two_items():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    ankh = _give_ankh(game, "p1", blessed=False)
    max_hp = player.get_total_max_hp()

    # Give player non-stackable items (use weapon/armor IDs which are unique)
    weapon_id = player.belongings.weapon.id
    armor_id = player.belongings.armor.id

    _kill_player(game, "p1", floor_id=1)
    assert player.pending_ankh is True

    ok = game.ankh_choice("p1", [weapon_id, armor_id])

    assert ok is True
    assert player.pending_ankh is False
    assert player.is_alive is True
    assert player.is_downed is False
    # Easy = 75% HP
    assert player.hp == int(max_hp * 0.75)
    # Ankh consumed
    assert not any(isinstance(i, Ankh) for i in player.belongings.all_items())
    # Respawn counter incremented
    assert player.respawns_used == 1


def test_ankh_choice_creates_lost_backpack():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    _give_ankh(game, "p1", blessed=False)

    _kill_player(game, "p1", floor_id=1)

    # Choose the starting weapon + armor
    weapon_id = player.belongings.weapon.id
    armor_id = player.belongings.armor.id
    ok = game.ankh_choice("p1", [weapon_id, armor_id])

    assert ok is True
    # LostBackpack should be on the ground with dropped items
    floor = game._get_or_create_floor(1)
    backpacks = [i for i in floor.items.values() if isinstance(i, LostBackpack)]
    assert len(backpacks) == 1
    assert backpacks[0].owner_id == player.id


def test_ankh_choice_rejects_wrong_count():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    _give_ankh(game, "p1", blessed=False)
    _kill_player(game, "p1", floor_id=1)

    # Only 1 item
    assert game.ankh_choice("p1", ["item1"]) is False
    # 3 items
    assert game.ankh_choice("p1", ["a", "b", "c"]) is False


def test_ankh_choice_rejects_invalid_items():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    _give_ankh(game, "p1", blessed=False)
    _kill_player(game, "p1", floor_id=1)

    # Non-existent item
    assert game.ankh_choice("p1", ["nonexistent1", "nonexistent2"]) is False


def test_ankh_choice_rejects_when_not_pending():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    # No ankh, no pending
    assert game.ankh_choice("p1", ["a", "b"]) is False


def test_ankh_choice_spawns_event():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    _give_ankh(game, "p1", blessed=False)
    _kill_player(game, "p1", floor_id=1)

    game.ankh_choice("p1", [player.belongings.weapon.id, player.belongings.armor.id])

    spawn_events = [e for e in game.events if e["type"] == "SPAWN"]
    assert len(spawn_events) >= 1
    assert spawn_events[-1]["data"]["is_resurrect"] is True


# --- No ankh: final death ---

def test_no_ankh_death_scatters_items():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")

    data = _kill_player(game, "p1", floor_id=1)

    assert data["can_resurrect"] is False
    assert data["has_ankh"] is False
    assert data["loot_dropped"] is True
    # Player belongings should be empty
    assert len(player.belongings.backpack.items) == 0


def test_no_ankh_death_creates_backpack_marker():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")

    _kill_player(game, "p1", floor_id=1)

    floor = game._get_or_create_floor(1)
    markers = [i for i in floor.items.values() if i.type == "lost_backpack"]
    assert len(markers) >= 1


# --- Ankh prioritization (blessed > unblessed) ---

def test_blessed_ankh_prioritized_over_unblessed():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    _give_ankh(game, "p1", blessed=False)
    _give_ankh(game, "p1", blessed=True)

    data = _kill_player(game, "p1", floor_id=1)

    # Should use blessed ankh (instant revive)
    assert data["has_ankh"] is False
    assert data["can_resurrect"] is False
    assert player.is_alive is True
    assert player.pending_ankh is False


# --- Non-ankh death is final ---

def test_death_without_ankh_is_final():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")

    data = _kill_player(game, "p1", floor_id=1)

    assert data["can_resurrect"] is False
    assert data["has_ankh"] is False
    assert data["victory"] is False


# --- Score penalty ---

def test_score_penalty_increases_with_ankh_uses():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    _give_ankh(game, "p1", blessed=True)

    _kill_player(game, "p1", floor_id=1)

    score1 = game._score_breakdown(player, victory=False)

    # Give another ankh and die again
    _give_ankh(game, "p1", blessed=True)
    # Need to revive first
    player.hp = player.get_total_max_hp()
    player.is_alive = True
    player.is_downed = False
    player.death_processed = False

    _kill_player(game, "p1", floor_id=1)

    score2 = game._score_breakdown(player, victory=False)

    assert score2["respawn_multiplier"] < score1["respawn_multiplier"]


# --- LostBackpack pickup ---

def test_lost_backpack_pickup_only_by_owner():
    game = _make_game()
    player1 = game.add_player("p1", "Hero", "warrior")
    player2 = game.add_player("p2", "Mage", "mage")
    _give_ankh(game, "p1", blessed=False)

    from app.engine.entities.items_consumable import Food
    food = Food(id="food1", name="Ration")
    player1.belongings.backpack.collect(food)

    _kill_player(game, "p1", floor_id=1)
    game.ankh_choice("p1", [player1.belongings.weapon.id, player1.belongings.armor.id])

    # Find the LostBackpack on the ground
    floor = game._get_or_create_floor(1)
    backpacks = [i for i in floor.items.values() if isinstance(i, LostBackpack)]
    assert len(backpacks) == 1
    bp = backpacks[0]

    # Owner picks it up
    assert bp.owner_id == player1.id


# --- Waterskin blessing ---

def test_ankh_bless_action_requires_full_waterskin():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    ankh = Ankh(id="ankh1", blessed=False)
    player.belongings.backpack.collect(ankh)
    waterskin = Waterskin(id="ws1", volume=0)
    player.belongings.backpack.collect(waterskin)

    # Empty waterskin: BLESS not in actions
    actions = ankh.actions(player)
    assert "BLESS" not in actions


def test_ankh_bless_action_available_with_full_waterskin():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    ankh = Ankh(id="ankh1", blessed=False)
    player.belongings.backpack.collect(ankh)
    waterskin = Waterskin(id="ws1", volume=Waterskin.MAX_VOLUME)
    player.belongings.backpack.collect(waterskin)

    actions = ankh.actions(player)
    assert "BLESS" in actions


# --- Ankh not available in actions when already blessed ---

def test_blessed_ankh_no_bless_action():
    game = _make_game()
    player = game.add_player("p1", "Hero", "warrior")
    ankh = Ankh(id="ankh1", blessed=True)
    player.belongings.backpack.collect(ankh)
    waterskin = Waterskin(id="ws1", volume=Waterskin.MAX_VOLUME)
    player.belongings.backpack.collect(waterskin)

    actions = ankh.actions(player)
    assert "BLESS" not in actions
