"""Convert SPD-parity GenLevel output into the remake's FloorState.

`gen_level_to_floor_state()` maps SPD's terrain constants, mob stubs, item
stubs, traps, and doors to the existing ``FloorState`` / ``MobEntity`` /
``Item`` types so that ``spd_levelgen.build_floor()`` results can be dropped
directly into the game loop.
"""

import logging
import random as _random
import uuid
from typing import Dict, List, Optional, Tuple

_log = logging.getLogger(__name__)

from app.engine.dungeon.constants import RoomKind, TrapType, TrapVisual
from app.engine.dungeon.models import Room as LegacyRoom, TrapInfo
from app.engine.dungeon.spd_levelgen import terrain as spd_terrain
from app.engine.dungeon.spd_levelgen.level import GenLevel
from app.engine.dungeon.spd_levelgen.mob_spawner import GenMob
from app.engine.dungeon.spd_levelgen.room import DoorType
from app.engine.dungeon.spd_levelgen.traps import Trap as SpdTrap
from app.engine.dungeon.spd_levelgen.traps import (
    BurningTrap, BlazingTrap, ShockingTrap, StormTrap,
    ChillingTrap, ToxicTrap, PoisonDartTrap,
    ConfusionTrap, FlockTrap, SummoningTrap, TeleportationTrap, GatewayTrap,
    AlarmTrap, OozeTrap, GrippingTrap, GeyserTrap,
    FrostTrap, CorrosionTrap, RockfallTrap, GuardianTrap, WarpingTrap, PitfallTrap,
    DisintegrationTrap, FlashingTrap, WeakeningTrap,
    DisarmingTrap, CursingTrap, DistortionTrap, GrimTrap,
    ExplosiveTrap,
)
from app.engine.dungeon.generator import TileType
from app.engine.entities.base import EntityType, Position
from app.engine.entities.item_union import Chest
from app.engine.entities.items_consumable import Amulet, CorpseDust, Dewdrop, EnergyCrystal, Food, Gold, Key, Seed, Stone
from app.engine.entities.items_bombs import Bomb, MetalShard
from app.engine.entities.items_equip import Armor, ClothArmor, LeatherArmor, MailArmor, make_named_melee_weapon, PlateArmor, ScaleArmor
from app.engine.entities.items_potions import HealthPotion
from app.engine.entities.items_scrolls import Scroll
from app.engine.entities.items_wands import Wand
from app.engine.entities.player import Item, Mob as MobEntity, Weapon
from app.engine.dungeon.spd_levelgen.run_state import SCROLL_DEFAULT_PROBS_TOTAL
from app.engine.entities.item_catalog import FLOOR_SCROLL_KINDS, TRANSMUTE_GROUPS, make_catalog_item
from app.engine.entities.weapon_defs import WEP_TIER_ORDER
from app.engine.entities.quest_bosses import FetidRat, Ghost, GnollTrickster, GreatCrab
from app.engine.entities.wandmaker_quest import DustWraith, RotHeart, RotLasher, Wandmaker
from app.engine.entities.wandmaker_quest_items import CeremonialCandle
from app.engine.entities.trinkets import TrinketCatalyst
from app.engine.entities.mobs import (
    AcidicScorpio,
    AlbinoRat,
    ArmoredStatue,
    Bandit,
    Bat,
    Bee,
    BlueShaman,
    Brute,
    ArmoredBrute,
    BrightFist,
    BurningFist,
    CausticSlime,
    ChaosElemental,
    Crab,
    DarkFist,
    DKGhoul,
    DKGolem,
    DKMonk,
    DKWarlock,
    DM100,
    DM200,
    DM201,
    DM300,
    DemonSpawner,
    CrystalMimic,
    EbonyMimic,
    Eye,
    FireElemental,
    FrostElemental,
    Ghoul,
    Gnoll,
    GnollExile,
    GoldenMimic,
    Golem,
    Goo,
    Guard,
    HermitCrab,
    Imp,
    Mimic,
    Monk,
    Necromancer,
    PhantomPiranha,
    Piranha,
    PurpleShaman,
    Pylon,
    RatKing,
    Shopkeeper,
    Rat,
    RedShaman,
    RipperDemon,
    RottingFist,
    RustedFist,
    Scorpio,
    Senior,
    Sentry,
    ShockElemental,
    Skeleton,
    Slime,
    Snake,
    SoiledFist,
    SpectralNecromancer,
    Spinner,
    Statue,
    Succubus,
    Swarm,
    Tengu,
    Thief,
    TormentedSpirit,
    Warlock,
    Wraith,
    YogDzewa,
    YogEye,
    YogRipper,
    YogScorpio,
    DwarfKing,
)
from app.engine.game.floor_state import FloorState
from app.engine.dungeon.spd_levelgen.generator import RolledItem
from app.engine.entities.items_wands import (
    WandOfMagicMissile, WandOfLightning, WandOfDisintegration, WandOfFireblast,
    WandOfCorrosion, WandOfBlastWave, WandOfLivingEarth, WandOfFrost,
    WandOfPrismaticLight, WandOfWarding, WandOfTransfusion, WandOfCorruption,
    WandOfRegrowth,
)

# WAND deck index (generator.py's _WAND table order) -> concrete wand class /
# item-catalog kind string. Shared by _rolled_item_to_item's WAND branch and
# world.py's Wandmaker reward builder (both need to turn a bare deck index
# into a real Wand item).
WAND_KIND_BY_INDEX = [
    "wand_magic_missile",     # 0
    "wand_lightning",         # 1
    "wand_disintegration",    # 2
    "wand_fireblast",         # 3
    "wand_corrosion",         # 4
    "wand_blast_wave",        # 5
    "wand_living_earth",      # 6
    "wand_frost",             # 7
    "wand_prismatic_light",   # 8
    "wand_warding",            # 9
    "wand_transfusion",         # 10
    "wand_corruption",          # 11
    "wand_regrowth",            # 12
]
WAND_CLASS_BY_INDEX = [
    WandOfMagicMissile, WandOfLightning, WandOfDisintegration, WandOfFireblast,
    WandOfCorrosion, WandOfBlastWave, WandOfLivingEarth, WandOfFrost,
    WandOfPrismaticLight, WandOfWarding, WandOfTransfusion, WandOfCorruption,
    WandOfRegrowth,
]


def build_wand_item(idx: int, level: int, iid: Optional[str] = None,
                     pos: Optional[Position] = None, **extra) -> Item:
    """Builds a concrete Wand item from a WAND-deck index (see
    WAND_CLASS_BY_INDEX above). `extra` forwards additional constructor
    kwargs (e.g. cursed=False, cursed_known=False)."""
    iid = iid or str(uuid.uuid4())
    if 0 <= idx < len(WAND_CLASS_BY_INDEX):
        return WAND_CLASS_BY_INDEX[idx](id=iid, pos=pos, name=WAND_KIND_BY_INDEX[idx], level=level, **extra)
    return Wand(id=iid, pos=pos, name="Wand", level=level, **extra)

# SPD terrain constant -> remake TileType
_SPD_TO_TILE = {
    spd_terrain.CHASM: TileType.CHASM,
    spd_terrain.EMPTY: TileType.FLOOR,
    spd_terrain.GRASS: TileType.FLOOR_GRASS,
    spd_terrain.EMPTY_WELL: TileType.FLOOR,
    spd_terrain.WALL: TileType.WALL,
    spd_terrain.DOOR: TileType.DOOR,
    spd_terrain.OPEN_DOOR: TileType.OPEN_DOOR,
    spd_terrain.ENTRANCE: TileType.STAIRS_UP,
    spd_terrain.ENTRANCE_SP: TileType.STAIRS_UP,
    spd_terrain.EXIT: TileType.STAIRS_DOWN,
    spd_terrain.EMBERS: TileType.EMBERS,
    spd_terrain.LOCKED_DOOR: TileType.LOCKED_DOOR,
    spd_terrain.HERO_LKD_DR: TileType.LOCKED_DOOR,
    spd_terrain.CRYSTAL_DOOR: TileType.CRYSTAL_DOOR,
    spd_terrain.PEDESTAL: TileType.FLOOR,
    spd_terrain.WALL_DECO: TileType.WALL_DECO,
    spd_terrain.BARRICADE: TileType.BARRICADE,
    # SPD's DungeonTileSheet: directVisuals[EMPTY_SP] = FLOOR_SP = GROUND+4,
    # the same atlas slot as our FLOOR_WOOD -- the distinct "special room"
    # floor look (vault rooms: Library, Storage, Treasury, etc.), not plain
    # FLOOR. Collapsing it to FLOOR lost that visual identity.
    spd_terrain.EMPTY_SP: TileType.FLOOR_WOOD,
    spd_terrain.HIGH_GRASS: TileType.HIGH_GRASS,
    spd_terrain.FURROWED_GRASS: TileType.FURROWED_GRASS,
    spd_terrain.SECRET_DOOR: TileType.SECRET_DOOR,
    spd_terrain.SECRET_TRAP: TileType.SECRET_TRAP,
    spd_terrain.TRAP: TileType.TRAP,
    spd_terrain.INACTIVE_TRAP: TileType.INACTIVE_TRAP,
    spd_terrain.EMPTY_DECO: TileType.EMPTY_DECO,
    spd_terrain.LOCKED_EXIT: TileType.LOCKED_EXIT,
    spd_terrain.UNLOCKED_EXIT: TileType.FLOOR,
    spd_terrain.WELL: TileType.WELL,
    spd_terrain.BOOKSHELF: TileType.BOOKSHELF,
    spd_terrain.ALCHEMY: TileType.ALCHEMY,
    spd_terrain.CUSTOM_DECO: TileType.WALL_DECO,
    spd_terrain.CUSTOM_DECO_EMPTY: TileType.EMPTY_DECO,
    spd_terrain.STATUE: TileType.STATUE,
    spd_terrain.STATUE_SP: TileType.STATUE,
    spd_terrain.REGION_DECO: TileType.REGION_DECO,
    spd_terrain.REGION_DECO_ALT: TileType.REGION_DECO_ALT,
    spd_terrain.MINE_CRYSTAL: TileType.WALL,
    spd_terrain.MINE_BOULDER: TileType.WALL,
    spd_terrain.WATER: TileType.FLOOR_WATER,
}

# GenMob class-name string -> MobEntity subclass
_MOB_CLASSES: Dict[str, type[MobEntity]] = {
    "Rat": Rat,
    "Snake": Snake,
    "Gnoll": Gnoll,
    "Swarm": Swarm,
    "Crab": Crab,
    "Slime": Slime,
    "Albino": AlbinoRat,
    "GnollExile": GnollExile,
    "HermitCrab": HermitCrab,
    "CausticSlime": CausticSlime,
    "Goo": Goo,
    "Skeleton": Skeleton,
    "Thief": Thief,
    "DM100": DM100,
    "Guard": Guard,
    "Necromancer": Necromancer,
    "Bandit": Bandit,
    "SpectralNecromancer": SpectralNecromancer,
    "Bat": Bat,
    "Brute": Brute,
    "ArmoredBrute": ArmoredBrute,
    "Shaman": RedShaman,  # Java simple class name maps to RedShaman by convention
    "RedShaman": RedShaman,
    "BlueShaman": BlueShaman,
    "PurpleShaman": PurpleShaman,
    "Spinner": Spinner,
    "DM200": DM200,
    "DM201": DM201,
    "Ghoul": Ghoul,
    "FireElemental": FireElemental,
    "FrostElemental": FrostElemental,
    "ShockElemental": ShockElemental,
    "ChaosElemental": ChaosElemental,
    "Elemental": FireElemental,
    "Warlock": Warlock,
    "Monk": Monk,
    "Senior": Senior,
    "Golem": Golem,
    "Succubus": Succubus,
    "Eye": Eye,
    "Scorpio": Scorpio,
    "Acidic": AcidicScorpio,
    "AcidicScorpio": AcidicScorpio,
    "RipperDemon": RipperDemon,
    "Tengu": Tengu,
    "DM300": DM300,
    # Universal/Environmental
    "Wraith": Wraith,
    "TormentedSpirit": TormentedSpirit,
    "Piranha": Piranha,
    "PhantomPiranha": PhantomPiranha,
    "Mimic": Mimic,
    "GoldenMimic": GoldenMimic,
    "EbonyMimic": EbonyMimic,
    "CrystalMimic": CrystalMimic,
    "Statue": Statue,
    "ArmoredStatue": ArmoredStatue,
    "Sentry": Sentry,
    "Bee": Bee,
    # DwarfKing + minions
    "DwarfKing": DwarfKing,
    "DKGhoul": DKGhoul,
    "DKMonk": DKMonk,
    "DKWarlock": DKWarlock,
    "DKGolem": DKGolem,
    # YogDzewa + fists + summons
    "YogDzewa": YogDzewa,
    "BurningFist": BurningFist,
    "SoiledFist": SoiledFist,
    "RottingFist": RottingFist,
    "RustedFist": RustedFist,
    "BrightFist": BrightFist,
    "DarkFist": DarkFist,
    "YogEye": YogEye,
    "YogScorpio": YogScorpio,
    "YogRipper": YogRipper,
    # Static spawners
    "DemonSpawner": DemonSpawner,
    "Pylon": Pylon,
    "RatKing": RatKing,
    "Shopkeeper": Shopkeeper,
    "Imp": Imp,
    # Sewers Ghost quest (depths 2-4)
    "Ghost": Ghost,
    "FetidRat": FetidRat,
    "GnollTrickster": GnollTrickster,
    "GreatCrab": GreatCrab,
    # Prison Wandmaker quest (depths 6-9), Corpse Dust variant
    "Wandmaker": Wandmaker,
    "DustWraith": DustWraith,
    "RotHeart": RotHeart,
    "RotLasher": RotLasher,
}

# Trap class (SPD) -> remake TrapType
_SPD_TRAP_TYPE: Dict[type[SpdTrap], str] = {}


# SPD Generator.java SCROLL.classes order → remake scroll kind
_SPD_SCROLL_INDEX_TO_KIND = {
    0: "scroll_of_upgrade",
    1: "scroll_of_identify",
    2: "scroll_of_remove_curse",
    3: "scroll_of_mirror_image",
    4: "scroll_of_recharging",
    5: "scroll_of_teleportation",
    6: "scroll_of_lullaby",
    7: "scroll_of_magic_mapping",
    8: "scroll_of_rage",
    9: "scroll_of_retribution",
    10: "scroll_of_terror",
    11: "scroll_of_transmutation",
}
# Remake-only scrolls not in SPD (e.g. scroll_of_metamorphosis) get a small
# fixed weight so they remain possible but rare in floor loot.
_NON_SPD_SCROLL_WEIGHT = 0.5

def _random_scroll(iid: str, pos: Position) -> Item:
    pool = []
    weights = []
    for idx, kind in _SPD_SCROLL_INDEX_TO_KIND.items():
        w = SCROLL_DEFAULT_PROBS_TOTAL[idx]
        if w > 0:
            pool.append(kind)
            weights.append(w)
    for kind in FLOOR_SCROLL_KINDS:
        if kind not in pool:
            pool.append(kind)
            weights.append(_NON_SPD_SCROLL_WEIGHT)
    kind = _random.choices(pool, weights=weights, k=1)[0]
    item = make_catalog_item(kind)
    item.id = iid
    item.pos = pos
    return item


def _register_trap(spd_cls: type[SpdTrap], trap_type: str) -> None:
    _SPD_TRAP_TYPE[spd_cls] = trap_type


_register_trap(type("WornDartTrap", (SpdTrap,), {}), TrapType.WORN_DART)
_register_trap(BurningTrap, TrapType.BURNING_TRAP)
_register_trap(BlazingTrap, TrapType.BLAZING_TRAP)
_register_trap(ShockingTrap, TrapType.SHOCKING_TRAP)
_register_trap(StormTrap, TrapType.STORM_TRAP)
_register_trap(ChillingTrap, TrapType.CHILLING_TRAP)
_register_trap(ToxicTrap, TrapType.TOXIC_TRAP)
_register_trap(PoisonDartTrap, TrapType.POISON_DART_TRAP)
_register_trap(ConfusionTrap, TrapType.CONFUSION_TRAP)
_register_trap(FlockTrap, TrapType.FLOCK_TRAP)
_register_trap(SummoningTrap, TrapType.SUMMONING_TRAP)
_register_trap(TeleportationTrap, TrapType.TELEPORTATION_TRAP)
_register_trap(GatewayTrap, TrapType.GATEWAY_TRAP)
_register_trap(AlarmTrap, TrapType.ALARM_TRAP)
_register_trap(OozeTrap, TrapType.OOZE_TRAP)
_register_trap(GrippingTrap, TrapType.GRIPPING_TRAP)
_register_trap(GeyserTrap, TrapType.GEYSER_TRAP)
_register_trap(FrostTrap, TrapType.FROST_TRAP)
_register_trap(CorrosionTrap, TrapType.CORROSION_TRAP)
_register_trap(RockfallTrap, TrapType.ROCKFALL_TRAP)
_register_trap(GuardianTrap, TrapType.GUARDIAN_TRAP)
_register_trap(WarpingTrap, TrapType.WARPING_TRAP)
_register_trap(PitfallTrap, TrapType.PITFALL_TRAP)
_register_trap(DisintegrationTrap, TrapType.DISINTEGRATION_TRAP)
_register_trap(FlashingTrap, TrapType.FLASHING_TRAP)
_register_trap(WeakeningTrap, TrapType.WEAKENING_TRAP)
_register_trap(DisarmingTrap, TrapType.DISARMING_TRAP)
_register_trap(CursingTrap, TrapType.CURSING_TRAP)
_register_trap(DistortionTrap, TrapType.DISTORTION_TRAP)
_register_trap(GrimTrap, TrapType.GRIM_TRAP)
_register_trap(ExplosiveTrap, TrapType.EXPLOSIVE_TRAP)


def _convert_tile(val: int) -> int:
    return _SPD_TO_TILE.get(val, TileType.FLOOR)


def _convert_room(spd_room) -> LegacyRoom:
    # SPD's left/right/top/bottom are the wall tiles themselves (doors sit
    # exactly on them); LegacyRoom.x/y/width/height describe the floor
    # interior only, with walls living one tile outside on every side
    # (see LegacyRoom.is_perimeter). Shrink by one tile on each side so the
    # two conventions line up.
    w = spd_room.right - spd_room.left - 1
    h = spd_room.bottom - spd_room.top - 1
    kind = RoomKind.STANDARD
    from app.engine.dungeon.spd_levelgen.room_types import SecretRoom, SpecialRoom
    if isinstance(spd_room, SecretRoom):
        kind = RoomKind.HIDDEN
    elif isinstance(spd_room, SpecialRoom):
        kind = RoomKind.SPECIAL
    return LegacyRoom(
        x=spd_room.left + 1,
        y=spd_room.top + 1,
        width=w,
        height=h,
        kind=kind,
        room_id=id(spd_room) & 0xFFFF,
    )


def _room_ids_by_kind(rooms: List[LegacyRoom]) -> Dict[str, List[int]]:
    by_kind: Dict[str, List[int]] = {RoomKind.STANDARD: [], RoomKind.SPECIAL: [], RoomKind.HIDDEN: []}
    for room in rooms:
        by_kind.setdefault(room.kind, []).append(room.room_id)
    return by_kind


def _spawn_mob(gen_mob: GenMob, width: int) -> MobEntity:
    cls = _MOB_CLASSES.get(gen_mob.cls_name)
    if cls is None:
        cls = Rat
    pos = gen_mob.pos
    x = pos % width
    y = pos // width
    # Don't override faction here: most mobs default to Faction.DUNGEON, but
    # NPCs (Shopkeeper, Imp, RatKing) override their class default to
    # Faction.PLAYER so players don't attack them on contact.
    mob = cls(id=str(uuid.uuid4()), pos=Position(x=x, y=y))
    # Set floor_level for depth-scaled mobs
    if hasattr(mob, 'floor_level'):
        mob.floor_level = gen_mob.depth
    if isinstance(mob, Sentry) and gen_mob.extra:
        left, top, right, bottom = gen_mob.extra["room"]
        mob.watch_room = [left, top, right, bottom]
        mob.sentry_depth = gen_mob.extra.get("depth", gen_mob.depth)
        # SPD's charge delay is turn-based (curChargeDelay -= hero.cooldown());
        # ~20 ticks/turn matches the tick rate other charge-up AI (Eye) uses.
        mob.initial_charge_ticks = max(1, round(gen_mob.extra["charge_delay"] * 20))
    return mob


def _spawn_item(heap_items: list, cell_x: int, cell_y: int) -> Item:
    for item in heap_items:
        if isinstance(item, Item):
            return item.model_copy(update={"id": str(uuid.uuid4()), "pos": Position(x=cell_x, y=cell_y)})
        if isinstance(item, RolledItem):
            return _rolled_item_to_item(item, cell_x, cell_y)
        if isinstance(item, frozenset):
            return _descriptor_to_item(item, cell_x, cell_y)
    return Gold(id=str(uuid.uuid4()), pos=Position(x=cell_x, y=cell_y))


_CHEST_TYPE_NAMES = {
    "CHEST": "Chest",
    "LOCKED_CHEST": "Locked Chest",
    "CRYSTAL_CHEST": "Crystal Chest",
    "TOMB": "Tomb",
    "SKELETON": "Skeleton",
    "REMAINS": "Remains",
}


def _spawn_chest(heap, cell_x: int, cell_y: int) -> Optional[Chest]:
    from app.engine.dungeon.spd_levelgen.generator import RolledItem
    chest_type = getattr(heap, "type", "HEAP")
    name = _CHEST_TYPE_NAMES.get(chest_type)
    if name is None:
        return None
    raw_items = list(getattr(heap, "items", []))
    item_category: Optional[str] = None
    contents = []
    for it in raw_items:
        if isinstance(it, RolledItem):
            item_category = it.category
            spawned = _rolled_item_to_item(it, cell_x, cell_y)
            if spawned:
                contents.append(spawned)
        else:
            spawned = _spawn_item([it], cell_x, cell_y)
            if spawned:
                contents.append(spawned)
    return Chest(
        id=str(uuid.uuid4()),
        name=name,
        pos=Position(x=cell_x, y=cell_y),
        chest_type=chest_type,
        contents=contents,
        item_category=item_category,
    )


def _make_melee_weapon(tier_category: str, item_index: int, level: int, iid: str, pos: Position) -> Item:
    """Builds a concrete melee weapon for a WEP_T1..WEP_T5 roll, picking the
    weapon name via `item_index` (the deck index already consumed by
    generator.py)."""
    name = WEP_TIER_ORDER[tier_category][item_index]
    return make_named_melee_weapon(name, level=level, id=iid, pos=pos)


def _rolled_item_to_item(ri: RolledItem, cx: int, cy: int) -> Item:
    iid = str(uuid.uuid4())
    pos = Position(x=cx, y=cy)
    if ri.category == "GOLD":
        return Gold(id=iid, pos=pos, name="Gold")
    if ri.category == "POTION":
        return HealthPotion(id=iid, pos=pos)
    if ri.category == "SCROLL":
        return _random_scroll(iid, pos)
    if ri.category == "FOOD":
        return Food(id=iid, pos=pos, name="Food")
    if ri.category == "SEED":
        return Seed(id=iid, pos=pos, name="Seed")
    if ri.category == "STONE":
        return Stone(id=iid, pos=pos, damage=1, range=5)
    if ri.category in ("WAND",):
        return build_wand_item(ri.item_index, ri.level, iid=iid, pos=pos)
    if ri.category in WEP_TIER_ORDER:
        return _make_melee_weapon(ri.category, ri.item_index, ri.level, iid, pos)
    if ri.category == "WEAPON":
        return Weapon(id=iid, pos=pos, name="Weapon", damage=2 + ri.level, range=1,
                      strength_requirement=10, attack_cooldown=2.0)
    if ri.category == "ARMOR":
        _ARMOR_TYPES = {1: ClothArmor, 2: LeatherArmor, 3: MailArmor, 4: ScaleArmor, 5: PlateArmor}
        _tier = min(max(1, ri.tier), 5)
        return _ARMOR_TYPES[_tier](id=iid, pos=pos, level=ri.level)
    if ri.category in ("MISSILE", "MIS_T1", "MIS_T2", "MIS_T3", "MIS_T4", "MIS_T5"):
        return Stone(id=iid, pos=pos, name="Missile", damage=1 + ri.level, range=5)
    if ri.category == "RING":
        from app.engine.entities.items_equip import Ring
        return Ring(id=iid, pos=pos, name="Ring")
    if ri.category == "ARTIFACT":
        from app.engine.entities.items_artifacts import AlchemistsToolkit, ChaliceOfBlood, CloakOfShadows, DriedRose, EtherealChains, HolyTome, HornOfPlenty, MasterThievesArmband, SandalsOfNature, SkeletonKey, TalismanOfForesight, TimekeepersHourglass, UnstableSpellbook
        from app.engine.entities.items_equip import Artifact
        # SPD Generator.Category.ARTIFACT.classes order (index -> class).
        # Indices 2 (Cloak) and 5 (Tome) have prob 0 -> never drawn from the
        # deck, but mapped defensively.
        _ARTIFACT_MAP = [
            AlchemistsToolkit,      # 0
            ChaliceOfBlood,         # 1
            CloakOfShadows,         # 2
            DriedRose,              # 3
            EtherealChains,         # 4
            HolyTome,               # 5
            HornOfPlenty,           # 6
            MasterThievesArmband,   # 7
            SandalsOfNature,        # 8
            SkeletonKey,            # 9
            TalismanOfForesight,    # 10
            TimekeepersHourglass,   # 11
            UnstableSpellbook,      # 12
        ]
        idx = ri.item_index
        if 0 <= idx < len(_ARTIFACT_MAP):
            return _ARTIFACT_MAP[idx](id=iid, pos=pos, cursed=ri.cursed)
        return Artifact(id=iid, pos=pos, name="Artifact")
    return Gold(id=iid, pos=pos, name="Gold")


_DESCRIPTOR_ITEM_MAP = {
    "PotionOfStrength": lambda iid, pos: HealthPotion(id=iid, pos=pos),
    "Scroll": lambda iid, pos: _random_scroll(iid, pos),
    "Runestone": lambda iid, pos: Stone(id=iid, pos=pos, name="Runestone", damage=1, range=5),
    "TrinketCatalyst": lambda iid, pos: TrinketCatalyst(id=iid, pos=pos, name="Trinket Catalyst"),
    "IronKey": lambda iid, pos: Key(id=iid, pos=pos, name="Iron Key", key_id="iron"),
    "GoldenKey": lambda iid, pos: Key(id=iid, pos=pos, name="Golden Key", key_id="golden"),
    "CrystalKey": lambda iid, pos: Key(id=iid, pos=pos, name="Crystal Key", key_id="crystal"),
    "Amulet": lambda iid, pos: Amulet(id=iid, pos=pos, name="Amulet of Yendor"),
    "GuidePage": lambda iid, pos: Scroll(id=iid, pos=pos, name="Guide Page"),
    "DocumentPage": lambda iid, pos: Scroll(id=iid, pos=pos, name="Document Page"),
    "Food": lambda iid, pos: Food(id=iid, pos=pos, name="Food"),
    "EnergyCrystal": lambda iid, pos: EnergyCrystal(id=iid, pos=pos),
    "Potion": lambda iid, pos: HealthPotion(id=iid, pos=pos),
    "Bomb": lambda iid, pos: Bomb(id=iid, pos=pos),
    "MetalShard": lambda iid, pos: MetalShard(id=iid, pos=pos),
    "Gold": lambda iid, pos: Gold(id=iid, pos=pos, name="Gold"),
    "Weapon": lambda iid, pos: Weapon(id=iid, pos=pos, name="Weapon", damage=2, range=1, strength_requirement=10, attack_cooldown=2.0),
    "Armor": lambda iid, pos: PlateArmor(id=iid, pos=pos),
    "CorpseDust": lambda iid, pos: CorpseDust(id=iid, pos=pos),
    "CeremonialCandle": lambda iid, pos: CeremonialCandle(id=iid, pos=pos),
}


def _descriptor_to_item(descriptor: frozenset, cx: int, cy: int) -> Item:
    iid = str(uuid.uuid4())
    pos = Position(x=cx, y=cy)
    item = None
    for key, factory in _DESCRIPTOR_ITEM_MAP.items():
        if key in descriptor:
            item = factory(iid, pos)
            break
    if item is None:
        item = HealthPotion(id=iid, pos=pos)
    # "qty:<n>" tags thread SPD drop quantities through the descriptor set.
    for tag in descriptor:
        if isinstance(tag, str) and tag.startswith("qty:"):
            item.quantity = int(tag[4:])
    return item


def _convert_plants(gen_level: GenLevel, w: int) -> Dict[Tuple[int, int], object]:
    """Port of Level.plants: seed descriptors dropped by PlantsRoom/GrassyGraveRoom's
    tall-grass patches. Surfaced for future plant-growth/proc integration --
    no runtime Plant system consumes this yet (tracked separately)."""
    plants: Dict[Tuple[int, int], object] = {}
    for cell, seed in getattr(gen_level, "plants", {}).items():
        plants[(cell % w, cell // w)] = seed
    return plants


def _convert_traps(gen_level: GenLevel, w: int) -> Dict[Tuple[int, int], TrapInfo]:
    traps: Dict[Tuple[int, int], TrapInfo] = {}
    for cell, spd_trap in gen_level.traps.items():
        x = cell % w
        y = cell // w
        trap_type_name = type(spd_trap).__name__
        trap_type = _SPD_TRAP_TYPE.get(type(spd_trap), TrapType.WORN_DART)
        traps[(x, y)] = TrapInfo(
            x=x, y=y, trap_type=trap_type,
            hidden=not spd_trap.visible,
            active=True,
            can_be_searched=getattr(spd_trap, 'can_be_searched', True),
        )
    return traps


def _extract_doors(gen_level: GenLevel, width: int, height: int) -> Tuple[Dict[Tuple[int, int], int], Dict[Tuple[int, int], str]]:
    hidden_doors: Dict[Tuple[int, int], int] = {}
    locked_doors: Dict[Tuple[int, int], str] = {}
    for cell in range(len(gen_level.map)):
        spd_val = gen_level.map[cell]
        x = cell % width
        y = cell // width
        if spd_val == spd_terrain.SECRET_DOOR:
            hidden_doors[(x, y)] = TileType.DOOR
        elif spd_val in (spd_terrain.LOCKED_DOOR, spd_terrain.HERO_LKD_DR):
            locked_doors[(x, y)] = "iron"
        elif spd_val == spd_terrain.CRYSTAL_DOOR:
            locked_doors[(x, y)] = "crystal"
        elif spd_val == spd_terrain.LOCKED_EXIT:
            locked_doors[(x, y)] = "goo_door"
    return hidden_doors, locked_doors


def _apply_depth_scaling_mimic(mob: "CrystalMimic", depth: int) -> None:
    """Set base stats for a crystal mimic (depth scaling applied at runtime)."""
    level = depth
    mob.floor_level = level
    mob.max_hp = (1 + level) * 6
    mob.hp = mob.max_hp
    mob.defense_skill = 2 + level // 2
    mob.attack_skill = 6 + level


def _adapt_gen_mobs_and_items(gen_mobs, width: int):
    """Convert GenMob list to (mobs dict, extra_items dict).

    CrystalMimic: spawn mob entity + fake Chest item at same position.
    Regular Mimic/GoldenMimic: extract items only (not yet real entities).
    Ghost: spawn mob and wire ghost_quest (handled via caller).
    """
    from app.engine.dungeon.spd_levelgen.generator import RolledItem
    from app.engine.entities.base import Faction
    mobs: Dict[str, MobEntity] = {}
    extra_items: Dict[str, Item] = {}
    for gen_mob in gen_mobs:
        if not isinstance(gen_mob, GenMob):
            continue
        pos = gen_mob.pos
        x = pos % width
        y = pos // width
        if gen_mob.cls_name == "CrystalMimic":
            mob = CrystalMimic(
                id=str(uuid.uuid4()),
                pos=Position(x=x, y=y),
                faction=Faction.DUNGEON,
                disguised=True,
            )
            _apply_depth_scaling_mimic(mob, 0)
            ri_items = [it for it in gen_mob.items if isinstance(it, RolledItem)]
            item_category = ri_items[0].category if ri_items else None
            fake_chest = Chest(
                id=str(uuid.uuid4()),
                name="Crystal Chest",
                pos=Position(x=x, y=y),
                chest_type="CRYSTAL_CHEST",
                contents=[],
                item_category=item_category,
                mimic_hint=True,
            )
            mob.fake_chest_id = fake_chest.id
            mobs[mob.id] = mob
            extra_items[fake_chest.id] = fake_chest
        elif gen_mob.cls_name in ("Mimic", "GoldenMimic") and gen_mob.items:
            item = _spawn_item(gen_mob.items, x, y)
            extra_items[item.id] = item
        else:
            mob = _spawn_mob(gen_mob, width)
            mobs[mob.id] = mob
    return mobs, extra_items


def gen_level_to_floor_state(gen_level: GenLevel, depth: int) -> FloorState:
    w = gen_level.width()
    h = gen_level.height()
    grid: List[List[int]] = []
    for y in range(h):
        row: List[int] = []
        for x in range(w):
            cell = x + y * w
            spd_val = gen_level.map[cell]
            row.append(_convert_tile(spd_val))
        grid.append(row)

    from app.engine.dungeon.spd_levelgen.connection_rooms import ConnectionRoom
    rooms = [_convert_room(r) for r in gen_level.rooms
             if hasattr(r, 'left') and not isinstance(r, ConnectionRoom)]

    mobs, extra_items = _adapt_gen_mobs_and_items(gen_level.mobs, w)

    # Ghost quest (sewers depths 2-4): wire ghost_quest.ghost_id to the live mob id.
    for gen_mob in gen_level.mobs:
        if isinstance(gen_mob, GenMob) and gen_mob.cls_name == "Ghost" and gen_level.run_state is not None:
            # find the spawned Ghost mob by position
            pos = gen_mob.pos
            x = pos % w
            y = pos // w
            for mob in mobs.values():
                if mob.pos.x == x and mob.pos.y == y and type(mob).__name__ == "Ghost":
                    gen_level.run_state.ghost_quest.ghost_id = mob.id
                    break

    items: Dict[str, Item] = {}
    for cell, heap in gen_level.heaps.items():
        x = cell % w
        y = cell // w
        item = _spawn_chest(heap, x, y) or _spawn_item(heap.items, x, y)
        items[item.id] = item
    items.update(extra_items)

    traps = _convert_traps(gen_level, w)
    plants = _convert_plants(gen_level, w)
    hidden_doors, locked_doors = _extract_doors(gen_level, w, h)

    key_spawns: Dict[str, Tuple[int, int]] = {}

    alchemy_pots: List[Tuple[int, int]] = []
    for cell, spd_val in enumerate(gen_level.map):
        if spd_val == spd_terrain.ALCHEMY:
            alchemy_pots.append((cell % w, cell // w))

    region = "sewers" if depth <= 5 else "prison" if depth <= 10 else "caves" if depth <= 15 else "city" if depth <= 20 else "halls"

    magic_wells = [
        {**well, "pos": (well["pos"] % w, well["pos"] // w)}
        for well in getattr(gen_level, 'magic_wells', [])
    ]
    sacrifice_fires = [
        {**fire, "pos": (fire["pos"] % w, fire["pos"] // w)}
        for fire in getattr(gen_level, 'sacrifice_fires', [])
    ]

    try:
        entrance_cell = gen_level.entrance()
        entrance_pos: Optional[Tuple[int, int]] = (entrance_cell % w, entrance_cell // w)
    except ValueError:
        entrance_pos = None
    except AttributeError:
        _log.warning("gen_level missing entrance() method — GenLevel subclass issue?")
        entrance_pos = None
    try:
        exit_cell = gen_level.exit()
        exit_pos: Optional[Tuple[int, int]] = (exit_cell % w, exit_cell // w)
    except ValueError:
        exit_pos = None
    except AttributeError:
        _log.warning("gen_level missing exit() method — GenLevel subclass issue?")
        exit_pos = None

    floor = FloorState(
        floor_id=depth,
        grid=grid,
        rooms=rooms,
        mobs=mobs,
        items=items,
        region=region,
        hidden_doors=hidden_doors,
        locked_doors=locked_doors,
        traps=traps,
        plants=plants,
        key_spawns=key_spawns,
        generation_meta={
            "seed": str(getattr(gen_level, '_seed', '')),
            "spd_generated": True,
            "layout_kind": getattr(gen_level, 'layout_kind', 'loop'),
            "room_ids_by_kind": _room_ids_by_kind(rooms),
            "magic_wells": magic_wells,
            "sacrifice_fires": sacrifice_fires,
            **({"imp_shop_room": gen_level.imp_shop_room, "imp_shop_spawned": False}
               if hasattr(gen_level, 'imp_shop_room') else {}),
        },
        dk_summon_spots=list(getattr(gen_level, 'dk_summon_spots', [])),
        yog_pos=getattr(gen_level, 'yog_pos', None),
        custom_tiles=list(getattr(gen_level, 'custom_tiles', [])),
        custom_walls=list(getattr(gen_level, 'custom_walls', [])),
        torches=list(getattr(gen_level, 'torches', [])),
        alchemy_pots=alchemy_pots,
        entrance_pos=entrance_pos,
        exit_pos=exit_pos,
    )
    floor.rebuild_flags()
    return floor
