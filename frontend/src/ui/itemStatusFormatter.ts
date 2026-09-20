import { WeaponSkillRegistry, calculateMaxCharges } from '../data/weaponSkills';

export interface ItemLike {
  name?: string;
  kind?: string;
  type?: string;
  volume?: number;
  charges?: number;
  max_charges?: number;
  charge?: number;
  charge_cap?: number;
  quantity?: number;
  [key: string]: unknown;
}

export interface ItemStatusResult {
  text: string;
  refText?: string;
  skillId?: string;
  skillName?: string;
  usageCount?: number;
}

export interface ItemStatusContext {
  classType?: string;
  weaponCharge?: number;
  maxWeaponCharges?: number;
  effects?: Array<{ name?: string; type?: string; id?: string; key?: string } | string>;
  active_effects?: Array<{ name?: string; type?: string; id?: string; key?: string } | string>;
  subclass?: string | null;
  [key: string]: unknown;
}

export interface IItemStatusFormatter {
  canFormat(item: ItemLike | null | undefined, context?: ItemStatusContext): boolean;
  format(item: ItemLike | null | undefined, context?: ItemStatusContext): ItemStatusResult | null;
}

export class WaterskinStatusFormatter implements IItemStatusFormatter {
  canFormat(item: ItemLike | null | undefined): boolean {
    return item?.kind === 'waterskin';
  }

  format(item: ItemLike | null | undefined): ItemStatusResult | null {
    const vol = item?.volume ?? 0;
    return {
      text: `${vol}/20`,
      refText: '20/20',
    };
  }
}

export class WandStatusFormatter implements IItemStatusFormatter {
  canFormat(item: ItemLike | null | undefined): boolean {
    if (!item) return false;
    const max = item.max_charges ?? 0;
    const isWandKind = item.kind === 'wand' || item.kind === 'staff' || (typeof item.kind === 'string' && item.kind.startsWith('wand_'));
    return max > 0 && isWandKind;
  }

  format(item: ItemLike | null | undefined): ItemStatusResult | null {
    const charges = item?.charges ?? 0;
    const max = item?.max_charges ?? 0;
    return {
      text: `${charges}/${max}`,
      refText: `${max}/${max}`,
    };
  }
}

export class ArtifactStatusFormatter implements IItemStatusFormatter {
  canFormat(item: ItemLike | null | undefined): boolean {
    return item?.type === 'artifact' || item?.kind === 'artifact';
  }

  format(item: ItemLike | null | undefined): ItemStatusResult | null {
    const cap = item?.charge_cap;
    const charge = item?.charge ?? 0;
    if (cap === 100) {
      return { text: `${charge}%`, refText: '100%' };
    }
    if (typeof cap === 'number' && cap > 0) {
      return { text: `${charge}/${cap}`, refText: `${cap}/${cap}` };
    }
    if (charge !== 0) {
      return { text: `${charge}`, refText: `${charge}` };
    }
    return null;
  }
}

export class DuelistWeaponStatusFormatter implements IItemStatusFormatter {
  canFormat(item: ItemLike | null | undefined, context?: ItemStatusContext): boolean {
    if (context?.classType !== 'duelist') return false;
    return WeaponSkillRegistry.isMeleeWeapon(item);
  }

  format(item: ItemLike | null | undefined, context?: ItemStatusContext): ItemStatusResult | null {
    const skill = WeaponSkillRegistry.getSkillForWeapon(item);
    if (!skill) return null;

    const charges = context?.weaponCharge ?? 0;
    const maxCharges = context?.maxWeaponCharges ?? calculateMaxCharges(typeof context?.level === 'number' ? context.level : 1, context?.subclass);

    const text = skill.formatStatus(charges, maxCharges, item, context);
    const usageCount = skill.getUsageCount(charges, item, context);

    return {
      text,
      refText: `${maxCharges}/${maxCharges}`,
      skillId: skill.id,
      skillName: skill.name,
      usageCount,
    };
  }
}

export class StackQuantityFormatter implements IItemStatusFormatter {
  canFormat(item: ItemLike | null | undefined): boolean {
    return typeof item?.quantity === 'number' && item.quantity > 1;
  }

  format(item: ItemLike | null | undefined): ItemStatusResult | null {
    const q = item?.quantity ?? 1;
    return {
      text: `${q}`,
      refText: `${q}`,
    };
  }
}

export class ItemStatusService {
  private static readonly formatters: IItemStatusFormatter[] = [
    new WaterskinStatusFormatter(),
    new WandStatusFormatter(),
    new ArtifactStatusFormatter(),
    new DuelistWeaponStatusFormatter(),
    new StackQuantityFormatter(),
  ];

  public static getItemStatus(item: ItemLike | null | undefined, context?: ItemStatusContext): ItemStatusResult | null {
    if (!item) return null;
    for (const formatter of this.formatters) {
      if (formatter.canFormat(item, context)) {
        const result = formatter.format(item, context);
        if (result) return result;
      }
    }
    return null;
  }
}
