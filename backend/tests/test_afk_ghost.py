import time

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.mobs import Rat
from app.engine.manager import GameInstance


def _open_room_game():
    game = GameInstance("test-game")
    game.players = {}
    game.grid = [[TileType.FLOOR for _ in range(10)] for _ in range(10)]
    game._get_or_create_floor(game.depth).rebuild_flags()
    game.mobs = {}
    return game


def test_afk_player_does_not_block_another_player():
    game = _open_room_game()
    ghost = game.add_player("ghost", "Ghost")
    ghost.pos = Position(x=2, y=1)
    ghost.is_afk = True

    mover = game.add_player("mover", "Mover")
    mover.pos = Position(x=1, y=1)

    game.move_entity("mover", 1, 0)

    assert (mover.pos.x, mover.pos.y) == (2, 1), "should walk straight through the AFK player"


def test_afk_player_does_not_block_a_mob():
    game = _open_room_game()
    ghost = game.add_player("ghost", "Ghost")
    ghost.pos = Position(x=2, y=1)
    ghost.is_afk = True

    mob = game._spawn_mob_at(Rat, 1, 1)
    game.mobs[mob.id] = mob

    game.move_entity(mob.id, 1, 0)

    assert (mob.pos.x, mob.pos.y) == (2, 1), "mob should walk straight through the AFK player"


def test_hunting_mob_never_attacks_afk_player():
    game = _open_room_game()
    player = game.add_player("p1", "Player")
    player.pos = Position(x=1, y=1)
    player.is_afk = True

    mob = game._spawn_mob_at(Rat, 2, 1)
    game.mobs[mob.id] = mob
    mob.ai_state = "hunting"
    mob.engaged = True

    # Wandering could legitimately land the mob on the ghost's tile (that's
    # the point -- it's non-solid), so only HP is asserted here, not position.
    for _ in range(25):
        mob.last_attack_time = time.time() - 10
        before = player.hp
        game.update_tick()
        assert player.hp == before, "AFK player must never take mob damage"
