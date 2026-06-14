from typing import Dict, Optional, List, Set

from pydantic import BaseModel, Field


class Subclass:
    WARDEN = "warden"
    BERSERKER = "berserker"
    GLADIATOR = "gladiator"
    # Rogue
    ASSASSIN = "assassin"
    FREERUNNER = "freerunner"
    # Mage
    BATTLEMAGE = "battlemage"
    WARLOCK = "warlock"
    # Huntress
    SNIPER = "sniper"


# Which subclasses each hero class may choose at level 6.
CLASS_SUBCLASSES: Dict[str, tuple[str, ...]] = {
    "warrior": (Subclass.BERSERKER, Subclass.GLADIATOR),
    "rogue": (Subclass.ASSASSIN, Subclass.FREERUNNER),
    "mage": (Subclass.BATTLEMAGE, Subclass.WARLOCK),
    "huntress": (Subclass.SNIPER, Subclass.WARDEN),
}


class ArmorAbilityType:
    HEROIC_LEAP = "heroic_leap"
    SHOCKWAVE = "shockwave"
    ENDURE = "endure"
    # Rogue
    SMOKE_BOMB = "smoke_bomb"
    DEATH_MARK = "death_mark"
    SHADOW_CLONE = "shadow_clone"
    # Mage
    ELEMENTAL_BLAST = "elemental_blast"
    WILD_MAGIC = "wild_magic"
    WARP_BEACON = "warp_beacon"
    # Huntress
    SPECTRAL_BLADES = "spectral_blades"
    NATURES_POWER = "natures_power"
    SPIRIT_HAWK = "spirit_hawk"


class Talent:
    # Tier 1 (level 2, universal, 2pts)
    HEARTY_MEAL = "hearty_meal"
    VETERANS_INTUITION = "veterans_intuition"
    PROVOKED_ANGER = "provoked_anger"
    IRON_WILL = "iron_will"

    # Tier 2 (level 7, universal, 2pts)
    IRON_STOMACH = "iron_stomach"
    LIQUID_WILLPOWER = "liquid_willpower"
    RUNIC_TRANSFERENCE = "runic_transference"
    LETHAL_MOMENTUM = "lethal_momentum"
    IMPROVISED_PROJECTILES = "improvised_projectiles"

    # Tier 3 (level 13, 3pts) — universal (requires subclass)
    HOLD_FAST = "hold_fast"
    STRONGMAN = "strongman"

    # Tier 3 — Berserker (3pts)
    ENDLESS_RAGE = "endless_rage"
    DEATHLESS_FURY = "deathless_fury"
    ENRAGED_CATALYST = "enraged_catalyst"

    # Tier 3 — Gladiator (3pts)
    CLEAVE = "cleave"
    LETHAL_DEFENSE = "lethal_defense"
    ENHANCED_COMBO = "enhanced_combo"

    # Tier 4 (level 21, 4pts) — Heroic Leap
    BODY_SLAM = "body_slam"
    IMPACT_WAVE = "impact_wave"
    DOUBLE_JUMP = "double_jump"

    # Tier 4 — Shockwave
    EXPANDING_WAVE = "expanding_wave"
    STRIKING_WAVE = "striking_wave"
    SHOCK_FORCE = "shock_force"

    # Tier 4 — Endure
    SUSTAINED_RETRIBUTION = "sustained_retribution"
    SHRUG_IT_OFF = "shrug_it_off"
    EVEN_THE_ODDS = "even_the_odds"

    # Tier 4 — universal (charge cost reduction)
    HEROIC_ENERGY = "heroic_energy"

    # ===================== ROGUE =====================
    # Tier 1 (level 2)
    CACHED_RATIONS = "cached_rations"
    THIEFS_INTUITION = "thiefs_intuition"
    SUCKER_PUNCH = "sucker_punch"
    PROTECTIVE_SHADOWS = "protective_shadows"

    # Tier 2 (level 7)
    MYSTICAL_MEAL = "mystical_meal"
    INSCRIBED_STEALTH = "inscribed_stealth"
    WIDE_SEARCH = "wide_search"
    SILENT_STEPS = "silent_steps"
    ROGUES_FORESIGHT = "rogues_foresight"

    # Tier 3 (level 13) — class
    ENHANCED_RINGS = "enhanced_rings"
    LIGHT_CLOAK = "light_cloak"
    # Tier 3 — Assassin
    ENHANCED_LETHALITY = "enhanced_lethality"
    ASSASSINS_REACH = "assassins_reach"
    BOUNTY_HUNTER = "bounty_hunter"
    # Tier 3 — Freerunner
    EVASIVE_ARMOR = "evasive_armor"
    PROJECTILE_MOMENTUM = "projectile_momentum"
    SPEEDY_STEALTH = "speedy_stealth"
    # Tier 4 (level 21) — Smoke Bomb
    HASTY_RETREAT = "hasty_retreat"
    BODY_REPLACEMENT = "body_replacement"
    SHADOW_STEP = "shadow_step"
    # Tier 4 — Death Mark
    FEAR_THE_REAPER = "fear_the_reaper"
    DEATHLY_DURABILITY = "deathly_durability"
    DOUBLE_MARK = "double_mark"
    # Tier 4 — Shadow Clone
    SHADOW_BLADE = "shadow_blade"
    CLONED_ARMOR = "cloned_armor"
    PERFECT_COPY = "perfect_copy"

    # ===================== MAGE =====================
    # Tier 1 (level 2)
    EMPOWERING_MEAL = "empowering_meal"
    SCHOLARS_INTUITION = "scholars_intuition"
    LINGERING_MAGIC = "lingering_magic"
    BACKUP_BARRIER = "backup_barrier"
    # Tier 2 (level 7)
    ENERGIZING_MEAL = "energizing_meal"
    INSCRIBED_POWER = "inscribed_power"
    WAND_PRESERVATION = "wand_preservation"
    ARCANE_VISION = "arcane_vision"
    SHIELD_BATTERY = "shield_battery"
    # Tier 3 (level 13) — class
    DESPERATE_POWER = "desperate_power"
    ALLY_WARP = "ally_warp"
    # Tier 3 — Battlemage
    EMPOWERED_STRIKE = "empowered_strike"
    MYSTICAL_CHARGE = "mystical_charge"
    EXCESS_CHARGE = "excess_charge"
    # Tier 3 — Warlock
    SOUL_EATER = "soul_eater"
    SOUL_SIPHON = "soul_siphon"
    NECROMANCERS_MINIONS = "necromancers_minions"
    # Tier 3 — armor ability selection
    ELEMENTAL_BLAST_ABILITY = "elemental_blast_talent"
    WILD_MAGIC_ABILITY = "wild_magic_talent"
    WARP_BEACON_ABILITY = "warp_beacon_talent"
    # Tier 4 (level 21) — Elemental Blast
    BLAST_RADIUS = "blast_radius"
    ELEMENTAL_POWER_TALENT = "elemental_power_talent"
    REACTIVE_BARRIER = "reactive_barrier"
    # Tier 4 — Wild Magic
    WILD_POWER = "wild_power"
    FIRE_EVERYTHING = "fire_everything"
    CONSERVED_MAGIC = "conserved_magic"
    # Tier 4 — Warp Beacon
    TELEFRAG = "telefrag"
    REMOTE_BEACON = "remote_beacon"
    LONGRANGE_WARP = "longrange_warp"

    # ===================== HUNTRESS =====================
    # Tier 1 (level 2)
    NATURES_BOUNTY = "natures_bounty"
    SURVIVALISTS_INTUITION = "survivalists_intuition"
    FOLLOWUP_STRIKE = "followup_strike"
    NATURES_AID = "natures_aid"
    # Tier 2 (level 7)
    INVIGORATING_MEAL = "invigorating_meal"
    LIQUID_NATURE = "liquid_nature"
    REJUVENATING_STEPS = "rejuvenating_steps"
    HEIGHTENED_SENSES = "heightened_senses"
    DURABLE_PROJECTILES = "durable_projectiles"
    # Tier 3 (level 13) — class
    POINT_BLANK = "point_blank"
    SEER_SHOT = "seer_shot"
    # Tier 3 — Sniper
    FARSIGHT = "farsight"
    SHARED_ENCHANTMENT = "shared_enchantment"
    SHARED_UPGRADES = "shared_upgrades"
    # Tier 3 — Warden
    DURABLE_TIPS = "durable_tips"
    BARKSKIN = "barkskin"
    SHIELDING_DEW = "shielding_dew"
    # Tier 3 — armor ability selection
    SPECTRAL_BLADES_ABILITY = "spectral_blades_talent"
    NATURES_POWER_ABILITY = "natures_power_talent"
    SPIRIT_HAWK_ABILITY = "spirit_hawk_talent"
    # Tier 4 (level 21) — Spectral Blades
    FAN_OF_BLADES = "fan_of_blades"
    PROJECTING_BLADES = "projecting_blades"
    SPIRIT_BLADES = "spirit_blades"
    # Tier 4 — Natures Power
    GROWING_POWER = "growing_power"
    NATURES_WRATH = "natures_wrath"
    WILD_MOMENTUM = "wild_momentum"
    # Tier 4 — Spirit Hawk
    EAGLE_EYE = "eagle_eye"
    GO_FOR_THE_EYES = "go_for_the_eyes"
    SWIFT_SPIRIT = "swift_spirit"


# Maps talent name → (max_points, tier, subclass_required_or_None)
TALENT_DEFS: Dict[str, tuple[int, int, Optional[str]]] = {
    # Tier 1 — universal
    Talent.HEARTY_MEAL: (2, 1, None),
    Talent.VETERANS_INTUITION: (2, 1, None),
    Talent.PROVOKED_ANGER: (2, 1, None),
    Talent.IRON_WILL: (2, 1, None),
    # Tier 2 — universal
    Talent.IRON_STOMACH: (2, 2, None),
    Talent.LIQUID_WILLPOWER: (2, 2, None),
    Talent.RUNIC_TRANSFERENCE: (2, 2, None),
    Talent.LETHAL_MOMENTUM: (2, 2, None),
    Talent.IMPROVISED_PROJECTILES: (2, 2, None),
    # Tier 3 — universal (requires subclass)
    Talent.HOLD_FAST: (3, 3, None),
    Talent.STRONGMAN: (3, 3, None),
    # Tier 3 — Berserker
    Talent.ENDLESS_RAGE: (3, 3, Subclass.BERSERKER),
    Talent.DEATHLESS_FURY: (3, 3, Subclass.BERSERKER),
    Talent.ENRAGED_CATALYST: (3, 3, Subclass.BERSERKER),
    # Tier 3 — Gladiator
    Talent.CLEAVE: (3, 3, Subclass.GLADIATOR),
    Talent.LETHAL_DEFENSE: (3, 3, Subclass.GLADIATOR),
    Talent.ENHANCED_COMBO: (3, 3, Subclass.GLADIATOR),
    # Tier 4 — Heroic Leap
    Talent.BODY_SLAM: (4, 4, None),
    Talent.IMPACT_WAVE: (4, 4, None),
    Talent.DOUBLE_JUMP: (4, 4, None),
    # Tier 4 — Shockwave
    Talent.EXPANDING_WAVE: (4, 4, None),
    Talent.STRIKING_WAVE: (4, 4, None),
    Talent.SHOCK_FORCE: (4, 4, None),
    # Tier 4 — Endure
    Talent.SUSTAINED_RETRIBUTION: (4, 4, None),
    Talent.SHRUG_IT_OFF: (4, 4, None),
    Talent.EVEN_THE_ODDS: (4, 4, None),
    # Tier 4 — universal
    Talent.HEROIC_ENERGY: (4, 4, None),

    # ===================== ROGUE =====================
    # Tier 1
    Talent.CACHED_RATIONS: (2, 1, None),
    Talent.THIEFS_INTUITION: (2, 1, None),
    Talent.SUCKER_PUNCH: (2, 1, None),
    Talent.PROTECTIVE_SHADOWS: (2, 1, None),
    # Tier 2
    Talent.MYSTICAL_MEAL: (2, 2, None),
    Talent.INSCRIBED_STEALTH: (2, 2, None),
    Talent.WIDE_SEARCH: (2, 2, None),
    Talent.SILENT_STEPS: (2, 2, None),
    Talent.ROGUES_FORESIGHT: (2, 2, None),
    # Tier 3 — class
    Talent.ENHANCED_RINGS: (3, 3, None),
    Talent.LIGHT_CLOAK: (3, 3, None),
    # Tier 3 — Assassin
    Talent.ENHANCED_LETHALITY: (3, 3, Subclass.ASSASSIN),
    Talent.ASSASSINS_REACH: (3, 3, Subclass.ASSASSIN),
    Talent.BOUNTY_HUNTER: (3, 3, Subclass.ASSASSIN),
    # Tier 3 — Freerunner
    Talent.EVASIVE_ARMOR: (3, 3, Subclass.FREERUNNER),
    Talent.PROJECTILE_MOMENTUM: (3, 3, Subclass.FREERUNNER),
    Talent.SPEEDY_STEALTH: (3, 3, Subclass.FREERUNNER),
    # Tier 4 — Smoke Bomb
    Talent.HASTY_RETREAT: (4, 4, None),
    Talent.BODY_REPLACEMENT: (4, 4, None),
    Talent.SHADOW_STEP: (4, 4, None),
    # Tier 4 — Death Mark
    Talent.FEAR_THE_REAPER: (4, 4, None),
    Talent.DEATHLY_DURABILITY: (4, 4, None),
    Talent.DOUBLE_MARK: (4, 4, None),
    # Tier 4 — Shadow Clone
    Talent.SHADOW_BLADE: (4, 4, None),
    Talent.CLONED_ARMOR: (4, 4, None),
    Talent.PERFECT_COPY: (4, 4, None),

    # ===================== MAGE =====================
    # Tier 1
    Talent.EMPOWERING_MEAL: (2, 1, None),
    Talent.SCHOLARS_INTUITION: (2, 1, None),
    Talent.LINGERING_MAGIC: (2, 1, None),
    Talent.BACKUP_BARRIER: (2, 1, None),
    # Tier 2
    Talent.ENERGIZING_MEAL: (2, 2, None),
    Talent.INSCRIBED_POWER: (2, 2, None),
    Talent.WAND_PRESERVATION: (2, 2, None),
    Talent.ARCANE_VISION: (2, 2, None),
    Talent.SHIELD_BATTERY: (2, 2, None),
    # Tier 3 — class
    Talent.DESPERATE_POWER: (3, 3, None),
    Talent.ALLY_WARP: (3, 3, None),
    # Tier 3 — Battlemage
    Talent.EMPOWERED_STRIKE: (3, 3, Subclass.BATTLEMAGE),
    Talent.MYSTICAL_CHARGE: (3, 3, Subclass.BATTLEMAGE),
    Talent.EXCESS_CHARGE: (3, 3, Subclass.BATTLEMAGE),
    # Tier 3 — Warlock
    Talent.SOUL_EATER: (3, 3, Subclass.WARLOCK),
    Talent.SOUL_SIPHON: (3, 3, Subclass.WARLOCK),
    Talent.NECROMANCERS_MINIONS: (3, 3, Subclass.WARLOCK),
    # Tier 3 — armor ability selection
    Talent.ELEMENTAL_BLAST_ABILITY: (1, 3, None),
    Talent.WILD_MAGIC_ABILITY: (1, 3, None),
    Talent.WARP_BEACON_ABILITY: (1, 3, None),
    # Tier 4 — Elemental Blast
    Talent.BLAST_RADIUS: (4, 4, None),
    Talent.ELEMENTAL_POWER_TALENT: (4, 4, None),
    Talent.REACTIVE_BARRIER: (4, 4, None),
    # Tier 4 — Wild Magic
    Talent.WILD_POWER: (4, 4, None),
    Talent.FIRE_EVERYTHING: (4, 4, None),
    Talent.CONSERVED_MAGIC: (4, 4, None),
    # Tier 4 — Warp Beacon
    Talent.TELEFRAG: (4, 4, None),
    Talent.REMOTE_BEACON: (4, 4, None),
    Talent.LONGRANGE_WARP: (4, 4, None),

    # ===================== HUNTRESS =====================
    # Tier 1
    Talent.NATURES_BOUNTY: (2, 1, None),
    Talent.SURVIVALISTS_INTUITION: (2, 1, None),
    Talent.FOLLOWUP_STRIKE: (2, 1, None),
    Talent.NATURES_AID: (2, 1, None),
    # Tier 2
    Talent.INVIGORATING_MEAL: (2, 2, None),
    Talent.LIQUID_NATURE: (2, 2, None),
    Talent.REJUVENATING_STEPS: (2, 2, None),
    Talent.HEIGHTENED_SENSES: (2, 2, None),
    Talent.DURABLE_PROJECTILES: (2, 2, None),
    # Tier 3 — class
    Talent.POINT_BLANK: (3, 3, None),
    Talent.SEER_SHOT: (3, 3, None),
    # Tier 3 — Sniper
    Talent.FARSIGHT: (3, 3, Subclass.SNIPER),
    Talent.SHARED_ENCHANTMENT: (3, 3, Subclass.SNIPER),
    Talent.SHARED_UPGRADES: (3, 3, Subclass.SNIPER),
    # Tier 3 — Warden
    Talent.DURABLE_TIPS: (3, 3, Subclass.WARDEN),
    Talent.BARKSKIN: (3, 3, Subclass.WARDEN),
    Talent.SHIELDING_DEW: (3, 3, Subclass.WARDEN),
    # Tier 3 — armor ability selection
    Talent.SPECTRAL_BLADES_ABILITY: (1, 3, None),
    Talent.NATURES_POWER_ABILITY: (1, 3, None),
    Talent.SPIRIT_HAWK_ABILITY: (1, 3, None),
    # Tier 4 — Spectral Blades
    Talent.FAN_OF_BLADES: (4, 4, None),
    Talent.PROJECTING_BLADES: (4, 4, None),
    Talent.SPIRIT_BLADES: (4, 4, None),
    # Tier 4 — Natures Power
    Talent.GROWING_POWER: (4, 4, None),
    Talent.NATURES_WRATH: (4, 4, None),
    Talent.WILD_MOMENTUM: (4, 4, None),
    # Tier 4 — Spirit Hawk
    Talent.EAGLE_EYE: (4, 4, None),
    Talent.GO_FOR_THE_EYES: (4, 4, None),
    Talent.SWIFT_SPIRIT: (4, 4, None),
}


# Talents restricted to a hero class (the engine otherwise gates only by
# subclass). Talents absent from this map are available to any class.
TALENT_CLASS_REQ: Dict[str, str] = {
    # Warrior
    Talent.HEARTY_MEAL: "warrior", Talent.VETERANS_INTUITION: "warrior",
    Talent.PROVOKED_ANGER: "warrior", Talent.IRON_WILL: "warrior",
    Talent.IRON_STOMACH: "warrior", Talent.LIQUID_WILLPOWER: "warrior",
    Talent.RUNIC_TRANSFERENCE: "warrior", Talent.LETHAL_MOMENTUM: "warrior",
    Talent.IMPROVISED_PROJECTILES: "warrior",
    Talent.HOLD_FAST: "warrior", Talent.STRONGMAN: "warrior",
    Talent.ENDLESS_RAGE: "warrior", Talent.DEATHLESS_FURY: "warrior", Talent.ENRAGED_CATALYST: "warrior",
    Talent.CLEAVE: "warrior", Talent.LETHAL_DEFENSE: "warrior", Talent.ENHANCED_COMBO: "warrior",
    Talent.BODY_SLAM: "warrior", Talent.IMPACT_WAVE: "warrior", Talent.DOUBLE_JUMP: "warrior",
    Talent.EXPANDING_WAVE: "warrior", Talent.STRIKING_WAVE: "warrior", Talent.SHOCK_FORCE: "warrior",
    Talent.SUSTAINED_RETRIBUTION: "warrior", Talent.SHRUG_IT_OFF: "warrior", Talent.EVEN_THE_ODDS: "warrior",
    # NOTE: HEROIC_ENERGY is intentionally absent — it's a shared T4 universal
    # talent available to any class once T4 is unlocked (see _belongs_to_class
    # in main.py for the per-class talent-list special case).
    # Rogue
    Talent.CACHED_RATIONS: "rogue", Talent.THIEFS_INTUITION: "rogue",
    Talent.SUCKER_PUNCH: "rogue", Talent.PROTECTIVE_SHADOWS: "rogue",
    Talent.MYSTICAL_MEAL: "rogue", Talent.INSCRIBED_STEALTH: "rogue",
    Talent.WIDE_SEARCH: "rogue", Talent.SILENT_STEPS: "rogue", Talent.ROGUES_FORESIGHT: "rogue",
    Talent.ENHANCED_RINGS: "rogue", Talent.LIGHT_CLOAK: "rogue",
    Talent.HASTY_RETREAT: "rogue", Talent.BODY_REPLACEMENT: "rogue", Talent.SHADOW_STEP: "rogue",
    Talent.FEAR_THE_REAPER: "rogue", Talent.DEATHLY_DURABILITY: "rogue", Talent.DOUBLE_MARK: "rogue",
    Talent.SHADOW_BLADE: "rogue", Talent.CLONED_ARMOR: "rogue", Talent.PERFECT_COPY: "rogue",
    # Mage
    Talent.EMPOWERING_MEAL: "mage", Talent.SCHOLARS_INTUITION: "mage",
    Talent.LINGERING_MAGIC: "mage", Talent.BACKUP_BARRIER: "mage",
    Talent.ENERGIZING_MEAL: "mage", Talent.INSCRIBED_POWER: "mage",
    Talent.WAND_PRESERVATION: "mage", Talent.ARCANE_VISION: "mage", Talent.SHIELD_BATTERY: "mage",
    Talent.DESPERATE_POWER: "mage", Talent.ALLY_WARP: "mage",
    Talent.ELEMENTAL_BLAST_ABILITY: "mage", Talent.WILD_MAGIC_ABILITY: "mage", Talent.WARP_BEACON_ABILITY: "mage",
    Talent.BLAST_RADIUS: "mage", Talent.ELEMENTAL_POWER_TALENT: "mage", Talent.REACTIVE_BARRIER: "mage",
    Talent.WILD_POWER: "mage", Talent.FIRE_EVERYTHING: "mage", Talent.CONSERVED_MAGIC: "mage",
    Talent.TELEFRAG: "mage", Talent.REMOTE_BEACON: "mage", Talent.LONGRANGE_WARP: "mage",
    # Huntress
    Talent.NATURES_BOUNTY: "huntress", Talent.SURVIVALISTS_INTUITION: "huntress",
    Talent.FOLLOWUP_STRIKE: "huntress", Talent.NATURES_AID: "huntress",
    Talent.INVIGORATING_MEAL: "huntress", Talent.LIQUID_NATURE: "huntress",
    Talent.REJUVENATING_STEPS: "huntress", Talent.HEIGHTENED_SENSES: "huntress", Talent.DURABLE_PROJECTILES: "huntress",
    Talent.POINT_BLANK: "huntress", Talent.SEER_SHOT: "huntress",
    Talent.SPECTRAL_BLADES_ABILITY: "huntress", Talent.NATURES_POWER_ABILITY: "huntress", Talent.SPIRIT_HAWK_ABILITY: "huntress",
    Talent.FAN_OF_BLADES: "huntress", Talent.PROJECTING_BLADES: "huntress", Talent.SPIRIT_BLADES: "huntress",
    Talent.GROWING_POWER: "huntress", Talent.NATURES_WRATH: "huntress", Talent.WILD_MOMENTUM: "huntress",
    Talent.EAGLE_EYE: "huntress", Talent.GO_FOR_THE_EYES: "huntress", Talent.SWIFT_SPIRIT: "huntress",
}


# Armor-ability talents → the ability they unlock (first point locks the choice).
ABILITY_TALENTS: Dict[str, str] = {
    # Mage
    Talent.ELEMENTAL_BLAST_ABILITY: ArmorAbilityType.ELEMENTAL_BLAST,
    Talent.WILD_MAGIC_ABILITY: ArmorAbilityType.WILD_MAGIC,
    Talent.WARP_BEACON_ABILITY: ArmorAbilityType.WARP_BEACON,
    # Huntress
    Talent.SPECTRAL_BLADES_ABILITY: ArmorAbilityType.SPECTRAL_BLADES,
    Talent.NATURES_POWER_ABILITY: ArmorAbilityType.NATURES_POWER,
    Talent.SPIRIT_HAWK_ABILITY: ArmorAbilityType.SPIRIT_HAWK,
}


# Tier 4 talent → the armor ability it belongs to. Talents absent from this
# map (e.g. HEROIC_ENERGY-equivalents) are available regardless of which
# ability was chosen.
T4_ABILITY_TALENTS: Dict[str, str] = {
    Talent.BODY_SLAM: ArmorAbilityType.HEROIC_LEAP,
    Talent.IMPACT_WAVE: ArmorAbilityType.HEROIC_LEAP,
    Talent.DOUBLE_JUMP: ArmorAbilityType.HEROIC_LEAP,
    Talent.EXPANDING_WAVE: ArmorAbilityType.SHOCKWAVE,
    Talent.STRIKING_WAVE: ArmorAbilityType.SHOCKWAVE,
    Talent.SHOCK_FORCE: ArmorAbilityType.SHOCKWAVE,
    Talent.SUSTAINED_RETRIBUTION: ArmorAbilityType.ENDURE,
    Talent.SHRUG_IT_OFF: ArmorAbilityType.ENDURE,
    Talent.EVEN_THE_ODDS: ArmorAbilityType.ENDURE,
    # Rogue
    Talent.HASTY_RETREAT: ArmorAbilityType.SMOKE_BOMB,
    Talent.BODY_REPLACEMENT: ArmorAbilityType.SMOKE_BOMB,
    Talent.SHADOW_STEP: ArmorAbilityType.SMOKE_BOMB,
    Talent.FEAR_THE_REAPER: ArmorAbilityType.DEATH_MARK,
    Talent.DEATHLY_DURABILITY: ArmorAbilityType.DEATH_MARK,
    Talent.DOUBLE_MARK: ArmorAbilityType.DEATH_MARK,
    Talent.SHADOW_BLADE: ArmorAbilityType.SHADOW_CLONE,
    Talent.CLONED_ARMOR: ArmorAbilityType.SHADOW_CLONE,
    Talent.PERFECT_COPY: ArmorAbilityType.SHADOW_CLONE,
}

# Armor abilities a class may choose from, by class_type.
CLASS_ARMOR_ABILITIES: Dict[str, tuple[str, ...]] = {
    "warrior": (ArmorAbilityType.HEROIC_LEAP, ArmorAbilityType.SHOCKWAVE, ArmorAbilityType.ENDURE),
    "rogue": (ArmorAbilityType.SMOKE_BOMB, ArmorAbilityType.DEATH_MARK, ArmorAbilityType.SHADOW_CLONE),
}


# Level thresholds where talent tiers unlock
TIER_UNLOCK_LEVELS: Dict[int, int] = {
    1: 2,
    2: 7,
    3: 13,
    4: 21,
}

# Tier → max points per talent
TIER_MAX_POINTS: Dict[int, int] = {
    1: 2,
    2: 2,
    3: 3,
    4: 4,
}

# Combo moves (Gladiator) unlocked by combo count threshold, with UI tint.
COMBO_MOVES: Dict[str, dict] = {
    "clobber": {"count": 2, "tint": 0x00FF00},
    "slam": {"count": 4, "tint": 0xCCFF00},
    "parry": {"count": 6, "tint": 0xFFFF00},
    "crush": {"count": 8, "tint": 0xFFCC00},
    "fury": {"count": 10, "tint": 0xFF0000},
}

COST_ARMOR_ABILITY = 35  # Leap/Shockwave charge cost
COST_ENDURE = 50  # Endure charge cost (slightly higher)

# Human-readable titles and descriptions served via /api/talents/{class}
TALENT_TITLES: Dict[str, str] = {
    # Warrior T1
    Talent.HEARTY_MEAL: "Hearty Meal",
    Talent.VETERANS_INTUITION: "Veteran's Intuition",
    Talent.PROVOKED_ANGER: "Provoked Anger",
    Talent.IRON_WILL: "Iron Will",
    # Warrior T2
    Talent.IRON_STOMACH: "Iron Stomach",
    Talent.LIQUID_WILLPOWER: "Liquid Willpower",
    Talent.RUNIC_TRANSFERENCE: "Runic Transference",
    Talent.LETHAL_MOMENTUM: "Lethal Momentum",
    Talent.IMPROVISED_PROJECTILES: "Improvised Projectiles",
    # Warrior T3 universal
    Talent.HOLD_FAST: "Hold Fast",
    Talent.STRONGMAN: "Strongman",
    # Warrior T3 Berserker
    Talent.ENDLESS_RAGE: "Endless Rage",
    Talent.DEATHLESS_FURY: "Deathless Fury",
    Talent.ENRAGED_CATALYST: "Enraged Catalyst",
    # Warrior T3 Gladiator
    Talent.CLEAVE: "Cleave",
    Talent.LETHAL_DEFENSE: "Lethal Defense",
    Talent.ENHANCED_COMBO: "Enhanced Combo",
    # Warrior T4 Heroic Leap
    Talent.BODY_SLAM: "Body Slam",
    Talent.IMPACT_WAVE: "Impact Wave",
    Talent.DOUBLE_JUMP: "Double Jump",
    # Warrior T4 Shockwave
    Talent.EXPANDING_WAVE: "Expanding Wave",
    Talent.STRIKING_WAVE: "Striking Wave",
    Talent.SHOCK_FORCE: "Shock Force",
    # Warrior T4 Endure
    Talent.SUSTAINED_RETRIBUTION: "Sustained Retribution",
    Talent.SHRUG_IT_OFF: "Shrug It Off",
    Talent.EVEN_THE_ODDS: "Even the Odds",
    # Warrior T4 universal
    Talent.HEROIC_ENERGY: "Heroic Energy",
    # Rogue T1
    Talent.CACHED_RATIONS: "Cached Rations",
    Talent.THIEFS_INTUITION: "Thief's Intuition",
    Talent.SUCKER_PUNCH: "Sucker Punch",
    Talent.PROTECTIVE_SHADOWS: "Protective Shadows",
    # Rogue T2
    Talent.MYSTICAL_MEAL: "Mystical Meal",
    Talent.INSCRIBED_STEALTH: "Inscribed Stealth",
    Talent.WIDE_SEARCH: "Wide Search",
    Talent.SILENT_STEPS: "Silent Steps",
    Talent.ROGUES_FORESIGHT: "Rogue's Foresight",
    # Rogue T3
    Talent.ENHANCED_RINGS: "Enhanced Rings",
    Talent.LIGHT_CLOAK: "Light Cloak",
    # Rogue T3 Assassin
    Talent.ENHANCED_LETHALITY: "Enhanced Lethality",
    Talent.ASSASSINS_REACH: "Assassin's Reach",
    Talent.BOUNTY_HUNTER: "Bounty Hunter",
    # Rogue T3 Freerunner
    Talent.EVASIVE_ARMOR: "Evasive Armor",
    Talent.PROJECTILE_MOMENTUM: "Projectile Momentum",
    Talent.SPEEDY_STEALTH: "Speedy Stealth",
    # Rogue T4 Smoke Bomb
    Talent.HASTY_RETREAT: "Hasty Retreat",
    Talent.BODY_REPLACEMENT: "Body Replacement",
    Talent.SHADOW_STEP: "Shadow Step",
    # Rogue T4 Death Mark
    Talent.FEAR_THE_REAPER: "Fear the Reaper",
    Talent.DEATHLY_DURABILITY: "Deathly Durability",
    Talent.DOUBLE_MARK: "Double Mark",
    # Rogue T4 Shadow Clone
    Talent.SHADOW_BLADE: "Shadow Blade",
    Talent.CLONED_ARMOR: "Cloned Armor",
    Talent.PERFECT_COPY: "Perfect Copy",
    # Mage T1
    Talent.EMPOWERING_MEAL: "Empowering Meal",
    Talent.SCHOLARS_INTUITION: "Scholar's Intuition",
    Talent.LINGERING_MAGIC: "Lingering Magic",
    Talent.BACKUP_BARRIER: "Backup Barrier",
    # Mage T2
    Talent.ENERGIZING_MEAL: "Energizing Meal",
    Talent.INSCRIBED_POWER: "Inscribed Power",
    Talent.WAND_PRESERVATION: "Wand Preservation",
    Talent.ARCANE_VISION: "Arcane Vision",
    Talent.SHIELD_BATTERY: "Shield Battery",
    # Mage T3
    Talent.DESPERATE_POWER: "Desperate Power",
    Talent.ALLY_WARP: "Ally Warp",
    # Mage T3 Battlemage
    Talent.EMPOWERED_STRIKE: "Empowered Strike",
    Talent.MYSTICAL_CHARGE: "Mystical Charge",
    Talent.EXCESS_CHARGE: "Excess Charge",
    # Mage T3 Warlock
    Talent.SOUL_EATER: "Soul Eater",
    Talent.SOUL_SIPHON: "Soul Siphon",
    Talent.NECROMANCERS_MINIONS: "Necromancer's Minions",
    # Huntress T1
    Talent.NATURES_BOUNTY: "Nature's Bounty",
    Talent.SURVIVALISTS_INTUITION: "Survivalist's Intuition",
    Talent.FOLLOWUP_STRIKE: "Followup Strike",
    Talent.NATURES_AID: "Nature's Aid",
    # Huntress T2
    Talent.INVIGORATING_MEAL: "Invigorating Meal",
    Talent.LIQUID_NATURE: "Liquid Nature",
    Talent.REJUVENATING_STEPS: "Rejuvenating Steps",
    Talent.HEIGHTENED_SENSES: "Heightened Senses",
    Talent.DURABLE_PROJECTILES: "Durable Projectiles",
    # Huntress T3
    Talent.POINT_BLANK: "Point Blank",
    Talent.SEER_SHOT: "Seer Shot",
    # Huntress T3 Sniper
    Talent.FARSIGHT: "Farsight",
    Talent.SHARED_ENCHANTMENT: "Shared Enchantment",
    Talent.SHARED_UPGRADES: "Shared Upgrades",
    # Huntress T3 Warden
    Talent.DURABLE_TIPS: "Durable Tips",
    Talent.BARKSKIN: "Barkskin",
    Talent.SHIELDING_DEW: "Shielding Dew",
    # Armor ability selectors
    Talent.ELEMENTAL_BLAST_ABILITY: "Elemental Blast",
    Talent.WILD_MAGIC_ABILITY: "Wild Magic",
    Talent.WARP_BEACON_ABILITY: "Warp Beacon",
    Talent.SPECTRAL_BLADES_ABILITY: "Spectral Blades",
    Talent.NATURES_POWER_ABILITY: "Nature's Power",
    Talent.SPIRIT_HAWK_ABILITY: "Spirit Hawk",
    # Huntress T4 Spectral Blades
    Talent.FAN_OF_BLADES: "Fan of Blades",
    Talent.PROJECTING_BLADES: "Projecting Blades",
    Talent.SPIRIT_BLADES: "Spirit Blades",
    # Huntress T4 Nature's Power
    Talent.GROWING_POWER: "Growing Power",
    Talent.NATURES_WRATH: "Nature's Wrath",
    Talent.WILD_MOMENTUM: "Wild Momentum",
    # Huntress T4 Spirit Hawk
    Talent.EAGLE_EYE: "Eagle Eye",
    Talent.GO_FOR_THE_EYES: "Go for the Eyes",
    Talent.SWIFT_SPIRIT: "Swift Spirit",
    # Mage T4 Elemental Blast
    Talent.BLAST_RADIUS: "Blast Radius",
    Talent.ELEMENTAL_POWER_TALENT: "Elemental Power",
    Talent.REACTIVE_BARRIER: "Reactive Barrier",
    # Mage T4 Wild Magic
    Talent.WILD_POWER: "Wild Power",
    Talent.FIRE_EVERYTHING: "Fire Everything",
    Talent.CONSERVED_MAGIC: "Conserved Magic",
    # Mage T4 Warp Beacon
    Talent.TELEFRAG: "Telefrag",
    Talent.REMOTE_BEACON: "Remote Beacon",
    Talent.LONGRANGE_WARP: "Longrange Warp",
    # Rogue T4 (ability-gated, subclass_req=None)
    Talent.HASTY_RETREAT: "Hasty Retreat",
    Talent.BODY_REPLACEMENT: "Body Replacement",
    Talent.SHADOW_STEP: "Shadow Step",
    Talent.FEAR_THE_REAPER: "Fear the Reaper",
    Talent.DEATHLY_DURABILITY: "Deathly Durability",
    Talent.DOUBLE_MARK: "Double Mark",
    Talent.SHADOW_BLADE: "Shadow Blade",
    Talent.CLONED_ARMOR: "Cloned Armor",
    Talent.PERFECT_COPY: "Perfect Copy",
}

TALENT_DESCRIPTIONS: Dict[str, str] = {
    # Warrior T1
    Talent.HEARTY_MEAL: "Eating food while below 1/3 HP heals an extra 2+2 per point.",
    Talent.VETERANS_INTUITION: "Identify melee weapons and armor faster; at 2pts, new armor is identified instantly.",
    Talent.PROVOKED_ANGER: "Your next attack after being provoked deals 1+2 per point bonus damage.",
    Talent.IRON_WILL: "Grants a shield (3 + armor tier + points) that recharges over time.",
    # Warrior T2
    Talent.IRON_STOMACH: "Eating while on a cooldown grants temporary immunity to food-related debuffs.",
    Talent.LIQUID_WILLPOWER: "Drinking a potion grants a shield equal to 3.0%/6.5%/10% of max HP per point.",
    Talent.RUNIC_TRANSFERENCE: "Allows transferring glyphs between your seal and armor.",
    Talent.LETHAL_MOMENTUM: "Killing blows have a 34%/67%/100% chance to not consume a turn.",
    Talent.IMPROVISED_PROJECTILES: "Thrown non-weapon items blind enemies for 1+points turns (50-turn cooldown).",
    # Warrior T3 universal
    Talent.HOLD_FAST: "While stationary, gain bonus armor DR and your buffs/debuffs decay slower.",
    Talent.STRONGMAN: "Effective Strength increases by 3%-18% per point.",
    # Warrior T3 Berserker
    Talent.ENDLESS_RAGE: "Berserk's power cap increases by 16.67% per point, boosting shield and recovery.",
    Talent.DEATHLESS_FURY: "If a fatal blow would kill you while raging, Berserk saves you at 1 HP instead.",
    Talent.ENRAGED_CATALYST: "While raging, weapon enchantment proc chance increases by up to 15% per point.",
    # Warrior T3 Gladiator
    Talent.CLEAVE: "Killing blows extend your combo timer to 15+15 per point seconds.",
    Talent.LETHAL_DEFENSE: "Combo kills reduce your Iron Will shield's cooldown by up to 33% per point.",
    Talent.ENHANCED_COMBO: "Empowers your Combo finishing moves at higher combo counts.",
    # Warrior T4 Heroic Leap
    Talent.BODY_SLAM: "Landing from Heroic Leap damages adjacent enemies.",
    Talent.IMPACT_WAVE: "Enemies not hit by Body Slam are knocked back and may be left Vulnerable.",
    Talent.DOUBLE_JUMP: "Heroic Leap grants a cheaper follow-up leap.",
    # Warrior T4 Shockwave
    Talent.EXPANDING_WAVE: "Shockwave's cone reaches further and wider per point.",
    Talent.STRIKING_WAVE: "Shockwave has a chance to trigger an extra attack on each target hit.",
    Talent.SHOCK_FORCE: "Shockwave deals more damage and may Paralyze instead of Cripple.",
    # Warrior T4 Endure
    Talent.SUSTAINED_RETRIBUTION: "Damage banked by Endure is increased by 15% per point when it ends.",
    Talent.SHRUG_IT_OFF: "Endure reduces incoming damage further, by 20% per point.",
    Talent.EVEN_THE_ODDS: "Banked Endure damage increases for each nearby enemy.",
    # Warrior T4 universal
    Talent.HEROIC_ENERGY: "Reduces your armor ability's charge cost by 12%/23%/32%/40%.",
    # Rogue T1
    Talent.CACHED_RATIONS: "Eating food grants a shield. +4 shield per point.",
    Talent.THIEFS_INTUITION: "Better at detecting secrets and traps.",
    Talent.SUCKER_PUNCH: "Surprise attacks stun the target briefly.",
    Talent.PROTECTIVE_SHADOWS: "Damage resistance while in shadow or stealthed.",
    # Rogue T2
    Talent.MYSTICAL_MEAL: "Eating food recharges your cloak by 1 charge per point.",
    Talent.INSCRIBED_STEALTH: "Reading a scroll grants brief stealth.",
    Talent.WIDE_SEARCH: "Searching reveals a larger area.",
    Talent.SILENT_STEPS: "Moving while stealthed does not break stealth.",
    Talent.ROGUES_FORESIGHT: "See traps and secrets from further away.",
    # Rogue T3
    Talent.ENHANCED_RINGS: "Ring effects are 20% stronger per point.",
    Talent.LIGHT_CLOAK: "The cloak of shadows recharges faster.",
    # Rogue T3 Assassin
    Talent.ENHANCED_LETHALITY: "Assassinate deals significantly more damage.",
    Talent.ASSASSINS_REACH: "Assassinate can be used from 1 tile further away.",
    Talent.BOUNTY_HUNTER: "Kills drop more gold.",
    # Rogue T3 Freerunner
    Talent.EVASIVE_ARMOR: "Armor no longer reduces dodge chance while moving.",
    Talent.PROJECTILE_MOMENTUM: "Ranged damage increases with distance.",
    Talent.SPEEDY_STEALTH: "Move at full speed while stealthed.",
    # Rogue T4 Smoke Bomb
    Talent.HASTY_RETREAT: "Smoke Bomb grants a speed boost.",
    Talent.BODY_REPLACEMENT: "When fatal damage would be taken, swap with your clone.",
    Talent.SHADOW_STEP: "Teleport to your shadow clone's location.",
    # Rogue T4 Death Mark
    Talent.FEAR_THE_REAPER: "Death Mark can instantly kill marked enemies.",
    Talent.DEATHLY_DURABILITY: "Death Mark weakens the target's damage output.",
    Talent.DOUBLE_MARK: "Can mark two enemies at once.",
    # Rogue T4 Shadow Clone
    Talent.SHADOW_BLADE: "Your clone deals increased damage.",
    Talent.CLONED_ARMOR: "Your clone inherits your armor rating.",
    Talent.PERFECT_COPY: "Your clone can use items from your inventory.",
    # Mage T1
    Talent.EMPOWERING_MEAL: "Eating food recharges your wands by 1 charge per point.",
    Talent.SCHOLARS_INTUITION: "Identify items more easily and quickly.",
    Talent.LINGERING_MAGIC: "Potion buff effects last 15% longer per point.",
    Talent.BACKUP_BARRIER: "Drinking a potion grants a shield.",
    # Mage T2
    Talent.ENERGIZING_MEAL: "Eating food recharges all wands. +1 charge per point.",
    Talent.INSCRIBED_POWER: "Reading a scroll grants a shield.",
    Talent.WAND_PRESERVATION: "Wands have a chance to not consume a charge.",
    Talent.ARCANE_VISION: "See magic traps and concealed doors.",
    Talent.SHIELD_BATTERY: "Using a wand grants a shield.",
    # Mage T3
    Talent.DESPERATE_POWER: "At low HP, wands recharge automatically.",
    Talent.ALLY_WARP: "Swap places with a friendly summoned creature.",
    # Mage T3 Battlemage
    Talent.EMPOWERED_STRIKE: "Staff melee attacks deal significantly more damage.",
    Talent.MYSTICAL_CHARGE: "Wand hits charge your staff.",
    Talent.EXCESS_CHARGE: "Overcharging your staff deals bonus damage on melee hit.",
    # Mage T3 Warlock
    Talent.SOUL_EATER: "Killing an enemy heals you. +2 HP per point.",
    Talent.SOUL_SIPHON: "Hitting an enemy with a wand drains life.",
    Talent.NECROMANCERS_MINIONS: "Kills have a chance to raise a minion.",
    # Huntress T1
    Talent.NATURES_BOUNTY: "More dew drops and seeds from plants.",
    Talent.SURVIVALISTS_INTUITION: "Identify plants more easily.",
    Talent.FOLLOWUP_STRIKE: "Hitting with a ranged weapon boosts follow-up melee damage.",
    Talent.NATURES_AID: "Dew drops heal for more HP.",
    # Huntress T2
    Talent.INVIGORATING_MEAL: "Eating food grants a speed boost.",
    Talent.LIQUID_NATURE: "Standing in water heals additional HP.",
    Talent.REJUVENATING_STEPS: "Walking on grass gradually heals.",
    Talent.HEIGHTENED_SENSES: "See hidden doors and traps more easily.",
    Talent.DURABLE_PROJECTILES: "Thrown weapons have a chance not to break.",
    # Huntress T3
    Talent.POINT_BLANK: "Ranged weapons deal more damage at close range.",
    Talent.SEER_SHOT: "Hitting an enemy with a ranged attack reveals them.",
    # Huntress T3 Sniper
    Talent.FARSIGHT: "Increases view distance by 1 tile per point.",
    Talent.SHARED_ENCHANTMENT: "Ranged weapons inherit your melee weapon's enchantment.",
    Talent.SHARED_UPGRADES: "Ranged weapons benefit from melee weapon upgrades.",
    # Huntress T3 Warden
    Talent.DURABLE_TIPS: "Thrown weapons never break.",
    Talent.BARKSKIN: "Grass provides an armor buff while standing on it.",
    Talent.SHIELDING_DEW: "Dew drops grant a shield.",
    # Armor ability selectors (no separate desc needed — handled by ability tooltip)
    Talent.ELEMENTAL_BLAST_ABILITY: "Unleash a blast of elemental energy.",
    Talent.WILD_MAGIC_ABILITY: "Trigger random wand effects.",
    Talent.WARP_BEACON_ABILITY: "Place a beacon to teleport back to.",
    Talent.SPECTRAL_BLADES_ABILITY: "Throw spectral blades that pierce enemies.",
    Talent.NATURES_POWER_ABILITY: "Empower yourself with nature's strength.",
    Talent.SPIRIT_HAWK_ABILITY: "Summon a spirit hawk to scout ahead.",
    # Mage T4 Elemental Blast
    Talent.BLAST_RADIUS: "Elemental Blast affects a larger area.",
    Talent.ELEMENTAL_POWER_TALENT: "Elemental Blast deals more damage.",
    Talent.REACTIVE_BARRIER: "Using Elemental Blast grants a shield.",
    # Mage T4 Wild Magic
    Talent.WILD_POWER: "Wild Magic triggers more effects.",
    Talent.FIRE_EVERYTHING: "Wild Magic fires additional projectiles.",
    Talent.CONSERVED_MAGIC: "Wild Magic has a chance to not consume charge.",
    # Mage T4 Warp Beacon
    Talent.TELEFRAG: "Teleporting onto an enemy damages them.",
    Talent.REMOTE_BEACON: "Can trigger the beacon from a distance.",
    Talent.LONGRANGE_WARP: "Warp Beacon has unlimited range.",
    # Huntress T4 Spectral Blades
    Talent.FAN_OF_BLADES: "Spectral Blades hit multiple targets.",
    Talent.PROJECTING_BLADES: "Spectral Blades pass through walls.",
    Talent.SPIRIT_BLADES: "Spectral Blades return to the owner after hitting.",
    # Huntress T4 Natures Power
    Talent.GROWING_POWER: "Nature's Power duration and strength increase.",
    Talent.NATURES_WRATH: "Nature's Power deals damage over time to nearby enemies.",
    Talent.WILD_MOMENTUM: "Nature's Power grants increased speed.",
    # Huntress T4 Spirit Hawk
    Talent.EAGLE_EYE: "The hawk reveals the entire floor map.",
    Talent.GO_FOR_THE_EYES: "The hawk blinds enemies it attacks.",
    Talent.SWIFT_SPIRIT: "The hawk attacks more frequently.",
    # Rogue T4 Smoke Bomb (ability-gated)
    Talent.HASTY_RETREAT: "Smoke Bomb grants a speed boost.",
    Talent.BODY_REPLACEMENT: "Fatal damage swaps you with your clone.",
    Talent.SHADOW_STEP: "Teleport to your shadow clone's location.",
    # Rogue T4 Death Mark
    Talent.FEAR_THE_REAPER: "Death Mark can instantly kill marked enemies.",
    Talent.DEATHLY_DURABILITY: "Death Mark weakens the target's attacks.",
    Talent.DOUBLE_MARK: "Mark two enemies at once.",
    # Rogue T4 Shadow Clone
    Talent.SHADOW_BLADE: "Your clone deals increased damage.",
    Talent.CLONED_ARMOR: "Your clone inherits your armor rating.",
    Talent.PERFECT_COPY: "Your clone can use items from your inventory.",
}


class TalentInfo(BaseModel):
    talents: Dict[str, int] = Field(default_factory=dict)

    def get(self, name: str) -> int:
        return self.talents.get(name, 0)

    def has(self, name: str) -> bool:
        return self.talents.get(name, 0) > 0

    def level(self, name: str) -> int:
        return self.talents.get(name, 0)

    def max_level(self, name: str) -> int:
        return TALENT_DEFS.get(name, (0, 0, None))[0]


class SubclassInfo(BaseModel):
    subclass: Optional[str] = None
    talent_info: TalentInfo = Field(default_factory=TalentInfo)
    # Available talent points per tier (tier → count). Player earns these when a
    # new tier unlocks (level 2, 7, 13, 21) and consumes them on upgrade_talent().
    talent_points: Dict[int, int] = Field(default_factory=dict)
    # Bonus talent points per tier, granted by Potion of Divine Inspiration.
    bonus_talent_points: Dict[int, int] = Field(default_factory=dict)
    # Tracks which milestone levels (2, 6, 13) have had their events emitted.
    # Prevents re-emission on subsequent level-ups and ensures events fire even
    # when a multi-level jump skips the exact milestone level.
    emitted_milestones: Set[int] = Field(default_factory=set, exclude=True)
    # Talents replaced via Scroll of Metamorphosis: {original_talent: replacement_talent}
    metamorphed_talents: Dict[str, str] = Field(default_factory=dict)
