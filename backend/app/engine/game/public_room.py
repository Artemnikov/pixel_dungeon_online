# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
"""Public-room-only mechanics: item replenishment and boss respawn.

Late-joining players in the public room can still find loot because items
periodically respawn on empty floor tiles, and defeated bosses come back
after a cooldown so new players can fight them too.
"""

import random
import uuid
from typing import List, Type

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction, Position
from app.engine.entities.items_consumable import Key
from app.engine.entities.mobs import MobEntity
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
from app.engine.game.floor_state import FloorState
from app.engine.dungeon.spd_levelgen.run_state import is_boss_level

# Floor ID → boss mob class (used for boss respawn).
_BOSS_CLASS_MAP = None


def _boss_class_for_floor(floor_id: int):
    """Return the boss mob class for a given floor, or None."""
    global _BOSS_CLASS_MAP
    if _BOSS_CLASS_MAP is None:
        from app.engine.entities.mobs import Goo, Tengu, DM300, DwarfKing, YogDzewa
        _BOSS_CLASS_MAP = {5: Goo, 10: Tengu, 15: DM300, 20: DwarfKing, 25: YogDzewa}
    return _BOSS_CLASS_MAP.get(floor_id)


# Item pools mirrored from generation.py for respawn consistency.
_ALL_POTIONS = None
_ALL_SCROLLS = None
_ALL_FOOD = None
_ALL_RUNESTONES = None


def _init_item_pools():
    global _ALL_POTIONS, _ALL_SCROLLS, _ALL_FOOD, _ALL_RUNESTONES
    if _ALL_POTIONS is not None:
        return
    from app.engine.entities.items_potions import (
        HealthPotion, RevivingPotion, FuryPotion,
        PotionOfStrength, PotionOfHaste, PotionOfInvisibility, PotionOfLevitation,
        PotionOfMindVision, PotionOfFrost, PotionOfLiquidFlame, PotionOfToxicGas,
        PotionOfParalyticGas, PotionOfPurity, PotionOfExperience,
    )
    from app.engine.entities.items_scrolls import (
        ScrollOfRage, ScrollOfUpgrade, ScrollOfIdentify, ScrollOfMagicMapping,
        ScrollOfTeleportation, ScrollOfRemoveCurse, ScrollOfRecharging, ScrollOfLullaby,
        ScrollOfTerror, ScrollOfMirrorImage, ScrollOfRetribution, ScrollOfTransmutation,
    )
    from app.engine.entities.items_consumable import SmallRation, Ration, Pasty
    from app.engine.entities.runestones import (
        StoneOfBlast, StoneOfBlink, StoneOfDeepSleep, StoneOfClairvoyance,
        StoneOfAggression, StoneOfFlock, StoneOfShock, StoneOfFear,
        StoneOfDetectMagic, StoneOfIntuition, StoneOfEnchantment, StoneOfAugmentation,
    )
    _ALL_POTIONS = [
        HealthPotion, RevivingPotion, FuryPotion,
        PotionOfStrength, PotionOfHaste, PotionOfInvisibility, PotionOfLevitation,
        PotionOfMindVision, PotionOfFrost, PotionOfLiquidFlame, PotionOfToxicGas,
        PotionOfParalyticGas, PotionOfPurity, PotionOfExperience,
    ]
    _ALL_SCROLLS = [
        ScrollOfRage, ScrollOfUpgrade, ScrollOfIdentify, ScrollOfMagicMapping,
        ScrollOfTeleportation, ScrollOfRemoveCurse, ScrollOfRecharging, ScrollOfLullaby,
        ScrollOfTerror, ScrollOfMirrorImage, ScrollOfRetribution, ScrollOfTransmutation,
    ]
    _ALL_FOOD = [SmallRation, Ration, Ration, Pasty]
    _ALL_RUNESTONES = [
        StoneOfBlast, StoneOfBlink, StoneOfDeepSleep, StoneOfClairvoyance,
        StoneOfAggression, StoneOfFlock, StoneOfShock, StoneOfFear,
        StoneOfDetectMagic, StoneOfIntuition, StoneOfEnchantment, StoneOfAugmentation,
    ]


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


def _random_item_at(x: int, y: int) -> "Item":
    """Create a random item at the given position (mirrors generation.py pools)."""
    _init_item_pools()
    from app.engine.entities.items_equip import LeatherArmor, MailArmor, ScaleArmor
    from app.engine.entities.items_consumable import ThrowableDagger, Boomerang

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
        floor.item_respawn_counter += 1
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
        boss_cls = _boss_class_for_floor(floor_id)
        if boss_cls is None:
            return

        has_alive_boss = any(
            isinstance(m, boss_cls) and m.is_alive for m in floor.mobs.values()
        )
        if has_alive_boss:
            floor.boss_dead_ticks = 0
            return

        floor.boss_dead_ticks += 1
        if floor.boss_dead_ticks < BOSS_RESPAWN_TICKS:
            return
        floor.boss_dead_ticks = 0

        # --- Reset locked doors so progression keys work again -----------
        consumed_keys = []
        for item in list(floor.items.values()):
            if isinstance(item, Key) and getattr(item, "key_id", None) in floor.locked_doors:
                consumed_keys.append(item)
        for item in consumed_keys:
            del floor.items[item.id]

        # --- Spawn the boss on a valid tile ------------------------------
        tiles = _empty_floor_tiles(floor, active_players)
        if not tiles:
            return
        x, y = random.choice(tiles)
        boss = boss_cls(
            id=str(uuid.uuid4()),
            pos=Position(x=x, y=y),
            faction=Faction.DUNGEON,
        )
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
            entry["ticks_left"] -= 1
            if entry["ticks_left"] > 0:
                remaining.append(entry)
                continue
            self._spawn_chest_with_key(floor, floor_id, entry["chest_type"], active_players)
        floor.chest_respawn_queue = remaining

    def _spawn_chest_with_key(self, floor: FloorState, floor_id: int,
                              chest_type: str, active_players: List[Player]) -> None:
        from app.engine.entities.item_union import Chest as ChestCls

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
        self.add_event("PLAY_SOUND", {"sound": "UNLOCK"}, floor_id=floor_id)
