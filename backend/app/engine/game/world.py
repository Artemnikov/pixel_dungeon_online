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
"""World interaction for GameInstance: searching, locked doors, and traps.

Reveals hidden doors/traps around a searching player, consumes keys to open
locked doors, and resolves trap triggers when a player steps onto one.
"""

import random
import time
import uuid
from typing import List, Optional, Tuple

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import (
    Armor, CharacterClass, Item, Key, Player, Position, make_named_melee_weapon,
)
from app.engine.entities.base import DwarfToken
from app.engine.entities.mobs import Imp, Shopkeeper
from app.engine.entities.quest_bosses import FetidRat, Ghost, GnollTrickster, GreatCrab
from app.engine.entities.weapon_defs import WEP_TIER_ORDER
from app.engine.game.floor_state import FloorState
from app.engine.game.constants import KEY_TIME_TO_UNLOCK

_FIRE_CARDINALS = [(0, -1), (1, 0), (0, 1), (-1, 0)]

# Ghost.java messages_en.properties (actors.mobs.npcs.ghost.*) -- markup
# (_italics_) stripped, the DriedRose lost-item hook in the reward text
# dropped (separate unimplemented quest).
_GHOST_INTRO_TEXT = {
    1: ("Hello {name}... Once I was like you - strong and confident... But I was slain by a foul "
        "beast... I can't leave this place... Not until I have my revenge... Slay the fetid rat, "
        "that has taken my life...\n\nIt stalks this floor... Spreading filth everywhere... "
        "Beware its cloud of stink and corrosive bite, the acid dissolves in water..."),
    2: ("Hello {name}... Once I was like you - strong and confident... But I was slain by a devious "
        "foe... I can't leave this place... Not until I have my revenge... Slay the gnoll trickster, "
        "that has taken my life...\n\nIt is not like the other gnolls... It hides and uses thrown "
        "weapons... Beware its poisonous and incendiary darts, don't attack from a distance..."),
    3: ("Hello {name}... Once I was like you - strong and confident... But I was slain by an ancient "
        "creature... I can't leave this place... Not until I have my revenge... Slay the great crab, "
        "that has taken my life...\n\nIt is unnaturally old... With a massive single claw and a "
        "thick shell... Beware its claw, you must surprise the crab or it will block with it..."),
}
_GHOST_REMINDER_TEXT = {
    1: "Please... Help me... Slay the abomination...\n\nFight it near water... Avoid the stench...",
    2: "Please... Help me... Slay the trickster...\n\nDon't let it hit you... Get near to it...",
    3: "Please... Help me... Slay the Crustacean...\n\nIt will always block... When it sees you coming...",
}
_GHOST_REWARD_TEXT = (
    "Please take one of these items, they are useless to me now... "
    "Maybe they will help you in your journey..."
)
_GHOST_BOSS_CLASSES = {1: FetidRat, 2: GnollTrickster, 3: GreatCrab}
_GHOST_ARMOR_NAMES = {2: "Leather Armor", 3: "Mail Armor", 4: "Scale Armor", 5: "Plate Armor"}
_GHOST_ARMOR_STR_REQ = {2: 12, 3: 14, 4: 16, 5: 18}


def _random_free_cell(floor: FloorState) -> Optional[Tuple[int, int]]:
    """Mirrors Dungeon.level.randomRespawnCell(Char) in spirit (a passable,
    non-solid, unoccupied cell) without the full FOV-exclusion machinery --
    plain retry sampling is good enough for a one-off quest-boss spawn."""
    if not floor.flags:
        return None
    occupied = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
    for _ in range(60):
        x = random.randint(0, floor.width - 1)
        y = random.randint(0, floor.height - 1)
        if floor.flags.passable[y][x] and not floor.flags.solid[y][x] and (x, y) not in occupied:
            return (x, y)
    return None


def _make_ghost_reward_item(quest, choice: str) -> Optional[Item]:
    """Materializes the weapon/armor GhostQuestState rolled at spawn time --
    deferred until claim so the hidden reward never leaks early."""
    if choice == "weapon" and quest.weapon_tier_category is not None:
        name = WEP_TIER_ORDER[quest.weapon_tier_category][quest.weapon_item_index]
        return make_named_melee_weapon(
            name, level=quest.item_level, level_known=True, cursed=False, id=str(uuid.uuid4()),
        )
    if choice == "armor" and quest.armor_tier is not None:
        tier = quest.armor_tier
        return Armor(
            id=str(uuid.uuid4()), name=_GHOST_ARMOR_NAMES[tier], tier=tier,
            strength_requirement=_GHOST_ARMOR_STR_REQ[tier],
            level=quest.item_level, level_known=True, cursed=False,
        )
    return None


def _spawn_trap_fire(floor: FloorState, cx: int, cy: int, radius: int, strength: int) -> None:
    blob_id = f"fire_trap_{cx}_{cy}"
    cells = set()
    volume = {}
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                tile = floor.grid[ny][nx]
                if tile == TileType.FLOOR_WATER:
                    continue
                can_burn = (floor.flags.flamable[ny][nx] if floor.flags else False)
                can_burn = can_burn or tile in (TileType.FLOOR, TileType.EMPTY_DECO)
                if can_burn or tile not in (TileType.WALL, TileType.VOID):
                    cells.add((nx, ny))
                    volume[(nx, ny)] = strength
    if cells:
        floor.blob_areas[blob_id] = {"type": "fire", "cells": cells, "volume": volume}


def _spawn_blazing_trap_fire(floor: FloorState, cx: int, cy: int) -> None:
    blob_id = f"blazing_trap_{cx}_{cy}"
    cells = set()
    volume = {}
    visited = set()
    queue = [(cx, cy, 0)]
    while queue:
        nx, ny, dist = queue.pop(0)
        if (nx, ny) in visited or dist > 2:
            continue
        visited.add((nx, ny))
        if not (0 <= nx < floor.width and 0 <= ny < floor.height):
            continue
        tile = floor.grid[ny][nx]
        if tile in (TileType.WALL, TileType.VOID, TileType.FLOOR_WATER):
            continue
        if dist > 0:
            cells.add((nx, ny))
            volume[(nx, ny)] = 5
        for dx, dy in _FIRE_CARDINALS:
            queue.append((nx + dx, ny + dy, dist + 1))
    if cells:
        floor.blob_areas[blob_id] = {"type": "fire", "cells": cells, "volume": volume}
class WorldInteractionMixin:
    def handle_mob_death(self, mob, floor: FloorState, floor_id: int) -> None:
        """Boss-specific on-death drops, called at every mob-death site.

        The Goo drops the key that unlocks the sealed arena exit (SPD Goo.die
        drops a WornKey). Regular loot (goo blobs) is handled by roll_drops; the
        key is dropped here because it needs the floor-specific lock id, and it
        must drop no matter how Goo died (melee or bleed) so progression can't
        soft-lock."""
        from app.engine.entities.base import DwarfToken
        from app.engine.entities.mobs import DM300, Golem, Goo, Monk, Necromancer, Pylon, Skeleton, Tengu, YogDzewa

        # Imp.Quest.process(): once the quest is given (and not yet
        # completed), killing a Monk (alternative) or Golem (!alternative)
        # anywhere in the dungeon (except floor 20) drops a DwarfToken.
        quest = self.run_state.imp_quest
        if quest.given and not quest.completed and floor_id != 20:
            wanted = Monk if quest.alternative else Golem
            if isinstance(mob, wanted):
                token = DwarfToken(id=str(uuid.uuid4()), pos=Position(x=mob.pos.x, y=mob.pos.y))
                floor.items[token.id] = token

        # Ghost.Quest.process(): called directly from each quest-boss's
        # die() override in the original (FetidRat/GnollTrickster/GreatCrab),
        # gated by depth == the floor the quest was given on.
        ghost_quest = self.run_state.ghost_quest
        if ghost_quest.boss_id and mob.id == ghost_quest.boss_id and ghost_quest.process(floor_id):
            self.add_event("MESSAGE", {"text": "Thank you... come find me..."}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "GHOST"}, floor_id=floor_id)

        # CavesBossLevel.eliminatePylon -> DM300.loseSupercharge: when an
        # activated Pylon dies, DM300 becomes vulnerable again. No
        # chain-activation of another pylon.
        if isinstance(mob, Pylon):
            for other in floor.mobs.values():
                if isinstance(other, DM300):
                    other.supercharged = False
                    break

        # Skeleton explosion: play bones sound on death (SPD Skeleton.die)
        if isinstance(mob, Skeleton):
            self.add_event("PLAY_SOUND", {"sound": "BONES"}, floor_id=floor_id)

        # GhostHeroMob death: clear ghost_id on the owner's DriedRose so
        # the rose can be recharged and re-summoned.
        from app.engine.entities.base import DriedRose
        from app.engine.entities.mobs import GhostHeroMob
        if isinstance(mob, GhostHeroMob) and mob.owner_id:
            owner = self.players.get(mob.owner_id)
            if owner:
                for item in owner.belongings.all_items():
                    if isinstance(item, DriedRose) and item.ghost_id == mob.id:
                        item.ghost_id = None
                        break

        # Necromancer.die(): kill the linked NecroSkeleton (mob.die already
        # zeroed its HP); emit DEATH so the frontend plays its death animation.
        if isinstance(mob, Necromancer) and mob.my_skeleton_id:
            skeleton = floor.mobs.get(mob.my_skeleton_id)
            if skeleton and not skeleton.is_alive:
                self.add_event("DEATH", {"target": skeleton.id}, floor_id=floor_id)

        # Tengu (floor 10): award base score + check badge qualification
        if isinstance(mob, Tengu):
            self.boss_scores[1] += 2000
            if self.qualified_for_boss_challenge:
                self.add_event("TENGU_BADGE_QUALIFIED", {}, floor_id=floor_id)
            self.add_event("BOSS_SLAIN", {"mob": mob.id, "depth": floor_id, "badge_image": 48}, floor_id=floor_id)
            return

        if isinstance(mob, YogDzewa):
            key_id = next(iter(floor.locked_doors.values()), "goo_door")
            if not any(isinstance(i, Key) and getattr(i, "key_id", None) == key_id
                       for i in floor.items.values()):
                key = Key(
                    id=str(uuid.uuid4()),
                    name="Worn Key",
                    pos=Position(x=mob.pos.x, y=mob.pos.y),
                    key_id=key_id,
                )
                floor.items[key.id] = key
            self.add_event("PLAY_SOUND", {"sound": "BOSS"}, floor_id=floor_id)
            return

        if not isinstance(mob, Goo):
            return
        key_id = next(iter(floor.locked_doors.values()), "goo_door")
        # Don't double-drop if the boss death is processed from two sites.
        if any(isinstance(i, Key) and getattr(i, "key_id", None) == key_id
               for i in floor.items.values()):
            return
        key = Key(
            id=str(uuid.uuid4()),
            name="Worn Key",
            pos=Position(x=mob.pos.x, y=mob.pos.y),
            key_id=key_id,
        )
        floor.items[key.id] = key
        self.add_event("PLAY_SOUND", {"sound": "BOSS"}, floor_id=floor_id)
        self.add_event("BOSS_SLAIN", {"mob": mob.id, "depth": floor_id, "badge_image": 15}, floor_id=floor_id)
        self._goo_unseal_entrance(floor, floor_id)
        self.boss_scores[0] += 1000
        if self.qualified_for_boss_challenge:
            self.add_event("GOO_BADGE_QUALIFIED", {}, floor_id=floor_id)
    def search(self, player_id: str):
        player = self.players.get(player_id)
        if not player:
            return

        floor = self._get_or_create_floor(player.floor_id)
        patches: List[dict] = []
        # Every in-bounds cell scanned this search, so the client can sweep a
        # CheckedCell ring over the whole radius (mirrors the original drawing a
        # CheckedCell on each cell in range, not only the ones that revealed something).
        checked: List[List[int]] = []
        found_secret = False

        wide_search = player.subclass_info.talent_info.level("wide_search")
        distance = 2 if player.class_type == CharacterClass.ROGUE else 1
        circular = False
        if wide_search > 0:
            distance += 1
            circular = wide_search == 1

        for dy in range(-distance, distance + 1):
            for dx in range(-distance, distance + 1):
                if dx == 0 and dy == 0:
                    continue
                if circular and dx * dx + dy * dy > distance * distance:
                    continue
                tx = player.pos.x + dx
                ty = player.pos.y + dy
                if not (0 <= tx < floor.width and 0 <= ty < floor.height):
                    continue

                checked.append([tx, ty])
                pos = (tx, ty)
                if pos in floor.hidden_doors:
                    actual_tile = floor.hidden_doors.pop(pos)
                    floor.grid[ty][tx] = actual_tile
                    patches.append({"x": tx, "y": ty, "tile": actual_tile})
                    found_secret = True

                trap = floor.traps.get(pos)
                if trap and trap.hidden:
                    trap.hidden = False
                    found_secret = True
                    if floor.grid[ty][tx] == TileType.SECRET_TRAP:
                        floor.grid[ty][tx] = TileType.TRAP
                        patches.append({"x": tx, "y": ty, "tile": TileType.TRAP})

        if patches:
            # Tile mutations changed the grid — refresh derived flag maps
            # so LOS / pathfinding / openSpace pick up the new state on
            # the next query (a revealed door is now passable + see-through).
            floor.rebuild_flags()
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=player.floor_id)

        # Original plays the SECRET sound whenever a door OR a trap is revealed.
        if found_secret:
            self.add_event("PLAY_SOUND", {"sound": "SECRET"}, player_id=player_id)

        # Searcher-only: drives the operate (hand-raise) animation + the cyan ring
        # sweep on the searching client. x/y is the hero position the rings emanate from.
        self.add_event(
            "SEARCH",
            {
                "player": player_id,
                "x": player.pos.x,
                "y": player.pos.y,
                "cells": checked,
                "revealed_tiles": len(patches),
            },
            player_id=player_id,
        )

    def _try_unlock_locked_door(self, player: Player, floor: FloorState, x: int, y: int) -> bool:
        key_id = floor.locked_doors.get((x, y))
        if not key_id:
            return False

        if not player.remove_key(key_id, floor.floor_id):
            self.add_event("LOCKED", {"player": player.id, "x": x, "y": y}, floor_id=player.floor_id)
            return False

        floor.locked_doors.pop((x, y), None)
        tile = floor.grid[y][x]
        if tile == TileType.LOCKED_EXIT or key_id == "goo_door":
            new_tile = TileType.STAIRS_DOWN
        elif tile == TileType.CRYSTAL_DOOR:
            new_tile = TileType.FLOOR
        else:
            new_tile = TileType.DOOR
        floor.grid[y][x] = new_tile
        # Tile mutated from LOCKED_DOOR to DOOR/STAIRS_DOWN — refresh flag maps
        # so LOS/pathfinding sees the door as passable now.
        floor.rebuild_flags()

        self.add_event("MAP_PATCH", {"tiles": [{"x": x, "y": y, "tile": new_tile}]}, floor_id=player.floor_id)
        self.add_event("UNLOCK", {"player": player.id, "x": x, "y": y}, floor_id=player.floor_id)
        if tile == TileType.CRYSTAL_DOOR:
            self.add_event("PLAY_SOUND", {"sound": "TELEPORT"}, floor_id=player.floor_id)
        else:
            self.add_event("PLAY_SOUND", {"sound": "UNLOCK"}, floor_id=player.floor_id)
        player.action_until = max(player.action_until, time.time() + KEY_TIME_TO_UNLOCK)
        return True

    def _trigger_trap_if_needed(self, floor: FloorState, player: Player, floor_id: int):
        pos = (player.pos.x, player.pos.y)
        trap = floor.traps.get(pos)
        if not trap or not trap.active:
            return

        patches: List[dict] = []
        if trap.hidden:
            trap.hidden = False

        # Any trap tile -> INACTIVE_TRAP on trigger
        tile = floor.grid[player.pos.y][player.pos.x]
        if tile in (TileType.SECRET_TRAP, TileType.TRAP):
            floor.grid[player.pos.y][player.pos.x] = TileType.INACTIVE_TRAP
            patches.append({"x": player.pos.x, "y": player.pos.y, "tile": TileType.INACTIVE_TRAP})

        trap.active = False

        # SPD TenguDartTrap: 8 poison damage (15 on challenge, but no
        # challenge system yet), plus boss score penalty on floor 10.
        if trap.trap_type == "tengu_dart":
            damage = 8
            dealt = player.take_damage(damage)
            from app.engine.entities.buffs import add_buff
            add_buff(player.buffs, "poison", duration=8.0, level=1, stack_mode="extend")
            self.boss_scores[1] -= 100
            self.qualified_for_boss_challenge = False
        elif trap.trap_type == "burning_trap":
            _spawn_trap_fire(floor, player.pos.x, player.pos.y, 2, 2)
            self.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
            damage = 0
            dealt = 0
        elif trap.trap_type == "blazing_trap":
            _spawn_blazing_trap_fire(floor, player.pos.x, player.pos.y)
            self.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
            damage = 0
            dealt = 0
        else:
            damage = 2
            dealt = player.take_damage(damage)

        if patches:
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)

        self.add_event(
            "TRAP_TRIGGERED",
            {"player": player.id, "trap": trap.trap_type, "damage": dealt},
            floor_id=floor_id,
        )
        if dealt > 0:
            self.add_event("DAMAGE", {"target": player.id, "amount": dealt}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id, source_player_id=player.id)
            if player.hp / max(1, player.get_total_max_hp()) <= 0.3:
                self.add_event("PLAY_SOUND", {"sound": "HEALTH_WARN"}, player_id=player.id)

    # -- Shop / NPC interaction --------------------------------------------

    def _buy_price(self, item, depth: int) -> int:
        # Shopkeeper.sellPrice(): the price the *shop* charges to sell an item
        # to the hero. Greedy 5x markup, scaling with depth.
        identified = item.kind in self.identified_kinds
        return item.value(identified=identified) * 5 * (depth // 5 + 1)

    def _can_sell(self, item, player: Player) -> bool:
        # Shopkeeper.canSell(): must have a positive value, not be a unique
        # non-stackable item, and not be cursed gear currently worn.
        identified = item.kind in self.identified_kinds
        if item.value(identified=identified) <= 0:
            return False
        if item.unique and not item.stackable:
            return False
        if player.belongings.is_equipped(item.id) and item.cursed:
            return False
        return True

    def npc_interact(self, player_id: str, npc_id: str) -> None:
        player = self.players.get(player_id)
        if not player:
            return
        floor = self._get_or_create_floor(player.floor_id)
        npc = floor.mobs.get(npc_id)
        if npc is None or npc.type != "npc":
            return
        if max(abs(npc.pos.x - player.pos.x), abs(npc.pos.y - player.pos.y)) > 1:
            return

        if isinstance(npc, Shopkeeper):
            stock = [
                self._serialize_floor_item(i)
                for i in floor.items.values()
                if i.for_sale and i.pos and max(abs(i.pos.x - npc.pos.x), abs(i.pos.y - npc.pos.y)) <= 1
            ]
            for item_dict in stock:
                source_item = floor.items.get(item_dict["id"])
                identified = source_item.kind in self.identified_kinds
                item_dict["value"] = self._buy_price(source_item, player.floor_id)
                item_dict["identified"] = identified
            self.add_event(
                "SHOP_OPEN",
                {"player": player.id, "npc": npc_id, "stock": stock, "gold": player.gold},
                player_id=player_id,
            )

        elif isinstance(npc, Imp):
            quest = self.run_state.imp_quest
            if not quest.given:
                quest.given = True
                quest.completed = False
                target = "Monks" if quest.alternative else "Golems"
                text = (
                    "Psst! Hey, "
                    f"{player.name}! I've lost a stash of tokens to the "
                    f"{target} around here. Bring me 5 of them"
                    + ("" if quest.alternative else " (4 will do)")
                    + " and I'll reward you handsomely."
                )
                self.add_event(
                    "IMP_DIALOGUE",
                    {"player": player.id, "npc": npc_id, "text": text, "can_claim": False},
                    player_id=player_id,
                )
            else:
                tokens_item = next(
                    (i for i in player.inventory if isinstance(i, DwarfToken)), None
                )
                tokens = tokens_item.quantity if tokens_item else 0
                required = 5 if quest.alternative else 4
                if tokens >= required:
                    self.add_event(
                        "IMP_DIALOGUE",
                        {
                            "player": player.id, "npc": npc_id,
                            "text": "You found them! Here, take this as thanks.",
                            "can_claim": True, "tokens": tokens,
                        },
                        player_id=player_id,
                    )
                else:
                    target = "Monks" if quest.alternative else "Golems"
                    self.add_event(
                        "IMP_DIALOGUE",
                        {
                            "player": player.id, "npc": npc_id,
                            "text": f"Still looking for those tokens? Check the {target}.",
                            "can_claim": False, "tokens": tokens,
                        },
                        player_id=player_id,
                    )

        elif isinstance(npc, Ghost):
            quest = self.run_state.ghost_quest
            if not quest.given:
                boss_cls = _GHOST_BOSS_CLASSES[quest.quest_type]
                boss_pos = _random_free_cell(floor)
                if boss_pos is None:
                    return
                boss = boss_cls(id=str(uuid.uuid4()), pos=Position(x=boss_pos[0], y=boss_pos[1]))
                floor.mobs[boss.id] = boss
                quest.given = True
                quest.boss_id = boss.id
                self.add_event(
                    "GHOST_DIALOGUE",
                    {
                        "player": player.id, "npc": npc_id,
                        "text": _GHOST_INTRO_TEXT[quest.quest_type].format(name=player.name),
                        "can_claim": False,
                    },
                    player_id=player_id,
                )
            elif not quest.processed:
                self.add_event(
                    "GHOST_DIALOGUE",
                    {
                        "player": player.id, "npc": npc_id,
                        "text": _GHOST_REMINDER_TEXT[quest.quest_type],
                        "can_claim": False,
                    },
                    player_id=player_id,
                )
            else:
                weapon = _make_ghost_reward_item(quest, "weapon")
                armor = _make_ghost_reward_item(quest, "armor")
                self.add_event(
                    "GHOST_DIALOGUE",
                    {
                        "player": player.id, "npc": npc_id,
                        "text": _GHOST_REWARD_TEXT,
                        "can_claim": True,
                        "weapon": self._serialize_floor_item(weapon) if weapon else None,
                        "armor": self._serialize_floor_item(armor) if armor else None,
                    },
                    player_id=player_id,
                )

    def shop_buy(self, player_id: str, npc_id: str, item_id: str) -> None:
        player = self.players.get(player_id)
        if not player:
            return
        floor = self._get_or_create_floor(player.floor_id)
        npc = floor.mobs.get(npc_id)
        if npc is None or not isinstance(npc, Shopkeeper):
            return
        if max(abs(npc.pos.x - player.pos.x), abs(npc.pos.y - player.pos.y)) > 1:
            return

        item = floor.items.get(item_id)
        if item is None or not item.for_sale:
            return
        price = self._buy_price(item, player.floor_id)
        if player.gold < price:
            return
        item.for_sale = False
        item.pos = None
        if not player.add_to_inventory(item):
            item.for_sale = True
            item.pos = Position(x=npc.pos.x, y=npc.pos.y)
            return

        player.gold -= price
        del floor.items[item_id]
        self.add_event(
            "SHOP_BUY",
            {"player": player.id, "item": item.id, "price": price},
            floor_id=player.floor_id, source_player_id=player.id,
        )

    def shop_sell(self, player_id: str, item_id: str) -> None:
        player = self.players.get(player_id)
        if not player:
            return
        item = player.belongings.get_item(item_id)
        if item is None or not self._can_sell(item, player):
            return

        if player.belongings.is_equipped(item.id):
            for slot in ("weapon", "armor", "artifact", "misc", "ring"):
                if getattr(player.belongings, slot) is not None and getattr(player.belongings, slot).id == item.id:
                    setattr(player.belongings, slot, None)
                    break
            detached = item
        else:
            detached = player.belongings.backpack.detach(item.id)
        if detached is None:
            return

        identified = detached.kind in self.identified_kinds
        price = detached.value(identified=identified)
        player.gold += price
        player.quickslot.clear_item(detached.id)
        self.add_event(
            "SHOP_SELL",
            {"player": player.id, "item": detached.id, "price": price},
            floor_id=player.floor_id, source_player_id=player.id,
        )

    # -- Imp quest -----------------------------------------------------------

    def _spawn_imp_shop(self, floor: FloorState) -> None:
        """ImpShopRoom.spawnShop(): places the Shopkeeper + the stock decided
        at floor-20 levelgen time, once Imp.Quest is completed and floor 20
        already exists (the common case, since the alternative=Monk variant
        completes after Halls floors, well after floor 20 was generated)."""
        room = floor.generation_meta.get("imp_shop_room")
        if not room or floor.generation_meta.get("imp_shop_spawned"):
            return
        floor.generation_meta["imp_shop_spawned"] = True

        left, top, right, bottom = room["left"], room["top"], room["right"], room["bottom"]
        cx, cy = (left + right) // 2, (top + bottom) // 2
        shopkeeper = Shopkeeper(id=str(uuid.uuid4()), pos=Position(x=cx, y=cy))
        floor.mobs[shopkeeper.id] = shopkeeper

        # ShopRoom.placeItems(): clockwise spiral from the entrance, inset by
        # one ring at a time once the spiral returns to the entrance.
        ex, ey = room["entrance"]
        if ey == top:
            ey += 1
        elif ey == bottom:
            ey -= 1
        elif ex == left:
            ex += 1
        else:
            ex -= 1

        cur_x, cur_y = ex, ey
        inset = 1

        def step(x: int, y: int) -> tuple:
            if x == left + inset and y != top + inset:
                return x, y - 1
            if y == top + inset and x != right - inset:
                return x + 1, y
            if x == right - inset and y != bottom - inset:
                return x, y + 1
            return x - 1, y

        def occupied(x: int, y: int) -> bool:
            if any(m.pos.x == x and m.pos.y == y for m in floor.mobs.values()):
                return True
            return any(i.pos and i.pos.x == x and i.pos.y == y for i in floor.items.values())

        remaining = list(room["items"])
        while remaining:
            cur_x, cur_y = step(cur_x, cur_y)

            if (cur_x, cur_y) == (ex, ey):
                if ey == top + inset:
                    ey += 1
                elif ey == bottom - inset:
                    ey -= 1
                if ex == left + inset:
                    ex += 1
                elif ex == right - inset:
                    ex -= 1
                inset += 1

                if inset > (min(right - left + 1, bottom - top + 1) - 3) // 2:
                    break

                cur_x, cur_y = step(ex, ey)

            if occupied(cur_x, cur_y):
                continue

            item = remaining.pop(0)
            placed = item.model_copy(update={
                "id": str(uuid.uuid4()), "pos": Position(x=cur_x, y=cur_y), "for_sale": True,
            })
            floor.items[placed.id] = placed

        # Leftover items (spiral ran out of room) go anywhere free.
        for x in range(left, right + 1):
            for y in range(top, bottom + 1):
                if not remaining:
                    break
                if floor.grid[y][x] == TileType.FLOOR and not occupied(x, y):
                    item = remaining.pop(0)
                    placed = item.model_copy(update={
                        "id": str(uuid.uuid4()), "pos": Position(x=x, y=y), "for_sale": True,
                    })
                    floor.items[placed.id] = placed
            if not remaining:
                break

    def imp_claim_reward(self, player_id: str, npc_id: str) -> None:
        player = self.players.get(player_id)
        if not player:
            return
        floor = self._get_or_create_floor(player.floor_id)
        npc = floor.mobs.get(npc_id)
        if npc is None or not isinstance(npc, Imp):
            return
        if max(abs(npc.pos.x - player.pos.x), abs(npc.pos.y - player.pos.y)) > 1:
            return

        quest = self.run_state.imp_quest
        if not quest.given or quest.completed:
            return

        tokens_item = next((i for i in player.inventory if isinstance(i, DwarfToken)), None)
        tokens = tokens_item.quantity if tokens_item else 0
        required = 5 if quest.alternative else 4
        if tokens < required:
            return

        # WndImp.takeReward(): remove all tokens, identify the reward (level
        # only -- cursed_known stays False, hidden curse), grant or drop it.
        player.belongings.backpack.detach_all(tokens_item.id)
        player.quickslot.clear_item(tokens_item.id)

        reward = quest.reward.model_copy(update={"id": str(uuid.uuid4())})
        if not player.add_to_inventory(reward):
            reward.pos = Position(x=npc.pos.x, y=npc.pos.y)
            floor.items[reward.id] = reward

        # Imp.flee(): the Imp despawns once the quest is resolved.
        del floor.mobs[npc.id]
        quest.completed = True

        self.add_event("DEATH", {"target": npc.id}, floor_id=player.floor_id)
        self.add_event(
            "IMP_REWARD",
            {"player": player.id, "npc": npc_id, "item": reward.id},
            player_id=player_id,
        )

        # ImpShopRoom.onLevelLoad(): if floor 20 already exists, spawn the
        # shop immediately (otherwise paint() handles it when floor 20 is
        # first generated).
        floor20 = self.floors.get(20)
        if floor20 is not None:
            self._spawn_imp_shop(floor20)

    # -- Ghost quest (sewers depths 2-4) --------------------------------------

    def ghost_claim_reward(self, player_id: str, npc_id: str, choice: str) -> None:
        player = self.players.get(player_id)
        if not player:
            return
        floor = self._get_or_create_floor(player.floor_id)
        npc = floor.mobs.get(npc_id)
        if npc is None or not isinstance(npc, Ghost):
            return
        if max(abs(npc.pos.x - player.pos.x), abs(npc.pos.y - player.pos.y)) > 1:
            return

        quest = self.run_state.ghost_quest
        if not quest.given or not quest.processed:
            return

        reward = _make_ghost_reward_item(quest, choice)
        if reward is None:
            return

        if not player.add_to_inventory(reward):
            reward.pos = Position(x=npc.pos.x, y=npc.pos.y)
            floor.items[reward.id] = reward

        # WndSadGhost.selectReward(): the ghost says farewell and despawns
        # once the player picks a reward.
        del floor.mobs[npc.id]
        quest.weapon_tier_category = None
        quest.armor_tier = None

        self.add_event("DEATH", {"target": npc.id}, floor_id=player.floor_id)
        self.add_event(
            "GHOST_REWARD",
            {"player": player.id, "npc": npc_id, "item": reward.id},
            player_id=player_id,
        )
