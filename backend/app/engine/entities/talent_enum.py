"""Shared talent identifiers and enums.

The full Talent enum is a single registry on purpose: talent IDs are
cross-cutting (serialization, API, engine gating), and a duplicate id between
two classes silently overwrote a TALENT_DEFS entry in the past (see
PRIEST_EMPOWERED_STRIKE). Per-class *data* (definitions, requirements, titles,
descriptions) lives in talent_data/.
"""

from enum import StrEnum


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
    # Duelist
    CHAMPION = "champion"
    MONK = "monk"
    # Cleric
    PRIEST = "priest"
    PALADIN = "paladin"


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
    # Duelist
    CHALLENGE = "challenge"
    ELEMENTAL_STRIKE = "elemental_strike"
    FEINT = "feint"
    # Cleric
    ASCENDED_FORM = "ascended_form"
    TRINITY = "trinity"
    POWER_OF_MANY = "power_of_many"


class Talent(StrEnum):
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

    # ===================== DUELIST =====================
    # Tier 1
    STRENGTHENING_MEAL = "strengthening_meal"
    ADVENTURERS_INTUITION = "adventurers_intuition"
    PATIENT_STRIKE = "patient_strike"
    AGGRESSIVE_BARRIER = "aggressive_barrier"
    # Legacy Tier 1 aliases
    AGGRESSIVE_APPROACH = "aggressive_approach"
    LIGHTWEIGHT_COMBAT = "lightweight_combat"
    DUELIST_LETHAL_MOMENTUM = "duelist_lethal_momentum"
    STICK_AND_MOVE = "stick_and_move"

    # Tier 2
    FOCUSED_MEAL = "focused_meal"
    LIQUID_AGILITY = "liquid_agility"
    WEAPON_RECHARGING = "weapon_recharging"
    LETHAL_HASTE = "lethal_haste"
    SWIFT_EQUIP = "swift_equip"
    # Legacy Tier 2 aliases
    DUAL_STRIKE = "dual_strike"
    CIRCLE_OF_SLAUGHTER = "circle_of_slaughter"
    FINISHER = "finisher"
    FEROCITY = "ferocity"

    # Tier 3 — class
    PRECISE_ASSAULT = "precise_assault"
    DEADLY_FOLLOWUP = "deadly_followup"
    CHARGED_ATTACK = "charged_attack"  # legacy alias

    # Tier 3 — Champion
    VARIED_CHARGE = "varied_charge"
    TWIN_UPGRADES = "twin_upgrades"
    COMBINED_LETHALITY = "combined_lethality"
    CHAMPION_POWER = "champion_power"  # legacy alias
    CHAMPION_ENDURANCE = "champion_endurance"  # legacy alias
    CHAMPION_REACH = "champion_reach"  # legacy alias

    # Tier 3 — Monk
    UNENCUMBERED_SPIRIT = "unencumbered_spirit"
    MONASTIC_VIGOR = "monastic_vigor"
    COMBINED_ENERGY = "combined_energy"
    MONKS_SPIRIT = "monks_spirit"  # legacy alias

    # Tier 4 (armor abilities)
    CHALLENGE_ABILITY = "challenge_talent"
    ELEMENTAL_STRIKE_ABILITY = "elemental_strike_talent"
    FEINT_ABILITY = "feint_talent"

    # Tier 4 — Challenge
    CLOSE_THE_GAP = "close_the_gap"
    INVIGORATING_VICTORY = "invigorating_victory"
    ELIMINATION_MATCH = "elimination_match"
    LASTING_CHALLENGE = "lasting_challenge"  # legacy alias
    HEIGHTENED_CHALLENGE = "heightened_challenge"  # legacy alias
    DUAL_CHALLENGE = "dual_challenge"  # legacy alias

    # Tier 4 — Elemental Strike
    ELEMENTAL_REACH = "elemental_reach"
    STRIKING_FORCE = "striking_force"
    DIRECTED_POWER = "directed_power"
    SEARING_STRIKE = "searing_strike"  # legacy alias
    CHILLING_STRIKE = "chilling_strike"  # legacy alias
    CHARGED_STRIKE = "charged_strike"  # legacy alias

    # Tier 4 — Feint
    FEIGNED_RETREAT = "feigned_retreat"
    EXPOSE_WEAKNESS = "expose_weakness"
    COUNTER_ABILITY = "counter_ability"
    SHADOW_FEINT = "shadow_feint"  # legacy alias
    REACTIVE_FEINT = "reactive_feint"  # legacy alias
    PHANTASMAL_FEINT = "phantasmal_feint"  # legacy alias

    # ===================== CLERIC =====================
    # Tier 1
    SATIATED_SPELLS = "satiated_spells"
    HOLY_INTUITION = "holy_intuition"
    SEARING_LIGHT = "searing_light"
    SHIELD_OF_LIGHT = "shield_of_light"
    # Tier 2
    ENLIGHTENING_MEAL = "enlightening_meal"
    RECALL_INSCRIPTION = "recall_inscription"
    SUNRAY = "sunray"
    DIVINE_SENSE = "divine_sense"
    BLESS = "bless"
    # Tier 3 — class
    CLEANSE = "cleanse"
    LIGHT_READING = "light_reading"
    # Tier 3 — Priest
    HOLY_LANCE = "holy_lance"
    HALLOWED_GROUND = "hallowed_ground"
    MNEMONIC_PRAYER = "mnemonic_prayer"
    # Tier 3 — Paladin
    LAY_ON_HANDS = "lay_on_hands"
    AURA_OF_PROTECTION = "aura_of_protection"
    WALL_OF_LIGHT = "wall_of_light"
    # Tier 4 (armor abilities)
    ASCENDED_FORM_ABILITY = "ascended_form_talent"
    TRINITY_ABILITY = "trinity_talent"
    POWER_OF_MANY_ABILITY = "power_of_many_talent"
    # Tier 4 — Ascended Form
    DIVINE_INTERVENTION = "divine_intervention"
    JUDGEMENT = "judgement"
    FLASH = "flash"
    # Tier 4 — Trinity
    BODY_FORM = "body_form"
    MIND_FORM = "mind_form"
    SPIRIT_FORM = "spirit_form"
    # Tier 4 — Power of Many
    BEAMING_RAY = "beaming_ray"
    LIFE_LINK = "life_link"
    STASIS = "stasis"
