import type { StateUpdateMessage } from '../../types/contract';
import type { IStateSynchronizer, StateSyncContext } from './IStateSynchronizer';

export class TurnSynchronizer implements IStateSynchronizer {
  public sync(data: StateUpdateMessage, ctx: StateSyncContext): void {
    // Cleared, not skipped when absent: a real-time frame has no `turn` key at
    // all, so leaving the last value in place would strand a stale "your turn"
    // badge on a client that switched rooms.
    ctx.turnState.syncTurnState(data.turn);
  }
}
