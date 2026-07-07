import pytest

from app.engine.manager import GameInstance
from app.engine.entities.base import Position
from app.engine.entities.player import CharacterClass, Mob as MobEntity
from app.engine.dungeon.constants import TileType


def _open_game():
    """A game with a fully-open 12x12 floor so line-of-fire is deterministic."""
    game = GameInstance("test-autoaim")
    game.mobs = {}
    game.grid = [[TileType.FLOOR for _ in range(12)] for _ in range(12)]
    game._get_or_create_floor(game.depth).rebuild_flags()
    return game


def _mob(game, mob_id, x, y):
    mob = MobEntity(id=mob_id, name="Rat", pos=Position(x=x, y=y),
                    hp=10, max_hp=10, attack=2, defense=0, defense_skill=0)
    game.mobs[mob_id] = mob
    return mob


def test_autoaim_direct_line_returns_target_cell():
    game = _open_game()
    player = game.add_player("p1", "Huntress", CharacterClass.HUNTRESS)
    player.pos = Position(x=5, y=5)
    mob = _mob(game, "m1", 5, 8)  # clear vertical line

    assert game._autoaim_cell(player, mob) == (mob.pos.x, mob.pos.y)


def test_autoaim_walled_in_target_falls_back_to_target_cell():
    game = _open_game()
    player = game.add_player("p1", "Huntress", CharacterClass.HUNTRESS)
    player.pos = Position(x=5, y=5)
    mob = _mob(game, "m1", 5, 9)

    # Enclose the mob so no shot from the hero can reach it: every cell within
    # Chebyshev radius 2 of the mob (except the mob itself) is a wall.
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            if dx == 0 and dy == 0:
                continue
            game.grid[mob.pos.y + dy][mob.pos.x + dx] = TileType.WALL
    game._get_or_create_floor(game.depth).rebuild_flags()

    # No line of fire exists -> auto-aim safely falls back to the target's cell.
    assert game._autoaim_cell(player, mob) == (mob.pos.x, mob.pos.y)
