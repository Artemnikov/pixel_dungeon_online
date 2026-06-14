// Talent icon indices into talent_icons.png (512×128, 32 cols × 8 rows of 16×16 icons)
// Per-class blocks: Warrior=0-31, Mage=32-63, Rogue=64-95, Huntress=96-127, Duelist=128-159, Cleric=160-191
export const TALENT_ICONS = {
  // ===== WARRIOR =====
  // Tier 1 (lvl2, universal)
  hearty_meal: 0,
  veterans_intuition: 1,
  provoked_anger: 2,
  iron_will: 3,
  // Tier 2 (lvl7, universal)
  iron_stomach: 4,
  liquid_willpower: 5,
  runic_transference: 6,
  lethal_momentum: 7,
  improvised_projectiles: 8,
  // Tier 3 universal
  hold_fast: 9,
  strongman: 10,
  // Tier 3 — Berserker
  endless_rage: 11,
  deathless_fury: 12,
  enraged_catalyst: 13,
  // Tier 3 — Gladiator
  cleave: 14,
  lethal_defense: 15,
  enhanced_combo: 16,
  // Tier 4 — Heroic Leap
  body_slam: 17,
  impact_wave: 18,
  double_jump: 19,
  // Tier 4 — Shockwave
  expanding_wave: 20,
  striking_wave: 21,
  shock_force: 22,
  // Tier 4 — Endure
  sustained_retribution: 23,
  shrug_it_off: 24,
  even_the_odds: 25,
  // Tier 4 — universal
  heroic_energy: 26,

  // ===== MAGE =====
  empowering_meal: 32,       // EMPOWERING_MEAL
  scholars_intuition: 33,    // SCHOLARS_INTUITION
  lingering_magic: 34,       // LINGERING_MAGIC
  backup_barrier: 35,        // BACKUP_BARRIER
  energizing_meal: 36,       // ENERGIZING_MEAL
  inscribed_power: 37,       // INSCRIBED_POWER
  wand_preservation: 38,     // WAND_PRESERVATION
  arcane_vision: 39,         // ARCANE_VISION
  shield_battery: 40,        // SHIELD_BATTERY
  desperate_power: 41,       // DESPERATE_POWER
  ally_warp: 42,             // ALLY_WARP
  empowered_strike: 43,      // EMPOWERED_STRIKE
  mystical_charge: 44,       // MYSTICAL_CHARGE
  excess_charge: 45,         // EXCESS_CHARGE
  soul_eater: 46,            // SOUL_EATER
  soul_siphon: 47,           // SOUL_SIPHON
  necromancers_minions: 48,  // NECROMANCERS_MINIONS
  elemental_blast_talent: 49,// BLAST_RADIUS
  wild_magic_talent: 52,     // WILD_POWER
  warp_beacon_talent: 55,    // TELEFRAG
  blast_radius: 49,          // BLAST_RADIUS
  elemental_power_talent: 50,// ELEMENTAL_POWER
  reactive_barrier: 51,      // REACTIVE_BARRIER
  wild_power: 52,            // WILD_POWER
  fire_everything: 53,       // FIRE_EVERYTHING
  conserved_magic: 54,       // CONSERVED_MAGIC
  telefrag: 55,              // TELEFRAG
  remote_beacon: 56,         // REMOTE_BEACON
  longrange_warp: 57,        // LONGRANGE_WARP

  // ===== ROGUE =====
  cached_rations: 64,        // CACHED_RATIONS
  thiefs_intuition: 65,      // THIEFS_INTUITION
  sucker_punch: 66,          // SUCKER_PUNCH
  protective_shadows: 67,    // PROTECTIVE_SHADOWS
  mystical_meal: 68,         // MYSTICAL_MEAL
  inscribed_stealth: 69,     // INSCRIBED_STEALTH
  wide_search: 70,           // WIDE_SEARCH
  silent_steps: 71,          // SILENT_STEPS
  rogues_foresight: 72,      // ROGUES_FORESIGHT
  enhanced_rings: 73,        // ENHANCED_RINGS
  light_cloak: 74,           // LIGHT_CLOAK
  enhanced_lethality: 75,    // ENHANCED_LETHALITY
  assassins_reach: 76,       // ASSASSINS_REACH
  bounty_hunter: 77,         // BOUNTY_HUNTER
  evasive_armor: 78,         // EVASIVE_ARMOR
  projectile_momentum: 79,   // PROJECTILE_MOMENTUM
  speedy_stealth: 80,        // SPEEDY_STEALTH
  hasty_retreat: 81,         // HASTY_RETREAT
  body_replacement: 82,      // BODY_REPLACEMENT
  shadow_step: 83,           // SHADOW_STEP
  fear_the_reaper: 84,       // FEAR_THE_REAPER
  deathly_durability: 85,    // DEATHLY_DURABILITY
  double_mark: 86,           // DOUBLE_MARK
  shadow_blade: 87,          // SHADOW_BLADE
  cloned_armor: 88,          // CLONED_ARMOR
  perfect_copy: 89,          // PERFECT_COPY

  // ===== HUNTRESS =====
  natures_bounty: 96,        // NATURES_BOUNTY
  survivalists_intuition: 97,// SURVIVALISTS_INTUITION
  followup_strike: 98,       // FOLLOWUP_STRIKE
  natures_aid: 99,           // NATURES_AID
  invigorating_meal: 100,    // INVIGORATING_MEAL
  liquid_nature: 101,        // LIQUID_NATURE
  rejuvenating_steps: 102,   // REJUVENATING_STEPS
  heightened_senses: 103,    // HEIGHTENED_SENSES
  durable_projectiles: 104,  // DURABLE_PROJECTILES
  point_blank: 105,          // POINT_BLANK
  seer_shot: 106,            // SEER_SHOT
  farsight: 107,             // FARSIGHT
  shared_enchantment: 108,   // SHARED_ENCHANTMENT
  shared_upgrades: 109,      // SHARED_UPGRADES
  durable_tips: 110,         // DURABLE_TIPS
  barkskin: 111,             // BARKSKIN
  shielding_dew: 112,        // SHIELDING_DEW
  spectral_blades_talent: 113, // FAN_OF_BLADES
  natures_power_talent: 116,   // GROWING_POWER
  spirit_hawk_talent: 119,     // EAGLE_EYE
  fan_of_blades: 113,        // FAN_OF_BLADES
  projecting_blades: 114,    // PROJECTING_BLADES
  spirit_blades: 115,        // SPIRIT_BLADES
  growing_power: 116,        // GROWING_POWER
  natures_wrath: 117,        // NATURES_WRATH
  wild_momentum: 118,        // WILD_MOMENTUM
  eagle_eye: 119,            // EAGLE_EYE
  go_for_the_eyes: 120,      // GO_FOR_THE_EYES
  swift_spirit: 121,         // SWIFT_SPIRIT

  // ===== DUELIST (mapped but unused by current 4-class support) =====
  strengthening_meal: 128,
  adventurers_intuition: 129,
  patient_strike: 130,
  aggressive_barrier: 131,
  focused_meal: 132,
  liquid_agility: 133,
  weapon_recharging: 134,
  lethal_haste: 135,
  swift_equip: 136,
  precise_assault: 137,
  // deadly_followup: 138, // Duelist (unused - key conflicts with Warrior T4)
  varied_charge: 139,
  twin_upgrades: 140,
  combined_lethality: 141,
  unencumbered_spirit: 142,
  monastic_vigor: 143,
  combined_energy: 144,
  close_the_gap: 145,
  invigorating_victory: 146,
  elimination_match: 147,
  elemental_reach: 148,
  striking_force: 149,
  directed_power: 150,
  feigned_retreat: 151,
  expose_weakness: 152,
  counter_ability: 153,
};

export function getTalentIconIndex(talentId) {
  return TALENT_ICONS[talentId] ?? 0;
}
