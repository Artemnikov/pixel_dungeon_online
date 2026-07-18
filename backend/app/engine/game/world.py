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
from app.engine.entities.base import Faction, Position
from app.engine.entities.items_consumable import Key
from app.engine.entities.items_equip import Armor, LeatherArmor, MailArmor, PlateArmor, ScaleArmor, make_named_melee_weapon
from app.engine.entities.player import CharacterClass, Item, Player, hurt_warning_sound
from app.engine.entities.items_consumable import CorpseDust, DwarfToken
from app.engine.entities.mobs import Imp, Shopkeeper
from app.engine.entities.quest_bosses import FetidRat, Ghost, GnollTrickster, GreatCrab
from app.engine.entities.wandmaker_quest import DustWraith, NewbornFireElemental, Wandmaker
from app.engine.entities.wandmaker_quest_items import CeremonialCandle, Embers, RotberrySeed
from app.engine.entities.weapon_defs import WEP_TIER_ORDER
from app.engine.entities.buffs import remove_buff
from app.engine.game.floor_state import FloorState
from app.engine.game.constants import KEY_TIME_TO_UNLOCK
from app.engine.game.spd_adapter import build_wand_item

_FIRE_CARDINALS = [(0, -1), (1, 0), (0, 1), (-1, 0)]
_ELECTRIC_CARDINALS = [(0, -1), (1, 0), (0, 1), (-1, 0)]


def _electric_reachable_cells(floor: FloorState, cx: int, cy: int, max_dist: int):
    """BFS returning set of (x,y) reachable within max_dist cardinal steps, avoiding solids."""
    from collections import deque
    visited = {(cx, cy)}
    q = deque([(cx, cy, 0)])
    while q:
        x, y, d = q.popleft()
        if d >= max_dist:
            continue
        for dx, dy in _ELECTRIC_CARDINALS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                if (nx, ny) not in visited and not floor.flags.solid[ny][nx]:
                    visited.add((nx, ny))
                    q.append((nx, ny, d + 1))
    return visited

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

# Wandmaker.java messages_en.properties (actors.mobs.npcs.wandmaker.*) --
# markup (_italics_) stripped. Types 1 (Corpse Dust) and 3 (Rotberry) are
# implemented; type 2 (Ceremonial Candle) is still deferred -- see
# wandmaker_quest.py's module docstring.
_WANDMAKER_INTRO_BY_CLASS = {
    "warrior": ("Oh, hello there! What a pleasant surprise to meet a warrior from the north "
                "in such a depressing place! You must have travelled quite far to get here. "
                "If you're looking for adventure, I may have a task for you."),
    "rogue": ("Oh Goodness, you startled me! I haven't met a bandit from this place that "
              "still has his sanity, so you must be from the surface! If you're up to "
              "helping a stranger out, I may have a task for you."),
    "mage": ("Oh, hello {name}! I heard there was some ruckus regarding you and the wizards "
             "institute? Oh never mind, I never liked those stick-in-the-muds anyway. If "
             "you're willing, I may have a task for you."),
    "huntress": ("Oh, hello miss! A friendly face is a pleasant surprise down here isn't it? "
                 "In fact, I swear I've seen your face before, but I can't put my finger on "
                 "it... Oh never mind, if you're here for adventure, I may have a task for you."),
    "duelist": ("Oh, hello miss! What a pleasant surprise to meet a hero in such a depressing "
                "place! If you're up to helping an old man out, I may have a task for you."),
    "cleric": ("Oh, hello Your Highness! What a pleasant surprise to meet you in such a "
               "depressing place! I hate to impose, but I may have a task for you."),
}
_WANDMAKER_INTRO_1 = (
    "\n\nI came here to find a rare ingredient for a wand, but I've gotten myself lost, and "
    "my magical shield is weakening. I'll need to leave soon, but can't bear to go without "
    "getting what I came for."
)
_WANDMAKER_INTRO_DUST = (
    "I'm looking for some corpse dust. It's a special kind of cursed bone meal that usually "
    "shows up in places like this. There should be a barricaded room around here somewhere, "
    "I'm sure some dust will turn up there. Do be careful though, the curse the dust carries "
    "is quite potent, get back to me as fast as you can and I'll cleanse it for you."
)
_WANDMAKER_INTRO_BERRY = (
    "The old warden of this prison kept a rotberry plant, and I'm after one of its seeds. The "
    "plant has probably gone wild by now though, so getting it to give up a seed might be "
    "tricky. Its garden should be somewhere around here. Try to keep away from its vine "
    "lashers if you want to stay in one piece. Using fire might be tempting but please don't, "
    "you'll kill the plant and destroy its seeds."
)
_WANDMAKER_INTRO_EMBER = (
    "I'm looking for some fresh embers from a newborn fire elemental. Elementals usually pop "
    "up when a summoning ritual isn't controlled, so just find some candles and a ritual site "
    "and I'm sure you can get one to pop up. You'll want to avoid boxing yourself in while "
    "fighting it though, or you could keep some sort of freezing item handy. Newborn Elementals "
    "are pretty powerful and chaotic, but they can't stand the cold."
)
_WANDMAKER_INTRO_2 = (
    "\n\nIf you can get that for me, I'll be happy to pay you with one of my finely crafted "
    "wands! I brought two with me, so you can take whichever one you prefer."
)
_WANDMAKER_INTRO_BY_TYPE = {1: _WANDMAKER_INTRO_DUST, 2: _WANDMAKER_INTRO_EMBER, 3: _WANDMAKER_INTRO_BERRY}
_WANDMAKER_REMINDER_DUST = "Any luck with corpse dust, {name}? Look for some barricades."
_WANDMAKER_REMINDER_BERRY = "Any luck with a Rotberry seed, {name}? Look for a room filled with vegetation."
_WANDMAKER_REMINDER_EMBER = "Any luck with those embers, {name}? You'll need to find four candles and the ritual site."
_WANDMAKER_REMINDER_BY_TYPE = {1: _WANDMAKER_REMINDER_DUST, 2: _WANDMAKER_REMINDER_EMBER, 3: _WANDMAKER_REMINDER_BERRY}
_WANDMAKER_REWARD_DUST = (
    "Oh, I see you have the dust! Don't worry about the wraiths, I can deal with them. As I "
    "promised, you can choose one of my high quality wands."
)
_WANDMAKER_REWARD_BERRY = (
    "Oh, I see you have the berry! I do hope the rotberry plant didn't trouble you too much. "
    "As I promised, you can choose one of my high quality wands."
)
_WANDMAKER_REWARD_EMBER = (
    "Oh, I see you have the embers! I do hope the fire elemental wasn't too much trouble. As I "
    "promised, you can choose one of my high quality wands."
)
_WANDMAKER_REWARD_BY_TYPE = {1: _WANDMAKER_REWARD_DUST, 2: _WANDMAKER_REWARD_EMBER, 3: _WANDMAKER_REWARD_BERRY}
_WANDMAKER_QUEST_ITEM_BY_TYPE = {1: CorpseDust, 2: Embers, 3: RotberrySeed}


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
        _ARMOR_TYPES = {2: LeatherArmor, 3: MailArmor, 4: ScaleArmor, 5: PlateArmor}
        return _ARMOR_TYPES[tier](
            id=str(uuid.uuid4()), level=quest.item_level, level_known=True, cursed=False,
        )
    return None


def _make_wandmaker_wand(quest, choice: str) -> Optional[Item]:
    """Materializes the Wandmaker reward WandmakerQuestState rolled at NPC-
    spawn time -- deferred until claim, same reasoning as
    _make_ghost_reward_item. wand1.cursed/upgrade() in Java forces cursed
    false regardless of the natural roll -- see WandmakerQuestState."""
    if choice == "wand1" and quest.wand1_index is not None:
        return build_wand_item(quest.wand1_index, quest.wand1_level,
                                cursed=False, cursed_known=False)
    if choice == "wand2" and quest.wand2_index is not None:
        return build_wand_item(quest.wand2_index, quest.wand2_level,
                                cursed=False, cursed_known=False)
    return None


def _spawn_trap_electricity(floor: FloorState, cx: int, cy: int, radius: int, strength: int) -> None:
    """Seed an electricity blob covering all cells within radius.
    radius=1 uses square (NEIGHBOURS9 matching SPD); radius>1 uses BFS pathfinding."""
    blob_id = f"electric_trap_{cx}_{cy}"
    cells = set()
    volume = {}
    if radius <= 1:
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < floor.width and 0 <= ny < floor.height:
                    if floor.flags and not floor.flags.solid[ny][nx]:
                        cells.add((nx, ny))
                        volume[(nx, ny)] = strength
    else:
        for nx, ny in _electric_reachable_cells(floor, cx, cy, radius):
            cells.add((nx, ny))
            volume[(nx, ny)] = strength
    if cells:
        floor.blob_areas[blob_id] = {"type": "electricity", "cells": cells, "volume": volume}


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
def _sacrifice_exp_value(mob) -> int:
    """Port of SacrificialFire.sacrifice()'s per-type exp lookup (same rates
    as Wand of Corruption, except Swarms)."""
    from app.engine.entities.mobs import (
        Bee, Mimic, GoldenMimic, EbonyMimic, CrystalMimic,
        Piranha, PhantomPiranha, Statue, ArmoredStatue, Swarm, TormentedSpirit, Wraith,
    )
    depth = getattr(mob, "floor_level", 1)
    if isinstance(mob, (Statue, ArmoredStatue, Mimic, GoldenMimic, EbonyMimic, CrystalMimic)):
        return 1 + depth
    if isinstance(mob, (Piranha, PhantomPiranha, Bee)):
        return 1 + depth // 2
    if isinstance(mob, (Wraith, TormentedSpirit)):
        return 1 + depth // 3
    if isinstance(mob, Swarm) and mob.exp == 0:
        return 1
    if mob.exp > 0:
        return 1 + mob.exp
    return 0


class WorldInteractionMixin:
    def _process_sacrifice_fire_death(self, mob, floor: FloorState, floor_id: int) -> None:
        """Port of SacrificialFire.sacrifice(): a mob that dies within the
        fire's blast radius (its 3x3 EMBERS block plus one ring of
        NEIGHBOURS9 marking) feeds the room's reward pool; once the pool is
        exhausted the pre-rolled prize drops. Simplified from SPD's
        continuous per-turn Marked-buff tracking to a proximity check taken
        at the moment of death (the fire only marks/consumes on death
        either way, so the outcome matches for the common case of a mob
        dying to a hit landed while adjacent to the fire)."""
        fires = floor.generation_meta.get("sacrifice_fires")
        if not fires:
            return
        for fire in fires:
            if fire["volume"] <= 0:
                continue
            fx, fy = fire["pos"]
            if max(abs(mob.pos.x - fx), abs(mob.pos.y - fy)) > 2:
                continue
            exp_value = _sacrifice_exp_value(mob) * random.randint(2, 3)
            if exp_value <= 0:
                self.add_event("SACRIFICE_UNWORTHY", {"x": mob.pos.x, "y": mob.pos.y}, floor_id=floor_id)
                return
            fire["volume"] -= exp_value
            if fire["volume"] > 0:
                self.add_event("SACRIFICE_FEED", {"x": fx, "y": fy}, floor_id=floor_id)
                return
            from app.engine.game.spd_adapter import _descriptor_to_item
            prize_item = _descriptor_to_item(fire["prize"], fx, fy)
            floor.items[prize_item.id] = prize_item
            self.add_event("SACRIFICE_REWARD", {"x": fx, "y": fy}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
            return

    def handle_mob_death(self, mob, floor: FloorState, floor_id: int) -> None:
        """Boss-specific on-death drops, called at every mob-death site.

        The Goo drops the key that unlocks the sealed arena exit (SPD Goo.die
        drops a WornKey). Regular loot (goo blobs) is handled by roll_drops; the
        key is dropped here because it needs the floor-specific lock id, and it
        must drop no matter how Goo died (melee or bleed) so progression can't
        soft-lock."""
        from app.engine.entities.items_consumable import DwarfToken
        from app.engine.entities.mobs import DM300, Golem, Goo, Monk, Necromancer, Pylon, Skeleton, Tengu, YogDzewa
        from app.engine.entities.wandmaker_quest import NewbornFireElemental, RotHeart
        from app.engine.entities.wandmaker_quest_items import Embers, RotberrySeed

        self._process_sacrifice_fire_death(mob, floor, floor_id)

        # Imp.Quest.process(): once the quest is given (and not yet
        # completed), killing a Monk (alternative) or Golem (!alternative)
        # anywhere in the dungeon (except floor 20) drops a DwarfToken.
        quest = self.run_state.imp_quest
        if quest.given and not quest.completed and floor_id != 20:
            wanted = Monk if quest.alternative else Golem
            if isinstance(mob, wanted):
                token = DwarfToken(id=str(uuid.uuid4()), pos=Position(x=mob.pos.x, y=mob.pos.y))
                floor.items[token.id] = token

        # RotHeart.die(): always drops the Rotberry seed, regardless of how
        # the Wandmaker quest's Rotberry variant is currently tracked.
        if isinstance(mob, RotHeart):
            seed = RotberrySeed(id=str(uuid.uuid4()), pos=Position(x=mob.pos.x, y=mob.pos.y))
            floor.items[seed.id] = seed

        # Elemental.NewbornFireElemental.die(): always drops embers.
        if isinstance(mob, NewbornFireElemental):
            embers = Embers(id=str(uuid.uuid4()), pos=Position(x=mob.pos.x, y=mob.pos.y))
            floor.items[embers.id] = embers

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
        from app.engine.entities.items_artifacts import DriedRose
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
            self.add_event("BOSS_YELL", {"mob": mob.id, "text": "Free at last...",
                                         "x": mob.pos.x, "y": mob.pos.y}, floor_id=floor_id)
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
                if trap and trap.hidden and trap.can_be_searched:
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

        # Tengu cell entrance: any player may pass freely once fight starts.
        if key_id != "tengu_boss" and not player.remove_key(key_id, floor.floor_id):
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

    def _trigger_trap_if_needed(self, floor: FloorState, player, floor_id: int):
        from app.engine.entities.base import Entity as _Entity
        if player.has_buff("levitation"):
            return
        pos = (player.pos.x, player.pos.y)
        trap = floor.traps.get(pos)
        if not trap or not trap.active:
            return

        is_player = isinstance(player, Player)
        patches: List[dict] = []
        if trap.hidden:
            trap.hidden = False

        # Any trap tile -> INACTIVE_TRAP on trigger
        tile = floor.grid[player.pos.y][player.pos.x]
        if tile in (TileType.SECRET_TRAP, TileType.TRAP):
            floor.grid[player.pos.y][player.pos.x] = TileType.INACTIVE_TRAP
            patches.append({"x": player.pos.x, "y": player.pos.y, "tile": TileType.INACTIVE_TRAP})

        trap.active = False

        if trap.trap_type == "tengu_dart":
            damage = 8
            dealt = player.take_damage(damage)
            from app.engine.entities.buffs import add_buff
            add_buff(player.buffs, "poison", duration=8.0, level=1, stack_mode="extend")
            if is_player:
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
        elif trap.trap_type == "shocking_trap":
            _spawn_trap_electricity(floor, player.pos.x, player.pos.y, 1, 10)
            self.add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=floor_id)
            damage = 0
            dealt = 0
        elif trap.trap_type == "storm_trap":
            _spawn_trap_electricity(floor, player.pos.x, player.pos.y, 2, 20)
            self.add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=floor_id)
            damage = 0
            dealt = 0
        elif trap.trap_type in ("toxic_trap", "poison_dart_trap"):
            from app.engine.entities.buffs import add_buff
            from app.engine.game.terrain_effects import _create_gas
            if trap.trap_type == "toxic_trap":
                _create_gas(floor, (player.pos.x, player.pos.y), 4 + floor_id // 3, "toxic_gas")
            else:
                add_buff(player.buffs, "poison", duration=10.0, level=1, stack_mode="extend")
                _create_gas(floor, (player.pos.x, player.pos.y), 2, "toxic_gas")
            self.add_event("PLAY_SOUND", {"sound": "GAS"}, floor_id=floor_id)
            damage = 0
            dealt = 0
        elif trap.trap_type == "chilling_trap":
            from app.engine.game.terrain_effects import _freeze_area
            _freeze_area(floor, (player.pos.x, player.pos.y))
            player.add_buff("chilled", duration=5.0, level=1, stack_mode="extend")
            self.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
            damage = 0
            dealt = 0
        elif trap.trap_type == "frost_trap":
            from app.engine.game.terrain_effects import _freeze_area
            _freeze_area(floor, (player.pos.x, player.pos.y))
            player.add_buff("frozen", duration=5.0, level=1, stack_mode="extend")
            self.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
            damage = 0
            dealt = 0
        elif trap.trap_type == "confusion_trap":
            player.add_buff("vertigo", duration=5.0, level=1, stack_mode="replace")
            self.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
            damage = 0
            dealt = 0
        elif trap.trap_type == "ooze_trap":
            player.add_buff("ooze", duration=10.0, level=1, stack_mode="extend")
            damage = 0
            dealt = 0
        elif trap.trap_type == "corrosion_trap":
            from app.engine.game.terrain_effects import _create_gas
            _create_gas(floor, (player.pos.x, player.pos.y), 1 + floor_id // 4, "corrosive_gas")
            self.add_event("PLAY_SOUND", {"sound": "GAS"}, floor_id=floor_id)
            damage = 0
            dealt = 0
        elif trap.trap_type == "flock_trap":
            self.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
            damage = 0
            dealt = 0
        elif trap.trap_type == "weakening_trap":
            player.add_buff("weakness", duration=10.0, level=1, stack_mode="extend")
            self.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)
            damage = 0
            dealt = 0
        elif trap.trap_type == "gripping_trap":
            _spawn_trap_fire(floor, player.pos.x, player.pos.y, 1, 1)
            self.add_event("PLAY_SOUND", {"sound": "BURNING"}, floor_id=floor_id)
            damage = 0
            dealt = 0
        elif trap.trap_type == "geyser_trap":
            _spawn_trap_electricity(floor, player.pos.x, player.pos.y, 1, 5)
            self.add_event("PLAY_SOUND", {"sound": "LIGHTNING"}, floor_id=floor_id)
            damage = 0
            dealt = 0
        elif trap.trap_type == "explosive_trap":
            damage = max(1, player.hp // 6)
            dealt = player.take_damage(damage)
            self.add_event("PLAY_SOUND", {"sound": "BLAST"}, floor_id=floor_id)
            blast_cells = []
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    blast_cells.append([player.pos.x + ox, player.pos.y + oy])
            self.add_event("BOMB_BLAST", {
                "x": player.pos.x, "y": player.pos.y,
                "kind": "bomb", "cells": blast_cells,
            }, floor_id=floor_id)
            self.add_event("SCREEN_SHAKE", {"intensity": 2, "duration_ms": 300},
                           floor_id=floor_id)
        elif trap.trap_type == "pitfall_trap":
            # SPD PitfallTrap: opens a 3x3 pit around the trap cell; mobs on
            # those cells fall to their death (Chasm.mobFall) and the hero
            # falls to the next floor (Chasm.heroFall). No-op on boss floors
            # or beyond depth 25 (SPD: "the ground is too solid").
            from app.engine.dungeon.spd_levelgen.run_state import is_boss_level
            from app.engine.game.constants import MAX_FLOOR_ID
            dealt = 0
            if is_boss_level(floor_id) or floor_id > 25 or floor_id >= MAX_FLOOR_ID:
                # Too solid — trap triggers but no pit opens.
                if is_player:
                    self.add_event("MESSAGE",
                        {"text": "The ground is too solid for a pitfall trap to work here."},
                        player_id=player.id)
            else:
                # PitfallParticle burst on the 3x3 around the trap cell.
                pit_cells = []
                for ox in (-1, 0, 1):
                    for oy in (-1, 0, 1):
                        cx, cy = player.pos.x + ox, player.pos.y + oy
                        if 0 <= cx < floor.width and 0 <= cy < floor.height:
                            if floor.flags and floor.flags.passable[cy][cx]:
                                pit_cells.append((cx, cy))
                # Emit VFX for the pit opening (reuses LEAF_BURST-style per-cell
                # particle spawn; the client renders a dust/earth burst).
                for cx, cy in pit_cells:
                    self.add_event("LEAF_BURST", {"x": cx, "y": cy}, floor_id=floor_id)
                self.add_event("PLAY_SOUND", {"sound": "SHATTER"}, floor_id=floor_id)

                # Mobs on pit cells fall to their death (Chasm.mobFall).
                for cx, cy in pit_cells:
                    for mob in list(floor.mobs.values()):
                        if mob.is_alive and mob.pos.x == cx and mob.pos.y == cy:
                            if not mob.flying and mob.faction != Faction.PLAYER:
                                mob.is_alive = False
                                self.add_event("MOB_CHASM_FALL",
                                    {"mob": mob.id, "x": cx, "y": cy},
                                    floor_id=floor_id)
                                # DEATH event so the client's death animation
                                # triggers alongside the fall VFX.
                                self.add_event("DEATH", {"target": mob.id},
                                    floor_id=floor_id)
                                self.handle_mob_death(mob, floor, floor_id)

                # Hero falls last (SPD: "process hero falling last").
                if is_player and not player.has_buff("levitation"):
                    # Emit TRAP_TRIGGERED before the fall moves the player to
                    # the next floor (after which floor_id is stale).
                    if patches:
                        self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)
                    self.add_event("TRAP_TRIGGERED",
                        {"player": player.id, "trap": trap.trap_type, "damage": 0,
                         "x": player.pos.x, "y": player.pos.y},
                        floor_id=floor_id)
                    self._perform_chasm_fall(player, floor_id, player.pos.x, player.pos.y)
                    return
                # Non-player entity falls to death in the pit.
                elif not is_player and not player.has_buff("levitation"):
                    player.is_alive = False
                    self.add_event("MOB_CHASM_FALL",
                        {"mob": player.id, "x": player.pos.x, "y": player.pos.y},
                        floor_id=floor_id)
                    self.add_event("DEATH", {"target": player.id}, floor_id=floor_id)
                    self.handle_mob_death(player, floor, floor_id)
        else:
            damage = 2
            dealt = player.take_damage(damage)

        if patches:
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)

        self.add_event(
            "TRAP_TRIGGERED",
            {"player": player.id, "trap": trap.trap_type, "damage": dealt,
             "x": player.pos.x, "y": player.pos.y},
            floor_id=floor_id,
        )
        if dealt > 0:
            self.add_event("DAMAGE", {"target": player.id, "amount": dealt}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id, source_player_id=player.id if is_player else None)
            if is_player:
                warn_sound = hurt_warning_sound(dealt, player.hp, player.get_total_max_hp())
                if warn_sound:
                    self.add_event("PLAY_SOUND", {"sound": warn_sound}, player_id=player.id)

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
                if i.for_sale and i.pos
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

        elif isinstance(npc, Wandmaker):
            quest = self.run_state.wandmaker_quest
            if not quest.given:
                # Wandmaker.interact(): two-part intro (class greeting + task
                # description), shown once. Java splits this into two
                # sequential WndQuest popups (hide() chains to the second) --
                # collapsed into one text block here.
                greeting = _WANDMAKER_INTRO_BY_CLASS.get(player.class_type, "")
                task = _WANDMAKER_INTRO_BY_TYPE.get(quest.quest_type, _WANDMAKER_INTRO_DUST)
                text = (greeting.format(name=player.name) + _WANDMAKER_INTRO_1
                        + task + _WANDMAKER_INTRO_2)
                quest.given = True
                self.add_event(
                    "WANDMAKER_DIALOGUE",
                    {"player": player.id, "npc": npc_id, "text": text, "can_claim": False},
                    player_id=player_id,
                )
            else:
                quest_item_cls = _WANDMAKER_QUEST_ITEM_BY_TYPE.get(quest.quest_type, CorpseDust)
                held = next((i for i in player.inventory if isinstance(i, quest_item_cls)), None)
                if held is not None:
                    wand1 = _make_wandmaker_wand(quest, "wand1")
                    wand2 = _make_wandmaker_wand(quest, "wand2")
                    reward_text = _WANDMAKER_REWARD_BY_TYPE.get(quest.quest_type, _WANDMAKER_REWARD_DUST)
                    self.add_event(
                        "WANDMAKER_DIALOGUE",
                        {
                            "player": player.id, "npc": npc_id,
                            "text": reward_text,
                            "can_claim": True,
                            "wand1": self._serialize_floor_item(wand1) if wand1 else None,
                            "wand2": self._serialize_floor_item(wand2) if wand2 else None,
                        },
                        player_id=player_id,
                    )
                else:
                    reminder_text = _WANDMAKER_REMINDER_BY_TYPE.get(quest.quest_type, _WANDMAKER_REMINDER_DUST)
                    self.add_event(
                        "WANDMAKER_DIALOGUE",
                        {
                            "player": player.id, "npc": npc_id,
                            "text": reminder_text.format(name=player.name),
                            "can_claim": False,
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
        floor20 = self._get_or_create_floor(20)
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

    def wandmaker_claim_reward(self, player_id: str, npc_id: str, choice: str) -> None:
        player = self.players.get(player_id)
        if not player:
            return
        floor = self._get_or_create_floor(player.floor_id)
        npc = floor.mobs.get(npc_id)
        if npc is None or not isinstance(npc, Wandmaker):
            return
        if max(abs(npc.pos.x - player.pos.x), abs(npc.pos.y - player.pos.y)) > 1:
            return

        quest = self.run_state.wandmaker_quest
        if not quest.given:
            return
        quest_item_cls = _WANDMAKER_QUEST_ITEM_BY_TYPE.get(quest.quest_type, CorpseDust)
        held = next((i for i in player.inventory if isinstance(i, quest_item_cls)), None)
        if held is None:
            return

        reward = _make_wandmaker_wand(quest, choice)
        if reward is None:
            return

        player.belongings.backpack.detach(held.id)
        if isinstance(held, CorpseDust):
            # CorpseDust.onDetach()/DustGhostSpawner.dispel(): remove the
            # buff and kill every wraith it spawned -- across all floors,
            # since the player may have changed floors while carrying it (a
            # single-level assumption in the original that doesn't hold
            # here). Rotberry's seed has no such held-item side effect.
            remove_buff(player.buffs, "dust_ghost_spawner")
            for fid, f in self.floors.items():
                for mob_id in [m.id for m in f.mobs.values() if isinstance(m, DustWraith)]:
                    del f.mobs[mob_id]
                    self.add_event("DEATH", {"target": mob_id}, floor_id=fid)

        if not player.add_to_inventory(reward):
            reward.pos = Position(x=npc.pos.x, y=npc.pos.y)
            floor.items[reward.id] = reward

        # Wandmaker.Quest.complete(): wand1/wand2 nulled -- Wandmaker itself
        # does NOT despawn (unlike Ghost), matching Java exactly.
        quest.wand1_index = None
        quest.wand2_index = None

        self.add_event(
            "WANDMAKER_REWARD",
            {"player": player.id, "npc": npc_id, "item": reward.id},
            player_id=player_id,
        )

    def _check_ritual_candles(self, floor_id: int) -> None:
        """CeremonialCandle.checkCandles(): if the 4 cells cardinally
        adjacent to the ritual's center each hold a landed CeremonialCandle,
        consume them and spawn a NewbornFireElemental at (or, if occupied,
        next to) the ritual center, already hunting. Called after any
        CeremonialCandle lands via drop (item_actions.action_drop) or throw
        (movement.perform_ranged_attack) -- mirrors Java's doDrop/onThrow
        both calling checkCandles(). The `aflame` partial-progress visual
        flag is dropped (see CeremonialCandle's docstring) -- purely
        cosmetic, no gameplay effect."""
        quest = self.run_state.wandmaker_quest
        if quest.ritual_pos is None or quest.ritual_floor_id != floor_id:
            return
        floor = self._get_or_create_floor(floor_id)
        width = floor.width
        rx, ry = quest.ritual_pos % width, quest.ritual_pos // width
        cardinals = [(rx, ry - 1), (rx + 1, ry), (rx, ry + 1), (rx - 1, ry)]
        landed = []
        for cx, cy in cardinals:
            item = next(
                (i for i in floor.items.values()
                 if isinstance(i, CeremonialCandle) and i.pos and i.pos.x == cx and i.pos.y == cy),
                None,
            )
            if item is None:
                return
            landed.append(item)

        for item in landed:
            del floor.items[item.id]

        occupied = {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}
        occupied |= {(p.pos.x, p.pos.y) for p in self._players_on_floor(floor_id) if p.is_alive and not p.is_afk}
        diagonals = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))
        candidates = [
            (rx + dx, ry + dy) for dx, dy in diagonals
            if 0 <= rx + dx < floor.width and 0 <= ry + dy < floor.height
            and (rx + dx, ry + dy) not in occupied
            and floor.flags and not floor.flags.solid[ry + dy][rx + dx]
        ]
        ex, ey = random.choice(candidates) if candidates else (rx, ry)

        elemental = NewbornFireElemental(id=str(uuid.uuid4()), pos=Position(x=ex, y=ey), ai_state="hunting")
        floor.mobs[elemental.id] = elemental
