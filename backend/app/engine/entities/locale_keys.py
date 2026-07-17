"""Locale key derivation for items and mobs.

Maps entity class names and names to locale keys used by the frontend i18n
system.  Auto-derived from class name (camelCase → snake_case) with a few
manual overrides for edge cases (DM-300, runic names, etc.).
"""

import re
from typing import Optional


def _camel_to_snake(name: str) -> str:
    """Convert CamelCase or mixed-case to snake_case.

    >>> _camel_to_snake("HealthPotion")
    'health_potion'
    >>> _camel_to_snake("DM300")
    'dm300'
    >>> _camel_to_snake("YogDzewa")
    'yog_dzewa'
    >>> _camel_to_snake("ScrollOfUpgrade")
    'scroll_of_upgrade'
    >>> _camel_to_snake("Shortsword")
    'shortsword'
    """
    s = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', name)
    s = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', '_', s)
    return s.lower()


# Chest is a single class covering several Heap.Type variants (chest_type
# field); auto-deriving from the class name alone would collapse Tomb/
# LockedChest/CrystalChest/Skeleton/Remains into "item.chest".
_CHEST_TYPE_KEYS: dict[str, str] = {
    "CHEST": "item.chest",
    "LOCKED_CHEST": "item.locked_chest",
    "CRYSTAL_CHEST": "item.crystal_chest",
    "TOMB": "item.tomb",
    "SKELETON": "item.skeleton",
    "REMAINS": "item.remains",
}


# Manual overrides for class/name → locale key where auto-derivation would be
# wrong or ambiguous.
_ITEM_OVERRIDES: dict[str, str] = {
    "ElixirOfAquaticRejuvenation": "item.elixir_of_aquatic_rejuvenation",
    "CloakOfShadows": "item.cloak_of_shadows",
    "ScrollHolder": "item.scroll_holder",
    "TenguMask": "item.tengus_mask",
    "MagicalHolster": "item.magical_holster",
    "PotionBandolier": "item.potion_bandolier",
    "VelvetPouch": "item.velvet_pouch",
    "DwarfToken": "item.dwarf_token",
    "KingsCrown": "item.kings_crown",
    "BrokenSeal": "item.broken_seal",
    "RevivingPotion": "item.reviving_potion",
    "FuryPotion": "item.fury_potion",
    "ChargrilledMeat": "item.chargrilled_meat",
    "MysteryMeat": "item.mystery_meat",
    "ThrowableDagger": "item.throwable_dagger",
    "SmallRation": "item.small_ration",
    "PotionOfStrength": "item.potion_of_strength",
    "PotionOfHaste": "item.potion_of_haste",
    "PotionOfInvisibility": "item.potion_of_invisibility",
    "PotionOfLevitation": "item.potion_of_levitation",
    "PotionOfMindVision": "item.potion_of_mind_vision",
    "PotionOfFrost": "item.potion_of_frost",
    "PotionOfLiquidFlame": "item.potion_of_liquid_flame",
    "PotionOfToxicGas": "item.potion_of_toxic_gas",
    "PotionOfParalyticGas": "item.potion_of_paralytic_gas",
    "PotionOfPurity": "item.potion_of_purity",
    "PotionOfExperience": "item.potion_of_experience",
    "ScrollOfRage": "item.scroll_of_rage",
    "ScrollOfMetamorphosis": "item.scroll_of_metamorphosis",
    "ScrollOfUpgrade": "item.scroll_of_upgrade",
    "ScrollOfIdentify": "item.scroll_of_identify",
    "ScrollOfMagicMapping": "item.scroll_of_magic_mapping",
    "ScrollOfTeleportation": "item.scroll_of_teleportation",
    "ScrollOfRemoveCurse": "item.scroll_of_remove_curse",
    "ScrollOfRecharging": "item.scroll_of_recharging",
    "ScrollOfLullaby": "item.scroll_of_lullaby",
    "ScrollOfTerror": "item.scroll_of_terror",
    "ScrollOfMirrorImage": "item.scroll_of_mirror_image",
    "ScrollOfRetribution": "item.scroll_of_retribution",
    "ScrollOfTransmutation": "item.scroll_of_transmutation",
}

_MOB_OVERRIDES: dict[str, str] = {
    "DM100": "mob.dm100",
    "DM200": "mob.dm200",
    "DM201": "mob.dm201",
    "DM300": "mob.dm300",
    "DKGhoul": "mob.dk_ghoul",
    "DKMonk": "mob.dk_monk",
    "DKWarlock": "mob.dk_warlock",
    "DKGolem": "mob.dk_golem",
    "YogDzewa": "mob.yog_dzewa",
    "YogEye": "mob.yog_eye",
    "YogScorpio": "mob.yog_scorpio",
    "YogRipper": "mob.yog_ripper",
    "GnollExile": "mob.gnoll_exile",
    "HermitCrab": "mob.hermit_crab",
    "CausticSlime": "mob.caustic_slime",
    "AlbinoRat": "mob.albino_rat",
    "ArmoredBrute": "mob.armored_brute",
    "RedShaman": "mob.red_shaman",
    "BlueShaman": "mob.blue_shaman",
    "PurpleShaman": "mob.purple_shaman",
    "FireElemental": "mob.fire_elemental",
    "FrostElemental": "mob.frost_elemental",
    "ShockElemental": "mob.shock_elemental",
    "ChaosElemental": "mob.chaos_elemental",
    "NecroSkeleton": "mob.necro_skeleton",
    "AcidicScorpio": "mob.acidic_scorpio",
    "RipperDemon": "mob.ripper_demon",
    "SpectralNecromancer": "mob.spectral_necromancer",
    "TormentedSpirit": "mob.tormented_spirit",
    "PhantomPiranha": "mob.phantom_piranha",
    "GoldenMimic": "mob.golden_mimic",
    "EbonyMimic": "mob.ebony_mimic",
    "ArmoredStatue": "mob.armored_statue",
    "DwarfKing": "mob.dwarf_king",
    "DemonSpawner": "mob.demon_spawner",
    "RatKing": "mob.rat_king",
    "MirrorImage": "mob.mirror_image",
    "GhostHeroMob": "mob.ghost_hero",
    "BurningFist": "mob.burning_fist",
    "SoiledFist": "mob.soiled_fist",
    "RottingFist": "mob.rotting_fist",
    "RustedFist": "mob.rusted_fist",
    "BrightFist": "mob.bright_fist",
    "DarkFist": "mob.dark_fist",
}

# Mapping of name strings for generated items (MeleeWeapon, etc.) to locale keys.
_GENERATED_ITEM_NAME_MAP: dict[str, str] = {
    "Gloves": "item.gloves",
    "Rapier": "item.rapier",
    "Cudgel": "item.cudgel",
    "Shortsword": "item.shortsword",
    "Hand Axe": "item.hand_axe",
    "Spear": "item.spear",
    "Quarterstaff": "item.quarterstaff",
    "Dirk": "item.dirk",
    "Sickle": "item.sickle",
    "Sword": "item.sword",
    "Mace": "item.mace",
    "Scimitar": "item.scimitar",
    "Round Shield": "item.round_shield",
    "Sai": "item.sai",
    "Whip": "item.whip",
    "Longsword": "item.longsword",
    "Battle Axe": "item.battle_axe",
    "Flail": "item.flail",
    "Runic Blade": "item.runic_blade",
    "Assassin's Blade": "item.assassins_blade",
    "Crossbow": "item.crossbow",
    "Katana": "item.katana",
    "Greatsword": "item.greatsword",
    "War Hammer": "item.war_hammer",
    "Glaive": "item.glaive",
    "Greataxe": "item.greataxe",
    "Greatshield": "item.greatshield",
    "Gauntlet": "item.gauntlet",
    "War Scythe": "item.war_scythe",
    "Worn Shortsword": "item.worn_shortsword",
    "Short Sword": "item.shortsword",
    "Dagger": "item.dagger",
    "Throwing Knife": "item.throwing_knife",
    "Scale Armor": "item.scale_armor",
    "Plate Armor": "item.plate_armor",
    "Chain Armor": "item.chain_armor",
    "Mail Armor": "item.mail_armor",
    "Leather Armor": "item.leather_armor",
    "Cloth Armor": "item.cloth_armor",
    "Pickaxe": "item.pickaxe",
}

# Items whose `kind` can serve as a locale key directly.
_KIND_AS_KEY: dict[str, str] = {
    "dagger": "item.dagger",
    "bow": "item.bow",
    # "staff" intentionally excluded — Staff name is dynamic (depends on imbued wand).
    "boomerang": "item.boomerang",
    "stone": "item.stone",
    "dewdrop": "item.dewdrop",
    "waterskin": "item.waterskin",
    "berry": "item.berry",
    "gold": "item.gold",
}


def item_locale_key(item) -> Optional[str]:
    """Derive the locale key for an item instance.

    Uses class name overrides first, falls back to auto-derivation from name
    for generated items, and finally auto-derives from class name.

    Returns ``None`` for base/abstract types that should not be translated
    (e.g. untyped potion/scroll base classes).
    """
    cls = item.__class__.__name__

    # Chest covers multiple Heap.Type variants via chest_type; key off that
    # before the generic class-name derivation collapses them all to "chest".
    if cls == "Chest":
        chest_type = getattr(item, "chest_type", "CHEST")
        return _CHEST_TYPE_KEYS.get(chest_type, "item.chest")

    # Concrete class override.
    if cls in _ITEM_OVERRIDES:
        return _ITEM_OVERRIDES[cls]

    # Kind-based lookup for items with a kind that uniquely identifies them.
    kind = getattr(item, "kind", "")
    if kind in _KIND_AS_KEY:
        return _KIND_AS_KEY[kind]

    # Generated items (MeleeWeapon, Armor) — derive from name.
    name = getattr(item, "name", "")
    if name in _GENERATED_ITEM_NAME_MAP:
        return _GENERATED_ITEM_NAME_MAP[name]
    # Also try lowercase.
    name_lower = name.lower()
    for key, val in _GENERATED_ITEM_NAME_MAP.items():
        if key.lower() == name_lower:
            return val

    # Auto-derive from class name.
    # Skip base/abstract classes that have no fixed identity.
    if cls in (
        "ItemBase", "EquipableItem", "KindOfWeapon", "MeleeWeapon", "Staff",
        "MissileWeapon", "Armor", "KindofMisc", "Ring", "Artifact",
        "Wand", "Potion", "Scroll", "Food", "Key", "Gold", "Throwable",
        "Seed", "Scenery", "Bag", "Stone",
    ):
        return None

    return f"item.{_camel_to_snake(cls)}"


def mob_locale_key(mob) -> Optional[str]:
    """Derive the locale key for a mob instance."""
    cls = mob.__class__.__name__

    if cls in _MOB_OVERRIDES:
        return _MOB_OVERRIDES[cls]

    # Skip base class.
    if cls in ("Entity", "Mob", "MobEntity"):
        return None

    return f"mob.{_camel_to_snake(cls)}"
