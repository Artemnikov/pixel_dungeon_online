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
from app.engine.entities.base import Faction, Position
from app.engine.entities.item_union import Bag, VelvetPouch
from app.engine.entities.items_artifacts import CloakOfShadows
from app.engine.entities.items_consumable import Amulet, Dewdrop, Ration, Stone, ThrowableDagger, Waterskin
from app.engine.entities.items_equip import Bow, ClothArmor, Dagger, SpiritBow, Staff, WornShortsword, make_named_melee_weapon
from app.engine.entities.items_potions import PotionOfLiquidFlame
from app.engine.entities.items_scrolls import ScrollOfIdentify, ScrollOfUpgrade
from app.engine.entities.items_wands import WandOfMagicMissile
from app.engine.entities.player import Belongings, CharacterClass, Difficulty, Item, Player, QuickSlot, Weapon
from app.engine.entities.buffs import add_buff, remove_buff
from app.engine.entities.item_catalog import make_catalog_item
from app.engine.game.constants import MAX_FLOOR_ID, RESPAWN_MAX_USES, RESPAWN_SPAWN_PROTECTION_TURNS
from app.engine.game.floor_state import FloorState
from app.engine.dungeon.spd_levelgen.run_state import is_boss_level

# Difficulty tiers that offer an in-place respawn on death (Easy keeps loot,
# Medium == Difficulty.NORMAL drops it). Hard never offers a respawn.
RESPAWN_CAPABLE_DIFFICULTIES = (Difficulty.EASY, Difficulty.NORMAL)

# Harmful buffs cleared on respawn (mirrors SPD ankh's "detachAll harmful"
# filter). Beneficial buffs (bless, barkskin, haste, invisibility, shadows,
# empowered_strike trackers, etc.) are kept.
HARMFUL_BUFFS = frozenset({
    "poison", "burning", "frozen", "frost", "chilled", "chill",
    "paralysis", "cripple", "blindness", "blinded", "weakness",
    "vulnerable", "hex", "ooze", "corrosion", "vertigo", "terror",
    "death_mark", "bleeding", "rooted", "sheep_timer", "slow",
})


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
            belongings.armor = ClothArmor(
                id=str(uuid.uuid4()),
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
            belongings.armor = ClothArmor(
                id=str(uuid.uuid4()),
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
            class_starting_quickslots.append((0, belongings.artifact))
            class_starting_quickslots.append((1, knives))

        elif class_type == CharacterClass.HUNTRESS:
            # SPD HeroClass.initHuntress(): Gloves (display "studded gloves")
            # + Spirit Bow (quickslot). No armor in SPD, but the remake gives
            # Cloth Armor for parity with other starting kits.
            belongings.weapon = make_named_melee_weapon("Gloves", id=str(uuid.uuid4()))
            belongings.armor = ClothArmor(
                id=str(uuid.uuid4()),
            )
            spirit_bow = SpiritBow(
                id=str(uuid.uuid4()),
            )
            belongings.backpack.collect(spirit_bow)
            class_starting_quickslots.append((0, spirit_bow))

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
        waterskin_slot = 2 if class_type == CharacterClass.ROGUE else 1
        player.quickslot.set_slot(waterskin_slot, waterskin)

        # HeroClass.initWarrior(): the BrokenSeal is affixed to the cloth
        # armor at spawn. The shield activates on HP dropping to <=50%
        # (Char.java:937-946 / WarriorShield.activate) and is invisible
        # (0 shielding, 0 cooldown) until then.
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

    def _random_fall_landing_cell(self, floor: FloorState, fall_into_pit: bool = False) -> Position:
        """SPD RegularLevel.fallCell(fallIntoPit): a passable, unoccupied cell on
        `floor` to land on after a chasm fall. When `fall_into_pit` is true SPD
        biases toward the PitRoom of a WeakFloorRoom; the remake doesn't yet
        track PitRoom cells, so both paths collapse to the same random respawn
        cell picker (mirrors Level.randomRespawnCell). The flag is threaded
        through so the bias hooks on once PitRoom generation lands."""
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
        """SPD Chasm.heroFall -> InterlevelScene.Mode.FALL -> Chasm.heroLand.

        Ordering mirrors the Java flow so the client can reproduce the FX:
          1. heroFall: FALLING sound + Mode.FALL (here: emit CHASM_FALL so the
             client fades the screen and snaps the camera).
          2. fall(): depth++, land at fallCell(fallIntoPit).
          3. heroLand (the Falling buff fires next actor turn): if an
             ElixirOfFeatherFall.FeatherBuff is active, spawn a JET particle
             burst and skip all damage/shake; else PixelScene.shake(4, 1f),
             Cripple, Bleeding, and the upfront damage — then the DESCEND sound
             on a new-deepest floor (GameScene.java).
          4. onDeath (Chasm implements Hero.Doom): flag the death cause so the
             death screen reads "You fell to death...".
        """
        player.pos = Position(x=x, y=y)
        player.pending_chasm_fall = None

        # fall_into_pit is true in SPD when the hero was inside a WeakFloorRoom;
        # the remake doesn't yet track that room type, so always false here.
        fall_into_pit = False
        feather = player.has_buff("feather_fall")
        first_visit = (floor_id + 1) > player.floors_explored

        # 1. heroFall — broadcast the fall so the client fades + snaps. Tagged
        #    player-only (no floor) so it reaches the hero regardless of which
        #    floor the flush sees them on (mirrors STAIRS_DOWN emission).
        self.add_event("CHASM_FALL", {
            "player": player.id,
            "first_visit": first_visit,
            "feather": feather,
            "fall_into_pit": fall_into_pit,
        }, player_id=player.id)

        # 2. fall() — depth++ and land at fallCell.
        target_floor = self._get_or_create_floor(floor_id + 1)
        landing = self._random_fall_landing_cell(target_floor, fall_into_pit)
        player.floor_id = floor_id + 1
        player.floors_explored = max(player.floors_explored, floor_id + 1)
        player.pos = landing
        self.depth = floor_id + 1

        # 3. heroLand — applied after arriving on the new floor so the DAMAGE /
        #    shake events render at the landing cell on the right floor (fixes
        #    the prior bug where DAMAGE was emitted with the old floor_id).
        if feather:
            # ElixirOfFeatherFall: JET particle burst, no damage, no shake.
            # The client spawns the feather VFX from the CHASM_FALL feather flag.
            # Tick down the buff so a single fall consumes one charge's worth,
            # mirroring FeatherBuff.processFall() (which detaches once exhausted).
            fb = player.get_buff("feather_fall")
            if fb is not None:
                remove_buff(player.buffs, "feather_fall")
            return

        # Flag the doom cause BEFORE damage so _kill_player (next tick) reads it.
        player.death_cause = "fall"
        add_buff(player.buffs, "cripple", duration=10.0, level=1)

        hp = player.hp
        max_hp = player.get_total_max_hp()
        player.bleed_amount = max(1, round(max_hp / (6 + 6 * (hp / max_hp))))
        player.bleed_turns = 2

        lo, hi = sorted((hp // 2, max_hp // 4))
        dmg_roll = random.randint(lo, hi) if lo < hi else lo
        dmg = max(hp // 2, dmg_roll)
        dealt = player.take_damage(dmg)
        # Survived the fall: clear the doom cause so a later, ordinary death
        # doesn't mislabel itself as a fall death.
        if player.is_alive:
            player.death_cause = None

        self.add_event("SCREEN_SHAKE", {"intensity": 4, "duration_ms": 1000}, player_id=player.id)
        self.add_event("DAMAGE", {"target": player.id, "amount": dealt}, player_id=player.id)
        # GameScene.java: DESCEND sound + "descend" log on entering a new
        # deepest floor via FALL or DESCEND.
        if first_visit:
            self.add_event("PLAY_SOUND", {"sound": "STAIRS_DOWN"}, player_id=player.id)

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
        # Run the death sequence once: scatter the backpack (unless Easy
        # preserves everything, or Medium which keeps just weapon+armor) and
        # mark the spot with a grave (mirrors Hero.reallyDie in Shattered
        # Pixel Dungeon), then offer an in-place resurrection on Easy/Medium.
        # Excluded on boss floors (5/10/15/20/25) and once the respawn cap is
        # exhausted, so those deaths are final regardless of difficulty.
        player.death_processed = True

        can_resurrect = (
            self.difficulty in RESPAWN_CAPABLE_DIFFICULTIES
            and not is_boss_level(floor_id)
            and player.respawns_used < RESPAWN_MAX_USES
        )
        # Easy keeps the hero's gear, but only when it's actually respawning
        # them in place -- a boss-floor/cap-exhausted death is final even on
        # Easy, so it scatters loot exactly like Medium/Hard.
        preserve_loot = self.difficulty == Difficulty.EASY and can_resurrect
        # Medium drops the backpack but lets the hero keep their equipped
        # weapon and armor -- same "final death is final" gate as Easy above.
        keep_weapon_armor = self.difficulty == Difficulty.NORMAL and can_resurrect

        if not preserve_loot:
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
            # items. Sub-bags drop their contents individually, not the bag itself.
            # Skip the starting weapon and waterskin (dewdrops from the latter).
            starting_weapon_class = {
                CharacterClass.WARRIOR: WornShortsword,
                CharacterClass.MAGE: Staff,
                CharacterClass.ROGUE: Dagger,
            }.get(player.class_type)

            dropped_items = []
            for s in player.belongings.equipped_slots():
                if s is None:
                    continue
                if keep_weapon_armor and (s is player.belongings.weapon or s is player.belongings.armor):
                    continue
                if starting_weapon_class and isinstance(s, starting_weapon_class):
                    continue
                if player.class_type == CharacterClass.HUNTRESS and s.name == "Gloves":
                    continue
                if player.class_type == CharacterClass.ROGUE and isinstance(s, CloakOfShadows):
                    continue
                if isinstance(s, ClothArmor):
                    continue
                dropped_items.append(s)

            for item in list(player.belongings.backpack.items):
                if isinstance(item, Bag):
                    dropped_items.extend(item.items)
                elif isinstance(item, Waterskin):
                    if item.volume > 0:
                        dropped_items.append(Dewdrop(
                            id=str(uuid.uuid4()), quantity=item.volume,
                        ))
                else:
                    dropped_items.append(item)
            for idx, item in enumerate(dropped_items):
                if idx < len(free_cells):
                    cx, cy = free_cells[idx]
                else:
                    cx, cy = player.pos.x, player.pos.y
                item.pos = Position(x=cx, y=cy)
                floor.items[item.id] = item
            kept_weapon = player.belongings.weapon if keep_weapon_armor else None
            kept_armor = player.belongings.armor if keep_weapon_armor else None
            player.belongings = Belongings(weapon=kept_weapon, armor=kept_armor)
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
            "can_resurrect": can_resurrect,
            "victory": False,
            "loot_dropped": not preserve_loot,
            "respawns_used": player.respawns_used,
            "max_respawns": RESPAWN_MAX_USES,
            "death_cause": player.death_cause,
        }, floor_id=floor_id)

    def _safe_spawn_near_stairs(self, floor: FloorState) -> Position:
        # Respawn cell picker for in-place resurrect: prefer the STAIRS_UP
        # tile itself, then its 8-neighbours, then a BFS outward for the
        # first passable+unoccupied cell. Falls back to a random fall-landing
        # cell if nothing near the stairs is free. Mirrors the safety pattern
        # of _random_fall_landing_cell (players.py:265-283).
        stairs = self._get_stairs_pos(TileType.STAIRS_UP, floor_id=floor.floor_id)
        occupied = {(p.pos.x, p.pos.y) for p in self._players_on_floor(floor.floor_id)}
        occupied |= {(m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive}

        def is_free(x: int, y: int) -> bool:
            if not (0 <= x < floor.width and 0 <= y < floor.height):
                return False
            if not floor.flags or not floor.flags.passable[y][x]:
                return False
            return (x, y) not in occupied

        if is_free(stairs.x, stairs.y):
            return stairs
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                if ox == 0 and oy == 0:
                    continue
                cx, cy = stairs.x + ox, stairs.y + oy
                if is_free(cx, cy):
                    return Position(x=cx, y=cy)
        return self._random_fall_landing_cell(floor)

    def resurrect_player(self, player_id: str) -> bool:
        # In-place resurrection (Easy/Medium): reborn at the same floor's
        # STAIRS_UP with 50% HP, debuffs cleared, 3-turn spawn-protection.
        # Inventory was either preserved (Easy) or already scattered by
        # _kill_player (Medium/Hard) -- this method doesn't touch it. Applies
        # score penalties (own respawn + witnessed by teammates). Returns
        # False if the player can't be resurrected (not downed, wrong
        # difficulty, boss floor, or cap exhausted).
        player = self.players.get(player_id)
        if not player or player.is_alive:
            return False
        if self.difficulty not in RESPAWN_CAPABLE_DIFFICULTIES:
            return False
        if is_boss_level(player.floor_id):
            return False
        if player.respawns_used >= RESPAWN_MAX_USES:
            return False

        floor = self._get_or_create_floor(player.floor_id)
        player.pos = self._safe_spawn_near_stairs(floor)
        player.hp = max(1, player.get_total_max_hp() // 2)
        player.is_alive = True
        player.is_downed = False
        player.death_processed = False
        player.death_cause = None
        player.respawns_used += 1

        # Clear harmful buffs; keep beneficial ones (SPD ankh behaviour).
        for buff_type in list(HARMFUL_BUFFS):
            remove_buff(player.buffs, buff_type)
        # Spawn protection: invulnerability window so a mob camping the
        # stairs can't instantly re-kill the reborn hero.
        add_buff(player.buffs, "spawn_protection",
                 duration=float(RESPAWN_SPAWN_PROTECTION_TURNS), level=1)

        # Score penalties: own respawn (multiplicative 0.5 per use) is read
        # directly from respawns_used in _score_breakdown. Teammates suffer
        # a flat -25% per witnessed resurrection (also multiplicative).
        for other in self.players.values():
            if other.id != player.id and other.is_alive:
                other.witnessed_respawns += 1

        # Broadcast SPAWN so teammates see the resurrection flash + clients
        # can play a rebirth sound. Per-floor so only co-heroes on the same
        # level see it.
        self.add_event("SPAWN", {
            "target": player.id,
            "floor_id": player.floor_id,
            "is_resurrect": True,
            "hp": player.hp,
            "respawns_used": player.respawns_used,
            "max_respawns": RESPAWN_MAX_USES,
        }, floor_id=player.floor_id)
        return True

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
        # Easy-mode respawn penalties (multiplicative). Own respawns halve
        # the score each time (3 respawns → 12.5%). Witnessed teammates'
        # respawns shave 25% each (floored at 10% final). Both only apply
        # when the player actually used/witnessed a respawn.
        respawn_mult = 0.5 ** player.respawns_used if player.respawns_used > 0 else 1.0
        witness_mult = max(0.1, 1.0 - 0.25 * player.witnessed_respawns) if player.witnessed_respawns > 0 else 1.0
        total = int((progress + treasure + explore + boss + quest) * win_mult * chal_mult * respawn_mult * witness_mult)
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
            "respawn_multiplier": round(respawn_mult, 3) if respawn_mult < 1 else None,
            "witness_multiplier": round(witness_mult, 3) if witness_mult < 1 else None,
            "respawns_used": player.respawns_used,
            "witnessed_respawns": player.witnessed_respawns,
            "total_score": total,
            "victory": victory,
        }
