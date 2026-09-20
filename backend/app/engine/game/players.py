# Copyright (C) 2026 ArtemNikov
#
"""Player lifecycle for GameInstance: join, floor traversal, and death.

Handles starting-gear setup per class, stair-based floor changes, and the SPD
death sequence (scatter the backpack, drop a grave).
"""

import random
import uuid
from typing import Callable, Dict, List, Optional

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction, Position
from app.engine.entities.items.union import Bag, VelvetPouch
from app.engine.entities.items.artifacts import CloakOfShadows, HolyTome
from app.engine.entities.items.consumables import Amulet, Ankh, Dewdrop, Gold, LostBackpack, Ration, Stone, ThrowableDagger, Waterskin
from app.engine.entities.items.equip import Bow, ClothArmor, Dagger, SpiritBow, Staff, WornShortsword, MissileWeapon, make_named_melee_weapon
from app.engine.entities.items.potions import ELIXIR_BREW_KINDS, PotionOfLiquidFlame, PotionOfStrength
from app.engine.entities.items.scrolls import ScrollOfIdentify, ScrollOfUpgrade, ScrollOfMirrorImage
from app.engine.entities.wands import WandOfMagicMissile
from app.engine.entities.player import Belongings, CharacterClass, Difficulty, Player
from app.engine.entities.buffs import add_buff, remove_buff
from app.engine.entities.items.catalog import make_catalog_item
from app.engine.game.constants import MAX_FLOOR_ID, RESPAWN_MAX_USES, RESPAWN_SPAWN_PROTECTION_TURNS
from app.engine.game.floor_state import FloorState
from app.engine.dungeon.spd_levelgen.run_state import is_boss_level

# Difficulties where players get free in-place respawns (up to RESPAWN_MAX_USES).
# Boss floors are excluded regardless of difficulty.
RESPAWN_CAPABLE_DIFFICULTIES = (Difficulty.EASY, Difficulty.NORMAL)

# Harmful buffs cleared on respawn (mirrors SPD ankh's "detachAll harmful"
# filter). Beneficial buffs (bless, barkskin, haste, invisibility, shadows,
# empowered_strike trackers, etc.) are kept.
HARMFUL_BUFFS = frozenset({
    "poison", "burning", "frozen", "frost", "chilled", "chill",
    "paralysis", "cripple", "blindness", "blinded", "weakness",
    "vulnerable", "hex", "ooze", "corrosion", "vertigo", "terror",
    "death_mark", "bleeding", "rooted", "sheep_timer", "slow",
    "stagger",
})


def _init_warrior(player: Player) -> None:
    player.seal_affixed = True


def _init_duelist(player: Player) -> None:
    player.weapon_charge = float(player.get_max_weapon_charges())
    player.finisher_ready = True


_CLASS_POST_INIT: Dict[str, Callable[[Player], None]] = {
    CharacterClass.WARRIOR: _init_warrior,
    CharacterClass.DUELIST: _init_duelist,
}


class PlayersMixin:
    def add_player(self, player_id: str, name: str, class_type: str = CharacterClass.WARRIOR, is_admin: bool = False) -> Player:
        floor = self._get_or_create_floor(1)
        spawn_pos = self._get_stairs_pos(TileType.STAIRS_UP, floor_id=floor.floor_id)

        self.player_count += 1

        # Starting gear goes straight into the relevant equip slots (SPD-style:
        # equipped items live in Belongings, not the backpack).
        belongings = Belongings()

        class_starting_quickslots = []

        # Starting gear that's auto-identified (SPD HeroClass.init*()); identified
        # after the Player object exists so the hero's own discovered_kinds records
        # them too.
        starting_identified = []

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
            starting_identified.append(soi)
            plf = PotionOfLiquidFlame(id=str(uuid.uuid4()), level_known=True, cursed_known=True)
            belongings.backpack.collect(plf)
            starting_identified.append(plf)

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

        elif class_type == CharacterClass.DUELIST:
            belongings.weapon = make_named_melee_weapon("Rapier", id=str(uuid.uuid4()))
            belongings.armor = ClothArmor(
                id=str(uuid.uuid4()),
            )
            throwing_spikes = MissileWeapon(name="Throwing Spikes", tier=1, quantity=2, id=str(uuid.uuid4()), level_known=True, cursed_known=True)
            belongings.backpack.collect(throwing_spikes)
            str_pot = PotionOfStrength(id=str(uuid.uuid4()))
            belongings.backpack.collect(str_pot)
            starting_identified.append(str_pot)
            mirror_scr = ScrollOfMirrorImage(id=str(uuid.uuid4()), level_known=True, cursed_known=True)
            belongings.backpack.collect(mirror_scr)
            starting_identified.append(mirror_scr)
            class_starting_quickslots.append((0, belongings.weapon))
            class_starting_quickslots.append((1, throwing_spikes))

        elif class_type == CharacterClass.CLERIC:
            belongings.weapon = make_named_melee_weapon("Cudgel", id=str(uuid.uuid4()))
            belongings.armor = ClothArmor(
                id=str(uuid.uuid4()),
            )
            holy_tome = HolyTome(
                id=str(uuid.uuid4()),
            )
            belongings.artifact = holy_tome
            class_starting_quickslots.append((0, holy_tome))

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
        starting_identified.append(si)

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

        # SPD HeroClass.initHero()'s auto-identified starting consumables — record
        # them in both the party-shared set and this hero's personal discovery.
        for starting_item in starting_identified:
            self.identify_kind(starting_item, player)

        # HeroClass.initHero(): class-specific quickslots (slot 0 for stones,
        # slot 2 for throwing knives, etc.), then Waterskin to slot 1.
        for slot_idx, item in class_starting_quickslots:
            player.quickslot.set_slot(slot_idx, item)
        waterskin_slot = 2 if class_type == CharacterClass.ROGUE else 1
        player.quickslot.set_slot(waterskin_slot, waterskin)

        class_init = _CLASS_POST_INIT.get(class_type)
        if class_init is not None:
            class_init(player)

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

        first_visit = target_floor_id > player.floors_explored
        player.floor_id = target_floor_id
        player.floors_explored = max(player.floors_explored, target_floor_id)
        player.pos = self._get_stairs_pos(spawn_tile, floor_id=target_floor_id)

        # Purge any movement queue / intent from the previous floor so that steps
        # queued just before stepping on stairs don't execute on the new floor.
        # The frontend's MovementPredictor preserves monotonic sequence numbers
        # across floors (clearInFlight() instead of clear()), but stale backend
        # queues would still cause the player to attempt moves from the wrong
        # coordinate space until the server rejects them via last_processed_seq.
        player.movement.stop()
        player.reset_move_cooldown()

        self.depth = target_floor_id

        # Grant Adventurer's Guide pages on first visit (SPD
        # EntranceRoom.placeEarlyGuidePages + Document page discovery).
        if first_visit:
            self._grant_guide_pages_for_floor(player, target_floor_id)

    # SPD Adventurer's Guide page IDs (Document.ADVENTURERS_GUIDE page keys).
    # Pages are granted progressively on first floor visits, matching SPD's
    # EntranceRoom.placeEarlyGuidePages and regular-level page drops.
    _GUIDE_PAGE_DEPTHS = {
        1: ["Intro", "Examining", "Surprise_Attacks", "Identifying",
            "Food", "Alchemy", "Dieing"],
        2: ["Searching"],
        3: ["Strength", "Upgrades"],
        4: ["Looting", "Levelling", "Positioning", "Magic"],
    }

    def _grant_guide_pages_for_floor(self, player: Player, floor_id: int) -> None:
        """Grant Adventurer's Guide pages appropriate for this floor (SPD
        EntranceRoom.placeEarlyGuidePages + RegularLevel guide page drops)."""
        pages = self._GUIDE_PAGE_DEPTHS.get(floor_id, [])
        newly_found = []
        for page_id in pages:
            if player.discover_guide_page(page_id):
                self.run_state.guide_pages_found.add(page_id)
                newly_found.append(page_id)
                self.add_event(
                    "GUIDE_PAGE_DISCOVERED",
                    {"player": player.id, "page": page_id},
                    player_id=player.id,
                )
        if newly_found:
            # SPD's Guidebook.doPickUp: one combined notice + sound for the
            # whole batch, not one per page (matches DocumentPage.doPickUp's
            # single Sample.play(ITEM), no per-page log spam).
            self.add_event("PLAY_SOUND", {"sound": "PICKUP"}, player_id=player.id)
            text = ("A new page has been added to your Adventurer's Guide!"
                    if len(newly_found) == 1 else
                    "New pages have been added to your Adventurer's Guide!")
            self.add_event("MESSAGE", {"text": text, "color": "positive"}, player_id=player.id)

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

    def admin_give_item(self, player_id: str, item_kind: str,
                        level: int | None = None,
                        cursed: bool | None = None,
                        enchant: str | None = None):
        """Admin-only: spawn one of `item_kind` into the player's backpack, or
        drop it at their feet if the backpack is full. No-op if not admin."""
        player = self.players.get(player_id)
        if not player or not player.is_admin:
            return
        item = make_catalog_item(item_kind)
        if item is None:
            return
        # Apply admin options
        from app.engine.entities.items.equip import KindOfWeapon, Armor, ArmorEnchantment
        from app.engine.entities.weapons.weapon_enchants import CURSES, ENCHANT_RARITY
        from app.engine.entities.armors.armor_glyphs import CURSE_GLYPHS, GLYPH_RARITY
        if level is not None:
            item.level = level
            item.level_known = True
        if cursed is not None and isinstance(item, (KindOfWeapon, Armor)):
            item.cursed = cursed
            # Auto-pick random curse enchant/glyph when cursed=True and no
            # specific enchant was requested.
            if cursed and enchant is None:
                if isinstance(item, KindOfWeapon):
                    item.enchantment = random.choice(CURSES)
                elif isinstance(item, Armor):
                    item.enchantment = ArmorEnchantment(type=random.choice(CURSE_GLYPHS))
        if enchant is not None:
            is_weapon_curse = enchant in CURSES
            is_armor_curse = enchant in CURSE_GLYPHS
            if isinstance(item, KindOfWeapon) and (enchant in ENCHANT_RARITY or is_weapon_curse):
                item.enchantment = enchant
                if is_weapon_curse:
                    item.cursed = True
            elif isinstance(item, Armor) and (enchant in GLYPH_RARITY or is_armor_curse):
                item.enchantment = ArmorEnchantment(type=enchant)
                if is_armor_curse:
                    item.cursed = True
        # The item browser is a testing tool: spawn potions/scrolls/rings already
        # identified so their real name + type glyph render immediately.
        if item.type in ("potion", "scroll", "ring") and item.kind not in ELIXIR_BREW_KINDS:
            self.identify_kind(item, player)
        item.id = str(uuid.uuid4())
        if isinstance(item, Gold):
            player.gold += item.quantity
            return
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

    def admin_set_hp(self, player_id: str, hp: int | None = None, hp_pct: float | None = None):
        """Admin-only: set player's current health directly or by percentage (0.01 - 1.0 or 1 - 100)."""
        player = self.players.get(player_id)
        if not player or not player.is_admin:
            return
        if hp_pct is None and hp is None:
            return
        total_max_hp = player.get_total_max_hp()
        if hp_pct is not None:
            pct = hp_pct / 100.0 if hp_pct > 1.0 else float(hp_pct)
            pct = max(0.01, min(1.0, pct))
            player.hp = max(1, min(total_max_hp, round(total_max_hp * pct)))
        elif hp is not None:
            player.hp = max(1, min(total_max_hp, int(hp)))
        player.is_alive = True
        player.is_downed = False
        player.death_processed = False

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

    def _death_event_payload(self, player: Player, *, can_resurrect: bool, has_ankh: bool, loot_dropped: bool) -> dict:
        return {
            "target": player.id,
            "score_breakdown": self._score_breakdown(player, victory=False),
            "can_resurrect": can_resurrect,
            "has_ankh": has_ankh,
            "victory": False,
            "loot_dropped": loot_dropped,
            "respawns_used": player.respawns_used,
            "max_respawns": RESPAWN_MAX_USES,
            "death_cause": player.death_cause,
        }

    def _ankh_revive_hp(self, player: Player) -> int:
        # Ankh instant/manual revive HP: Easy 75%, Normal/Hard 25% (SPD: HT/4 = 25%).
        hp_pct = 0.75 if self.difficulty == Difficulty.EASY else 0.25
        return max(1, int(player.get_total_max_hp() * hp_pct))

    def _kill_player(self, player: Player, floor: FloorState, floor_id: int):
        # Run the death sequence once. Ankh check runs first: blessed ankhs
        # grant instant revive with all items preserved; unblessed ankhs
        # pause for the player to choose 2 items to keep. Without ankh,
        # death is final: scatter the backpack and show the game-over screen.
        player.death_processed = True

        # --- Ankh check (SPD Hero.die) --------------------------------
        ankhs = [i for i in player.belongings.all_items() if isinstance(i, Ankh)]
        # Prioritize blessed ankhs (SPD: "preferring ones which are blessed").
        ankh = next((a for a in ankhs if a.blessed), None) or (ankhs[0] if ankhs else None)
        blessed_ankh = ankh is not None and ankh.blessed

        if blessed_ankh:
            player.hp = self._ankh_revive_hp(player)
            player.is_alive = True
            player.is_downed = False
            # Consume the ankh.
            self._detach_item(player, ankh)
            # Clear harmful buffs, grant invulnerability.
            for buff_type in list(HARMFUL_BUFFS):
                remove_buff(player.buffs, buff_type)
            add_buff(player.buffs, "invulnerability",
                     duration=float(RESPAWN_SPAWN_PROTECTION_TURNS))
            player.respawns_used += 1

            self.add_event("DEATH", self._death_event_payload(
                player, can_resurrect=False, has_ankh=False, loot_dropped=False,
            ), floor_id=floor_id)
            self.add_event("SPAWN", {
                "target": player.id,
                "floor_id": player.floor_id,
                "is_resurrect": True,
                "hp": player.hp,
                "respawns_used": player.respawns_used,
                "max_respawns": RESPAWN_MAX_USES,
            }, floor_id=floor_id)
            return

        if ankh is not None:
            # Unblessed ankh: pause for player choice (SPD WndResurrect).
            player.pending_ankh = True
            player.death_processed = False  # keep alive for the choice window

            self.add_event("DEATH", self._death_event_payload(
                player, can_resurrect=True, has_ankh=True, loot_dropped=False,
            ), floor_id=floor_id)
            return

        # --- Difficulty-based respawn (Easy/Normal only, not on boss floors) --
        can_resurrect = (
            self.difficulty in RESPAWN_CAPABLE_DIFFICULTIES
            and not is_boss_level(floor_id)
            and player.respawns_used < RESPAWN_MAX_USES
        )

        if can_resurrect:
            # Easy keeps all gear, Normal keeps weapon+armor, Hard scatters all.
            keep_equipped = self.difficulty == Difficulty.NORMAL
            self._scatter_backpack(player, floor, keep_equipped=keep_equipped)

            self.add_event("DEATH", self._death_event_payload(
                player, can_resurrect=True, has_ankh=False, loot_dropped=True,
            ), floor_id=floor_id)
            return

        # --- Final death: no ankh, no respawns left — scatter everything --
        self._scatter_backpack(player, floor, keep_equipped=False)

        self.add_event("DEATH", self._death_event_payload(
            player, can_resurrect=False, has_ankh=False, loot_dropped=True,
        ), floor_id=floor_id)

    def resurrect_player(self, player_id: str) -> bool:
        """In-place resurrection (Easy/Normal): reborn at the same floor's
        STAIRS_UP with 50% HP, debuffs cleared, 3-turn spawn-protection.
        Inventory was either preserved (Easy) or already scattered by
        _kill_player (Normal) -- this method doesn't touch it. Applies
        score penalties (own respawn + witnessed by teammates). Returns
        False if the player can't be resurrected (not downed, wrong
        difficulty, boss floor, or cap exhausted)."""
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

    def _detach_item(self, player: Player, item) -> None:
        """Remove an item from the player's belongings (equipped or backpack)."""
        # Check if it's in an equipped slot.
        slot_name = player.belongings.find_equipped_slot(item.id)
        if slot_name is not None:
            setattr(player.belongings, slot_name, None)
            player.quickslot.clear_item(item.id)
            return
        # Otherwise detach from backpack.
        player.belongings.backpack.detach_all(item.id)
        player.quickslot.clear_item(item.id)

    def _scatter_backpack(self, player: Player, floor: FloorState,
                          keep_equipped: bool = False) -> None:
        """Drop the hero's belongings into a single owner-only LostBackpack
        at the death tile.

        When keep_equipped is True (Medium difficulty), weapon and armor are
        kept. Bags (Velvet Pouch, Scroll Holder, Magical Holster, Potion
        Bandolier) always persist on the player, with their contents intact.
        Everything else the hero carried -- including the Waterskin, volume
        intact -- goes into the LostBackpack's stored_items, recoverable only
        by the owner walking over it.
        """
        # Drop everything the hero carried — equipped gear plus the backpack's
        # loose items — except bags, which persist on the player, and the
        # starting weapon/armor, which are never lost.
        starting_weapon_class = {
            CharacterClass.WARRIOR: WornShortsword,
            CharacterClass.MAGE: Staff,
            CharacterClass.ROGUE: Dagger,
        }.get(player.class_type)

        dropped_items = []
        kept_bags = []
        quickslot_map = {}

        def _note_quickslot(original_id: str, new_item) -> None:
            # Record the *original* item's slot against whatever item ends up
            # representing it in the drop (itself -- the dropped item keeps
            # its own id -- or a fresh-id Waterskin swap, should one ever be
            # introduced again) so the binding is never lost.
            idx = player.quickslot.index_of(original_id)
            if idx != -1:
                quickslot_map[new_item.id] = idx
            # Clear the original binding explicitly -- the quickslot isn't
            # reset wholesale below, so kept items (bag contents, kept
            # weapon/armor on keep_equipped) retain their bindings.
            player.quickslot.clear_item(original_id)

        for s in player.belongings.equipped_slots():
            if s is None:
                continue
            if keep_equipped and (s is player.belongings.weapon or s is player.belongings.armor):
                continue
            if starting_weapon_class and isinstance(s, starting_weapon_class):
                continue
            if player.class_type == CharacterClass.HUNTRESS and s.name == "Gloves":
                continue
            if isinstance(s, ClothArmor):
                continue
            dropped_items.append(s)
            _note_quickslot(s.id, s)

        for item in list(player.belongings.backpack.items):
            if isinstance(item, Bag):
                kept_bags.append(item)
            elif isinstance(item, Waterskin):
                dropped_items.append(item)
                _note_quickslot(item.id, item)
            else:
                dropped_items.append(item)
                _note_quickslot(item.id, item)

        if keep_equipped:
            kept_weapon = player.belongings.weapon
            kept_armor = player.belongings.armor
            player.belongings = Belongings(weapon=kept_weapon, armor=kept_armor)
        else:
            player.belongings = Belongings()
        for bag in kept_bags:
            player.belongings.backpack.collect(bag)

        if dropped_items:
            bp_id = f"backpack_{uuid.uuid4().hex[:8]}"
            floor.items[bp_id] = LostBackpack(
                id=bp_id,
                pos=Position(x=player.pos.x, y=player.pos.y),
                owner_id=player.id,
                stored_items=dropped_items,
                quickslot_map=quickslot_map,
            )

    def _recover_lost_backpack(self, player: Player, backpack: LostBackpack) -> None:
        """Return every item in a recovered LostBackpack to the player.

        Equipables (weapon/armor/artifact) are re-equipped automatically when
        their equip slot is empty -- restoring the hero's pre-death loadout.
        A slot already holding a different item (picked up since respawn) is
        never displaced; that recovered item stays in the backpack.

        Items that were quickslotted at death are re-seated in that same
        slot, unless the player has since bound a different item there --
        in that case the recovered item is left unbound rather than
        claiming some other empty slot. Items with no recorded slot (never
        quickslotted before death) are just returned to the backpack, same
        as picking that item up off the ground normally never auto-binds
        it to a quickslot.
        """
        for stored in backpack.stored_items:
            player.add_to_inventory(stored)
            if isinstance(stored, Bag):
                continue
            slot_name = player.belongings.slot_name_for(stored)
            if slot_name in ("weapon", "armor", "artifact") and \
                    getattr(player.belongings, slot_name) is None:
                # equip_item detaches from the backpack but never touches the
                # quickslot, so the binding restored below survives the equip.
                player.equip_item(stored.id)
            slot_idx = backpack.quickslot_map.get(stored.id)
            if slot_idx is None:
                continue  # never quickslotted before death -- backpack only.
            slot = player.quickslot.slots[slot_idx]
            if slot.item_id is None and not slot.is_placeholder:
                player.quickslot.set_slot(slot_idx, stored)
            # else: a different item already claims that slot -- leave unbound.

    def ankh_choice(self, player_id: str, kept_item_ids: List[str]) -> bool:
        """Handle the ANKH_CHOICE message: player picks 2 items to keep."""
        player = self.players.get(player_id)
        if not player or not player.pending_ankh:
            return False
        if len(kept_item_ids) != 2:
            return False

        ankh = next((i for i in player.belongings.all_items() if isinstance(i, Ankh)), None)
        if ankh is None:
            return False

        floor = self._get_or_create_floor(player.floor_id)

        # Validate all kept items exist and belong to player (exclude ankhs/bags).
        kept_items = []
        for item_id in kept_item_ids:
            item = player.belongings.get_item(item_id)
            if item is not None and not isinstance(item, Ankh) and not isinstance(item, Bag):
                kept_items.append(item)
        if len(kept_items) != 2:
            return False

        # Collect dropped items (everything except ankh + kept items). Bags
        # persist on the player, same as a normal death, so scan top-level
        # only (equipped slots + backpack) rather than the recursive
        # all_items() -- that would also yield bag contents separately and
        # double-count them once bags are excluded.
        kept_ids = set(kept_item_ids) | {ankh.id}
        dropped_items = []
        kept_bags = []
        for s in player.belongings.equipped_slots():
            if s is None or isinstance(s, Ankh):
                continue
            if isinstance(s, Bag):
                kept_bags.append(s)
            elif s.id not in kept_ids:
                dropped_items.append(s)
        for item in list(player.belongings.backpack.items):
            if isinstance(item, Bag):
                kept_bags.append(item)
            elif item.id not in kept_ids:
                dropped_items.append(item)

        # Snapshot which dropped items were quickslotted, so they can be
        # re-seated in the same slot on recovery. Unlike _scatter_backpack,
        # this path doesn't reset the whole quickslot -- only the consumed
        # ankh is cleared below -- so stale bindings to now-dropped items
        # must be cleared explicitly, or recovery would see those slots as
        # falsely "occupied".
        dropped_ids = {i.id for i in dropped_items}
        quickslot_map = {
            s.item_id: idx for idx, s in enumerate(player.quickslot.slots)
            if s.item_id and s.item_id in dropped_ids
        }
        for item in dropped_items:
            player.quickslot.clear_item(item.id)

        # Create LostBackpack at death position with dropped items.
        if dropped_items:
            backpack = LostBackpack(
                id=f"lostbp_{uuid.uuid4().hex[:8]}",
                stored_items=dropped_items,
                owner_id=player.id,
                pos=Position(x=player.pos.x, y=player.pos.y),
                quickslot_map=quickslot_map,
            )
            floor.items[backpack.id] = backpack

        # Build new belongings with only kept items plus persisted bags.
        new_belongings = Belongings()
        for item in kept_items:
            slot = new_belongings.slot_name_for(item)
            if slot is not None:
                setattr(new_belongings, slot, item)
            else:
                new_belongings.backpack.collect(item)
        for bag in kept_bags:
            new_belongings.backpack.collect(bag)
        player.belongings = new_belongings

        # Consume the ankh.
        self._detach_item(player, ankh)

        player.hp = self._ankh_revive_hp(player)
        player.is_alive = True
        player.is_downed = False
        player.pending_ankh = False
        player.death_processed = False
        player.respawns_used += 1

        # Clear harmful buffs, grant spawn protection.
        for buff_type in list(HARMFUL_BUFFS):
            remove_buff(player.buffs, buff_type)
        add_buff(player.buffs, "spawn_protection",
                 duration=float(RESPAWN_SPAWN_PROTECTION_TURNS), level=1)

        # Score penalties: teammates witness the resurrection.
        for other in self.players.values():
            if other.id != player.id and other.is_alive:
                other.witnessed_respawns += 1

        self.add_event("SPAWN", {
            "target": player.id,
            "floor_id": player.floor_id,
            "is_resurrect": True,
            "hp": player.hp,
            "respawns_used": player.respawns_used,
            "max_respawns": RESPAWN_MAX_USES,
        }, floor_id=player.floor_id)
        return True

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
