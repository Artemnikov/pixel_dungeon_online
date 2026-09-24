import { isAttackReady, consumeAttackCooldown } from '../../net/events/combat';
import {
  isObjectTargetingMode,
  type ObjectTargetingMode,
} from '../targetingMode';

export interface EquippedWeaponRef {
  id?: string;
  attack_cooldown?: number;
}

export interface TargetingTapContext {
  send: (msg: Record<string, unknown>) => void;
  equippedItems?: { weapon?: EquippedWeaponRef | null };
  entitiesRef?: { current: { mobs?: Record<string, { renderPos?: { x: number; y: number } }> } };
  selectedEnemyIdRef?: { current: string | null };
  setTargetingMode: (mode: unknown) => void;
}

/**
 * A single resolution path for a targeting-mode tile tap. Handlers are checked
 * in order and the first one that can handle the mode consumes the tap.
 */
export interface ITargetingTapHandler {
  canHandle(tm: unknown, ctx: TargetingTapContext): boolean;
  handle(tm: unknown, tileX: number, tileY: number, ctx: TargetingTapContext): boolean;
}

export class ArmorAbilityTapHandler implements ITargetingTapHandler {
  public canHandle(tm: unknown): boolean {
    return isObjectTargetingMode(tm) && Boolean(tm.ability);
  }

  public handle(tm: unknown, tileX: number, tileY: number, ctx: TargetingTapContext): boolean {
    const mode = tm as ObjectTargetingMode;
    ctx.send({ type: 'USE_ARMOR_ABILITY', ability: mode.ability, target_x: tileX, target_y: tileY });
    ctx.setTargetingMode(false);
    return true;
  }
}

export class ComboMoveTapHandler implements ITargetingTapHandler {
  public canHandle(tm: unknown): boolean {
    return isObjectTargetingMode(tm) && Boolean(tm.comboMove);
  }

  public handle(tm: unknown, tileX: number, tileY: number, ctx: TargetingTapContext): boolean {
    const mode = tm as ObjectTargetingMode;
    ctx.send({ type: 'USE_COMBO_MOVE', move: mode.comboMove, target_x: tileX, target_y: tileY });
    ctx.setTargetingMode(false);
    return true;
  }
}

export class PrepStrikeTapHandler implements ITargetingTapHandler {
  public canHandle(tm: unknown): boolean {
    return isObjectTargetingMode(tm) && Boolean(tm.prepStrike);
  }

  public handle(_tm: unknown, tileX: number, tileY: number, ctx: TargetingTapContext): boolean {
    ctx.send({ type: 'PREPARATION_STRIKE', target_x: tileX, target_y: tileY });
    ctx.setTargetingMode(false);
    return true;
  }
}

export class DuelistFinisherTapHandler implements ITargetingTapHandler {
  public canHandle(tm: unknown): boolean {
    return isObjectTargetingMode(tm) && Boolean(tm.duelistFinisher);
  }

  public handle(tm: unknown, tileX: number, tileY: number, ctx: TargetingTapContext): boolean {
    const mode = tm as ObjectTargetingMode;
    if (mode.useSecondary) {
      ctx.send({ type: 'USE_WEAPON_ABILITY', target_x: tileX, target_y: tileY, use_secondary: true });
    } else {
      ctx.send({ type: 'DUELIST_FINISHER', target_x: tileX, target_y: tileY });
    }
    ctx.setTargetingMode(false);
    return true;
  }
}

export class ClericSpellTapHandler implements ITargetingTapHandler {
  public canHandle(tm: unknown): boolean {
    return isObjectTargetingMode(tm) && Boolean(tm.clericSpell);
  }

  public handle(tm: unknown, tileX: number, tileY: number, ctx: TargetingTapContext): boolean {
    const mode = tm as ObjectTargetingMode;
    ctx.send({ type: 'CAST_CLERIC_SPELL', spell: mode.clericSpell, target_x: tileX, target_y: tileY });
    ctx.setTargetingMode(false);
    return true;
  }
}

export class ItemActionTapHandler implements ITargetingTapHandler {
  public canHandle(tm: unknown): boolean {
    return isObjectTargetingMode(tm) && Boolean(tm.action);
  }

  public handle(tm: unknown, tileX: number, tileY: number, ctx: TargetingTapContext): boolean {
    const mode = tm as ObjectTargetingMode;
    const isCombatAction = mode.action === 'THROW' || mode.action === 'ZAP';
    if (isCombatAction && !isAttackReady()) return true;
    if (isCombatAction) consumeAttackCooldown();
    ctx.send({
      type: 'EXECUTE_ITEM_ACTION',
      item_id: mode.itemId,
      action: mode.action,
      target_x: tileX,
      target_y: tileY,
    });
    ctx.setTargetingMode(false);
    return true;
  }
}

export class RangedWeaponTapHandler implements ITargetingTapHandler {
  public canHandle(tm: unknown, ctx: TargetingTapContext): boolean {
    return typeof tm === 'string' || Boolean(ctx.equippedItems?.weapon?.id);
  }

  public handle(tm: unknown, tileX: number, tileY: number, ctx: TargetingTapContext): boolean {
    const weaponId = typeof tm === 'string' ? tm : ctx.equippedItems?.weapon?.id;
    if (!weaponId) return false;
    if (!isAttackReady()) return true;
    consumeAttackCooldown((ctx.equippedItems?.weapon?.attack_cooldown ?? 1.0) * 1000);
    // If the tapped cell is the locked target's cell, let the server auto-aim
    // (angle around corners) via target_entity_id; SPD QuickSlotButton.autoAim.
    const lockId = ctx.selectedEnemyIdRef?.current || null;
    const lock = lockId ? ctx.entitiesRef?.current?.mobs?.[lockId] : null;
    const onLock = lock
      && Math.round(lock.renderPos?.x ?? 0) === tileX
      && Math.round(lock.renderPos?.y ?? 0) === tileY;
    ctx.send({
      type: 'RANGED_ATTACK',
      item_id: weaponId,
      target_x: tileX,
      target_y: tileY,
      target_entity_id: onLock ? lockId : null,
    });
    ctx.setTargetingMode(typeof tm === 'string' ? false : true);
    return true;
  }
}

export class TargetingTapDispatcher {
  private handlers: ITargetingTapHandler[];

  constructor(handlers?: ITargetingTapHandler[]) {
    this.handlers = handlers ?? [
      new ArmorAbilityTapHandler(),
      new ComboMoveTapHandler(),
      new PrepStrikeTapHandler(),
      new DuelistFinisherTapHandler(),
      new ClericSpellTapHandler(),
      new ItemActionTapHandler(),
      new RangedWeaponTapHandler(),
    ];
  }

  public register(handler: ITargetingTapHandler): void {
    this.handlers.push(handler);
  }

  /**
   * Resolves a targeting-mode tile tap. Unlike ToolbarClickDispatcher, the tap
   * handlers are mutually exclusive per mode shape, so the first canHandle
   * match always consumes the tap and later handlers are never consulted.
   */
  public dispatch(tm: unknown, tileX: number, tileY: number, ctx: TargetingTapContext): boolean {
    for (const handler of this.handlers) {
      if (handler.canHandle(tm, ctx)) {
        return handler.handle(tm, tileX, tileY, ctx);
      }
    }
    return false;
  }
}

export const defaultTargetingTapDispatcher = new TargetingTapDispatcher();