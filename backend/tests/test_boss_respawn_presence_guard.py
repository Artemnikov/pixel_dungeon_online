import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.base import Faction, Position
from app.engine.entities.mobs.sewers import Goo
from app.engine.entities.mobs.caves import DM300
from app.engine.entities.mobs.city import DwarfKing
from app.engine.entities.mobs.halls import YogDzewa
from app.engine.manager import GameInstance
from app.engine.game.constants import BOSS_RESPAWN_TICKS, PUBLIC_ROOM_ID


# Non-Tengu boss rooms: floor_id -> boss class. These bosses never leave the
# world mid-fight (no "between stages" removal window like Tengu), so a single
# presence guard covers them uniformly -- but only if dead entries are purged on
# death so that "absent from floor.mobs" reliably means defeated. Level gen
# already places one live boss per room, which the tests use as the fighting copy.
BOSS_ROOMS = {
    5: Goo,
    15: DM300,
    20: DwarfKing,
    25: YogDzewa,
}


def make_public_game(floor_id):
    game = GameInstance(PUBLIC_ROOM_ID)
    game.players = {}
    floor = game.generate_floor(floor_id)
    player = game.add_player("p1", "Hero")
    player.floor_id = floor_id
    return game, floor


def live_bosses(game, floor, cls):
    return [m for m in floor.mobs.values() if isinstance(m, cls) and m.is_alive]


def boss_count(game, floor, cls):
    return sum(1 for m in floor.mobs.values() if isinstance(m, cls))


def test_presence_guard_blocks_respawn_while_dead_boss_lingers():
    """The presence guard's unique value: a boss that has died but whose dead
    entry still lingers in floor.mobs (e.g. death processed on another tick, or
    before purge) must NOT trigger a respawn -- even though has_alive_boss is now
    False and the cooldown elapsed. On unguarded code this would spawn a second
    copy while the first corpse sits in the world."""
    for floor_id, cls in BOSS_ROOMS.items():
        game, floor = make_public_game(floor_id)

        # Simulate a lingering death: mark the generated boss dead but do NOT
        # purge it (leave the entry in place). Now has_alive_boss == False.
        boss = live_bosses(game, floor, cls)[0]
        boss.is_alive = False
        assert not any(m.is_alive for m in floor.mobs.values() if isinstance(m, cls))

        floor.boss_dead_ticks = BOSS_RESPAWN_TICKS + 1   # cooldown long past threshold
        game._process_boss_respawns(floor_id, floor, [game.players["p1"]])

        assert boss_count(game, floor, cls) == 1, \
            f"floor {floor_id}: respawn fired while a dead boss instance still lingers in the world"


def test_purge_on_death_then_post_defeat_respawn():
    """End-to-end for every non-Tengu boss room: the presence guard blocks a
    premature double-spawn while the boss fights; once it dies and is purged from
    floor.mobs, the cooldown respawn brings back exactly one fresh copy."""
    for floor_id, cls in BOSS_ROOMS.items():
        game, floor = make_public_game(floor_id)

        # --- Fight ongoing: presence guard blocks premature respawn ---------
        boss = live_bosses(game, floor, cls)[0]
        floor.boss_dead_ticks = BOSS_RESPAWN_TICKS + 1

        game._process_boss_respawns(floor_id, floor, [game.players["p1"]])
        assert boss_count(game, floor, cls) == 1, \
            f"floor {floor_id}: premature respawn during fight (count={boss_count(game, floor, cls)})"

        # --- Full defeat: kill the boss so it is purged from the world -------
        boss.is_alive = False
        game.handle_mob_death(boss, floor, floor_id)   # public room -> purge dead bosses
        assert not any(isinstance(m, cls) for m in floor.mobs.values()), \
            f"floor {floor_id}: dead boss entry not purged from floor.mobs"

        # Cooldown elapses since defeat -> respawn exactly once at its specific tile.
        floor.boss_dead_ticks = BOSS_RESPAWN_TICKS + 1
        game._process_boss_respawns(floor_id, floor, [game.players["p1"]])
        assert boss_count(game, floor, cls) == 1, \
            f"floor {floor_id}: no post-defeat respawn after cooldown (count={boss_count(game, floor, cls)})"
        respawned = live_bosses(game, floor, cls)[0]
        if floor.boss_spawn_pos:
            assert (respawned.pos.x, respawned.pos.y) == floor.boss_spawn_pos
