import { WeaponSkillRegistry } from '../../data/weaponSkills';
import { pickAutoAimTarget } from '../../game/autoAim';
import { canAutoAim } from '../../game/targetingModeInfo';
import { isAttackReady, consumeAttackCooldown } from '../../net/events/combat';
import {
  buildWeaponSkillContext,
  type DuelistStats,
  type ToolbarItem,
} from './types';

export interface RenderTarget {
  id?: string;
  name?: string;
  faction?: string;
  is_alive?: boolean;
  is_downed?: boolean;
  hp?: number;
  renderPos?: { x: number; y: number };
}

export interface ToolbarDoubleClickContext {
  send: (msg: Record<string, unknown>) => void;
  entitiesRef: { current: { mobs?: Record<string, RenderTarget>; players?: Record<string, RenderTarget> } };
  myPlayerIdRef: { current: string };
  visionRef: { current: { visible: Set<string> } };
  selectedEnemyIdRef: { current: string | null };
  myStats?: DuelistStats;
  equippedItems?: { weapon?: ToolbarItem | null };
  belongings?: { secondary_weapon?: ToolbarItem | null };
  setTargetingMode?: (mode: unknown) => void;
}

/**
 * Every living hostile entity (mobs + enemy players) visible to the local
 * player, used for nearest-enemy auto-aim (SPD QuickSlotButton.autoAim).
 */
export function buildCandidateTargets(
  entitiesRef: ToolbarDoubleClickContext['entitiesRef'],
  myPlayerId: string,
  myFaction: string,
): Record<string, RenderTarget> {
  const targets: Record<string, RenderTarget> = { ...entitiesRef.current.mobs };
  for (const [id, p] of Object.entries(entitiesRef.current.players || {})) {
    if (id === myPlayerId || p.is_alive === false || p.is_downed || (p.faction || 'player') === myFaction) continue;
    targets[id] = { ...p, faction: p.faction || 'player' };
  }
  return targets;
}

/**
 * A single toolbar double-click resolution path. Handlers are checked in
 * order and the first one that can handle the item consumes the double-click.
 */
export interface IToolbarDoubleClickHandler {
  canHandle(item: ToolbarItem, ctx: ToolbarDoubleClickContext): boolean;
  handle(item: ToolbarItem, ctx: ToolbarDoubleClickContext): boolean;
}

export class DuelistFinisherDoubleClickHandler implements IToolbarDoubleClickHandler {
  public canHandle(item: ToolbarItem, ctx: ToolbarDoubleClickContext): boolean {
    if (ctx.myStats?.classType !== 'duelist') return false;
    const isPrimary = ctx.equippedItems?.weapon?.id === item.id;
    const isSecondary = ctx.belongings?.secondary_weapon?.id === item.id;
    return isPrimary || isSecondary;
  }

  public handle(item: ToolbarItem, ctx: ToolbarDoubleClickContext): boolean {
    const isSecondary = ctx.belongings?.secondary_weapon?.id === item.id;
    const skill = WeaponSkillRegistry.getSkillForWeapon(item);
    if (!skill) return false; // Not a melee-duelist weapon; try the ranged auto-aim handler.
    const skillContext = buildWeaponSkillContext(ctx.myStats);
    if (!skill.isReady(skillContext.weaponCharge, item, skillContext)) {
      return true;
    }
    if (!skill.requiresTarget) {
      if (isSecondary) {
        ctx.send({ type: 'USE_WEAPON_ABILITY', use_secondary: true });
      } else {
        ctx.send({ type: 'DUELIST_FINISHER' });
      }
      ctx.setTargetingMode?.(false);
      return true;
    }

    const myPlayer = ctx.entitiesRef.current.players?.[ctx.myPlayerIdRef.current];
    if (!myPlayer) return true;

    const myFaction = myPlayer.faction || 'player';
    const candidateTargets = buildCandidateTargets(ctx.entitiesRef, ctx.myPlayerIdRef.current, myFaction);

    const isReach2Skill = skill.id === 'lunge' || skill.id === 'spike';
    const queryRange = isReach2Skill ? 2.85 : Math.max(1.5, (item.range || 1) * 1.45);
    if (skill.id !== 'sneak') {
      const pick = pickAutoAimTarget(
        ctx.selectedEnemyIdRef.current,
        candidateTargets,
        ctx.visionRef.current.visible,
        { x: myPlayer.renderPos?.x ?? 0, y: myPlayer.renderPos?.y ?? 0 },
        queryRange,
        myFaction,
      );
      if (pick) {
        const px = Math.round(myPlayer.renderPos?.x ?? 0);
        const py = Math.round(myPlayer.renderPos?.y ?? 0);
        const dist = Math.max(Math.abs(pick.x - px), Math.abs(pick.y - py));
        if ((isReach2Skill && dist === 2) || (!isReach2Skill && dist <= (item.range || 1))) {
          if (isSecondary) {
            ctx.send({ type: 'USE_WEAPON_ABILITY', target_x: pick.x, target_y: pick.y, use_secondary: true });
          } else {
            ctx.send({ type: 'DUELIST_FINISHER', target_x: pick.x, target_y: pick.y });
          }
          ctx.setTargetingMode?.(false);
          return true;
        }
      }
    }

    ctx.setTargetingMode?.({ duelistFinisher: true, itemId: item.id, useSecondary: isSecondary });
    return true;
  }
}

export class RangedAttackDoubleClickHandler implements IToolbarDoubleClickHandler {
  public canHandle(item: ToolbarItem): boolean {
    return canAutoAim(item);
  }

  public handle(item: ToolbarItem, ctx: ToolbarDoubleClickContext): boolean {
    if (!isAttackReady()) return true;

    const myPlayer = ctx.entitiesRef.current.players?.[ctx.myPlayerIdRef.current];
    if (!myPlayer) return true;

    const myFaction = myPlayer.faction || 'player';
    const candidateTargets = buildCandidateTargets(ctx.entitiesRef, ctx.myPlayerIdRef.current, myFaction);

    // SPD QuickSlotButton.autoAim: prefer the remembered/locked target, else
    // the nearest visible mob in range.
    const pick = pickAutoAimTarget(
      ctx.selectedEnemyIdRef.current,
      candidateTargets,
      ctx.visionRef.current.visible,
      { x: myPlayer.renderPos?.x ?? 0, y: myPlayer.renderPos?.y ?? 0 },
      item.range,
      myFaction,
    );
    if (pick) {
      consumeAttackCooldown((item.attack_cooldown ?? 1.0) * 1000);
      ctx.send({ type: 'RANGED_ATTACK', item_id: item.id, target_x: pick.x, target_y: pick.y, target_entity_id: pick.id });
    }
    return true;
  }
}

export class ToolbarDoubleClickDispatcher {
  private handlers: IToolbarDoubleClickHandler[];

  constructor(handlers?: IToolbarDoubleClickHandler[]) {
    this.handlers = handlers ?? [
      new DuelistFinisherDoubleClickHandler(),
      new RangedAttackDoubleClickHandler(),
    ];
  }

  public register(handler: IToolbarDoubleClickHandler): void {
    this.handlers.push(handler);
  }

  public dispatch(item: ToolbarItem | null | undefined, ctx: ToolbarDoubleClickContext): boolean {
    if (!item) return false;
    for (const handler of this.handlers) {
      if (handler.canHandle(item, ctx) && handler.handle(item, ctx)) return true;
    }
    return false;
  }
}

export const defaultToolbarDoubleClickDispatcher = new ToolbarDoubleClickDispatcher();