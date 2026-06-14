from app.engine.manager import GameInstance
from app.engine.entities.base import Mob as MobEntity, Position
from app.engine.game.constants import PATH_BLOCKED_GIVE_UP_TICKS


def test_path_queue_survives_temporary_mob_blockage():
    """A MOVE_TO path should resume once a mob that was blocking the next
    step moves out of the way, instead of being abandoned permanently."""
    game = GameInstance("test-game")
    player = game.add_player("p1", "Tester")

    floor = game._get_or_create_floor(player.floor_id)
    floor.mobs.clear()

    start_x, start_y = player.pos.x, player.pos.y
    player.path_queue = [(1, 0), (1, 0), (1, 0)]
    player.move_intent = None
    player.last_auto_move_time = 0.0

    blocker = MobEntity(
        id="blocker", name="Rat",
        pos=Position(x=start_x + 1, y=start_y),
        hp=10, max_hp=10,
    )
    floor.mobs[blocker.id] = blocker

    # Next step is blocked by the mob: stay put, but keep the path queued
    # so the player continues once the tile clears.
    game.update_tick()
    assert (player.pos.x, player.pos.y) == (start_x, start_y)
    assert player.path_queue == [(1, 0), (1, 0), (1, 0)]

    # Mob moves out of the way; the queued path should resume.
    blocker.pos = Position(x=start_x + 5, y=start_y + 5)
    player.last_auto_move_time = 0.0
    game.update_tick()

    assert (player.pos.x, player.pos.y) == (start_x + 1, start_y)
    assert player.path_queue == [(1, 0), (1, 0)]


def test_path_queue_gives_up_after_persistent_mob_blockage():
    """If a mob permanently camps the next tile, the queued path is dropped
    after a bounded number of retries rather than stalling forever."""
    game = GameInstance("test-game")
    player = game.add_player("p1", "Tester")

    floor = game._get_or_create_floor(player.floor_id)
    floor.mobs.clear()

    start_x, start_y = player.pos.x, player.pos.y
    player.path_queue = [(1, 0)]
    player.move_intent = None
    player.last_auto_move_time = 0.0

    blocker = MobEntity(
        id="blocker", name="Rat",
        pos=Position(x=start_x + 1, y=start_y),
        hp=10, max_hp=10,
    )
    floor.mobs[blocker.id] = blocker

    for _ in range(PATH_BLOCKED_GIVE_UP_TICKS + 1):
        player.last_auto_move_time = 0.0
        game.update_tick()

    assert (player.pos.x, player.pos.y) == (start_x, start_y)
    assert player.path_queue == []
    assert player.path_blocked_ticks == 0
