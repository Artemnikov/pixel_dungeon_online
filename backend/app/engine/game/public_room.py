# Copyright (C) 2026 ArtemNikov
#
"""Public-room-only mechanics: item replenishment and boss respawn.

Late-joining players in the public room can still find loot because items
periodically respawn on empty floor tiles, and defeated bosses come back
after a cooldown so new players can fight them too.
"""

import random
import uuid
from typing import List

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction, Position
from app.engine.entities.items.union import AnyItem
from app.engine.entities.items.consumables import Key
from app.engine.entities.player import Player
from app.engine.game.constants import (
    BOSS_FLOORS,
    BOSS_RESPAWN_TICKS,
    CHEST_RESPAWN_TICKS,
    ITEM_RESPAWN_BASE_COUNT,
    ITEM_RESPAWN_PLAYER_BONUS,
    ITEM_RESPAWN_TURNS,
    PUBLIC_ROOM_ID,
)
from app.engine.game.tengu_arena import PRISON_BOSS_FLOOR
from app.engine.game.floor_state import FloorState
from app.engine.game.generation import ALL_POTIONS as _ALL_POTIONS, ALL_SCROLLS as _ALL_SCROLLS, ALL_FOOD as _ALL_FOOD, ALL_RUNESTONES as _ALL_RUNESTONES
from app.engine.entities.mobs import DM300, DwarfKing, Goo, Tengu, YogDzewa
from app.engine.dungeon.spd_levelgen.run_state import is_boss_level

# Floor ID → boss mob class (used for boss respawn in public rooms).
BOSS_CLASS_BY_FLOOR = {
    5: Goo,
    10: Tengu,
    15: DM300,
    20: DwarfKing,
    25: YogDzewa,
}
PUBLIC_ROOM_BOSS_TYPES = tuple(BOSS_CLASS_BY_FLOOR.values())


def _purge_dead_bosses(floor: FloorState) -> None:
    """Remove dead boss corpses from floor.mobs so that "no instance present"
    reliably means "defeated". Keeps the respawn presence-guard meaningful."""
    for mob_id, m in list(floor.mobs.items()):
        if isinstance(m, PUBLIC_ROOM_BOSS_TYPES) and not m.is_alive:
            del floor.mobs[mob_id]


def _empty_floor_tiles(floor: FloorState, players: "List[Player]") -> List[tuple]:
    """Return all walkable floor tiles that have no item, mob, or player."""
    tiles = []
    occupied_items = {(it.pos.x, it.pos.y) for it in floor.items.values() if it.pos is not None}
    occupied_mobs = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
    occupied_players = {(p.pos.x, p.pos.y) for p in players if p.pos is not None}
    walkable = {TileType.FLOOR, TileType.FLOOR_WOOD, TileType.FLOOR_WATER,
                TileType.FLOOR_COBBLE, TileType.FLOOR_GRASS}
    for y in range(floor.height):
        for x in range(floor.width):
            if floor.grid[y][x] not in walkable:
                continue
            if (x, y) in occupied_items or (x, y) in occupied_mobs or (x, y) in occupied_players:
                continue
            tiles.append((x, y))
    return tiles


def _random_item_at(x: int, y: int) -> AnyItem:
    """Create a random item at the given position (shares generation.py's pools)."""
    from app.engine.entities.items.equip import LeatherArmor, MailArmor, ScaleArmor
    from app.engine.entities.items.consumables import ThrowableDagger, Boomerang

    rand = random.random()
    if rand < 0.15:
        armor_tiers = [LeatherArmor, MailArmor, ScaleArmor]
        cls = random.choice(armor_tiers)
        return cls(id=str(uuid.uuid4()), pos=Position(x=x, y=y))
    elif rand < 0.22:
        if random.random() < 0.5:
            return ThrowableDagger(id=str(uuid.uuid4()), pos=Position(x=x, y=y), damage=4, range=4)
        else:
            return Boomerang(id=str(uuid.uuid4()), pos=Position(x=x, y=y), damage=3, range=6)
    elif rand < 0.50:
        cls = random.choice(_ALL_POTIONS)
        return cls(id=str(uuid.uuid4()), pos=Position(x=x, y=y))
    elif rand < 0.78:
        cls = random.choice(_ALL_SCROLLS)
        return cls(id=str(uuid.uuid4()), pos=Position(x=x, y=y))
    elif rand < 0.92:
        cls = random.choice(_ALL_RUNESTONES)
        return cls(id=str(uuid.uuid4()), pos=Position(x=x, y=y))
    else:
        cls = random.choice(_ALL_FOOD)
        return cls(id=str(uuid.uuid4()), pos=Position(x=x, y=y))


class PublicRoomMixin:
    """Item replenishment and boss respawn for the public room."""

    def _is_public_room(self) -> bool:
        return self.game_id == PUBLIC_ROOM_ID

    # ------------------------------------------------------------------
    # Item respawn
    # ------------------------------------------------------------------

    def _process_item_respawns(self, floor_id: int, floor: FloorState,
                               active_players: List[Player]) -> None:
        if not self._is_public_room() or floor_id in BOSS_FLOORS:
            return
        floor.item_respawn_counter += self.sim_ticks
        if floor.item_respawn_counter < ITEM_RESPAWN_TURNS:
            return
        floor.item_respawn_counter = 0

        if floor.original_item_count <= 0:
            return
        current = len(floor.items)
        deficit = floor.original_item_count - current
        if deficit <= 0:
            return
        wave = min(deficit, ITEM_RESPAWN_BASE_COUNT + ITEM_RESPAWN_PLAYER_BONUS * len(active_players))
        tiles = _empty_floor_tiles(floor, active_players)
        if not tiles:
            return
        random.shuffle(tiles)
        spawned = 0
        for x, y in tiles:
            if spawned >= wave:
                break
            item = _random_item_at(x, y)
            floor.items[item.id] = item
            spawned += 1
        if spawned:
            self.add_event("MESSAGE",
                           {"text": f"The dungeon stirs... {spawned} new items appear!"},
                           floor_id=floor_id)

    # ------------------------------------------------------------------
    # Boss respawn
    # ------------------------------------------------------------------

    def _process_boss_respawns(self, floor_id: int, floor: FloorState,
                                active_players: List[Player]) -> None:
        if not self._is_public_room() or not is_boss_level(floor_id):
            return
        boss_cls = BOSS_CLASS_BY_FLOOR.get(floor_id)
        if boss_cls is None:
            return

        # "Not initiated / between stages": any instance of this boss present --
        # whether alive-but-unstarted (fight not yet triggered) or a corpse that
        # hasn't been purged yet -- means the boss isn't defeated, so don't spawn.
        if any(isinstance(m, boss_cls) for m in floor.mobs.values()):
            return

        # The prison-boss state machine (floor 10, Tengu) owns its own lifecycle
        # through START -> FIGHT_START -> FIGHT_PAUSE -> FIGHT_ARENA -> WON. While
        # it is mid-fight this generic cooldown respawn must not fire -- during
        # FIGHT_PAUSE the Tengu is temporarily removed from the world and restored
        # later, so treating that as a "defeat" would resurrect an extra copy. Only
        # after a full defeat (WON) does this path take over to bring back new players.
        if floor_id == PRISON_BOSS_FLOOR and floor.tengu_state != "WON":
            return

        floor.boss_dead_ticks += self.sim_ticks
        if floor.boss_dead_ticks < BOSS_RESPAWN_TICKS:
            return
        floor.boss_dead_ticks = 0

        # --- Reset locked doors so progression keys work again -----------
        consumed_keys = []
        for item in list(floor.items.values()):
            if isinstance(item, Key) and getattr(item, "key_id", None) in floor.locked_doors.values():
                consumed_keys.append(item)
        for item in consumed_keys:
            del floor.items[item.id]

        # --- Spawn the boss on its designated spawn tile (or closest empty tile) ---
        tiles = _empty_floor_tiles(floor, active_players)
        spawn_pos = floor.boss_spawn_pos
        occupied_entities = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
        occupied_entities.update((p.pos.x, p.pos.y) for p in active_players if p.pos is not None)
        walkable = {TileType.FLOOR, TileType.FLOOR_WOOD, TileType.FLOOR_WATER,
                    TileType.FLOOR_COBBLE, TileType.FLOOR_GRASS, TileType.WALL_DECO}

        if (spawn_pos and 0 <= spawn_pos[0] < floor.width and 0 <= spawn_pos[1] < floor.height
                and floor.grid[spawn_pos[1]][spawn_pos[0]] in walkable
                and spawn_pos not in occupied_entities):
            x, y = spawn_pos
        elif tiles and spawn_pos:
            x, y = min(tiles, key=lambda t: (t[0] - spawn_pos[0]) ** 2 + (t[1] - spawn_pos[1]) ** 2)
        elif tiles:
            x, y = random.choice(tiles)
        else:
            return
        boss = boss_cls(
            id=str(uuid.uuid4()),
            pos=Position(x=x, y=y),
            faction=Faction.DUNGEON,
        )
        boss.floor_id = floor_id
        floor.mobs[boss.id] = boss
        self.add_event("MESSAGE",
                       {"text": f"A {boss.name} has respawned on floor {floor_id}!"})

    # ------------------------------------------------------------------
    # Chest respawn
    # ------------------------------------------------------------------

    # chest_type → (key_id, display_name) for locked chests; plain chests need no key.
    _CHEST_KEY_MAP = {
        "LOCKED_CHEST": ("golden", "Golden Key"),
        "CRYSTAL_CHEST": ("crystal", "Crystal Key"),
    }

    def _queue_chest_respawn(self, floor: FloorState, chest) -> None:
        """Called from _try_open_chest when a chest is looted in the public room."""
        if not self._is_public_room():
            return
        if chest.chest_type not in ("CHEST", "LOCKED_CHEST", "CRYSTAL_CHEST"):
            return
        floor.chest_respawn_queue.append({
            "ticks_left": CHEST_RESPAWN_TICKS,
            "chest_type": chest.chest_type,
        })

    def _process_chest_respawns(self, floor_id: int, floor: FloorState,
                                 active_players: List[Player]) -> None:
        if not self._is_public_room() or floor_id in BOSS_FLOORS or not floor.chest_respawn_queue:
            return
        remaining = []
        for entry in floor.chest_respawn_queue:
            entry["ticks_left"] -= self.sim_ticks
            if entry["ticks_left"] > 0:
                remaining.append(entry)
                continue
            self._spawn_chest_with_key(floor, floor_id, entry["chest_type"], active_players)
        floor.chest_respawn_queue = remaining

    def _spawn_chest_with_key(self, floor: FloorState, floor_id: int,
                              chest_type: str, active_players: List[Player]) -> None:
        from app.engine.entities.items.union import Chest as ChestCls

        tiles = _empty_floor_tiles(floor, active_players)
        if len(tiles) < 2:
            return
        random.shuffle(tiles)
        chest_pos = tiles.pop()
        key_pos = tiles.pop()

        num_items = random.randint(1, 3)
        contents = [_random_item_at(chest_pos[0], chest_pos[1]) for _ in range(num_items)]

        chest = ChestCls(
            id=str(uuid.uuid4()),
            name="Chest",
            pos=Position(x=chest_pos[0], y=chest_pos[1]),
            chest_type=chest_type,
            contents=contents,
        )
        floor.items[chest.id] = chest

        key_info = self._CHEST_KEY_MAP.get(chest_type)
        if key_info:
            key_id, key_name = key_info
            key = Key(
                id=str(uuid.uuid4()),
                name=key_name,
                pos=Position(x=key_pos[0], y=key_pos[1]),
                key_id=key_id,
            )
            floor.items[key.id] = key

        self.add_event("MESSAGE",
                       {"text": f"A {chest_type.replace('_', ' ').title()} has appeared!"},
                       floor_id=floor_id)
