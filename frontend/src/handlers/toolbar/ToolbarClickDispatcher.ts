import { WeaponSkillRegistry } from '../../data/weaponSkills';
import {
  isDuelistFinisherArmed,
  isTargetingArmedForItem,
} from '../../game/targetingMode';
import {
  buildWeaponSkillContext,
  type DuelistStats,
  type ToolbarItem,
} from './types';

/**
 * Actions that arm a target-selection mode instead of firing immediately when
 * routed through `executeItemAction` without an explicit target tile.
 */
export const TARGETED_ACTIONS = [
  'THROW',
  'ZAP',
  'DIRECT',
  'SHOOT',
  'CAST',
  'STEAL',
  'PLANT_SEED',
  'UNLOCK',
  'KEY_REVEAL',
];

export interface ExecuteItemActionOptions {
  tx?: number;
  ty?: number;
  fromQuickbar?: boolean;
}

export interface ToolbarClickContext {
  send: (msg: Record<string, unknown>) => void;
  equippedItems?: { weapon?: ToolbarItem | null };
  belongings?: {
    secondary_weapon?: ToolbarItem | null;
    artifact?: ToolbarItem | null;
    misc?: ToolbarItem | null;
    backpack?: { items?: ToolbarItem[] };
  };
  myStats?: DuelistStats;
  targetingMode?: unknown;
  setTargetingMode: (mode: unknown) => void;
  equipItem: (itemId: string) => void;
  executeItemAction: (itemId: string, action: string, opts?: ExecuteItemActionOptions) => void;
  onOpenClericCastBar?: () => void;
}

/**
 * A single toolbar single-click resolution path. Handlers are checked in
 * order and the first one that handles the item consumes the click.
 */
export interface IToolbarClickHandler {
  canHandle(item: ToolbarItem, ctx: ToolbarClickContext): boolean;
  handle(item: ToolbarItem, ctx: ToolbarClickContext): boolean;
}

export class HolyTomeClickHandler implements IToolbarClickHandler {
  public canHandle(item: ToolbarItem): boolean {
    return item.kind === 'holy_tome';
  }

  public handle(_item: ToolbarItem, ctx: ToolbarClickContext): boolean {
    ctx.onOpenClericCastBar?.();
    return true;
  }
}

export class PotionClickHandler implements IToolbarClickHandler {
  public canHandle(item: ToolbarItem): boolean {
    return item.type === 'potion';
  }

  public handle(item: ToolbarItem, ctx: ToolbarClickContext): boolean {
    ctx.send({ type: 'USE_ITEM', item_id: item.id });
    return true;
  }
}

export class StaffClickHandler implements IToolbarClickHandler {
  public canHandle(item: ToolbarItem): boolean {
    return item.type === 'weapon' && item.kind === 'staff';
  }

  public handle(item: ToolbarItem, ctx: ToolbarClickContext): boolean {
    if (isTargetingArmedForItem(ctx.targetingMode, item.id)) {
      ctx.setTargetingMode(false);
    } else if (item.default_action) {
      ctx.executeItemAction(item.id, item.default_action!, { fromQuickbar: true });
    }
    return true;
  }
}

export class DuelistWeaponClickHandler implements IToolbarClickHandler {
  public canHandle(item: ToolbarItem, ctx: ToolbarClickContext): boolean {
    return item.type === 'weapon' && ctx.myStats?.classType === 'duelist';
  }

  public handle(item: ToolbarItem, ctx: ToolbarClickContext): boolean {
    const isPrimary = ctx.equippedItems?.weapon?.id === item.id;
    const isSecondary = ctx.belongings?.secondary_weapon?.id === item.id;
    if (!isPrimary && !isSecondary) {
      ctx.equipItem(item.id);
      return true;
    }
    const skill = WeaponSkillRegistry.getSkillForWeapon(item);
    if (!skill) return false; // Not a melee-duelist weapon; let later handlers decide.
    if (isDuelistFinisherArmed(ctx.targetingMode, item.id)) {
      ctx.setTargetingMode(false);
      return true;
    }
    const skillContext = buildWeaponSkillContext(ctx.myStats);
    if (skill.isReady(skillContext.weaponCharge, item, skillContext)) {
      if (skill.requiresTarget) {
        ctx.setTargetingMode({ duelistFinisher: true, itemId: item.id, useSecondary: isSecondary, fromQuickbar: true });
      } else if (isSecondary) {
        ctx.send({ type: 'USE_WEAPON_ABILITY', use_secondary: true });
      } else {
        ctx.send({ type: 'DUELIST_FINISHER' });
      }
    }
    return true;
  }
}

export class TargetedWeaponClickHandler implements IToolbarClickHandler {
  public canHandle(item: ToolbarItem): boolean {
    if (item.type !== 'weapon' || !item.default_action) return false;
    return TARGETED_ACTIONS.includes(item.default_action);
  }

  public handle(item: ToolbarItem, ctx: ToolbarClickContext): boolean {
    ctx.executeItemAction(item.id, item.default_action!, { fromQuickbar: true });
    return true;
  }
}

export class EquippableWeaponClickHandler implements IToolbarClickHandler {
  public canHandle(item: ToolbarItem): boolean {
    return item.type === 'weapon';
  }

  public handle(item: ToolbarItem, ctx: ToolbarClickContext): boolean {
    const isEquipped = ctx.equippedItems?.weapon?.id === item.id;
    if (!isEquipped) {
      ctx.equipItem(item.id);
      if (item.range && item.range > 1) {
        ctx.setTargetingMode(item.id);
      } else {
        ctx.setTargetingMode(false);
      }
    } else if (item.range && item.range > 1) {
      // Functional update: React setState supports updaters; toggles armed/unarmed.
      ctx.setTargetingMode((prev: unknown) => !prev);
    }
    return true;
  }
}

export class WearableClickHandler implements IToolbarClickHandler {
  public canHandle(item: ToolbarItem): boolean {
    return item.type === 'wearable';
  }

  public handle(item: ToolbarItem, ctx: ToolbarClickContext): boolean {
    ctx.equipItem(item.id);
    return true;
  }
}

export class ThrowableClickHandler implements IToolbarClickHandler {
  public canHandle(item: ToolbarItem): boolean {
    return item.throw_behavior === 'missile'
      || item.type === 'throwable'
      || item.throw_behavior === 'seed'
      || item.type === 'seed'
      || item.default_action === 'THROW';
  }

  public handle(item: ToolbarItem, ctx: ToolbarClickContext): boolean {
    if (isTargetingArmedForItem(ctx.targetingMode, item.id)) {
      ctx.setTargetingMode(false);
    } else {
      ctx.setTargetingMode({ itemId: item.id, action: 'THROW', fromQuickbar: true });
    }
    return true;
  }
}

export class WandClickHandler implements IToolbarClickHandler {
  public canHandle(item: ToolbarItem): boolean {
    return item.type === 'wand';
  }

  public handle(item: ToolbarItem, ctx: ToolbarClickContext): boolean {
    if (isTargetingArmedForItem(ctx.targetingMode, item.id)) {
      ctx.setTargetingMode(false);
    } else {
      ctx.executeItemAction(item.id, 'ZAP', { fromQuickbar: true });
    }
    return true;
  }
}

export class DefaultActionClickHandler implements IToolbarClickHandler {
  public canHandle(item: ToolbarItem): boolean {
    return Boolean(item.default_action);
  }

  public handle(item: ToolbarItem, ctx: ToolbarClickContext): boolean {
    ctx.executeItemAction(item.id, item.default_action!, { fromQuickbar: true });
    return true;
  }
}

export class ToolbarClickDispatcher {
  private handlers: IToolbarClickHandler[];

  constructor(handlers?: IToolbarClickHandler[]) {
    this.handlers = handlers ?? [
      new HolyTomeClickHandler(),
      new PotionClickHandler(),
      new StaffClickHandler(),
      new DuelistWeaponClickHandler(),
      new TargetedWeaponClickHandler(),
      new EquippableWeaponClickHandler(),
      new WearableClickHandler(),
      new ThrowableClickHandler(),
      new WandClickHandler(),
      new DefaultActionClickHandler(),
    ];
  }

  public register(handler: IToolbarClickHandler): void {
    this.handlers.push(handler);
  }

  public dispatch(item: ToolbarItem | null | undefined, ctx: ToolbarClickContext): boolean {
    if (!item) return false;
    for (const handler of this.handlers) {
      if (handler.canHandle(item, ctx) && handler.handle(item, ctx)) return true;
    }
    return false;
  }
}

export const defaultToolbarClickDispatcher = new ToolbarClickDispatcher();