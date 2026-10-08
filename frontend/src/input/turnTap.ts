import type { Ref } from '../net/types';
import type { GameMode } from '../types/contract';

/** The shape `resolveTapAction` returns, narrowed to what a tap can send. */
export interface TapAction {
  type: string;
  direction?: string;
  steps?: number[][];
}

/**
 * Whether the room runs on the turn scheduler rather than the 40Hz loop.
 */
export function isTurnRoom(gameModeRef?: Ref<GameMode> | null): boolean {
  return gameModeRef?.current === 'turnbased';
}

/**
 * Sends one canvas tap in a turn-based room, where one tap is one turn.
 *
 * A turn room reads no continuous input, so the paced, seq-acked movement
 * plumbing a real-time tap relies on is dropped by its dispatcher: an adjacent
 * tap has to go out as a plain `MOVE`, and it is the server's bump into the
 * occupied tile that resolves as the attack. `WAIT` and `NPC_INTERACT` are
 * single messages a turn room understands, so they pass through unchanged.
 *
 * A far tap sends the BFS path from `resolveTapAction`, which the server keeps
 * and drains one tile per turn -- a second click retargets it, and any other
 * action cancels it. An empty path is not a turn: the click found no route, so
 * nothing is spent.
 */
export function sendTurnRoomTap(socket: WebSocket, action: TapAction): void {
  if (action.type === 'MOVE' && action.direction) {
    socket.send(JSON.stringify({ type: 'MOVE', direction: action.direction }));
    return;
  }
  if (action.type === 'WAIT' || action.type === 'NPC_INTERACT') {
    socket.send(JSON.stringify(action));
    return;
  }
  if (action.type === 'PATH_STEPS' && action.steps && action.steps.length > 0) {
    socket.send(JSON.stringify({ type: 'PATH_STEPS', steps: action.steps }));
  }
}
