"""Keys are tracked as a per-player, depth-keyed counter (mirrors SPD's
Notes.KeyRecord), never as bag items. See Player.add_key/key_count/remove_key."""
from app.engine.entities.base import Position, Faction
from app.engine.entities.player import Player


def make_player():
    return Player(id="p1", name="Hero", pos=Position(x=0, y=0), hp=50, max_hp=50, faction=Faction.PLAYER)


def test_add_key_then_count():
    p = make_player()
    p.add_key("iron", depth=3, name="Iron Key")

    assert p.key_count("iron", depth=3) == 1
    assert p.keys[0].name == "Iron Key"


def test_add_key_stacks_same_key_id_and_depth():
    p = make_player()
    p.add_key("iron", depth=3, name="Iron Key")
    p.add_key("iron", depth=3, name="Iron Key")

    assert p.key_count("iron", depth=3) == 2
    assert len(p.keys) == 1


def test_keys_are_scoped_by_depth():
    p = make_player()
    p.add_key("iron", depth=3, name="Iron Key")

    assert p.key_count("iron", depth=3) == 1
    assert p.key_count("iron", depth=7) == 0


def test_remove_key_decrements_and_drops_empty_record():
    p = make_player()
    p.add_key("iron", depth=3, name="Iron Key")

    assert p.remove_key("iron", depth=3) is True
    assert p.key_count("iron", depth=3) == 0
    assert p.keys == []


def test_remove_key_fails_when_none_held():
    p = make_player()

    assert p.remove_key("iron", depth=3) is False


def test_remove_key_does_not_consume_a_key_from_a_different_depth():
    p = make_player()
    p.add_key("iron", depth=3, name="Iron Key")

    # An Iron Key found on floor 3 must not unlock an Iron Key vault on floor 7.
    assert p.remove_key("iron", depth=7) is False
    assert p.key_count("iron", depth=3) == 1
