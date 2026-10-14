import type { IKeyCommand, InputContext } from '../IKeyCommand';
import type { MoveResult } from '../../../net/types';
import { DIRECTION_KEYS, getVector, vectorToDirection } from '../../directionUtils';
import * as movementPredictor from '../../../net/movementPredictor';
import { defaultMoveResultDispatcher } from '../../../net/movement/MoveResultDispatcher';
import { startLocalPlayerMeleeAnim } from '../../../net/events/combat';
import AudioManager from '../../../audio/AudioManager';

export const DEFAULT_CHORD_DELAY_MS = 35;

export class DirectionalMoveCommand implements IKeyCommand {
  private pressedKeys: Set<string>;
  private lastSentVector: { dx: number; dy: number } = { dx: 0, dy: 0 };
  private lastTurnStepTime = 0;
  private onVectorChanged?: (hasHeldKeys: boolean) => void;
  private chordDelayMs: number;
  private chordTimer: ReturnType<typeof setTimeout> | null = null;
  private pendingChordVector: { dx: number; dy: number } | null = null;

  constructor(
    pressedKeys: Set<string>,
    onVectorChanged?: (hasHeldKeys: boolean) => void,
    chordDelayMs = 0,
  ) {
    this.pressedKeys = pressedKeys;
    this.onVectorChanged = onVectorChanged;
    this.chordDelayMs = chordDelayMs;
  }

  public canExecute(code: string, context: InputContext): boolean {
    if (!DIRECTION_KEYS.has(code)) return false;
    if (context.myPlayer?.is_downed || context.myPlayer?.is_alive === false) return false;
    // Turn rooms deliberately do NOT gate on canActRef here: direction keys
    // must always register so a chorded diagonal's second keydown and the
    // keyup that disarms the pump are seen. sendTurnMove/paceStep decide
    // whether a turn may actually be spent.
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
   * A turn-based room moves on a plain `MOVE`, charged by the scheduler.
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

    if (dx === 0 && dy === 0) {
      if (this.chordTimer !== null && this.pendingChordVector !== null) {
        const pending = this.pendingChordVector;
        this.clearChordTimer();
        this.commitMove(context, pending.dx, pending.dy, true);
      }
      this.clearChordTimer();
      this.commitMove(context, 0, 0, false);
      return;
    }

    if (dx !== 0 && dy !== 0) {
      this.clearChordTimer();
      this.commitMove(context, dx, dy, isKeyDown);
      return;
    }

    if (
      this.chordDelayMs > 0 &&
      isKeyDown &&
      this.lastSentVector.dx === 0 &&
      this.lastSentVector.dy === 0
    ) {
      this.pendingChordVector = { dx, dy };
      if (this.chordTimer === null) {
        this.chordTimer = setTimeout(() => {
          this.chordTimer = null;
          const pending = this.pendingChordVector;
          this.pendingChordVector = null;
          if (pending && (pending.dx !== 0 || pending.dy !== 0)) {
            this.commitMove(context, pending.dx, pending.dy, true);
          }
        }, this.chordDelayMs);
      }
      return;
    }

    this.clearChordTimer();
    this.commitMove(context, dx, dy, isKeyDown);
  }

  private clearChordTimer(): void {
    if (this.chordTimer !== null) {
      clearTimeout(this.chordTimer);
      this.chordTimer = null;
    }
    this.pendingChordVector = null;
  }

  public flushChord(context: InputContext): void {
    if (this.chordTimer !== null && this.pendingChordVector !== null) {
      const pending = this.pendingChordVector;
      this.clearChordTimer();
      this.commitMove(context, pending.dx, pending.dy, true);
    }
  }

  private commitMove(context: InputContext, dx: number, dy: number, isKeyDown: boolean): void {
    const socket = context.socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

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
      if (isKeyDown && context.canActRef?.current === true) {
        this.sendTurnMove(context, dx, dy);
        this.lastTurnStepTime = performance.now();
        context.canActRef.current = false;
      }
      this.onVectorChanged?.(true);
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
    if (this.chordTimer !== null) return;

    const { dx, dy } = getVector(this.pressedKeys);
    if (dx === 0 && dy === 0) return;

    if (this.isTurnMode(context)) {
      // Held-key continuation: the pump calls this every frame while a
      // direction is held. Spend a turn only once the server says we may act
      // again and the previous step's animation has had time to play.
      if (context.canActRef?.current !== true) return;
      const now = performance.now();
      if (now - this.lastTurnStepTime < movementPredictor.getStepDuration(context.myPlayer)) return;
      this.sendTurnMove(context, dx, dy);
      this.lastTurnStepTime = now;
      context.canActRef.current = false;
      return;
    }

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
    this.clearChordTimer();
    this.lastSentVector = { dx: 0, dy: 0 };
    this.lastTurnStepTime = 0;
  }
}
