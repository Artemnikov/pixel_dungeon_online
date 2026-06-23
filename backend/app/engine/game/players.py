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
"""Player lifecycle for GameInstance: join, floor traversal, and death.

Handles starting-gear setup per class, stair-based floor changes, and the SPD
death sequence (scatter the backpack, drop a grave).
"""

import random
import uuid
from typing import List, Optional, Tuple

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import (
    Amulet,
    Armor,
    Belongings,
    Bow,
    CharacterClass,
    CloakOfShadows,
    Dagger,
    Faction,
    Item,
    Player,
    Position,
    PotionOfLiquidFlame,
    QuickSlot,
    Ration,
    ScrollOfIdentify,
    ScrollOfUpgrade,
    Staff,
    Stone,
    ThrowableDagger,
    VelvetPouch,
    WandOfMagicMissile,
    Waterskin,
    Weapon,
    WornShortsword,
)
from app.engine.entities.buffs import add_buff
from app.engine.entities.item_catalog import make_catalog_item
from app.engine.game.constants import MAX_FLOOR_ID
from app.engine.game.floor_state import FloorState


class PlayersMixin:
    def add_player(self, player_id: str, name: str, class_type: str = CharacterClass.WARRIOR, is_admin: bool = False) -> Player:
        floor = self._get_or_create_floor(1)
        spawn_pos = self._get_stairs_pos(TileType.STAIRS_UP, floor_id=floor.floor_id)

        self.player_count += 1

        # Starting gear goes straight into the relevant equip slots (SPD-style:
        # equipped items live in Belongings, not the backpack).
        belongings = Belongings()

        class_starting_quickslots = []

        if class_type == CharacterClass.WARRIOR:
            belongings.weapon = WornShortsword(
                id=str(uuid.uuid4()),
            )
            belongings.armor = Armor(
                id=str(uuid.uuid4()),
                name="Cloth Armor",
                tier=1,
                strength_requirement=10,
            )
            stones = Stone(
                id=str(uuid.uuid4()),
                quantity=3,
                level_known=True,
                cursed_known=True,
            )
            belongings.backpack.collect(stones)
            class_starting_quickslots.append((0, stones))

        elif class_type == CharacterClass.MAGE:
            wand = WandOfMagicMissile(
                id=str(uuid.uuid4()),
                charges=4,
                max_charges=4,
                level_known=True,
                cursed_known=True,
            )
            belongings.weapon = Staff(
                id=str(uuid.uuid4()),
                imbued_wand=wand,
                level_known=True,
                cursed_known=True,
            )
            belongings.weapon.update_wand(False)
            class_starting_quickslots.append((0, belongings.weapon))

            # HeroClass.initMage(): Scroll of Upgrade + Potion of Liquid Flame
            # (both auto-identified).
            soi = ScrollOfUpgrade(id=str(uuid.uuid4()), level_known=True, cursed_known=True)
            belongings.backpack.collect(soi)
            self.identify_kind(soi)
            plf = PotionOfLiquidFlame(id=str(uuid.uuid4()), level_known=True, cursed_known=True)
            belongings.backpack.collect(plf)
            self.identify_kind(plf)

        elif class_type == CharacterClass.ROGUE:
            # SPD: Dagger + Cloth Armor base + Cloak of Shadows artifact +
            # Throwing Knives (quickslot). The cloak — not the armor — is the
            # signature item.
            belongings.weapon = Dagger(
                id=str(uuid.uuid4()),
            )
            belongings.armor = Armor(
                id=str(uuid.uuid4()),
                name="Cloth Armor",
                tier=1,
                strength_requirement=10,
            )
            belongings.artifact = CloakOfShadows(
                id=str(uuid.uuid4()),
            )
            knives = ThrowableDagger(
                id=str(uuid.uuid4()),
                name="Throwing Knife",
                quantity=3,
            )
            belongings.backpack.collect(knives)

        elif class_type == CharacterClass.HUNTRESS:
            belongings.weapon = Bow(
                id=str(uuid.uuid4()),
                name="Spirit Bow",
                damage=2,
                strength_requirement=10,
                attack_cooldown=3.5,
            )
            class_starting_quickslots.append((0, belongings.weapon))

        # HeroClass.initHero(): every hero starts with a ration of food, a
        # Velvet Pouch (for seeds/stones), and a Waterskin in the backpack.
        belongings.backpack.collect(Ration(
            id=str(uuid.uuid4()),
        ))
        belongings.backpack.collect(VelvetPouch(
            id=str(uuid.uuid4()),
        ))

        # HeroClass.initHero(): every hero starts with a Waterskin in the
        # backpack, bound to the first empty quickslot.
        waterskin = Waterskin(id=str(uuid.uuid4()))
        belongings.backpack.collect(waterskin)

        # HeroClass.initHero(): every hero starts with a Scroll of Identify
        # (auto-identified).
        si = ScrollOfIdentify(id=str(uuid.uuid4()), level_known=True, cursed_known=True)
        belongings.backpack.collect(si)
        self.identify_kind(si)

        # SPD identifies a hero's starting gear (HeroClass.java's .identify()), so
        # its STR requirement renders in white (":N") instead of the orange,
        # unidentified "N?" form, and the slot carries no unknown-item tint.
        for slot in belongings.equipped_slots():
            if slot is not None:
                slot.level_known = True
                slot.cursed_known = True

        player = Player(
            id=player_id,
            name=name,
            pos=spawn_pos,
            hp=20,
            max_hp=20,
            attack=3,
            defense=1,
            faction=Faction.PLAYER,
            class_type=class_type,
            belongings=belongings,
            floor_id=1,
            is_admin=is_admin,
        )

        # HeroClass.initHero(): class-specific quickslots (slot 0 for stones,
        # slot 2 for throwing knives, etc.), then Waterskin to slot 1.
        for slot_idx, item in class_starting_quickslots:
            player.quickslot.set_slot(slot_idx, item)
        player.quickslot.set_slot(1, waterskin)

        # HeroClass.initWarrior(): the BrokenSeal starts affixed to the cloth
        # armor (not in any equip slot), providing shielding on low HP.
        if class_type == CharacterClass.WARRIOR:
            player.seal_affixed = True

        self.players[player_id] = player
        self.depth = 1
        return player

    def _get_stairs_pos(self, tile_type: int, floor_id: Optional[int] = None) -> Position:
        floor = self._get_or_create_floor(floor_id or self.depth)
        for y in range(floor.height):
            for x in range(floor.width):
                if floor.grid[y][x] == tile_type:
                    return Position(x=x, y=y)
        return Position(x=0, y=0)

    def _move_player_to_floor(self, player: Player, target_floor_id: int, spawn_tile: int):
        target_floor_id = max(1, min(MAX_FLOOR_ID, target_floor_id))
        self._get_or_create_floor(target_floor_id)

        player.floor_id = target_floor_id
        player.floors_explored = max(player.floors_explored, target_floor_id)
        player.pos = self._get_stairs_pos(spawn_tile, floor_id=target_floor_id)

        self.depth = target_floor_id

    def next_floor(self, player_id: Optional[str] = None):
        target_players = []
        if player_id and player_id in self.players:
            target_players = [self.players[player_id]]
        elif not player_id and len(self.players) == 1:
            target_players = list(self.players.values())

        for player in target_players:
            if player.floor_id < MAX_FLOOR_ID:
                self._move_player_to_floor(player, player.floor_id + 1, TileType.STAIRS_UP)

    def prev_floor(self, player_id: Optional[str] = None):
        target_players = []
        if player_id and player_id in self.players:
            target_players = [self.players[player_id]]
        elif not player_id and len(self.players) == 1:
            target_players = list(self.players.values())

        for player in target_players:
            if player.floor_id > 1:
                self._move_player_to_floor(player, player.floor_id - 1, TileType.STAIRS_DOWN)

    def admin_teleport(self, player_id: str, target_floor: int):
        """Admin-only direct floor teleport. No-op if the player is not admin."""
        player = self.players.get(player_id)
        if not player or not player.is_admin:
            return
        target_floor = max(1, min(MAX_FLOOR_ID, target_floor))
        self._move_player_to_floor(player, target_floor, TileType.STAIRS_UP)

    def admin_give_item(self, player_id: str, item_kind: str):
        """Admin-only: spawn one of `item_kind` into the player's backpack, or
        drop it at their feet if the backpack is full. No-op if not admin."""
        player = self.players.get(player_id)
        if not player or not player.is_admin:
            return
        item = make_catalog_item(item_kind)
        if item is None:
            return
        item.id = str(uuid.uuid4())
        if not player.belongings.backpack.collect(item):
            item.pos = Position(x=player.pos.x, y=player.pos.y)
            floor = self._get_or_create_floor(player.floor_id)
            floor.items[item.id] = item

    def admin_level_up(self, player_id: str):
        """Admin-only: grant exactly enough XP for one level. No-op if not admin or at max level."""
        player = self.players.get(player_id)
        if not player or not player.is_admin:
            return
        if player.level >= Player.MAX_LEVEL:
            return
        xp_needed = player.max_exp() - player.experience
        if player.earn_exp(xp_needed):
            self.on_talent_level_up(player)

    def _random_fall_landing_cell(self, floor: FloorState) -> Position:
        """Any passable, unoccupied cell on `floor` — simplified from SPD's
        entrance-room-biased randomRespawnCell() (see design spec)."""
        occupied = {
            (p.pos.x, p.pos.y) for p in self._players_on_floor(floor.floor_id)
        }
        occupied |= {
            (m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive
        }
        candidates = [
            (x, y)
            for y in range(floor.height)
            for x in range(floor.width)
            if floor.flags and floor.flags.passable[y][x] and (x, y) not in occupied
        ]
        if not candidates:
            return Position(x=0, y=0)
        x, y = random.choice(candidates)
        return Position(x=x, y=y)

    def _perform_chasm_fall(self, player: Player, floor_id: int, x: int, y: int):
        """SPD Chasm.heroLand(): damage, Cripple, a Bleeding-equivalent, a
        screen shake, then drop to floor_id + 1 at a random landing cell."""
        player.pos = Position(x=x, y=y)
        player.pending_chasm_fall = None

        add_buff(player.buffs, "cripple", duration=10.0, level=1)

        hp = player.hp
        max_hp = player.get_total_max_hp()
        player.bleed_amount = max(1, round(max_hp / (6 + 6 * (hp / max_hp))))
        player.bleed_turns = 2

        lo, hi = sorted((hp // 2, max_hp // 4))
        dmg_roll = random.randint(lo, hi) if lo < hi else lo
        dmg = max(hp // 2, dmg_roll)
        dealt = player.take_damage(dmg)

        self.add_event("DAMAGE", {"target": player.id, "amount": dealt}, floor_id=floor_id)
        self.add_event("SCREEN_SHAKE", {"intensity": 4, "duration_ms": 300}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "FALLING"}, floor_id=floor_id, player_id=player.id)

        target_floor = self._get_or_create_floor(floor_id + 1)
        landing = self._random_fall_landing_cell(target_floor)
        player.floor_id = floor_id + 1
        player.floors_explored = max(player.floors_explored, floor_id + 1)
        player.pos = landing
        self.depth = floor_id + 1

    def confirm_chasm_fall(self, player_id: str, x: int, y: int):
        player = self.players.get(player_id)
        if not player or not player.is_alive or player.is_downed:
            return
        if player.pending_chasm_fall != (x, y):
            return
        floor_id = player.floor_id
        if floor_id >= MAX_FLOOR_ID:
            player.pending_chasm_fall = None
            return
        if abs(player.pos.x - x) > 1 or abs(player.pos.y - y) > 1:
            player.pending_chasm_fall = None
            return
        floor = self._get_or_create_floor(floor_id)
        if floor.grid[y][x] != TileType.CHASM:
            player.pending_chasm_fall = None
            return
        self._perform_chasm_fall(player, floor_id, x, y)

    def _kill_player(self, player: Player, floor: FloorState, floor_id: int):
        # Run the death sequence once: scatter the backpack and mark the spot
        # with a grave (mirrors Hero.reallyDie in Shattered Pixel Dungeon).
        player.death_processed = True

        # Collect passable 8-neighbour cells with no item on them, shuffled.
        free_cells: List[Tuple[int, int]] = []
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                if ox == 0 and oy == 0:
                    continue
                cx, cy = player.pos.x + ox, player.pos.y + oy
                if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                    continue
                if not floor.flags or not floor.flags.passable[cy][cx]:
                    continue
                if any(i.pos and i.pos.x == cx and i.pos.y == cy for i in floor.items.values()):
                    continue
                free_cells.append((cx, cy))
        random.shuffle(free_cells)

        # Drop everything the hero carried — equipped gear plus the backpack's
        # top-level items (sub-bags drop whole). Overflow lands on the death tile.
        dropped_items = [s for s in player.belongings.equipped_slots() if s is not None]
        dropped_items += list(player.belongings.backpack.items)
        for idx, item in enumerate(dropped_items):
            if idx < len(free_cells):
                cx, cy = free_cells[idx]
            else:
                cx, cy = player.pos.x, player.pos.y
            item.pos = Position(x=cx, y=cy)
            floor.items[item.id] = item
        player.belongings = Belongings()
        player.quickslot = QuickSlot()

        # Grave marker on the death tile.
        grave_id = f"grave_{uuid.uuid4().hex[:8]}"
        floor.items[grave_id] = Item(
            id=grave_id,
            name="Grave",
            type="grave",
            pos=Position(x=player.pos.x, y=player.pos.y),
        )

        self.add_event("DEATH", {
            "target": player.id,
            "score_breakdown": self._score_breakdown(player, victory=False),
            "can_resurrect": False,
            "victory": False,
        }, floor_id=floor_id)

    def _complete_victory(self, player: Player, floor: FloorState, floor_id: int):
        # Parallel to _kill_player, not built on it: a winner keeps every
        # item (no backpack scatter, no grave) -- the run ends in triumph,
        # not death. Setting is_alive=False + death_processed=True together
        # excludes the player from further ticking/input via the same checks
        # _kill_player relies on, without ever routing through it.
        player.is_alive = False
        player.death_processed = True

        self.add_event("DEATH", {
            "target": player.id,
            "score_breakdown": self._score_breakdown(player, victory=True),
            "can_resurrect": False,
            "victory": True,
        }, floor_id=floor_id)

    def _score_breakdown(self, player: Player, victory: bool) -> dict:
        # SPD WndScoreBreakdown: progress + treasure + explore + boss + quest.
        # Each category is capped; multipliers apply for win/challenges.
        progress = min(50000, player.floors_explored * 1500 + (player.level - 1) * 2000)
        treasure = min(20000, player.gold * 20)
        explore = min(20000, player.floors_explored * 800)
        boss_total = sum(self.boss_scores.values())
        boss = min(15000, boss_total)
        quest = min(10000, 0)  # quest tracking not yet implemented
        win_mult = 1.5 if victory else 1.0
        chal_mult = 1.25 if "stronger_bosses" in self.challenges else 1.0
        total = int((progress + treasure + explore + boss + quest) * win_mult * chal_mult)
        return {
            "kills": player.kills_count,
            "floors": player.floors_explored,
            "gold": player.gold,
            "progress_score": progress,
            "treasure_score": treasure,
            "explore_score": explore,
            "boss_score": boss,
            "quest_score": quest,
            "win_multiplier": win_mult if victory else None,
            "challenge_multiplier": chal_mult if chal_mult > 1 else None,
            "total_score": total,
            "victory": victory,
        }
