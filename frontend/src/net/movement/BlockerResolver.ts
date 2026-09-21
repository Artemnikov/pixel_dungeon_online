import type {
  RenderPlayer,
  RenderMob,
  RenderTrap,
  EntitiesState,
  SerializedItem,
  BlockingEntity,
  MoveResult,
  BumpAction,
} from '../types';
import { getTileDescriptor } from '../../constants.js';

const BUMP_PRECEDENCE: Record<BumpAction, number> = {
  'melee-attack': 8,
  'npc-interact': 7,
  'open-chest': 6,
  'unlock-door': 5,
  'open-alchemy': 4,
  'chasm-jump': 3,
  'face-only': 2,
  'none': 1,
};

const BUMP_BLOCKER_KINDS = new Set([
  'wall',
  'door',
  'chasm',
  'alchemy-table',
  'chest',
  'mob',
  'merchant',
  'quest-npc',
  'player',
  'ally',
]);

const MERCHANT_NAMES = new Set(['Shopkeeper']);

export interface EvaluationContext {
  actorId: string;
  actorFaction: string;
}

export interface IEntityBlockerEvaluator<T> {
  evaluate(target: T, context: EvaluationContext): BlockingEntity | null;
}

export class TileBlockerEvaluator implements IEntityBlockerEvaluator<number | undefined> {
  public evaluate(tile: number | undefined): BlockingEntity | null {
    return getTileDescriptor(tile).onInteract(tile);
  }
}

export class TrapBlockerEvaluator implements IEntityBlockerEvaluator<RenderTrap> {
  public evaluate(trap: RenderTrap): BlockingEntity | null {
    return { kind: 'trap', trapType: trap.trap_type, action: 'none' };
  }
}

export class ItemBlockerEvaluator implements IEntityBlockerEvaluator<SerializedItem & { type?: string; chest_type?: string; opened?: boolean }> {
  public evaluate(
    item: SerializedItem & { type?: string; chest_type?: string; opened?: boolean },
  ): BlockingEntity {
    if (item.type === 'chest') {
      return {
        kind: 'chest',
        id: item.id,
        chestType: item.chest_type,
        opened: item.opened,
        action: 'open-chest',
      };
    }
    return { kind: 'item', id: item.id, action: 'none' };
  }
}

export class PlayerBlockerEvaluator implements IEntityBlockerEvaluator<RenderPlayer> {
  public evaluate(player: RenderPlayer, context: EvaluationContext): BlockingEntity | null {
    if (player.id === context.actorId || player.is_downed || player.is_alive === false) {
      return null;
    }

    const targetFaction = player.faction || 'player';
    const isHostile = targetFaction !== context.actorFaction;

    return {
      kind: 'player',
      id: player.id,
      action: isHostile ? 'melee-attack' : 'face-only',
    };
  }
}

function resolveFactionMobBlocker(
  mob: RenderMob,
  defaultFaction: string,
  context: EvaluationContext,
): BlockingEntity {
  const mobFaction = mob.faction || defaultFaction;
  const isFriendly = mobFaction === context.actorFaction;
  return isFriendly
    ? { kind: 'ally', id: mob.id, name: mob.name, action: 'face-only' }
    : { kind: 'mob', id: mob.id, name: mob.name, action: 'melee-attack' };
}

export interface IMobTypeHandler {
  canHandle(mob: RenderMob, context: EvaluationContext): boolean;
  handle(mob: RenderMob, context: EvaluationContext): BlockingEntity | null;
}

export class OwnedCloneMobHandler implements IMobTypeHandler {
  public canHandle(mob: RenderMob, context: EvaluationContext): boolean {
    return (
      (mob.type === 'ghost_hero' || mob.type === 'mirror_image') &&
      mob.owner_id === context.actorId
    );
  }

  public handle(_mob: RenderMob, _context: EvaluationContext): BlockingEntity | null {
    return null;
  }
}

export class SummonAllyMobHandler implements IMobTypeHandler {
  public canHandle(mob: RenderMob): boolean {
    return mob.type === 'ghost_hero' || mob.type === 'mirror_image';
  }

  public handle(mob: RenderMob, context: EvaluationContext): BlockingEntity | null {
    return resolveFactionMobBlocker(mob, 'player', context);
  }
}

export class MerchantNpcMobHandler implements IMobTypeHandler {
  private merchantNames: Set<string>;

  constructor(merchantNames: Set<string> = MERCHANT_NAMES) {
    this.merchantNames = merchantNames;
  }

  public canHandle(mob: RenderMob): boolean {
    return mob.type === 'npc' && Boolean(mob.name && this.merchantNames.has(mob.name));
  }

  public handle(mob: RenderMob): BlockingEntity | null {
    return { kind: 'merchant', id: mob.id, name: mob.name, action: 'npc-interact' };
  }
}

export class QuestNpcMobHandler implements IMobTypeHandler {
  public canHandle(mob: RenderMob): boolean {
    return mob.type === 'npc';
  }

  public handle(mob: RenderMob): BlockingEntity | null {
    return { kind: 'quest-npc', id: mob.id, name: mob.name, action: 'npc-interact' };
  }
}

export class DungeonFactionMobHandler implements IMobTypeHandler {
  public canHandle(mob: RenderMob, context: EvaluationContext): boolean {
    const mobFaction = mob.faction || 'dungeon';
    return context.actorFaction === 'dungeon' && mobFaction === 'dungeon';
  }

  public handle(mob: RenderMob): BlockingEntity | null {
    const isImmovable =
      mob.properties?.includes('IMMOVABLE') ||
      mob.type === 'spawner' ||
      mob.type === 'sentry';
    if (isImmovable) {
      return { kind: 'ally', id: mob.id, name: mob.name, action: 'face-only' };
    }
    return null;
  }
}

export class DefaultCombatMobHandler implements IMobTypeHandler {
  public canHandle(_mob: RenderMob): boolean {
    return true;
  }

  public handle(mob: RenderMob, context: EvaluationContext): BlockingEntity | null {
    return resolveFactionMobBlocker(mob, 'dungeon', context);
  }
}

export class MobBlockerEvaluator implements IEntityBlockerEvaluator<RenderMob> {
  private handlers: IMobTypeHandler[];

  constructor(handlers?: IMobTypeHandler[]) {
    this.handlers = handlers ?? [
      new OwnedCloneMobHandler(),
      new SummonAllyMobHandler(),
      new MerchantNpcMobHandler(),
      new QuestNpcMobHandler(),
      new DungeonFactionMobHandler(),
      new DefaultCombatMobHandler(),
    ];
  }

  public evaluate(mob: RenderMob, context: EvaluationContext): BlockingEntity | null {
    if (mob.is_alive === false) return null;
    for (const handler of this.handlers) {
      if (handler.canHandle(mob, context)) {
        return handler.handle(mob, context);
      }
    }
    return null;
  }
}

export class BlockerResolver {
  private tileEvaluator: TileBlockerEvaluator;
  private trapEvaluator: TrapBlockerEvaluator;
  private itemEvaluator: ItemBlockerEvaluator;
  private playerEvaluator: PlayerBlockerEvaluator;
  private mobEvaluator: MobBlockerEvaluator;

  constructor(
    tileEvaluator: TileBlockerEvaluator = new TileBlockerEvaluator(),
    trapEvaluator: TrapBlockerEvaluator = new TrapBlockerEvaluator(),
    itemEvaluator: ItemBlockerEvaluator = new ItemBlockerEvaluator(),
    playerEvaluator: PlayerBlockerEvaluator = new PlayerBlockerEvaluator(),
    mobEvaluator: MobBlockerEvaluator = new MobBlockerEvaluator(),
  ) {
    this.tileEvaluator = tileEvaluator;
    this.trapEvaluator = trapEvaluator;
    this.itemEvaluator = itemEvaluator;
    this.playerEvaluator = playerEvaluator;
    this.mobEvaluator = mobEvaluator;
  }

  public primaryBlocker(blockers: BlockingEntity[]): BlockingEntity | null {
    let best: BlockingEntity | null = null;
    for (const b of blockers) {
      if (!best || BUMP_PRECEDENCE[b.action] > BUMP_PRECEDENCE[best.action]) best = b;
    }
    return best;
  }

  public isBump(blockers: BlockingEntity[]): boolean {
    return blockers.some(b => BUMP_BLOCKER_KINDS.has(b.kind));
  }

  public faceLiving(player: RenderPlayer, tx: number, ty: number, blockers: BlockingEntity[]): void {
    const primary = this.primaryBlocker(blockers);
    if (!primary || primary.action === 'none') return;
    const dx = tx - Math.round(player.renderPos.x);
    const dy = ty - Math.round(player.renderPos.y);
    if (Math.abs(dx) >= Math.abs(dy)) {
      if (dx > 0) { player.facing = 'RIGHT'; player.flipX = false; }
      else if (dx < 0) { player.facing = 'LEFT'; player.flipX = true; }
    } else {
      if (dy > 0) player.facing = 'DOWN';
      else if (dy < 0) player.facing = 'UP';
    }
  }

  public bumpedOrNull(
    player: RenderPlayer,
    newX: number,
    newY: number,
    playerId: string,
    grid: number[][],
    entities: EntitiesState,
  ): MoveResult | null {
    const blockers: BlockingEntity[] = [];
    const context: EvaluationContext = {
      actorId: playerId,
      actorFaction: player.faction || 'player',
    };

    const row = grid[newY];
    const tile = row?.[newX];
    const tileB = this.tileEvaluator.evaluate(tile);
    if (tileB) blockers.push(tileB);

    const trap = entities.traps?.find(t => t.x === newX && t.y === newY);
    if (trap) {
      const trapB = this.trapEvaluator.evaluate(trap);
      if (trapB) blockers.push(trapB);
    }

    for (const it of entities.items || []) {
      const p = it.pos;
      if (p && Math.round(p.x) === newX && Math.round(p.y) === newY) {
        blockers.push(this.itemEvaluator.evaluate(it));
      }
    }

    for (const m of Object.values(entities.mobs)) {
      const mx = m.targetPos?.x ?? m.pos.x;
      const my = m.targetPos?.y ?? m.pos.y;
      if (Math.round(mx) === newX && Math.round(my) === newY) {
        const b = this.mobEvaluator.evaluate(m, context);
        if (b) blockers.push(b);
      }
    }

    for (const p of Object.values(entities.players)) {
      const px = p.targetPos?.x ?? p.pos.x;
      const py = p.targetPos?.y ?? p.pos.y;
      if (Math.round(px) === newX && Math.round(py) === newY) {
        const b = this.playerEvaluator.evaluate(p, context);
        if (b) blockers.push(b);
      }
    }

    if (!this.isBump(blockers)) return null;
    this.faceLiving(player, newX, newY, blockers);
    return { kind: 'bumped', x: newX, y: newY, blockers };
  }
}
