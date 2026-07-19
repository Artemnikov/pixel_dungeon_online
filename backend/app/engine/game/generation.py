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
"""Floor generation and content spawning for GameInstance.

Generates each depth's layout using SPD-parity generation, then populates it
with mobs, items, traps.
"""

import random
import uuid
from typing import List, Tuple, Type

from app.engine.dungeon.constants import TileType
from app.engine.dungeon.dungeon_seed import seed_for_depth
from app.engine.entities.base import EntityType, Faction, Position
from app.engine.entities.items_consumable import Boomerang, SmallRation, Ration, Pasty, Key, Stone, ThrowableDagger
from app.engine.entities.items_equip import Armor, Bow, ClothArmor, ScaleArmor, LeatherArmor, MailArmor
from app.engine.entities.items_potions import HealthPotion, RevivingPotion, FuryPotion, PotionOfStrength, PotionOfHaste, PotionOfInvisibility, PotionOfLevitation, PotionOfMindVision, PotionOfFrost, PotionOfLiquidFlame, PotionOfToxicGas, PotionOfParalyticGas, PotionOfPurity, PotionOfExperience
from app.engine.entities.items_scrolls import ScrollOfRage, ScrollOfUpgrade, ScrollOfIdentify, ScrollOfMagicMapping, ScrollOfTeleportation, ScrollOfRemoveCurse, ScrollOfRecharging, ScrollOfLullaby, ScrollOfTerror, ScrollOfMirrorImage, ScrollOfRetribution, ScrollOfTransmutation
from app.engine.entities.player import Mob as MobEntity, Weapon
from app.engine.entities.runestones import (
    StoneOfBlast, StoneOfBlink, StoneOfDeepSleep, StoneOfClairvoyance,
    StoneOfAggression, StoneOfFlock, StoneOfShock, StoneOfFear,
    StoneOfDetectMagic, StoneOfIntuition, StoneOfEnchantment, StoneOfAugmentation,
)
from app.engine.entities.mobs import (
    Rat, Snake, Gnoll, Swarm, Crab, Slime,
    AlbinoRat, GnollExile, HermitCrab, CausticSlime,
    Goo,
    Skeleton, Thief, DM100, Guard, Necromancer,
)
from app.engine.game.constants import MAP_HEIGHT, MAP_WIDTH, MAX_FLOOR_ID, SEWERS_MAX_FLOOR, PRISON_MAX_FLOOR
from app.engine.game.spd_adapter import gen_level_to_floor_state
from app.engine.dungeon.spd_levelgen.run_state import is_boss_level
from app.engine.game.floor_state import FloorState


class GenerationMixin:
    def generate_floor(self, depth: int) -> FloorState:
        depth = max(1, min(MAX_FLOOR_ID, depth))
        self.depth = depth

        floor = self._generate_floor_spd(depth)

        self.floors[depth] = floor
        return floor

    def _trinket_state(self) -> dict:
        """Compute levelgen-relevant trinket multipliers from the first player."""
        from app.engine.entities.trinkets import trinket_level as _tl
        state = {}
        for name in ("rat_skull", "petrified_seed", "exotic_crystals",
                     "mossy_clump", "dimensional_sundial", "trap_mechanism",
                     "mimic_tooth", "parchment_scrap", "wondrous_resin"):
            state[name] = -1
        if not self.players:
            return state
        p = next((p for p in self.players.values() if hasattr(p, "belongings")), None)
        if not p:
            return state
        for name in state:
            state[name] = _tl(p, name)
        return state

    def _trinket_apply_post_spawn(self, floor: FloorState):
        """Post-processing for levelgen trinket effects after SPD gen."""
        import random
        from app.engine.entities.trinkets import (
            RatSkull,
            MimicTooth,
            ExoticCrystals,
        )
        state = self._trinket_state()

        # RatSkull: swap some mobs to alts (RARE_ALTS from mob_spawner)
        rs_lvl = state["rat_skull"]
        if rs_lvl >= 0:
            from app.engine.entities.trinkets import RatSkull
            from app.engine.dungeon.spd_levelgen.mob_spawner import RARE_ALTS
            mult = RatSkull.exotic_chance_multiplier(rs_lvl)
            alt_chance = (1.0 / 50.0) * mult
            from app.engine.entities.mobs import (
                Rat, Gnoll, Crab, Slime, Thief, Necromancer, Brute,
                DM200, Monk, Scorpio,
                AlbinoRat, GnollExile, HermitCrab, CausticSlime,
                Bandit, SpectralNecromancer, ArmoredBrute,
                DM201, Senior, Acidic,
            )
            ALT_MAP = {
                Rat: AlbinoRat, Gnoll: GnollExile, Crab: HermitCrab,
                Slime: CausticSlime, Thief: Bandit, Necromancer: SpectralNecromancer,
                Brute: ArmoredBrute, DM200: DM201, Monk: Senior,
                Scorpio: Acidic,
            }
            for mob_id, mob in list(floor.mobs.items()):
                cls = type(mob)
                alt_cls = ALT_MAP.get(cls)
                if alt_cls and random.random() < alt_chance:
                    new_mob = alt_cls(
                        id=mob_id,
                        pos=mob.pos,
                        faction=mob.faction,
                        hp=mob.hp,
                        max_hp=mob.max_hp,
                        attack_skill=mob.attack_skill,
                        defense_skill=mob.defense_skill,
                        damage_min=mob.damage_min,
                        damage_max=mob.damage_max,
                    )
                    floor.mobs[mob_id] = new_mob

        # ExoticCrystals: swap some potions/scrolls to exotic variants
        ec_lvl = state["exotic_crystals"]
        if ec_lvl >= 0:
            from app.engine.entities.trinkets import ExoticCrystals
            exo_chance = ExoticCrystals.consumable_exotic_chance(ec_lvl)
            _exotic_potion_map = {
                "health_potion": "exotic_health",
                "potion_of_strength": "exotic_strength",
                "potion_of_haste": "exotic_haste",
            }
            for item_id, item in list(floor.items.items()):
                kind = getattr(item, "kind", "")
                if kind in ("potion",) and random.random() < exo_chance:
                    from app.engine.entities.items_potions import HealthPotion
                    floor.items[item_id] = HealthPotion(
                        id=item_id, pos=item.pos, name="Exotic Potion"
                    )

        # MimicTooth: convert some chests to mimics
        mt_lvl = state["mimic_tooth"]
        if mt_lvl >= 0:
            from app.engine.entities.trinkets import MimicTooth
            mult = MimicTooth.mimic_chance_multiplier(mt_lvl)
            extra_mimic_chance = (mult - 1.0) / 4.0
            from app.engine.entities.item_union import Chest as ChestCls
            from app.engine.entities.mobs import Mimic as MimicMob
            for item_id, item in list(floor.items.items()):
                if isinstance(item, ChestCls) and item.chest_type == "CHEST":
                    if random.random() < extra_mimic_chance:
                        mimic = MimicMob(
                            id=str(uuid.uuid4()),
                            pos=item.pos,
                            faction=Faction.DUNGEON,
                            disguised=True,
                        )
                        mimic.carried_items = [
                            c.model_copy(deep=True) for c in getattr(item, "contents", [])
                        ]
                        fake_chest = ChestCls(
                            id=str(uuid.uuid4()),
                            name="Chest",
                            pos=item.pos,
                            chest_type="CHEST",
                            contents=[],
                            mimic_hint=True,
                        )
                        mimic.fake_chest_id = fake_chest.id
                        floor.mobs[mimic.id] = mimic
                        del floor.items[item_id]
                        floor.items[fake_chest.id] = fake_chest

    def _generate_floor_spd(self, depth: int) -> FloorState:
        import random
        from app.engine.dungeon.spd_random import SPDRandom
        from app.engine.dungeon.spd_levelgen.boss_level import build_boss_floor
        from app.engine.dungeon.spd_levelgen.last_level import build_last_level
        from app.engine.dungeon.spd_levelgen.regular_level import build_floor

        floor_seed = seed_for_depth(self.master_seed, depth, 0)
        rng = SPDRandom()
        rng.push_generator(floor_seed)

        state = self._trinket_state()
        mossy_chance = 0.0
        trap_chance = 0.0
        if state["mossy_clump"] >= 0:
            from app.engine.entities.trinkets import MossyClump
            mossy_chance = MossyClump.override_normal_level_chance(state["mossy_clump"])
        if state["trap_mechanism"] >= 0:
            from app.engine.entities.trinkets import TrapMechanism
            trap_chance = TrapMechanism.override_normal_level_chance(state["trap_mechanism"])

        if depth == 26:
            gen_level, _rooms = build_last_level(rng, depth, self.run_state)
        elif is_boss_level(depth):
            gen_level, _rooms = build_boss_floor(rng, depth, self.run_state)
        else:
            gen_level, _rooms = build_floor(rng, depth, self.run_state,
                                            mossy_chance, trap_chance)
        rng.pop_generator()

        floor = gen_level_to_floor_state(gen_level, depth)

        if "stronger_bosses" in self.challenges:
            from app.engine.entities.mobs import Goo
            for mob in floor.mobs.values():
                if isinstance(mob, Goo):
                    mob.hp = 120
                    mob.max_hp = 120

        self._apply_party_loot_bonus(floor)
        self._trinket_apply_post_spawn(floor)

        return floor

    def _apply_party_loot_bonus(self, floor: FloorState) -> None:
        """Online-only, no SPD equivalent: extra potions/scrolls scaled by
        live co-op party size (party_loot_multiplier), layered on top of
        SPD-parity generation rather than perturbing its RNG sequence.

        Scales off THIS floor's own just-generated potion/scroll count
        (general category rolls + the guaranteed Potion of
        Strength/Scroll of Upgrade minimums -- both already materialize as
        plain Potion/Scroll instances by this point, see
        spd_adapter._DESCRIPTOR_ITEM_MAP, so they can't be told apart and
        are scaled together) rather than a hand-tuned rate, so a 5-player
        party (3x) ends up with ~3x this floor's own potions and ~3x its
        own scrolls regardless of depth/region/special-room variance.
        """
        from app.engine.game.constants import party_loot_multiplier
        from app.engine.game.world import _random_free_cell
        from app.engine.game.spd_adapter import _random_scroll, _random_potion
        from app.engine.entities.items_potions import Potion
        from app.engine.entities.items_scrolls import Scroll

        alive = len([p for p in self.players.values() if p.is_alive])
        mult = party_loot_multiplier(alive)
        if mult <= 1.0:
            return
        extra = mult - 1.0

        base_potions = sum(1 for it in floor.items.values() if isinstance(it, Potion))
        base_scrolls = sum(1 for it in floor.items.values() if isinstance(it, Scroll))

        def rolled_count(rate: float) -> int:
            c = rate * extra
            cnt = 0
            while c > 0:
                if random.random() < min(c, 1.0):
                    cnt += 1
                c -= 1.0
            return cnt

        def drop(make_item) -> None:
            cell = _random_free_cell(floor)
            if cell is None:
                return
            x, y = cell
            item = make_item(x, y)
            floor.items[item.id] = item

        for _ in range(rolled_count(base_potions)):
            drop(lambda x, y: _random_potion(str(uuid.uuid4()), Position(x=x, y=y)))
        for _ in range(rolled_count(base_scrolls)):
            drop(lambda x, y: _random_scroll(str(uuid.uuid4()), Position(x=x, y=y)))

    def _get_sewers_rotation(self, floor_id: int) -> List[Type[MobEntity]]:
        rotations = {
            1: [Rat, Rat, Rat, Snake],
            2: [Rat, Rat, Snake, Gnoll, Gnoll],
            3: [Rat, Snake, Gnoll, Gnoll, Gnoll, Swarm, Crab],
            4: [Gnoll, Swarm, Crab, Crab, Slime, Slime],
        }
        return rotations.get(floor_id, [Rat])

    def _get_prison_rotation(self, floor_id: int) -> List[Type[MobEntity]]:
        rotations = {
            6: [Skeleton, Skeleton, Thief, DM100],
            7: [Skeleton, Thief, DM100, DM100, Guard],
            8: [Thief, DM100, Guard, Guard, Necromancer],
            9: [DM100, Guard, Necromancer, Necromancer],
        }
        return rotations.get(floor_id, [Skeleton])

    def _get_mob_limit(self, floor_id: int) -> int:
        if floor_id == 1:
            return 8
        if floor_id <= 4:
            return 3 + floor_id % 5 + random.randint(0, 2)
        return 5 + floor_id

    def _spawn_mob_at(self, cls: Type[MobEntity], x: int, y: int) -> MobEntity:
        mob_id = str(uuid.uuid4())
        # attack_cooldown comes from the mob class, decoupled from movement
        # `speed` (a fast mover chases quicker but does not attack quicker).
        mob = cls(id=mob_id, pos=Position(x=x, y=y), faction=Faction.DUNGEON)
        return mob

    def _spawn_content(self, floor: FloorState):
        floor_tiles = [
            (x, y)
            for y in range(floor.height)
            for x in range(floor.width)
            if floor.grid[y][x] in [
                TileType.FLOOR,
                TileType.FLOOR_WOOD,
                TileType.FLOOR_WATER,
                TileType.FLOOR_COBBLE,
                TileType.FLOOR_GRASS,
            ]
        ]

        self._spawn_floor_keys(floor)
        blocked_item_tiles = {
            (item.pos.x, item.pos.y) for item in floor.items.values() if item.pos is not None
        }
        if blocked_item_tiles:
            floor_tiles = [pos for pos in floor_tiles if pos not in blocked_item_tiles]
        mob_spawn_tiles = list(floor_tiles)

        if floor.floor_id % 5 == 0:
            self._spawn_boss(floor, mob_spawn_tiles)

        if floor.floor_id != 5 and floor.floor_id != 10:
            if floor.floor_id <= SEWERS_MAX_FLOOR:
                rotation = self._get_sewers_rotation(floor.floor_id)
                rare_chance = 0.02
                rare_alts = {
                    Rat: AlbinoRat,
                    Gnoll: GnollExile,
                    Crab: HermitCrab,
                    Slime: CausticSlime,
                }
            elif floor.floor_id <= PRISON_MAX_FLOOR:
                rotation = self._get_prison_rotation(floor.floor_id)
                rare_chance = 0.0
                rare_alts = {}
            else:
                rotation = self._get_sewers_rotation(floor.floor_id)
                rare_chance = 0.02
                rare_alts = {
                    Rat: AlbinoRat,
                    Gnoll: GnollExile,
                    Crab: HermitCrab,
                    Slime: CausticSlime,
                }
            mob_limit = self._get_mob_limit(floor.floor_id)
            floor.mob_limit = mob_limit

            spawn_count = mob_limit if floor.floor_id != 1 else min(mob_limit, len(rotation) * 2)
            for i in range(spawn_count):
                if not mob_spawn_tiles:
                    break
                x, y = mob_spawn_tiles.pop(random.randint(0, len(mob_spawn_tiles) - 1))
                cls = rotation[i % len(rotation)]
                rare_cls = rare_alts.get(cls)
                if rare_cls and random.random() < rare_chance:
                    cls = rare_cls
                mob = self._spawn_mob_at(cls, x, y)
                floor.mobs[mob.id] = mob

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

        num_items = 4 + random.randint(0, 3)
        for _ in range(num_items):
            if not floor_tiles:
                break
            x, y = floor_tiles.pop(random.randint(0, len(floor_tiles) - 1))
            item_id = str(uuid.uuid4())

            rand = random.random()
            if rand < 0.2:
                floor.items[item_id] = Weapon(
                    id=item_id,
                    name=random.choice(["Rusty Sword", "Wooden Club", "Dagger"]),
                    pos=Position(x=x, y=y),
                    damage=2 + random.randint(0, 2),
                    range=1,
                    strength_requirement=10 + random.randint(-2, 2),
                    attack_cooldown=3.0 if "Dagger" not in "Rusty Sword, Wooden Club" else 1.5,
                )
            elif rand < 0.3:
                floor.items[item_id] = Bow(
                    id=item_id,
                    name="Old Bow",
                    pos=Position(x=x, y=y),
                    damage=2 + random.randint(0, 2),
                    strength_requirement=10,
                    attack_cooldown=3.5,
                )
            # Thresholds below rescaled by 7/6 after the unique never-dropping

            # Staff's 10%-wide band (rand<0.4) was removed, so armor/throwables/
            # potion/scroll/food keep their original relative proportions instead
            # of armor silently absorbing the freed probability mass.
            elif rand < 0.53:
                armor_tiers = [
                    ClothArmor,
                    LeatherArmor,
                    MailArmor,
                    ScaleArmor,
                ]
                tier_idx = min(len(armor_tiers) - 1, (floor.floor_id - 1) // 4)
                cls = random.choice(armor_tiers[:tier_idx + 1])
                floor.items[item_id] = cls(id=item_id, pos=Position(x=x, y=y))
            elif rand < 0.59:
                t_rand = random.random()
                if t_rand < 0.5:
                    floor.items[item_id] = Stone(id=item_id, pos=Position(x=x, y=y), damage=1, range=5)
                elif t_rand < 0.8:
                    floor.items[item_id] = ThrowableDagger(id=item_id, pos=Position(x=x, y=y), damage=4, range=4)
                else:
                    floor.items[item_id] = Boomerang(id=item_id, pos=Position(x=x, y=y), damage=3, range=6)
            elif rand < 0.77:
                cls = random.choice(_ALL_POTIONS)
                floor.items[item_id] = cls(id=item_id, pos=Position(x=x, y=y))
            elif rand < 0.92:
                cls = random.choice(_ALL_SCROLLS)
                floor.items[item_id] = cls(id=item_id, pos=Position(x=x, y=y))
            elif rand < 0.97:
                cls = random.choice(_ALL_RUNESTONES)
                floor.items[item_id] = cls(id=item_id, pos=Position(x=x, y=y))
            else:
                cls = random.choice(_ALL_FOOD)
                floor.items[item_id] = cls(id=item_id, pos=Position(x=x, y=y))


    def _spawn_floor_keys(self, floor: FloorState):
        for key_id, (x, y) in floor.key_spawns.items():
            item_id = str(uuid.uuid4())
            floor.items[item_id] = Key(
                id=item_id,
                name="Rusty Key",
                pos=Position(x=x, y=y),
                key_id=key_id,
            )

    def _spawn_boss(self, floor: FloorState, floor_tiles: List[Tuple[int, int]]):
        if floor.floor_id in (5, 10, 15, 20, 25):
            # Bosses for these floors are placed by the boss floor builder (spd_adapter)
            return
        else:
            if not floor_tiles:
                return
            x, y = floor_tiles.pop(random.randint(0, len(floor_tiles) - 1))
            boss_id = str(uuid.uuid4())
            floor.mobs[boss_id] = MobEntity(
                id=boss_id,
                type=EntityType.BOSS,
                name=f"Floor {floor.floor_id} Boss",
                pos=Position(x=x, y=y),
                hp=100 + (floor.floor_id * 20),
                max_hp=100 + (floor.floor_id * 20),
                attack=10 + floor.floor_id,
                defense=5 + floor.floor_id,
                attack_cooldown=3.0,
                faction=Faction.DUNGEON,
                exp=10 + floor.floor_id,
            )
