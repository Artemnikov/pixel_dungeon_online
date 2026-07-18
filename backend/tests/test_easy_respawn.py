import pytest

from app.engine.manager import GameInstance
from app.engine.entities.base import Position
from app.engine.entities.player import Difficulty
from app.engine.entities.buffs import has_buff


def _make_easy_game(floor_id: int = 1) -> GameInstance:
    game = GameInstance("test-easy-respawn")
    game.change_difficulty(Difficulty.EASY)
    return game


def _kill_player(game: GameInstance, player_id: str, floor_id: int = 1) -> dict:
    """Simulate death: down the player, run _kill_player, return the DEATH event data.

    Moves the player to `floor_id` first so the resurrect's boss-floor check
    sees the same floor the death happened on.
    """
    player = game.players[player_id]
    player.floor_id = floor_id
    player.hp = 0
    player.is_alive = False
    player.is_downed = True
    floor = game._get_or_create_floor(floor_id)
    game._kill_player(player, floor, floor_id)
    death_events = [e for e in game.events if e["type"] == "DEATH"]
    return death_events[-1]["data"]


def test_easy_mode_offers_resurrect_on_normal_floor():
    game = _make_easy_game()
    player = game.add_player("p1", "Hero", "warrior")
    initial_backpack = len(player.belongings.backpack.items)

    data = _kill_player(game, "p1", floor_id=1)

    assert data["can_resurrect"] is True
    assert data["victory"] is False
    assert data["respawns_used"] == 0
    assert data["max_respawns"] == 3
    assert data["loot_dropped"] is False
    # No loot scattered — inventory intact
    assert len(player.belongings.backpack.items) == initial_backpack
    # No grave
    floor = game._get_or_create_floor(1)
    assert not any(it.type == "grave" for it in floor.items.values())


def test_easy_mode_resurrect_revives_player_with_half_hp_and_protection():
    game = _make_easy_game()
    player = game.add_player("p1", "Hero", "warrior")
    _kill_player(game, "p1", floor_id=1)

    ok = game.resurrect_player("p1")

    assert ok is True
    assert player.is_alive is True
    assert player.is_downed is False
    assert player.death_processed is False
    assert player.hp == player.get_total_max_hp() // 2
    assert player.respawns_used == 1
    # Spawn protection buff applied
    assert has_buff(player.buffs, "spawn_protection")


def test_easy_mode_resurrect_emits_spawn_event():
    game = _make_easy_game()
    game.add_player("p1", "Hero", "warrior")
    _kill_player(game, "p1", floor_id=1)
    game.events = []  # clear DEATH

    game.resurrect_player("p1")

    spawn_events = [e for e in game.events if e["type"] == "SPAWN"]
    assert len(spawn_events) == 1
    assert spawn_events[0]["data"]["is_resurrect"] is True
    assert spawn_events[0]["data"]["target"] == "p1"
    assert spawn_events[0]["data"]["respawns_used"] == 1


def test_easy_mode_resurrect_clears_harmful_buffs_keeps_beneficial():
    from app.engine.entities.buffs import add_buff
    game = _make_easy_game()
    player = game.add_player("p1", "Hero", "warrior")
    # Apply a harmful debuff and a beneficial buff
    add_buff(player.buffs, "poison", duration=10.0, level=1)
    add_buff(player.buffs, "barkskin", duration=30.0, level=2)
    _kill_player(game, "p1", floor_id=1)

    game.resurrect_player("p1")

    assert not has_buff(player.buffs, "poison")
    assert has_buff(player.buffs, "barkskin")


def test_boss_floor_excludes_resurrect():
    game = _make_easy_game()
    player = game.add_player("p1", "Hero", "warrior")
    initial_backpack = len(player.belongings.backpack.items)
    # Floor 5 = Goo boss floor
    data = _kill_player(game, "p1", floor_id=5)

    assert data["can_resurrect"] is False
    assert data["loot_dropped"] is True
    # Loot scattered (normal death sequence ran)
    assert len(player.belongings.backpack.items) < initial_backpack
    # Resurrect refused
    assert game.resurrect_player("p1") is False
    assert player.is_alive is False


def test_respawn_cap_excludes_resurrect_after_three_uses():
    game = _make_easy_game()
    player = game.add_player("p1", "Hero", "warrior")
    player.respawns_used = 3  # already exhausted the cap

    data = _kill_player(game, "p1", floor_id=1)

    assert data["can_resurrect"] is False
    assert game.resurrect_player("p1") is False


def _make_medium_game() -> GameInstance:
    game = GameInstance("test-medium-respawn")
    game.change_difficulty(Difficulty.NORMAL)  # Medium == Difficulty.NORMAL (UI label only)
    return game


def test_medium_difficulty_offers_resurrect_but_drops_backpack():
    game = _make_medium_game()
    player = game.add_player("p1", "Hero", "warrior")
    initial_backpack = len(player.belongings.backpack.items)

    data = _kill_player(game, "p1", floor_id=1)

    assert data["can_resurrect"] is True
    assert data["loot_dropped"] is True
    assert data["respawns_used"] == 0
    assert data["max_respawns"] == 3
    # Backpack scattered — inventory emptied, unlike Easy
    assert len(player.belongings.backpack.items) < initial_backpack
    # Grave placed, same as a full death
    floor = game._get_or_create_floor(1)
    assert any(it.type == "grave" for it in floor.items.values())


def test_medium_difficulty_keeps_equipped_weapon_and_armor():
    from app.engine.entities.items_equip import make_named_melee_weapon, LeatherArmor

    game = _make_medium_game()
    player = game.add_player("p1", "Hero", "warrior")
    sword = make_named_melee_weapon("Sword", id="sword-1")
    armor = LeatherArmor(id="armor-1")
    player.belongings.weapon = sword
    player.belongings.armor = armor

    data = _kill_player(game, "p1", floor_id=1)

    assert data["can_resurrect"] is True
    # Weapon/armor stay equipped, unlike the rest of the loadout.
    assert player.belongings.weapon is sword
    assert player.belongings.armor is armor
    floor = game._get_or_create_floor(1)
    assert not any(it.id in ("sword-1", "armor-1") for it in floor.items.values())


def test_medium_difficulty_resurrect_respawns_without_restoring_backpack():
    from app.engine.entities.items_equip import make_named_melee_weapon, LeatherArmor

    game = _make_medium_game()
    player = game.add_player("p1", "Hero", "warrior")
    player.belongings.weapon = make_named_melee_weapon("Sword", id="sword-1")
    player.belongings.armor = LeatherArmor(id="armor-1")
    _kill_player(game, "p1", floor_id=1)

    ok = game.resurrect_player("p1")

    assert ok is True
    assert player.is_alive is True
    assert player.hp == player.get_total_max_hp() // 2
    # Backpack stays empty — resurrect doesn't restore scattered gear.
    assert len(player.belongings.backpack.items) == 0
    # Weapon/armor survived the death sequence untouched.
    assert player.belongings.weapon is not None and player.belongings.weapon.id == "sword-1"
    assert player.belongings.armor is not None and player.belongings.armor.id == "armor-1"


def test_medium_boss_floor_excludes_resurrect_and_drops_everything():
    from app.engine.entities.items_equip import make_named_melee_weapon, LeatherArmor

    game = _make_medium_game()
    player = game.add_player("p1", "Hero", "warrior")
    player.belongings.weapon = make_named_melee_weapon("Sword", id="sword-1")
    player.belongings.armor = LeatherArmor(id="armor-1")
    initial_backpack = len(player.belongings.backpack.items)
    # Floor 5 = Goo boss floor
    data = _kill_player(game, "p1", floor_id=5)

    assert data["can_resurrect"] is False
    assert data["loot_dropped"] is True
    assert game.resurrect_player("p1") is False
    assert player.is_alive is False
    # A final death is final -- Medium's weapon/armor perk doesn't apply.
    assert len(player.belongings.backpack.items) < initial_backpack
    assert player.belongings.weapon is None
    assert player.belongings.armor is None


def test_medium_respawn_cap_excludes_resurrect_after_three_uses():
    game = _make_medium_game()
    player = game.add_player("p1", "Hero", "warrior")
    player.respawns_used = 3  # already exhausted the cap

    data = _kill_player(game, "p1", floor_id=1)

    assert data["can_resurrect"] is False
    assert game.resurrect_player("p1") is False


def test_hard_difficulty_does_not_offer_resurrect():
    game = GameInstance("test-hard-respawn")
    game.change_difficulty(Difficulty.HARD)
    game.add_player("p1", "Hero", "warrior")

    data = _kill_player(game, "p1", floor_id=1)

    assert data["can_resurrect"] is False
    assert data["loot_dropped"] is True


def test_hard_difficulty_drops_weapon_and_armor_too():
    from app.engine.entities.items_equip import make_named_melee_weapon, LeatherArmor

    game = GameInstance("test-hard-respawn-gear")
    game.change_difficulty(Difficulty.HARD)
    player = game.add_player("p1", "Hero", "warrior")
    player.belongings.weapon = make_named_melee_weapon("Sword", id="sword-1")
    player.belongings.armor = LeatherArmor(id="armor-1")

    _kill_player(game, "p1", floor_id=1)

    # Unlike Medium, Hard has no weapon/armor perk.
    assert player.belongings.weapon is None
    assert player.belongings.armor is None


def test_resurrect_refused_for_alive_player():
    game = _make_easy_game()
    game.add_player("p1", "Hero", "warrior")
    # Player still alive — resurrect should be a no-op
    assert game.resurrect_player("p1") is False


def test_score_penalty_own_respawns():
    game = _make_easy_game()
    player = game.add_player("p1", "Hero", "warrior")
    player.gold = 100
    player.floors_explored = 5

    # Baseline: no respawns
    base = game._score_breakdown(player, victory=False)
    assert base["respawn_multiplier"] is None

    # 1 respawn: 0.5x
    player.respawns_used = 1
    b1 = game._score_breakdown(player, victory=False)
    assert b1["respawn_multiplier"] == 0.5
    assert b1["total_score"] == int(base["total_score"] * 0.5)

    # 3 respawns: 0.125x
    player.respawns_used = 3
    b3 = game._score_breakdown(player, victory=False)
    assert b3["respawn_multiplier"] == 0.125
    assert b3["total_score"] == int(base["total_score"] * 0.125)


def test_score_penalty_witnessed_respawns():
    game = _make_easy_game()
    player = game.add_player("p1", "Hero", "warrior")
    player.gold = 100
    player.floors_explored = 5
    base = game._score_breakdown(player, victory=False)

    player.witnessed_respawns = 2
    b = game._score_breakdown(player, victory=False)
    assert b["witness_multiplier"] == 0.5
    assert b["total_score"] == int(base["total_score"] * 0.5)


def test_score_witness_penalty_floored_at_10_percent():
    game = _make_easy_game()
    player = game.add_player("p1", "Hero", "warrior")
    player.witnessed_respawns = 10  # way over the cap
    b = game._score_breakdown(player, victory=False)
    assert b["witness_multiplier"] == 0.1


def test_multiplayer_witness_counter_increments_on_resurrect():
    game = _make_easy_game()
    p1 = game.add_player("p1", "Hero1", "warrior")
    p2 = game.add_player("p2", "Hero2", "mage")

    assert p1.witnessed_respawns == 0
    assert p2.witnessed_respawns == 0

    _kill_player(game, "p1", floor_id=1)
    game.resurrect_player("p1")

    assert p1.respawns_used == 1
    assert p1.witnessed_respawns == 0  # own respawn tracked via respawns_used
    assert p2.witnessed_respawns == 1  # witnessed the resurrection


def test_three_respawns_then_fourth_death_is_final():
    game = _make_easy_game()
    player = game.add_player("p1", "Hero", "warrior")

    # Three resurrections
    for i in range(3):
        _kill_player(game, "p1", floor_id=1)
        assert game.resurrect_player("p1") is True
        assert player.respawns_used == i + 1

    # Fourth death — no more resurrections
    data = _kill_player(game, "p1", floor_id=1)
    assert data["can_resurrect"] is False
    assert game.resurrect_player("p1") is False


def test_spawn_protection_blocks_damage():
    game = _make_easy_game()
    player = game.add_player("p1", "Hero", "warrior")
    _kill_player(game, "p1", floor_id=1)
    game.resurrect_player("p1")

    hp_before = player.hp
    dealt = player.take_damage(15)

    assert dealt == 0
    assert player.hp == hp_before  # spawn protection blocked the hit


def test_spawn_protection_buff_present_with_correct_duration():
    from app.engine.entities.buffs import get_buff
    game = _make_easy_game()
    player = game.add_player("p1", "Hero", "warrior")
    _kill_player(game, "p1", floor_id=1)
    game.resurrect_player("p1")

    buff = get_buff(player.buffs, "spawn_protection")
    assert buff is not None
    assert buff.remaining == pytest.approx(3.0)


def test_resurrect_message_round_trips_through_client_adapter():
    from app.schemas.messages import CLIENT_MESSAGE_ADAPTER
    msg = CLIENT_MESSAGE_ADAPTER.validate_python({"type": "RESURRECT"})
    assert msg.type == "RESURRECT"
