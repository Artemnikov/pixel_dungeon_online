import type { IKeyCommand, InputContext } from '../IKeyCommand';
import type { MoveResult } from '../../../net/types';
import { DIRECTION_KEYS, getVector, vectorToDirection } from '../../directionUtils';
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

  public canExecute(code: string, context: InputContext): boolean {
    if (!DIRECTION_KEYS.has(code)) return false;
    if (context.myPlayer?.is_downed || context.myPlayer?.is_alive === false) return false;
    if (this.isTurnMode(context) && context.canActRef?.current === false) return false;
    return true;
  }

  private isTurnMode(context: InputContext): boolean {
    return context.gameModeRef?.current === 'turnbased';
  }

  public execute(_code: string, context: InputContext, isKeyDown: boolean): void {
    if (context.showItemBrowserRef?.current) return;
    this.syncMoveIntent(context, isKeyDown);
  }

  /**
   * A turn-based room moves one tile per key press, on a plain `MOVE`.
   *
   * The real-time path below is the wrong shape for it: `MOVE_INTENT`,
   * `MOVE_STEP` and `MOVE_STOP` are dropped by a turn room's dispatcher, and
   * client-side prediction would race the scheduler's own decision about when
   * the step is legal. The scheduler charges the move, so the position is just
   * whatever the next authoritative frame says.
   */
  private sendTurnMove(context: InputContext, dx: number, dy: number): void {
    const direction = vectorToDirection(dx, dy);
    if (!direction) return;
    if (context.isRefocusingRef) context.isRefocusingRef.current = true;
    if (context.isDraggingRef) context.isDraggingRef.current = false;
    if (context.isCameraDetachedRef) context.isCameraDetachedRef.current = false;
    if (context.panOffsetRef) context.panOffsetRef.current = { x: 0, y: 0 };
    context.socket?.send(JSON.stringify({ type: 'MOVE', direction }));
  }

  public syncMoveIntent(context: InputContext, isKeyDown = false): void {
    const socket = context.socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    const { dx, dy } = getVector(this.pressedKeys);
    const last = this.lastSentVector;
    if (dx === last.dx && dy === last.dy) return;

    this.lastSentVector = { dx, dy };

    if (dx === 0 && dy === 0) {
      if (!this.isTurnMode(context)) {
        const lastSeq = movementPredictor.getLastSentSeq();
        socket.send(JSON.stringify({ type: 'MOVE_STOP', last_seq: lastSeq }));
      }
      this.onVectorChanged?.(false);
      return;
    }

    if (this.isTurnMode(context)) {
      // Turn-based: one press, one tile, no pump. Never arm `onVectorChanged`,
      // which is what starts the per-frame `paceStep` auto-walk.
      if (isKeyDown) this.sendTurnMove(context, dx, dy);
      this.onVectorChanged?.(false);
      return;
    }

    if (context.isRefocusingRef) context.isRefocusingRef.current = true;
    if (context.isDraggingRef) context.isDraggingRef.current = false;
    if (context.isCameraDetachedRef) context.isCameraDetachedRef.current = false;
    if (context.panOffsetRef) context.panOffsetRef.current = { x: 0, y: 0 };

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

  public paceStep(context: InputContext): void {
    // Turn-based rooms never auto-walk: the pump is only armed by the
    // real-time branch above. Guarded anyway so a stray frame is a no-op.
    if (this.isTurnMode(context)) return;

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
