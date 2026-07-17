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
"""Port of the run-level RNG-consuming initialization sequence
(Dungeon.init -> Scroll.initLabels/Potion.initColors/Ring.initGems/
SpecialRoom.initForRun/SecretRoom.initForRun/Generator.fullReset) plus the
per-floor SpecialRoom/SecretRoom selection machinery
(SpecialRoom.initForFloor/createRoom/useType, SecretRoom.secretsForFloor/
createRoom).

This whole chain runs on a SEPARATE generator (`seed+1`, pushed once at game
start and then discarded -- see Dungeon.init/Random.resetGenerators) -- it
must be replayed in order to reproduce the `runSpecials`/`runSecrets`
selection queues that gate per-floor StandardRoom/SpecialRoom/SecretRoom
`set_size` draws (and thus genuinely affect *layout* RNG, not just item/mob
spawning -- selected room subclasses override min/max width/height). Floors
must be "generated" (i.e. this state threaded) strictly in depth order,
mirroring SPD's lazy floor creation (Level.create is called once per floor,
the first time it's visited)."""

from __future__ import annotations

import math
from typing import List, Optional, Tuple, Type

from app.engine.dungeon.spd_levelgen.geom import _to_f32
from app.engine.dungeon.spd_levelgen.generator import GeneratorState, _CategoryDeck, _random_deck_category, init_generator_state
from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
from app.engine.dungeon.spd_levelgen.room import Room
from app.engine.dungeon.spd_levelgen import special_rooms as sr
from app.engine.dungeon.spd_levelgen import terrain
from app.engine.dungeon.spd_levelgen.standard_rooms import _neighbours4
from app.engine.dungeon.spd_random import SPDRandom

# Number of item classes in each "deck" category that uses an
# ItemStatusHandler (Scroll/Potion/Ring): each draws Random.Int(n) once per
# item, n descending from len(labelImages) (== len(classes) == 12 for all
# three categories) down to 1.
_ITEM_STATUS_HANDLER_ITEMS = 12


def _consume_item_status_handler(rng: SPDRandom) -> None:
    """ItemStatusHandler(items, labelImages) ctor: draws
    Random.Int(labelsLeft.size()) once per item, decrementing the pool."""
    labels_left = _ITEM_STATUS_HANDLER_ITEMS
    for _ in range(_ITEM_STATUS_HANDLER_ITEMS):
        rng.IntMax(labels_left)
        labels_left -= 1


# Generator.Category.POTION/SCROLL static-init tables (Generator.java) --
# classes arrays collapsed to indices (0-11); only defaultProbs/defaultProbs2
# matter for deck-roll RNG parity and sort-order (defaultProbsTotal).
_POTION_DEFAULT_PROBS = (0.0, 3.0, 2.0, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
_POTION_DEFAULT_PROBS2 = (0.0, 3.0, 2.0, 2.0, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0)
_SCROLL_DEFAULT_PROBS = (0.0, 3.0, 2.0, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
_SCROLL_DEFAULT_PROBS2 = (0.0, 3.0, 2.0, 2.0, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0)

# Index of PotionOfExperience in POTION.classes / ScrollOfTransmutation in
# SCROLL.classes -- the "guaranteed" reward items CrystalPathRoom places
# directly via `new` (not Generator.random), gated only by a Random.Float()
# exotic-substitution check that always evaluates false on a fresh game.
POTION_EXPERIENCE_INDEX = 11
SCROLL_TRANSMUTATION_INDEX = 11


def _default_probs_total(probs: Tuple[float, ...], probs2: Tuple[float, ...]) -> Tuple[float, ...]:
    return tuple(a + b for a, b in zip(probs, probs2))


POTION_DEFAULT_PROBS_TOTAL = _default_probs_total(_POTION_DEFAULT_PROBS, _POTION_DEFAULT_PROBS2)
SCROLL_DEFAULT_PROBS_TOTAL = _default_probs_total(_SCROLL_DEFAULT_PROBS, _SCROLL_DEFAULT_PROBS2)


# -- itemsToSpawn descriptors -----------------------------------------------
# Level.findPrizeItem(Class<?extends Item> match) only ever gets called (across
# all special rooms) with one of: None, TrinketCatalyst, Scroll, Runestone,
# PotionOfStrength -- so an item only needs to record which of THOSE four
# `match.isInstance(item)` checks it satisfies. Each descriptor is a frozenset
# of the labels it matches; `findPrizeItem` checks `match_label in descriptor`.
# (PotionOfStrength/ScrollOfUpgrade are POTION.classes[0]/SCROLL.classes[0],
# both with defaultProbs[0]==defaultProbs2[0]==0 -- impossible to roll via
# Generator.random(POTION/SCROLL), and TrinketCatalyst is not a member of
# TRINKET.classes -- so Generator-rolled items never satisfy
# PotionOfStrength/TrinketCatalyst, only (sometimes) Scroll/Runestone.)
SPAWN_FOOD = frozenset()
SPAWN_POTION_OF_STRENGTH = frozenset({"PotionOfStrength", "Potion"})
SPAWN_SCROLL_OF_UPGRADE = frozenset({"Scroll"})
SPAWN_STYLUS = frozenset()
SPAWN_STONE_OF_ENCHANTMENT = frozenset({"Runestone"})
SPAWN_STONE_OF_INTUITION = frozenset({"Runestone"})
SPAWN_TRINKET_CATALYST = frozenset({"TrinketCatalyst"})

# Descriptors for items createItems queues/drops directly (not via the
# preamble's findPrizeItem matching) -- GoldenKey on a LOCKED_CHEST roll,
# GuidePage("Intro") on the fresh-game guide-page roll (missingPages is always
# the fixed 13-name list with "Intro" first, since no pages are ever found).
SPAWN_GOLDEN_KEY = frozenset({"GoldenKey"})
SPAWN_GUIDE_PAGE_INTRO = frozenset({"GuidePage", "DocumentPage"})


SPAWN_GENERIC_SCROLL = frozenset({"Scroll"})
SPAWN_GENERIC_RUNESTONE = frozenset({"Runestone"})


def generator_category_spawn_item(cat_name: str) -> frozenset:
    """Descriptor for an item produced by Generator.random(Category)/
    randomUsingDefaults -- only SCROLL/STONE rolls can ever satisfy a
    findPrizeItem(Scroll/Runestone) check (see note above)."""
    if cat_name == "SCROLL":
        return SPAWN_GENERIC_SCROLL
    if cat_name == "STONE":
        return SPAWN_GENERIC_RUNESTONE
    return SPAWN_FOOD


def generator_random_class_index(deck: _CategoryDeck, rng: SPDRandom) -> int:
    """Port of Generator.random(Category) for POTION/SCROLL: rolls and
    returns the chosen class index, mutating deck state and consuming the
    Random.Float() draw that always follows on the MAIN sequence.

    Every POTION class is in ExoticPotion.regToExo and every SCROLL class is
    in ExoticScroll.regToExo (verified 12-for-12 against Generator.classes
    arrays), so `ExoticPotion/ScrollMaps.regToExo.containsKey(itemCls)` is
    always true -- the conditional `Random.Float() < consumableExoticChance()`
    draw always fires. consumableExoticChance() == 0 for a fresh game (no
    ExoticCrystals trinket owned), so the draw never substitutes the class --
    meaning the rolled identity is always the regular (non-exotic) class at
    `index`, and class-identity comparisons (dedup/sort) need no exotic-map
    indirection."""
    rng.push_generator(deck.seed)
    for _ in range(deck.dropped):
        rng.Long()
    i = rng.chances(deck.probs)
    if i == -1:
        deck.reset()
        i = rng.chances(deck.probs)
    deck.probs[i] -= 1
    rng.pop_generator()
    deck.dropped += 1

    rng.Float()  # Random.Float() < ExoticCrystals.consumableExoticChance() -- always false, draw always made
    return i


# 5 regions (sewers/prison/caves/city/halls); region = depth/5.
_BASE_REGION_SECRETS = (2.0, 2.25, 2.5, 2.75, 3.0)


class ImpQuestState:
    """Mirrors actors/mobs/npcs/Imp.Quest's static fields: tracks the
    Golem/Monk token-collection quest spawned in AmbitiousImpRoom (depths
    17-19) and resolved via ImpShopRoom on floor 20."""

    def __init__(self) -> None:
        self.spawned: bool = False
        self._spawn_depth: Optional[int] = None
        self.alternative: bool = False
        self.given: bool = False
        self.completed: bool = False
        self.reward = None  # type: Optional[object] -- a Ring item once rolled

    def maybe_spawn(self, rng: SPDRandom, depth: int):
        """Imp.Quest.spawn(): rolled once per depth 17-19 after a floor's
        other rooms are decided. Returns an AmbitiousImpRoom if it spawns.

        _init_rooms() may be re-invoked across builder retries for the same
        depth (see build_floor); once spawned for `depth`, re-add the room
        on each retry without re-rolling so the builder eventually places it."""
        from app.engine.dungeon.spd_levelgen.room_types import AmbitiousImpRoom

        if self.spawned and self._spawn_depth == depth:
            return AmbitiousImpRoom()
        if self.spawned or depth <= 16:
            return None
        if rng.IntMax(20 - depth) != 0:
            return None

        self.spawned = True
        self._spawn_depth = depth
        if depth == 18:
            self.alternative = rng.IntMax(2) == 0
        elif depth == 19:
            self.alternative = False
        else:  # depth == 17 (default)
            self.alternative = True
        self.given = False

        from app.engine.entities.items_equip import Ring
        self.reward = Ring(name="Ring", level=2, level_known=True, cursed=True, cursed_known=False)

        return AmbitiousImpRoom()


# Weapon.Enchantment.random()/Armor.Glyph.random() (Weapon.java:606-615,
# Armor.java:863-872): chances(50,40,10) picks common/uncommon/rare, then
# Random.element() draws one item from that tier's list. Both enchant and
# glyph have identical tier sizes (4/6/3) -- consumed below for RNG-sequence
# parity only; this engine has no enchant/glyph application yet (a separate,
# pre-existing gap), so the rolled identity itself is discarded.
_ENCHANT_GLYPH_TYPE_CHANCES = (50.0, 40.0, 10.0)
_ENCHANT_GLYPH_TIER_SIZES = (4, 6, 3)


def _consume_enchant_or_glyph_roll(rng: SPDRandom) -> None:
    tier = rng.chances(_ENCHANT_GLYPH_TYPE_CHANCES)
    rng.IntMax(_ENCHANT_GLYPH_TIER_SIZES[tier])


class GhostQuestState:
    """Mirrors actors/mobs/npcs/Ghost.Quest's static fields (Ghost.java):
    tracks the sewers floors-2-4 side quest (kill the depth-specific
    miniboss, claim a hidden weapon-or-armor reward)."""

    def __init__(self) -> None:
        self.spawned: bool = False
        self.quest_type: int = 0          # 1=FetidRat(depth2) 2=GnollTrickster(depth3) 3=GreatCrab(depth4)
        self.given: bool = False
        self.processed: bool = False
        self.depth: Optional[int] = None  # floor the quest was given on -- process() only fires there
        self.ghost_id: Optional[str] = None
        self.boss_id: Optional[str] = None
        # Reward, rolled once at spawn time and hidden until `processed`.
        self.armor_tier: Optional[int] = None             # 2-5
        self.weapon_tier_category: Optional[str] = None   # "WEP_T2".."WEP_T5"
        self.weapon_item_index: Optional[int] = None
        self.item_level: int = 0                          # +0/+1/+2/+3, shared by both

    def process(self, depth: int) -> bool:
        """Ghost.Quest.process() (Ghost.java:367-385) -- called from the
        quest boss's death handler. Marks the quest complete if it's still
        active and the boss died on the same depth the quest was given on.
        Returns True the moment it just completed (caller plays the
        "find_me" message/sound)."""
        if self.spawned and self.given and not self.processed and self.depth == depth:
            self.processed = True
            return True
        return False

    def maybe_spawn(self, rng: SPDRandom, level) -> Optional[GenMob]:
        """Ghost.Quest.spawn(SewerLevel, Room) (Ghost.java:303-364) -- depths
        2-4 only, one ghost per run. Returns a GenMob for the caller to add
        to the floor's mob list, or None."""
        depth = level.depth
        if self.spawned or depth <= 1:
            return None
        if rng.IntMax(5 - depth) != 0:
            return None

        # do { ghost.pos = level.pointToCell(room.random()); } while (...) --
        # unbounded retry, no tries cap (matches the original exactly).
        room = level.room_exit
        while True:
            pos = level.point_to_cell(room.random(rng))
            if pos != -1 and not level.solid[pos] and level.open_space[pos] and pos != level.exit():
                break

        self.spawned = True
        self.quest_type = depth - 1
        self.given = False
        self.processed = False
        self.depth = depth

        # Armor tier: chances(0,0,10,6,3,1) -> index IS the tier (2-5), since
        # indices 0/1 have zero weight and the original switches on the same
        # index value (case 2: Leather, case 3: Mail, case 4: Scale, case 5: Plate).
        self.armor_tier = rng.chances((0.0, 0.0, 10.0, 6.0, 3.0, 1.0))

        # Weapon tier: same chances() shape, then Generator.random(wepTiers[
        # tier-1]) -- a deck-backed roll within that one tier (reuses the
        # existing weapon-tier deck roller used elsewhere for normal loot).
        wep_tier = rng.chances((0.0, 0.0, 10.0, 6.0, 3.0, 1.0))
        tier_category = f"WEP_T{wep_tier}"
        ri = _random_deck_category(level.run_state.generator_state, rng, tier_category)
        # ri.level (the item's natural upgrade roll) is discarded -- the
        # original immediately resets weapon.level(0)/enchant(null)/cursed=
        # false right after Generator.random() returns.
        self.weapon_tier_category = tier_category
        self.weapon_item_index = ri.item_index

        # Item level: 50%/30%/15%/5% -> +0/+1/+2/+3, via manual thresholds on
        # ONE Float() draw (not chances()) -- shared by both weapon and armor.
        roll = rng.Float()
        if roll < 0.5:
            self.item_level = 0
        elif roll < 0.8:
            self.item_level = 1
        elif roll < 0.95:
            self.item_level = 2
        else:
            self.item_level = 3

        # Enchant/glyph: pre-rolled so the outcome doesn't affect RNG-call
        # count even when discarded (see _consume_enchant_or_glyph_roll).
        _consume_enchant_or_glyph_roll(rng)  # Weapon.Enchantment.random()
        _consume_enchant_or_glyph_roll(rng)  # Armor.Glyph.random()
        rng.Float()  # enchantRoll -- ParchmentScrap.enchantChanceMultiplier() == 1.0 baseline

        return GenMob(cls_name="Ghost", pos=pos, depth=depth)


class WandmakerQuestState:
    """Mirrors actors/mobs/npcs/Wandmaker.Quest's static fields (Wandmaker.
    java): the Prison depths 6-9 side quest. Phase 1 only implements the
    Corpse Dust variant (type 1) -- see wandmaker_quest.py's module
    docstring for why types 2/3 (Ceremonial Candle/Rotberry) still consume
    the same RNG draw but silently produce no room, keeping later floor
    generation for a given seed byte-identical to vanilla regardless of
    which type is rolled.

    wand1/wand2 are stored as bare deck-index + level descriptors (not
    concrete Item objects) -- mirrors GhostQuestState's weapon_tier_category/
    weapon_item_index/item_level split, deferring the actual Wand
    construction to world.py's claim handler (spd_levelgen must not
    construct runtime Item objects directly -- see spd_adapter.py's
    build_wand_item, the one place that conversion happens)."""

    def __init__(self) -> None:
        self.spawned: bool = False               # Quest.spawned -- NPC actually placed
        self.quest_type: int = 0                  # Quest.type -- 1=CorpseDust (2/3 unimplemented)
        self.quest_room_spawned: bool = False     # Quest.questRoomSpawned (transient)
        self.given: bool = False                  # Quest.given -- intro dialogue already shown
        self.npc_id: Optional[str] = None
        self.wand1_index: Optional[int] = None
        self.wand1_level: int = 0
        self.wand2_index: Optional[int] = None
        self.wand2_level: int = 0

    def maybe_spawn_room(self, rng: SPDRandom, depth: int):
        """Wandmaker.Quest.spawnRoom() -- called once all other Prison-floor
        rooms are decided (only depths 7-9 roll; depth 9's Random.IntMax(1)
        always succeeds, forcing a decision by then if not already made).
        Once quest_type is nonzero (decided this floor or an earlier builder
        retry of the same floor -- `spawned` only flips true later, in
        maybe_spawn_npc, well after this floor's build finishes), no further
        roll ever happens -- matches Java's `type != 0` short-circuit."""
        self.quest_room_spawned = False
        if self.spawned:
            return None
        if self.quest_type == 0:
            if not (depth > 6 and rng.IntMax(10 - depth) == 0):
                return None
            self.quest_type = rng.IntMax(3) + 1
        if self.quest_type == 1:
            self.quest_room_spawned = True
            return sr.MassGraveRoom()
        return None

    def maybe_spawn_npc(self, rng: SPDRandom, level) -> Optional[GenMob]:
        """Wandmaker.Quest.spawnWandmaker(Level, Room) -- called at the top
        of create_mobs() for Prison depths (mirrors _ghost_quest_spawn's call
        site/shape in regular_level.py). Spawns into level.room_entrance
        (NOT the quest room -- matches PrisonLevel.createMobs() passing
        `roomEntrance`), via the shrinking-margin room.random(dist) retry.
        Rolls both reward wands here, in the exact RNG order Java does:
        placement, then wand1 draw + upgrade roll, then wand2 draw(s)
        (redrawing on a duplicate class, undoing the rejected draws' deck
        decrements only after the loop exits, matching Java's toUndo-after-
        loop timing) + upgrade roll."""
        if not self.quest_room_spawned:
            return None
        self.quest_room_spawned = False

        room = level.room_entrance
        neighbours4 = _neighbours4(level.width())
        entrance = level.entrance()
        tries = 0
        dist = 2
        while True:
            if tries > 30 and dist > 0:
                tries = 0
                dist -= 1
            pos = level.point_to_cell(room.random(rng, dist))
            valid = pos != entrance and not level.solid[pos]
            if valid:
                for nb in neighbours4:
                    if level.map[pos + nb] == terrain.DOOR:
                        valid = False
                        break
            if valid and (level.traps.get(pos) is not None
                          or not level.passable[pos]
                          or level.map[pos] == terrain.EMPTY_SP):
                valid = False
            tries += 1
            if valid:
                break

        self.spawned = True
        self.given = False

        gen_state = level.run_state.generator_state
        wand1_ri = _random_deck_category(gen_state, rng, "WAND")
        rng.IntMax(3)  # Wand.upgrade()'s cursed=false reroll (already forced false by Quest)
        self.wand1_index = wand1_ri.item_index
        self.wand1_level = wand1_ri.level + 1

        wand2_ri = _random_deck_category(gen_state, rng, "WAND")
        to_undo = []
        while wand2_ri.item_index == wand1_ri.item_index:
            to_undo.append(wand2_ri.item_index)
            wand2_ri = _random_deck_category(gen_state, rng, "WAND")
        for idx in to_undo:
            gen_state.decks["WAND"].undo_drop(idx)
        rng.IntMax(3)  # Wand.upgrade()'s cursed=false reroll
        self.wand2_index = wand2_ri.item_index
        self.wand2_level = wand2_ri.level + 1

        return GenMob(cls_name="Wandmaker", pos=pos, depth=level.depth)


def is_boss_level(depth: int) -> bool:
    return depth in (5, 10, 15, 20, 25)


def region_for_depth(depth: int) -> str:
    if depth <= 5:
        return "sewers"
    if depth <= 10:
        return "prison"
    if depth <= 15:
        return "caves"
    if depth <= 20:
        return "city"
    return "halls"


class RunState:
    """Mutable per-run state mirroring SpecialRoom/SecretRoom static fields
    plus the LimitedDrops.LAB_ROOM counter -- threaded across sequential
    floor generation within a single game/seed."""

    def __init__(self) -> None:
        self.run_specials: List[Type[Room]] = []
        self.floor_specials: List[Type[Room]] = []
        self.pit_needed_depth: int = -1

        self.run_secrets: List[Type[Room]] = []
        self.region_secrets_this_run: List[int] = [0, 0, 0, 0, 0]

        self.lab_room_count: int = 0

        # Dungeon.LimitedDrops counters consulted by Level.create()'s item
        # preamble (posNeeded/souNeeded/asNeeded/enchStoneNeeded/...) -- start
        # at 0/false for a fresh run and accumulate strictly in depth order.
        self.strength_potions: int = 0
        self.upgrade_scrolls: int = 0
        self.arcane_styli: int = 0
        self.ench_stone_dropped: bool = False
        self.int_stone_dropped: bool = False
        self.trinket_cata_dropped: bool = False

        # Generator's persistent state (categoryProbs/usingFirstDeck/per-
        # category decks incl. POTION/SCROLL for CrystalPathRoom rolls and
        # everything createItems/createMobs need), threaded across the run.
        # Populated by init_for_run via Generator.fullReset's RNG sequence.
        self.generator_state: Optional[GeneratorState] = None

        # Imp quest (actors/mobs/npcs/Imp.Quest), depths 17-19 + floor 20 shop.
        self.imp_quest = ImpQuestState()

        # Ghost quest (actors/mobs/npcs/Ghost.Quest), sewers depths 2-4.
        self.ghost_quest = GhostQuestState()

        # Wandmaker quest (actors/mobs/npcs/Wandmaker.Quest), prison depths 6-9.
        self.wandmaker_quest = WandmakerQuestState()

    @property
    def potion_deck(self) -> _CategoryDeck:
        return self.generator_state.decks["POTION"]

    @property
    def scroll_deck(self) -> _CategoryDeck:
        return self.generator_state.decks["SCROLL"]

    # -- run-start init (Dungeon.init RNG sequence, pushed generator seed+1) -
    def init_for_run(self, rng: SPDRandom) -> None:
        _consume_item_status_handler(rng)  # Scroll.initLabels
        _consume_item_status_handler(rng)  # Potion.initColors
        _consume_item_status_handler(rng)  # Ring.initGems

        self._special_room_init_for_run(rng)
        self._secret_room_init_for_run(rng)

        self.generator_state = init_generator_state(rng)

    def _special_room_init_for_run(self, rng: SPDRandom) -> None:
        equip = list(sr.EQUIP_SPECIALS)
        consumable = list(sr.CONSUMABLE_SPECIALS)
        rng.shuffle(equip)
        rng.shuffle(consumable)

        run_specials: List[Type[Room]] = []
        # "TODO currently always a consumable special first" -- Java comment
        run_specials.append(consumable.pop(0))
        while equip or consumable:
            if equip:
                run_specials.append(equip.pop(0))
            if consumable:
                run_specials.append(consumable.pop(0))
        self.run_specials = run_specials
        self.pit_needed_depth = -1

    def _secret_room_init_for_run(self, rng: SPDRandom) -> None:
        region_secrets = []
        for base in _BASE_REGION_SECRETS:
            count = int(base)
            if rng.Float() < (base % 1.0):
                count += 1
            region_secrets.append(count)
        self.region_secrets_this_run = region_secrets

        run_secrets = list(sr.ALL_SECRETS)
        rng.shuffle(run_secrets)
        self.run_secrets = run_secrets

    # -- per-floor (pushed generator seedForDepth(depth), strictly in order) -
    def init_for_floor(self, rng: SPDRandom, depth: int) -> None:
        self.floor_specials = list(self.run_specials)
        if self._lab_room_needed(rng, depth):
            self.lab_room_count += 1
            self.floor_specials.insert(0, sr.LaboratoryRoom)

    def _lab_room_needed(self, rng: SPDRandom, depth: int) -> bool:
        region = 1 + depth // 5
        if region > self.lab_room_count:
            floor_this_region = depth % 5
            if floor_this_region >= 4:
                return True
            elif floor_this_region == 3 and rng.IntMax(2) == 0:
                return True
        return False

    # -- item preamble (Level.create() lines 217-256, branch==0 non-boss only) -
    def consume_item_preamble(self, rng: SPDRandom, depth: int) -> List[frozenset]:
        """Replays Level.create()'s unconditional addItemToSpawn block,
        returning the itemsToSpawn descriptors it queues this floor (in
        order -- this becomes the level's initial itemsToSpawn, consumed by
        findPrizeItem() in special-room paint() methods).

        Generator.random(FOOD) itself draws from a separate cat.seed-pushed
        deck generator and consumes ZERO from this floor's sequence (verified:
        Food/Pasty/MysteryMeat aren't in ExoticPotion/ScrollMaps -- no Float()
        draw fires); only the gating Random.Int draws below touch this floor's
        sequence. The FOOD roll's *result* still gets queued though (as a
        non-matching descriptor -- it never satisfies any findPrizeItem check)."""
        items: List[frozenset] = [SPAWN_FOOD]
        if self._pos_needed(rng, depth):
            self.strength_potions += 1
            items.append(SPAWN_POTION_OF_STRENGTH)
        if self._sou_needed(rng, depth):
            self.upgrade_scrolls += 1
            # `!Dungeon.isChallenged(NO_SCROLLS) || count%2!=0` -- always true
            # on the fresh-game baseline (no challenges active).
            items.append(SPAWN_SCROLL_OF_UPGRADE)
        if self._as_needed(rng, depth):
            self.arcane_styli += 1
            items.append(SPAWN_STYLUS)
        if self._ench_stone_needed(rng, depth):
            self.ench_stone_dropped = True
            items.append(SPAWN_STONE_OF_ENCHANTMENT)
        if self._int_stone_needed(rng, depth):
            self.int_stone_dropped = True
            items.append(SPAWN_STONE_OF_INTUITION)
        if self._trinket_cata_needed(rng, depth):
            self.trinket_cata_dropped = True
            items.append(SPAWN_TRINKET_CATALYST)
        return items

    def _pos_needed(self, rng: SPDRandom, depth: int) -> bool:
        pos_left_this_set = 2 - (self.strength_potions - (depth // 5) * 2)
        if pos_left_this_set <= 0:
            return False
        floor_this_set = depth % 5
        target_pos_left = 2 - floor_this_set // 2
        if floor_this_set % 2 == 1 and rng.IntMax(2) == 0:
            target_pos_left -= 1
        return target_pos_left < pos_left_this_set

    def _sou_needed(self, rng: SPDRandom, depth: int) -> bool:
        sou_left_this_set = 3 - (self.upgrade_scrolls - (depth // 5) * 3)
        if sou_left_this_set <= 0:
            return False
        floor_this_set = depth % 5
        return rng.IntMax(5 - floor_this_set) < sou_left_this_set

    def _as_needed(self, rng: SPDRandom, depth: int) -> bool:
        as_left_this_set = 1 - (self.arcane_styli - (depth // 5))
        if as_left_this_set <= 0:
            return False
        floor_this_set = depth % 5
        return rng.IntMax(5 - floor_this_set) < as_left_this_set

    def _ench_stone_needed(self, rng: SPDRandom, depth: int) -> bool:
        if not self.ench_stone_dropped:
            region = 1 + depth // 5
            if region > 1:
                floors_visited = depth - 5
                if floors_visited > 4:
                    floors_visited -= 1
                return rng.IntMax(9 - floors_visited) == 0
        return False

    def _int_stone_needed(self, rng: SPDRandom, depth: int) -> bool:
        return depth < 5 and not self.int_stone_dropped and rng.IntMax(4 - depth) == 0

    def _trinket_cata_needed(self, rng: SPDRandom, depth: int) -> bool:
        return depth < 5 and not self.trinket_cata_dropped and rng.IntMax(4 - depth) == 0

    def _use_type(self, room_type: Type[Room]) -> None:
        if room_type in self.floor_specials:
            self.floor_specials.remove(room_type)
        if room_type in sr.CRYSTAL_KEY_SPECIALS:
            for t in sr.CRYSTAL_KEY_SPECIALS:
                while t in self.floor_specials:
                    self.floor_specials.remove(t)
        if room_type in sr.POTION_SPAWN_ROOMS:
            for t in sr.POTION_SPAWN_ROOMS:
                while t in self.floor_specials:
                    self.floor_specials.remove(t)
        if room_type in self.run_specials:
            self.run_specials.remove(room_type)
            self.run_specials.append(room_type)

    def create_special_room(self, rng: SPDRandom, depth: int) -> Room:
        if depth == self.pit_needed_depth:
            self.pit_needed_depth = -1
            self._use_type(sr.PitRoom)
            return sr.PitRoom()

        if sr.LaboratoryRoom in self.floor_specials:
            self._use_type(sr.LaboratoryRoom)
            return sr.LaboratoryRoom()

        if is_boss_level(depth + 1) and sr.WeakFloorRoom in self.floor_specials:
            self.floor_specials.remove(sr.WeakFloorRoom)

        index = rng.chances((6.0, 3.0, 1.0))
        while index >= len(self.floor_specials):
            index -= 1

        room_type = self.floor_specials[index]
        room = room_type()

        if isinstance(room, sr.WeakFloorRoom):
            self.pit_needed_depth = depth + 1

        self._use_type(room_type)
        return room

    # -- secrets -------------------------------------------------------------
    def secrets_for_floor(self, rng: SPDRandom, depth: int) -> int:
        if depth == 1:
            return 0

        region = depth // 5
        floor = depth % 5
        floors_left = 5 - floor

        if floors_left == 0:
            secrets = float(self.region_secrets_this_run[region])
        else:
            secrets = _to_f32(self.region_secrets_this_run[region] / float(floors_left))
            frac = _to_f32(math.fmod(secrets, 1.0))
            if rng.Float() < frac:
                secrets = _to_f32(math.ceil(secrets))
            else:
                secrets = _to_f32(math.floor(secrets))

        self.region_secrets_this_run[region] -= int(secrets)
        return int(secrets)

    def create_secret_room(self, rng: SPDRandom) -> Room:
        index = rng.chances((6.0, 3.0, 1.0))
        while index >= len(self.run_secrets):
            index -= 1

        room_type = self.run_secrets[index]
        room = room_type()
        self.run_secrets.append(self.run_secrets.pop(index))
        return room
