import asyncio

from app.main import ConnectionManager


class DummyWebSocket:
    def __init__(self):
        self.accepted = False
        self.messages = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, payload):
        self.messages.append(payload)


def test_reconnect_same_session_rebinds_to_existing_hero():
    async def scenario():
        manager = ConnectionManager()
        game_id, session_id = "g", "sess-1"

        ws1 = DummyWebSocket()
        player_id, is_new = await manager.connect(game_id, ws1, session_id)
        assert is_new is True
        game = manager.game_instances[game_id]
        game.add_player(player_id, "Hero")

        # Mutate state so we can prove it survives the reconnect.
        game.players[player_id].hp = 7
        game.players[player_id].gold = 42

        # Drop: hero is kept alive (grace), not deleted.
        manager.disconnect(game_id, ws1)
        assert player_id in game.players
        assert player_id in manager.disconnect_deadline[game_id]

        # Reconnect with the same session → rebind to the same hero.
        ws2 = DummyWebSocket()
        rejoin_id, is_new2 = await manager.connect(game_id, ws2, session_id)
        assert is_new2 is False
        assert rejoin_id == player_id
        assert game.players[player_id].hp == 7
        assert game.players[player_id].gold == 42
        # Grace deadline cleared; INIT will be re-sent (last_sent_floor reset).
        assert player_id not in manager.disconnect_deadline[game_id]
        assert player_id not in manager.last_sent_floor[game_id]
        assert manager.active_connections[game_id][ws2] == player_id

    asyncio.run(scenario())


def test_new_session_spawns_fresh_hero():
    async def scenario():
        manager = ConnectionManager()
        game_id = "g"

        ws1 = DummyWebSocket()
        pid1, _ = await manager.connect(game_id, ws1, "sess-A")
        manager.game_instances[game_id].add_player(pid1, "A")

        ws2 = DummyWebSocket()
        pid2, is_new = await manager.connect(game_id, ws2, "sess-B")
        assert is_new is True
        assert pid2 != pid1

    asyncio.run(scenario())


def test_reaper_kills_hero_after_grace_expires():
    async def scenario():
        manager = ConnectionManager()
        game_id, session_id = "g", "sess-1"

        ws = DummyWebSocket()
        player_id, _ = await manager.connect(game_id, ws, session_id)
        game = manager.game_instances[game_id]
        game.add_player(player_id, "Hero")
        player = game.players[player_id]
        # Give the hero something to drop (default class is Warrior, whose
        # starting weapon is WornShortsword -- a Dagger isn't exempt from drop).
        from app.engine.entities.items_equip import Dagger
        player.belongings.weapon = Dagger(id="dagger-1")

        manager.disconnect(game_id, ws)
        assert player.is_afk is True
        # Force the deadline into the past, then reap.
        manager.disconnect_deadline[game_id][player_id] = 0.0
        manager.reap_expired_players(game_id)

        # Reap only flips the hero to dead; the death sequence (gear scatter,
        # grave, DEATH event) runs on the next tick, same as any other death.
        assert player_id in game.players
        assert player.is_alive is False
        assert player.death_processed is False

        game.update_tick()
        assert player.death_processed is True
        assert player.belongings.weapon is None
        dropped = [i for i in game._get_or_create_floor(player.floor_id).items.values()
                   if isinstance(i, Dagger)]
        assert len(dropped) == 1
        events = game.flush_events()
        assert any(e["type"] == "DEATH" and e["data"]["target"] == player_id for e in events)

        # The session mapping and hero both survive -- a late reconnect rebinds
        # to the dead hero and sees the normal death/score screen, it isn't
        # silently swapped for a fresh spawn.
        assert session_id in manager.sessions[game_id]
        ws2 = DummyWebSocket()
        rejoin_id, is_new = await manager.connect(game_id, ws2, session_id)
        assert is_new is False
        assert rejoin_id == player_id
        assert game.players[player_id].is_alive is False

    asyncio.run(scenario())


def test_reconnect_within_grace_clears_afk_flag():
    async def scenario():
        manager = ConnectionManager()
        game_id, session_id = "g", "sess-1"

        ws1 = DummyWebSocket()
        player_id, _ = await manager.connect(game_id, ws1, session_id)
        game = manager.game_instances[game_id]
        game.add_player(player_id, "Hero")

        manager.disconnect(game_id, ws1)
        assert game.players[player_id].is_afk is True

        ws2 = DummyWebSocket()
        await manager.connect(game_id, ws2, session_id)
        assert game.players[player_id].is_afk is False

    asyncio.run(scenario())


def test_reaped_corpse_does_not_block_game_cleanup():
    async def scenario():
        manager = ConnectionManager()
        game_id, session_id = "g", "sess-1"

        ws = DummyWebSocket()
        player_id, _ = await manager.connect(game_id, ws, session_id)
        game = manager.game_instances[game_id]
        game.add_player(player_id, "Hero")

        manager.disconnect(game_id, ws)
        manager.disconnect_deadline[game_id][player_id] = 0.0
        manager.reap_expired_players(game_id)
        game.update_tick()

        # Nobody connected, no pending deadline, only a corpse left -> the
        # abandoned game must still be torn down, not leak forever.
        manager.cleanup_if_empty(game_id)
        assert game_id not in manager.game_instances

    asyncio.run(scenario())


def test_reconnect_before_reap_keeps_hero():
    async def scenario():
        manager = ConnectionManager()
        game_id, session_id = "g", "sess-1"

        ws = DummyWebSocket()
        player_id, _ = await manager.connect(game_id, ws, session_id)
        manager.game_instances[game_id].add_player(player_id, "Hero")

        manager.disconnect(game_id, ws)
        # Reconnect first...
        ws2 = DummyWebSocket()
        await manager.connect(game_id, ws2, session_id)
        # ...then a reaper pass must NOT remove the now-connected hero.
        manager.reap_expired_players(game_id)
        assert player_id in manager.game_instances[game_id].players

    asyncio.run(scenario())
