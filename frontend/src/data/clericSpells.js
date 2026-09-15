export const CLERIC_SPELLS = [
  { id: 'guiding_light', label: 'Guiding Light', tier: 1, cost: 1, icon: '🕯️', targeting: 'mob', desc: 'Fires a holy bolt dealing 2-8 magic damage and illuminating the target.' },
  { id: 'holy_weapon', label: 'Holy Weapon', tier: 1, cost: 2, icon: '⚔️', targeting: 'none', desc: 'Imbues weapon attacks with holy power for 50 turns (+2 magic damage, +6 for Paladin).' },
  { id: 'holy_ward', label: 'Holy Ward', tier: 1, cost: 1, icon: '🛡️', targeting: 'none', desc: 'Imbues armor with holy defense for 50 turns (+1 damage blocked, +3 for Paladin).' },
  { id: 'holy_intuition', label: 'Holy Intuition', tier: 1, cost: 3, icon: '🔍', targeting: 'none', talent: 'holy_intuition', desc: 'Reveals whether items in your backpack are cursed.' },
  { id: 'shield_of_light', label: 'Shield of Light', tier: 1, cost: 1, icon: '✨', targeting: 'mob', talent: 'shield_of_light', desc: 'Creates a ward absorbing incoming damage from a targeted enemy.' },
  { id: 'recall_inscription', label: 'Recall Inscription', tier: 2, cost: 3, icon: '📜', targeting: 'none', talent: 'recall_inscription', desc: 'Repeats the effect of the last runestone or scroll used.' },
  { id: 'sunray', label: 'Sunray', tier: 2, cost: 1, icon: '☀️', targeting: 'mob', talent: 'sunray', desc: 'Blasts an enemy for magic damage and blinds them (paralyzing if already blind).' },
  { id: 'divine_sense', label: 'Divine Sense', tier: 2, cost: 2, icon: '👁️', targeting: 'none', talent: 'divine_sense', desc: 'Grants Mind Vision in an 8-12 tile radius for 50 turns.' },
  { id: 'bless', label: 'Bless', tier: 2, cost: 1, icon: '🙏', targeting: 'ally_or_self', talent: 'bless', desc: 'Blesses yourself with accuracy and shield, or an ally with Bless and healing.' },
  { id: 'cleanse', label: 'Cleanse', tier: 3, cost: 2, icon: '🕊️', targeting: 'none', talent: 'cleanse', desc: 'Cleanses all negative debuffs and grants barrier & debuff immunity.' },
  { id: 'radiance', label: 'Radiance', tier: 3, cost: 2, icon: '🌟', targeting: 'none', subclass: 'priest', desc: 'Paralyzes visible enemies and detonates Illuminated targets.' },
  { id: 'holy_lance', label: 'Holy Lance', tier: 3, cost: 4, icon: '🔱', targeting: 'mob', talent: 'holy_lance', desc: 'Pierces enemies in a line for high holy damage.' },
  { id: 'hallowed_ground', label: 'Hallowed Ground', tier: 3, cost: 2, icon: '🌱', targeting: 'cell', talent: 'hallowed_ground', desc: 'Sanctifies the ground, healing allies and crippling enemies.' },
  { id: 'mnemonic_prayer', label: 'Mnemonic Prayer', tier: 3, cost: 1, icon: '📖', targeting: 'ally_or_self', talent: 'mnemonic_prayer', desc: 'Extends positive buffs on allies or negative debuffs on enemies.' },
  { id: 'smite', label: 'Smite', tier: 3, cost: 2, icon: '⚡', targeting: 'mob', subclass: 'paladin', desc: 'Strikes an adjacent foe with infinite accuracy and bonus holy damage.' },
  { id: 'lay_on_hands', label: 'Lay on Hands', tier: 3, cost: 1, icon: '🤲', targeting: 'ally_or_self', talent: 'lay_on_hands', desc: 'Grants barrier to yourself or restores health to an ally.' },
  { id: 'aura_of_protection', label: 'Aura of Protection', tier: 3, cost: 2, icon: '🛡️', targeting: 'none', talent: 'aura_of_protection', desc: 'Emits a protective aura reducing damage taken by allies within 2 tiles.' },
  { id: 'wall_of_light', label: 'Wall of Light', tier: 3, cost: 3, icon: '🧱', targeting: 'cell', talent: 'wall_of_light', desc: 'Raises a solid barrier of light for 20 turns, knocking back and stunning enemies.' },
  { id: 'divine_intervention', label: 'Divine Intervention', tier: 4, cost: 5, icon: '👑', targeting: 'none', talent: 'divine_intervention', desc: 'Grants a massive shield (150-300) and extends Ascended Form.' },
  { id: 'judgement', label: 'Judgement', tier: 4, cost: 3, icon: '⚡', targeting: 'none', talent: 'judgement', desc: 'Smites all visible enemies, dealing damage amplified by spells cast during Ascension.' },
  { id: 'flash', label: 'Flash', tier: 4, cost: 2, icon: '⚡', targeting: 'cell', talent: 'flash', desc: 'Teleports up to 3-6 tiles away instantly.' },
  { id: 'body_form', label: 'Body Form', tier: 4, cost: 2, icon: '⚔️', targeting: 'none', talent: 'body_form', desc: 'Imbues weapon enchantment or armor glyph for 20-40 turns.' },
  { id: 'mind_form', label: 'Mind Form', tier: 4, cost: 3, icon: '🔮', targeting: 'mob', talent: 'mind_form', desc: 'Casts a high level wand blast or thrown missile.' },
  { id: 'spirit_form', label: 'Spirit Form', tier: 4, cost: 4, icon: '💍', targeting: 'none', talent: 'spirit_form', desc: 'Borrows the power of an identified ring or artifact for 20 turns.' },
  { id: 'beaming_ray', label: 'Beaming Ray', tier: 4, cost: 1, icon: '🌠', targeting: 'cell', talent: 'beaming_ray', desc: 'Teleports your Light Ally up to 4-16 tiles and boosts their damage.' },
  { id: 'life_link', label: 'Life Link', tier: 4, cost: 2, icon: '🔗', targeting: 'none', talent: 'life_link', desc: 'Links HP with your Light Ally for 10-20 turns and duplicates spells.' },
  { id: 'stasis', label: 'Stasis', tier: 4, cost: 2, icon: '⏳', targeting: 'none', talent: 'stasis', desc: 'Stores your Light Ally inside you in stasis for up to 60-150 turns.' },
];

export function getClericSpell(spellId) {
  return CLERIC_SPELLS.find(s => s.id === spellId) || null;
}

export function isSpellUnlocked(spell, { talentLevels = {}, subclass = null, ascendedFormActive = false, poweredAllyId = null } = {}) {
  if (spell.talent && !talentLevels[spell.talent]) {
    return false;
  }
  if (spell.subclass && spell.subclass !== subclass) {
    return false;
  }
  if (spell.tier === 4) {
    if (['divine_intervention', 'judgement', 'flash'].includes(spell.id) && !ascendedFormActive) {
      return false;
    }
    if (['beaming_ray', 'life_link', 'stasis'].includes(spell.id) && !poweredAllyId) {
      return false;
    }
  }
  return true;
}
