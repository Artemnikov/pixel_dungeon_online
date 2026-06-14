import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.base import Armor, Player, Position
from app.engine.manager import GameInstance
import uuid


def test_admin_player_takes_no_damage():
    player = Player(
        id="p1", name="Admin", pos=Position(x=0, y=0),
        hp=20, max_hp=20, attack=5, defense=0, faction="player",
        is_admin=True,
    )
    dmg = player.take_damage(5)
    assert dmg == 0
    assert player.hp == 20
    assert player.is_downed == False


def test_normal_player_takes_damage():
    player = Player(
        id="p2", name="Normal", pos=Position(x=0, y=0),
        hp=20, max_hp=20, attack=5, defense=0, faction="player",
        is_admin=False,
    )
    dmg = player.take_damage(5)
    assert dmg == 5
    assert player.hp == 15


def test_add_player_sets_is_admin():
    game = GameInstance("test-admin")
    player_id = str(uuid.uuid4())
    player = game.add_player(player_id, "Admin", is_admin=True)
    assert player.is_admin == True


def test_admin_get_state_shows_all_mobs():
    from app.engine.entities.base import Mob as MobEntity
    game = GameInstance("test-admin-vision")
    player_id = str(uuid.uuid4())
    player = game.add_player(player_id, "Admin", is_admin=True)

    floor = game._get_or_create_floor(player.floor_id)
    mob = MobEntity(
        id=str(uuid.uuid4()), name="FarRat",
        pos=Position(x=0, y=0),
        hp=5, max_hp=5, attack=1, defense=0, faction="dungeon",
    )
    floor.mobs[mob.id] = mob
    player.pos = Position(x=59, y=39)

    state = game.get_state(player_id)
    mob_ids = [m["id"] for m in state["mobs"]]
    assert mob.id in mob_ids, "Admin should see mobs outside normal LOS"


def test_admin_get_state_visible_tiles_is_full_grid():
    game = GameInstance("test-admin-tiles")
    player_id = str(uuid.uuid4())
    player = game.add_player(player_id, "Admin", is_admin=True)
    state = game.get_state(player_id)
    expected_count = game.width * game.height
    assert len(state["visible_tiles"]) == expected_count


def test_admin_level_up_grants_one_level():
    game = GameInstance("test-admin-lvl")
    pid = str(uuid.uuid4())
    p = game.add_player(pid, "Admin", is_admin=True)
    old_level = p.level
    old_max_hp = p.max_hp
    game.admin_level_up(pid)
    assert p.level == old_level + 1
    assert p.max_hp == old_max_hp + 5
    assert p.hp == old_max_hp + 5  # healed by the level-up
    assert p.experience == 0


def test_admin_level_up_non_admin_noop():
    game = GameInstance("test-admin-lvl-na")
    pid = str(uuid.uuid4())
    p = game.add_player(pid, "Normal", is_admin=False)
    old = p.level
    game.admin_level_up(pid)
    assert p.level == old


def test_admin_level_up_max_level_noop():
    game = GameInstance("test-admin-lvl-max")
    pid = str(uuid.uuid4())
    p = game.add_player(pid, "Admin", is_admin=True)
    p.level = 30
    p.experience = 0
    game.admin_level_up(pid)
    assert p.level == 30


def test_admin_give_item_non_admin_noop():
    game = GameInstance("test-admin-give-na")
    pid = str(uuid.uuid4())
    p = game.add_player(pid, "Normal", is_admin=False)
    before = len(p.belongings.backpack.items)
    game.admin_give_item(pid, "health_potion")
    assert len(p.belongings.backpack.items) == before


def test_admin_give_item_unknown_kind_noop():
    game = GameInstance("test-admin-give-unknown")
    pid = str(uuid.uuid4())
    p = game.add_player(pid, "Admin", is_admin=True)
    before = len(p.belongings.backpack.items)
    game.admin_give_item(pid, "not_a_real_item")
    assert len(p.belongings.backpack.items) == before


def test_admin_give_item_adds_to_backpack():
    game = GameInstance("test-admin-give")
    pid = str(uuid.uuid4())
    p = game.add_player(pid, "Admin", is_admin=True)
    game.admin_give_item(pid, "health_potion")
    kinds = [item.kind for item in p.belongings.backpack.items]
    assert "health_potion" in kinds


def test_admin_give_item_drops_on_floor_when_backpack_full():
    game = GameInstance("test-admin-give-full")
    pid = str(uuid.uuid4())
    p = game.add_player(pid, "Admin", is_admin=True)
    p.pos = Position(x=5, y=5)
    p.belongings.backpack.items = [
        Armor(id=str(uuid.uuid4()), name=f"Armor {i}", tier=1) for i in range(p.belongings.backpack.capacity)
    ]
    before = len(p.belongings.backpack.items)
    floor = game._get_or_create_floor(p.floor_id)
    before_dropped = {item.id for item in floor.items.values() if item.kind == "health_potion"}

    game.admin_give_item(pid, "health_potion")

    assert len(p.belongings.backpack.items) == before
    dropped = [item for item in floor.items.values() if item.kind == "health_potion" and item.id not in before_dropped]
    assert len(dropped) == 1
    assert dropped[0].pos == Position(x=5, y=5)
