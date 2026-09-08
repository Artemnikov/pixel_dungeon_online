# Copyright (C) 2026 ArtemNikov
#
"""Authority gates for client-driven movement and click-to-attack.

Guards against crafted messages warping the player across the map: non-unit
step deltas, teleport-spam through the legacy MOVE handler, and cross-floor
click-to-attacks. Mirrors the guarantees the frontend relies on for its
tap-to-move / tap-to-attack paths.
"""

from app.api.ws_handlers import handle_move, handle_path_steps
from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.mobs import Rat
from app.engine.manager import GameInstance
from app.schemas import messages as msg
from app.schemas.common import Direction


def _open_room_game(width=20, height=20):
    game = GameInstance("test-game")
    game.players = {}
    game.mobs = {}
    floor = game._get_or_create_floor(1)
    floor.grid = [[TileType.FLOOR for _ in range(width)] for _ in range(height)]
    floor.rebuild_flags()
    return game


def _spawn_rat(game, x, y):
    mob = game._spawn_mob_at(Rat, x, y)
    game.mobs[mob.id] = mob
    return mob


# --- attack_mob reach gate ---------------------------------------------------

def test_attack_mob_far_target_is_noop():
    game = _open_room_game()
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=3, y=3)
    mob = _spawn_rat(game, 9, 3)
    hp_before = mob.hp

    game.attack_mob(player.id, mob.id)

    assert (player.pos.x, player.pos.y) == (3, 3), "player must not warp toward a far target"
    assert mob.hp == hp_before, "no melee should land on a far target"


def test_attack_mob_adjacent_target_hits():
    game = _open_room_game()
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=3, y=3)
    mob = _spawn_rat(game, 4, 3)
    player.last_attack_time = 0.0
    hp_before = mob.hp

    game.attack_mob(player.id, mob.id)

    assert mob.hp < hp_before, "adjacent melee attack should land"


# --- unit-delta gates --------------------------------------------------------

def test_queue_move_step_rejects_non_unit_delta():
    game = _open_room_game()
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=3, y=3)

    game.queue_move_step(player.id, 1, 5, 0)
    game.queue_move_step(player.id, 2, 0, 7)

    assert len(player.movement.step_queue) == 0


def test_move_entity_rejects_non_unit_seq_steps():
    # Defense-in-depth: even if something bypasses queue_move_step, a seq'd
    # (client-originated) step must be a unit move.
    game = _open_room_game()
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=3, y=3)

    game.move_entity(player.id, 5, 0, seq=1)

    assert (player.pos.x, player.pos.y) == (3, 3)


def test_move_entity_internal_multi_tile_push_still_works():
    # Knockback / wall-slam pushes call move_entity without a seq and must be
    # unaffected by the client-delta gate.
    game = _open_room_game()
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=3, y=3)

    game.move_entity(player.id, 3, 0)

    assert (player.pos.x, player.pos.y) == (6, 3)


def test_set_move_intent_clamps_non_unit():
    game = _open_room_game()
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=3, y=3)

    game.set_move_intent(player.id, 4, 0)

    assert player.movement.move_intent == (1, 0)


# --- legacy MOVE handler -----------------------------------------------------

def test_legacy_move_handler_is_paced():
    game = _open_room_game()
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=3, y=3)

    # Two MOVE messages back-to-back may only move a single tile: the handler
    # runs through the same step cooldown as the tick.
    handle_move(game, player.id, msg.Move(type="MOVE", direction=Direction.RIGHT))
    handle_move(game, player.id, msg.Move(type="MOVE", direction=Direction.RIGHT))

    assert (player.pos.x, player.pos.y) == (4, 3)


def test_legacy_move_handler_bump_into_mob_resolves_melee():
    game = _open_room_game()
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=3, y=3)
    mob = _spawn_rat(game, 4, 3)
    player.last_attack_time = 0.0
    hp_before = mob.hp

    handle_move(game, player.id, msg.Move(type="MOVE", direction=Direction.RIGHT))

    assert mob.hp < hp_before, "bump-attack should still land through the legacy handler"


# --- PATH_STEPS handler ------------------------------------------------------

def test_path_steps_handler_drops_non_unit_steps():
    game = _open_room_game()
    player = game.add_player("p1", "Tester")
    player.pos = Position(x=3, y=3)

    handle_path_steps(game, player.id, msg.PathSteps(type="PATH_STEPS", steps=[[100, 0], [1, 0], [1, 1]]))

    assert list(player.movement.path_queue) == [(1, 0), (1, 1)]