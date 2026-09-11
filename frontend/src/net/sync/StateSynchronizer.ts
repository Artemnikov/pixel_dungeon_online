import type { StateUpdateMessage } from '../../types/contract';
import type { IStateSynchronizer, StateSyncContext } from './IStateSynchronizer';
import { PlayersSynchronizer } from './PlayersSynchronizer';
import { SelfPlayerSynchronizer } from './SelfPlayerSynchronizer';
import { MobsSynchronizer } from './MobsSynchronizer';
import { ItemsSynchronizer } from './ItemsSynchronizer';
import { TrapsSynchronizer } from './TrapsSynchronizer';
import { PlantsSynchronizer } from './PlantsSynchronizer';
import { VisionSynchronizer } from './VisionSynchronizer';
import { EnvironmentSynchronizer } from './EnvironmentSynchronizer';

export class StateSynchronizer {
  private synchronizers: IStateSynchronizer[];

  constructor(synchronizers?: IStateSynchronizer[]) {
    this.synchronizers = synchronizers ?? [
      new SelfPlayerSynchronizer(),
      new PlayersSynchronizer(),
      new MobsSynchronizer(),
      new ItemsSynchronizer(),
      new TrapsSynchronizer(),
      new PlantsSynchronizer(),
      new VisionSynchronizer(),
      new EnvironmentSynchronizer(),
    ];
  }

  public sync(data: StateUpdateMessage, ctx: StateSyncContext): void {
    for (const sync of this.synchronizers) {
      sync.sync(data, ctx);
    }
  }
}

export const defaultStateSynchronizer = new StateSynchronizer();
