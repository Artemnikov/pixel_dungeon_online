// Hero icon indices into hero_icons.png (128×256, 8 cols × 16 rows of 16×16 icons)
// Matches SPD's HeroIcon.java constants
export const SUBCLASS_ICONS = {
  berserker: 0,
  gladiator: 1,
  battlemage: 2,
  warlock: 3,
  assassin: 4,
  freerunner: 5,
  sniper: 6,
  warden: 7,
  champion: 8,
  monk: 9,
  priest: 10,
  paladin: 11,
};

export const ABILITY_ICONS = {
  heroic_leap: 16,
  shockwave: 17,
  endure: 18,
  elemental_blast: 19,
  wild_magic: 20,
  warp_beacon: 21,
  smoke_bomb: 22,
  death_mark: 23,
  shadow_clone: 24,
  spectral_blades: 25,
  natures_power: 26,
  spirit_hawk: 27,
  challenge: 28,
  elemental_strike: 29,
  feint: 30,
  ascended_form: 31,
  trinity: 32,
  power_of_many: 33,
  ratmogrify: 34,
};

export const ACTION_INDICATOR_ICONS = {
  berserk: 104,
  combo: 105,
  preparation: 106,
  momentum: 107,
  snipers_mark: 108,
  weapon_swap: 109,
  monk_abilities: 110,
};

export const CLERIC_SPELL_ICONS = {
  holy_intuition: 43,
  shield_of_light: 44,
  recall_inscription: 45,
  sunray: 46,
  divine_sense: 47,
  bless: 48,
  cleanse: 49,
  holy_lance: 51,
  hallowed_ground: 52,
  mnemonic_prayer: 53,
  lay_on_hands: 55,
  aura_of_protection: 56,
  wall_of_light: 57,
  divine_intervention: 58,
  judgement: 59,
  flash: 60,
  body_form: 61,
  mind_form: 62,
  spirit_form: 63,
  beaming_ray: 64,
  life_link: 65,
  stasis: 66,
};

export function getHeroIconIndex(type, id) {
  if (type === 'subclass') return SUBCLASS_ICONS[id] ?? 127;
  if (type === 'ability') return ABILITY_ICONS[id] ?? 127;
  if (type === 'cleric_spell') return CLERIC_SPELL_ICONS[id] ?? 127;
  return 127;
}
