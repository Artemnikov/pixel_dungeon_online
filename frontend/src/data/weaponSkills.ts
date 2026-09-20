export interface WeaponSkillContext {
  effects?: Array<{ name?: string; type?: string; id?: string; key?: string } | string>;
  active_effects?: Array<{ name?: string; type?: string; id?: string; key?: string } | string>;
  [key: string]: unknown;
}

function hasEffect(context: WeaponSkillContext | undefined, effectKey: string): boolean {
  if (!context) return false;
  const list = context.effects || context.active_effects || [];
  return list.some((eff) => {
    if (typeof eff === 'string') return eff === effectKey;
    return eff?.name === effectKey || eff?.type === effectKey || eff?.id === effectKey || eff?.key === effectKey;
  });
}

export function calculateMaxCharges(level: number = 1, subclass?: string | null): number {
  if (subclass === 'champion') {
    return Math.min(10, 4 + Math.floor((Math.max(1, level) - 1) / 3));
  }
  return Math.min(8, 2 + Math.floor((Math.max(1, level) - 1) / 3));
}

export abstract class WeaponSkill {
  abstract readonly id: string;
  abstract readonly name: string;
  abstract readonly description: string;
  abstract readonly requiresTarget: boolean;

  getChargeCost(_item?: unknown, _context?: WeaponSkillContext): number {
    return 1.0;
  }

  getUsageCount(charges: number, item?: unknown, context?: WeaponSkillContext): number {
    const cost = this.getChargeCost(item, context);
    if (cost <= 0) {
      return Math.max(1, Math.floor(charges));
    }
    return Math.floor(charges / cost);
  }

  formatStatus(charges: number, maxCharges: number, item?: unknown, context?: WeaponSkillContext): string {
    const cost = this.getChargeCost(item, context);
    if (cost === 0 && hasEffect(context, 'cleave_tracker')) {
      return 'FREE';
    }
    return `${Math.floor(charges)}/${maxCharges}`;
  }

  isReady(charges: number, item?: unknown, context?: WeaponSkillContext): boolean {
    const cost = this.getChargeCost(item, context);
    return charges >= cost || cost === 0;
  }
}

export class LungeSkill extends WeaponSkill {
  readonly id = 'lunge';
  readonly name = 'Lunge';
  readonly description = 'Lunge at an enemy within 2 tiles with infinite accuracy and bonus damage.';
  readonly requiresTarget = true;
}

export class SneakSkill extends WeaponSkill {
  readonly id = 'sneak';
  readonly name = 'Sneak';
  readonly description = 'Teleport to a visible tile and turn invisible for several turns.';
  readonly requiresTarget = true;
}

export class CleaveSkill extends WeaponSkill {
  readonly id = 'cleave';
  readonly name = 'Cleave';
  readonly description = 'Strike an adjacent enemy with infinite accuracy. If it dies, the action is instant and the next Cleave is free.';
  readonly requiresTarget = true;

  override getChargeCost(_item?: unknown, context?: WeaponSkillContext): number {
    if (hasEffect(context, 'cleave_tracker')) {
      return 0.0;
    }
    return 1.0;
  }
}

export class SpikeSkill extends WeaponSkill {
  readonly id = 'spike';
  readonly name = 'Spike';
  readonly description = 'Strike an enemy at reach 2 with bonus damage and knockback.';
  readonly requiresTarget = true;
}

export class DefensiveStanceSkill extends WeaponSkill {
  readonly id = 'defensive_stance';
  readonly name = 'Defensive Stance';
  readonly description = 'Enter a defensive stance granting 3x evasion for several turns.';
  readonly requiresTarget = false;
}

export class SwordDanceSkill extends WeaponSkill {
  readonly id = 'sword_dance';
  readonly name = 'Sword Dance';
  readonly description = 'Perform a blade dance granting +50% accuracy and +60% attack speed.';
  readonly requiresTarget = false;
}

export class HarvestSkill extends WeaponSkill {
  readonly id = 'harvest';
  readonly name = 'Harvest';
  readonly description = 'Inflict severe armor-ignoring bleed damage on target enemy.';
  readonly requiresTarget = true;
}

export class LashSkill extends WeaponSkill {
  readonly id = 'lash';
  readonly name = 'Whirling Strike';
  readonly description = 'Simultaneously strike all visible enemies within reach.';
  readonly requiresTarget = false;
}

export class SpinSkill extends WeaponSkill {
  readonly id = 'spin';
  readonly name = 'Spin';
  readonly description = 'Wind up momentum (up to 3 stacks) to unleash massive bonus damage on your next attack.';
  readonly requiresTarget = false;

  override getChargeCost(_item?: unknown, context?: WeaponSkillContext): number {
    if (hasEffect(context, 'spin_tracker')) {
      return 0.0;
    }
    return 1.0;
  }
}

export class ComboStrikeSkill extends WeaponSkill {
  readonly id = 'combo_strike';
  readonly name = 'Combo Strike';
  readonly description = 'Strike with infinite accuracy, scaling with recent combo hits.';
  readonly requiresTarget = true;
}

export class HeavyBlowSkill extends WeaponSkill {
  readonly id = 'heavy_blow';
  readonly name = 'Heavy Blow';
  readonly description = 'Guaranteed hit with infinite accuracy; inflicts Dazed on surprise attack.';
  readonly requiresTarget = true;
}

export class RetributionSkill extends WeaponSkill {
  readonly id = 'retribution';
  readonly name = 'Execute';
  readonly description = 'Devastating strike when below 50% HP with infinite accuracy; free turn on kill.';
  readonly requiresTarget = true;
}

export class GuardSkill extends WeaponSkill {
  readonly id = 'guard';
  readonly name = 'Guard';
  readonly description = 'Enter a guarding stance to block the next incoming attack completely.';
  readonly requiresTarget = false;
}

export class ChargedShotSkill extends WeaponSkill {
  readonly id = 'charged_shot';
  readonly name = 'Charged Shot';
  readonly description = 'Empower your next dart shot with infinite accuracy and a blast wave.';
  readonly requiresTarget = false;
}

export class RunicSlashSkill extends WeaponSkill {
  readonly id = 'runic_slash';
  readonly name = 'Runic Slash';
  readonly description = 'Strike with infinite accuracy and greatly amplified enchantment power.';
  readonly requiresTarget = true;
}

export class PierceSkill extends WeaponSkill {
  readonly id = 'pierce';
  readonly name = 'Heavy Strike';
  readonly description = 'Strike with bonus damage vs inorganic enemies and inflict Vulnerable.';
  readonly requiresTarget = true;
}

export class BrawlerStanceSkill extends WeaponSkill {
  readonly id = 'brawler_stance';
  readonly name = "Brawler's Stance";
  readonly description = 'Toggle unarmed combat stance while maintaining weapon enchantments.';
  readonly requiresTarget = false;

  override getChargeCost(): number {
    return 0.0;
  }
}

export const SKILL_LUNGE = new LungeSkill();
export const SKILL_SNEAK = new SneakSkill();
export const SKILL_CLEAVE = new CleaveSkill();
export const SKILL_SPIKE = new SpikeSkill();
export const SKILL_DEFENSIVE_STANCE = new DefensiveStanceSkill();
export const SKILL_SWORD_DANCE = new SwordDanceSkill();
export const SKILL_HARVEST = new HarvestSkill();
export const SKILL_LASH = new LashSkill();
export const SKILL_SPIN = new SpinSkill();
export const SKILL_COMBO_STRIKE = new ComboStrikeSkill();
export const SKILL_HEAVY_BLOW = new HeavyBlowSkill();
export const SKILL_RETRIBUTION = new RetributionSkill();
export const SKILL_GUARD = new GuardSkill();
export const SKILL_CHARGED_SHOT = new ChargedShotSkill();
export const SKILL_RUNIC_SLASH = new RunicSlashSkill();
export const SKILL_PIERCE = new PierceSkill();
export const SKILL_BRAWLER_STANCE = new BrawlerStanceSkill();

const DEFAULT_WEAPON_SKILL: WeaponSkill = SKILL_CLEAVE;

export class WeaponSkillRegistry {
  private static readonly skillMap: Record<string, WeaponSkill> = {
    'Rapier': SKILL_LUNGE,
    'Dagger': SKILL_SNEAK,
    'Gloves': SKILL_COMBO_STRIKE,
    'Cudgel': SKILL_HEAVY_BLOW,
    'Worn Shortsword': SKILL_CLEAVE,
    'worn_shortsword': SKILL_CLEAVE,
    'Shortsword': SKILL_CLEAVE,
    'Hand Axe': SKILL_HEAVY_BLOW,
    'Spear': SKILL_SPIKE,
    'Quarterstaff': SKILL_DEFENSIVE_STANCE,
    'Dirk': SKILL_SNEAK,
    'Sickle': SKILL_HARVEST,
    'Pickaxe': SKILL_PIERCE,
    'Sword': SKILL_CLEAVE,
    'Mace': SKILL_HEAVY_BLOW,
    'Scimitar': SKILL_SWORD_DANCE,
    'Round Shield': SKILL_GUARD,
    'Sai': SKILL_COMBO_STRIKE,
    'Whip': SKILL_LASH,
    'Longsword': SKILL_CLEAVE,
    'Battle Axe': SKILL_HEAVY_BLOW,
    'Flail': SKILL_SPIN,
    'Runic Blade': SKILL_RUNIC_SLASH,
    "Assassin's Blade": SKILL_SNEAK,
    'Crossbow': SKILL_CHARGED_SHOT,
    'Katana': SKILL_LUNGE,
    'Greatsword': SKILL_CLEAVE,
    'War Hammer': SKILL_HEAVY_BLOW,
    'Glaive': SKILL_SPIKE,
    'Greataxe': SKILL_RETRIBUTION,
    'Greatshield': SKILL_GUARD,
    'Gauntlet': SKILL_COMBO_STRIKE,
    'War Scythe': SKILL_HARVEST,
    'Ring of Force': SKILL_BRAWLER_STANCE,
  };

  public static getSkillForWeapon(item: { name?: string; kind?: string; type?: string } | null | undefined): WeaponSkill | null {
    if (!item) return null;
    if (item.name && this.skillMap[item.name]) {
      return this.skillMap[item.name];
    }
    if (item.kind && this.skillMap[item.kind]) {
      return this.skillMap[item.kind];
    }
    if (this.isMeleeWeapon(item)) {
      return DEFAULT_WEAPON_SKILL;
    }
    return null;
  }

  public static isMeleeWeapon(item: { name?: string; kind?: string; type?: string } | null | undefined): boolean {
    if (!item) return false;
    if (item.name === 'Ring of Force') return true;
    if (item.kind === 'staff' || item.name === "Mage's Staff" || item.kind === 'bow' || item.kind === 'spirit_bow') {
      return false;
    }
    if (item.kind === 'melee_weapon' || item.kind === 'worn_shortsword' || item.kind === 'dagger') {
      return true;
    }
    if (item.type === 'weapon' && item.kind !== 'missile_weapon') {
      return true;
    }
    if (item.name && this.skillMap[item.name]) {
      return true;
    }
    return false;
  }
}
