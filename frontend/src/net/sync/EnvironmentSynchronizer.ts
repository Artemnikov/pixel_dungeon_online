import type { StateUpdateMessage } from '../../types/contract';
import type { IStateSynchronizer, StateSyncContext } from './IStateSynchronizer';

const YOG_DEPTH = 25;
const STAIRS_DOWN_TILE = 5;

/** Floor 25 before the win: the exit stairs only appear once Yog-Dzewa dies. */
export function hallsArenaPending(data: StateUpdateMessage, ctx: StateSyncContext): boolean {
  if (ctx.world.depth !== YOG_DEPTH) return false;
  const yogEngaged = (data.mobs || []).some(m => m.name === 'Yog-Dzewa' && m.is_alive !== false
    && (m as { fight_started?: boolean }).fight_started === true);
  if (yogEngaged) return false;
  return !ctx.world.getGrid().some(row => row.includes(STAIRS_DOWN_TILE));
}

export class EnvironmentSynchronizer implements IStateSynchronizer {
  public sync(data: StateUpdateMessage, ctx: StateSyncContext): void {
    if (typeof data.depth === 'number') {
      ctx.world.setDepth(data.depth);
    }
    if (typeof data.gold === 'number') {
      ctx.heroState.syncGold(data.gold);
    }
    if (typeof data.energy === 'number') {
      ctx.heroState.syncEnergy(data.energy);
    }

    ctx.world.updateOpenDoors(data.open_doors);
    ctx.heroState.syncBossInfo(data.mobs || []);
    ctx.heroState.syncBossLurking(data.mobs || [], hallsArenaPending(data, ctx));
  }
}
