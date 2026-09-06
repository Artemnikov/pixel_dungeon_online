import type { IKeyCommand, InputContext } from '../IKeyCommand';
import type { MoveResult } from '../../../net/types';
import { DIRECTION_KEYS, getVector } from '../../directionUtils';
import * as movementPredictor from '../../../net/movementPredictor';
import { defaultMoveResultDispatcher } from '../../../net/movement/MoveResultDispatcher';
import { startLocalPlayerMeleeAnim } from '../../../net/events/combat';
import AudioManager from '../../../audio/AudioManager';

export class DirectionalMoveCommand implements IKeyCommand {
  private pressedKeys: Set<string>;
  private lastSentVector: { dx: number; dy: number } = { dx: 0, dy: 0 };
  private onVectorChanged?: (hasHeldKeys: boolean) => void;

  constructor(pressedKeys: Set<string>, onVectorChanged?: (hasHeldKeys: boolean) => void) {
    this.pressedKeys = pressedKeys;
    this.onVectorChanged = onVectorChanged;
  }

  public canExecute(code: string, _context: InputContext): boolean {
    return DIRECTION_KEYS.has(code);
  }

  public execute(_code: string, context: InputContext, isKeyDown: boolean): void {
    if (context.showItemBrowserRef?.current) return;
    this.syncMoveIntent(context, isKeyDown);
  }

  public syncMoveIntent(context: InputContext, isKeyDown = false): void {
    const socket = context.socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    const { dx, dy } = getVector(this.pressedKeys);
    const last = this.lastSentVector;
    if (dx === last.dx && dy === last.dy) return;

    this.lastSentVector = { dx, dy };

    if (dx === 0 && dy === 0) {
      const lastSeq = movementPredictor.getLastSentSeq();
      socket.send(JSON.stringify({ type: 'MOVE_STOP', last_seq: lastSeq }));
      this.onVectorChanged?.(false);
    } else {
      if (context.isRefocusingRef) context.isRefocusingRef.current = true;
      if (context.isDraggingRef) context.isDraggingRef.current = false;

      const me = context.myPlayer;
      if (me && (isKeyDown || !movementPredictor.isPending())) {
        const moveRes = movementPredictor.predictMove(
          me,
          dx,
          dy,
          context.myPlayerId,
          context.grid,
          context.entities,
        );
        this.dispatchStep(context, moveRes, dx, dy);
      }
      this.onVectorChanged?.(true);
    }
  }

  public paceStep(context: InputContext): void {
    const { dx, dy } = getVector(this.pressedKeys);
    if (dx === 0 && dy === 0) return;

    const me = context.myPlayer;
    if (!me) return;

    const moveRes = movementPredictor.paceStep(
      me,
      dx,
      dy,
      context.myPlayerId,
      context.grid,
      context.entities,
    );

    this.dispatchStep(context, moveRes, dx, dy);
  }

  private dispatchStep(
    context: InputContext,
    moveRes: MoveResult & { seq?: number; replacedSeq?: number },
    dx: number,
    dy: number,
  ): void {
    defaultMoveResultDispatcher.dispatch(moveRes, {
      myPlayer: context.myPlayer,
      playerAnimRef: context.playerAnimRef,
      onOpenAlchemyRef: context.onOpenAlchemyRef,
      onMeleeAttack: () => startLocalPlayerMeleeAnim(context.myPlayer, context.playerAnimRef, AudioManager),
      socket: context.socket,
      dx,
      dy,
    });
  }

  public reset(): void {
    this.lastSentVector = { dx: 0, dy: 0 };
  }
}
