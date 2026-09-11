import type {
  RenderPlayer,
  EntitiesState,
  MoveResult,
} from '../types';
import { MOVE_DURATION } from '../../constants.js';
import { BlockerResolver } from './BlockerResolver';
import { resetAttackCooldown } from '../events/combat';

export interface UnconfirmedStep {
  seq: number;
  dx: number;
  dy: number;
  targetX: number;
  targetY: number;
  timestamp: number;
}

const BLOCKING_DEBUFFS = new Set(['paralysis', 'frozen', 'stagger', 'roots', 'daze']);
const PENDING_TIMEOUT_MS = MOVE_DURATION * 2.5;
const SMOOTH_GLIDE_MAX_TILES = 3;
// In-flight step buffer. Was 2: on a live WAN the step ack cadence lags the
// local animation cadence (RTT + 40Hz state-frame batching), so the buffer
// would fill and paceStep() would return 'busy' -- freezing the walk for a
// beat every few steps. 3 absorbs that jitter; the server queues up to 8 and
// steps are still blocked locally by walls/mobs, so it can't walk off-grid.
const MAX_IN_FLIGHT_STEPS = 3;

function chebyshevDist(ax: number, ay: number, bx: number, by: number): number {
  return Math.max(Math.abs(ax - bx), Math.abs(ay - by));
}

export class MovementPredictor {
  private seqCounter = 0;
  private unconfirmedSteps: UnconfirmedStep[] = [];
  private confirmedPos: { x: number; y: number } | null = null;
  private predictedPos: { x: number; y: number } | null = null;
  private pendingMove = false;
  private lastStepTime = 0;
  private pendingPathSteps: Array<{ dx: number; dy: number }> = [];
  private blockerResolver: BlockerResolver;

  constructor(blockerResolver: BlockerResolver = new BlockerResolver()) {
    this.blockerResolver = blockerResolver;
  }

  public getBlockerResolver(): BlockerResolver {
    return this.blockerResolver;
  }

  public canPredict(player: RenderPlayer): boolean {
    if (player.buffs?.some(b => BLOCKING_DEBUFFS.has(b.type))) return false;
    if (player.is_downed) return false;
    return true;
  }

  public getStepDuration(player?: RenderPlayer | null): number {
    return player?.step_duration_ms ?? player?.moveDuration ?? MOVE_DURATION;
  }

  public isAnimComplete(player: RenderPlayer): boolean {
    const target = player.targetPos;
    if (!target) return true;
    if (Math.abs(player.renderPos.x - target.x) < 0.01
        && Math.abs(player.renderPos.y - target.y) < 0.01) return true;
    if (player.animStartTime == null) return false;
    const dur = player.moveDuration || this.getStepDuration(player);
    return performance.now() - player.animStartTime >= dur;
  }

  public retarget(player: RenderPlayer, tx: number, ty: number, updateFacing: boolean): void {
    const dist = chebyshevDist(tx, ty, player.renderPos.x, player.renderPos.y);
    player.targetPos = { x: tx, y: ty };
    if (dist <= 0.01) {
      player.animStartPos = { x: tx, y: ty };
      player.animStartTime = null;
      return;
    }
    player.animStartPos = { x: player.renderPos.x, y: player.renderPos.y };
    player.animStartTime = performance.now();
    const baseDuration = this.getStepDuration(player);
    player.moveDuration = dist <= SMOOTH_GLIDE_MAX_TILES
      ? Math.max(baseDuration, Math.round(dist * baseDuration))
      : baseDuration;
    if (!updateFacing) return;
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

  public isPending(): boolean {
    return this.pendingMove || this.unconfirmedSteps.length > 0;
  }

  public getLastSentSeq(): number {
    return this.seqCounter;
  }

  public getNextSeq(): number {
    return this.seqCounter + 1;
  }

  public getUnconfirmedSteps(): UnconfirmedStep[] {
    return this.unconfirmedSteps;
  }

  public redirectMove(
    player: RenderPlayer,
    dx: number,
    dy: number,
    playerId: string,
    grid: number[][],
    entities: EntitiesState,
  ): MoveResult & { seq?: number; replacedSeq?: number } {
    if (!this.pendingMove || !this.canPredict(player)) return { kind: 'busy' };
    const now = performance.now();
    const dur = this.getStepDuration(player);
    if (now - this.lastStepTime > dur * 0.5) return { kind: 'busy' };

    const startTile = this.unconfirmedSteps.length > 1
      ? { x: this.unconfirmedSteps[this.unconfirmedSteps.length - 2].targetX, y: this.unconfirmedSteps[this.unconfirmedSteps.length - 2].targetY }
      : this.confirmedPos || {
        x: Math.round(player.animStartPos?.x ?? player.renderPos.x),
        y: Math.round(player.animStartPos?.y ?? player.renderPos.y),
      };

    const newX = startTile.x + dx;
    const newY = startTile.y + dy;

    const bumped = this.blockerResolver.bumpedOrNull(player, newX, newY, playerId, grid, entities);
    if (bumped) {
      this.lastStepTime = now;
      const seq = ++this.seqCounter;
      return { ...bumped, seq };
    }

    const replacedSeq = this.unconfirmedSteps.length > 0
      ? this.unconfirmedSteps[this.unconfirmedSteps.length - 1].seq
      : undefined;

    const seq = ++this.seqCounter;
    this.predictedPos = { x: newX, y: newY };
    const step: UnconfirmedStep = { seq, dx, dy, targetX: newX, targetY: newY, timestamp: now };
    if (this.unconfirmedSteps.length > 0) {
      this.unconfirmedSteps[this.unconfirmedSteps.length - 1] = step;
    } else {
      this.unconfirmedSteps = [step];
    }
    this.lastStepTime = now;

    this.retarget(player, newX, newY, true);
    return { kind: 'moved', seq, replacedSeq };
  }

  public predictMove(
    player: RenderPlayer,
    dx: number,
    dy: number,
    playerId: string,
    grid: number[][],
    entities: EntitiesState,
  ): MoveResult & { seq?: number; replacedSeq?: number } {
    if (this.pendingMove) {
      return this.redirectMove(player, dx, dy, playerId, grid, entities);
    }
    if (!this.canPredict(player)) return { kind: 'busy' };

    const from = player.targetPos || player.renderPos;
    const newX = Math.round(from.x) + dx;
    const newY = Math.round(from.y) + dy;

    const bumped = this.blockerResolver.bumpedOrNull(player, newX, newY, playerId, grid, entities);
    if (bumped) {
      this.lastStepTime = performance.now();
      const seq = ++this.seqCounter;
      return { ...bumped, seq };
    }

    if (!this.isAnimComplete(player)) return { kind: 'busy' };

    const seq = ++this.seqCounter;
    this.predictedPos = { x: newX, y: newY };
    this.pendingMove = true;
    this.lastStepTime = performance.now();
    this.unconfirmedSteps.push({ seq, dx, dy, targetX: newX, targetY: newY, timestamp: this.lastStepTime });
    if (this.unconfirmedSteps.length > MAX_IN_FLIGHT_STEPS) this.unconfirmedSteps.shift();

    this.retarget(player, newX, newY, true);

    return { kind: 'moved', seq };
  }

  public paceStep(
    player: RenderPlayer,
    dx: number,
    dy: number,
    playerId: string,
    grid: number[][],
    entities: EntitiesState,
  ): MoveResult & { seq?: number } {
    if (this.unconfirmedSteps.length >= MAX_IN_FLIGHT_STEPS) return { kind: 'busy' };

    const from = player.targetPos || player.renderPos;
    const nx = Math.round(from.x) + dx;
    const ny = Math.round(from.y) + dy;
    const bumped = this.blockerResolver.bumpedOrNull(player, nx, ny, playerId, grid, entities);
    if (bumped) {
      const now = performance.now();
      const dur = this.getStepDuration(player);
      if (this.lastStepTime !== 0 && now - this.lastStepTime < dur) return { kind: 'busy' };
      this.lastStepTime = now;
      const seq = ++this.seqCounter;
      return { ...bumped, seq };
    }

    const now = performance.now();
    const dur = this.getStepDuration(player);
    if (now - this.lastStepTime < dur) return { kind: 'busy' };
    if (!this.isAnimComplete(player)) return { kind: 'busy' };

    if (this.pendingMove) {
      this.pendingMove = false;
      this.predictedPos = null;
    }
    return this.predictMove(player, dx, dy, playerId, grid, entities);
  }

  public startPath(
    player: RenderPlayer,
    steps: Array<{ dx: number; dy: number }>,
    playerId: string,
    grid: number[][],
    entities: EntitiesState,
  ): MoveResult & { seq?: number } {
    if (steps.length === 0) return { kind: 'busy' };
    const first = steps[0];
    const moved = this.predictMove(player, first.dx, first.dy, playerId, grid, entities);
    if (moved.kind === 'moved') {
      this.pendingPathSteps = steps.slice(1);
    }
    return moved;
  }

  public pacePathStep(
    player: RenderPlayer,
    playerId: string,
    grid: number[][],
    entities: EntitiesState,
  ): MoveResult & { seq?: number } {
    if (this.pendingPathSteps.length === 0) return { kind: 'busy' };
    const now = performance.now();
    const next = this.pendingPathSteps[0];

    const from = player.targetPos || player.renderPos;
    const nx = Math.round(from.x) + next.dx;
    const ny = Math.round(from.y) + next.dy;
    const bumped = this.blockerResolver.bumpedOrNull(player, nx, ny, playerId, grid, entities);
    if (bumped) return bumped;

    const dur = this.getStepDuration(player);
    if (now - this.lastStepTime < dur) return { kind: 'busy' };
    if (this.pendingMove) {
      if (!this.isAnimComplete(player)) return { kind: 'busy' };
      this.pendingMove = false;
      this.predictedPos = null;
    }
    this.pendingPathSteps.shift();
    return this.predictMove(player, next.dx, next.dy, playerId, grid, entities);
  }

  public onMoveResult(
    data: { entity: string; seq?: number; x: number; y: number; ok: boolean },
    player: RenderPlayer | null,
  ): void {
    if (!player) return;
    const rx = Math.round(data.x);
    const ry = Math.round(data.y);

    if (data.ok) {
      this.confirmedPos = { x: rx, y: ry };
      if (data.seq !== undefined) {
        const ackIdx = this.unconfirmedSteps.findIndex(s => s.seq === data.seq);
        if (ackIdx >= 0) {
          this.unconfirmedSteps.splice(0, ackIdx + 1);
        }
      } else {
        const caughtIdx = this.unconfirmedSteps.findIndex(s => s.targetX === rx && s.targetY === ry);
        if (caughtIdx >= 0) {
          this.unconfirmedSteps.splice(0, caughtIdx + 1);
        }
      }
      if (this.unconfirmedSteps.length === 0) {
        this.predictedPos = null;
        this.pendingMove = false;
      } else {
        const latest = this.unconfirmedSteps[this.unconfirmedSteps.length - 1];
        this.predictedPos = { x: latest.targetX, y: latest.targetY };
      }
      return;
    }

    this.confirmedPos = { x: rx, y: ry };
    if (data.seq !== undefined) {
      // A specific seq'd step was rejected by the server. Drop only that step
      // (and anything before it) instead of wiping the whole in-flight buffer:
      // surviving steps are re-anchored to the authoritative server position by
      // re-accumulating their stored deltas, so one blocked step no longer yanks
      // the player all the way back ("teleport-back").
      const failedIdx = this.unconfirmedSteps.findIndex(s => s.seq === data.seq);
      if (failedIdx >= 0) {
        this.unconfirmedSteps = this.unconfirmedSteps.slice(failedIdx + 1);
      }
      this.rejectAndReanchor(player, rx, ry);
      return;
    }

    if (this.unconfirmedSteps.length > 0) {
      // A no-seq rejection (path/auto-move step blocked server-side) must not
      // wipe a live keyboard walk. Re-anchor the surviving steps to the
      // authoritative position and continue; a full reset here is what used to
      // yank the hero back a tile mid-walk ("spring-back").
      this.rejectAndReanchor(player, rx, ry);
      return;
    }

    this.predictedPos = null;
    this.pendingMove = false;
    this.pendingPathSteps = [];
    this.unconfirmedSteps = [];
    this.lastStepTime = performance.now();
    this.retarget(player, rx, ry, false);
  }

  /**
   * Shared tail for a rejected step: re-anchor the surviving unconfirmed steps
   * to the authoritative server position, refresh the chain's predicted head,
   * and glide the hero back to the server tile (no hard snap).
   */
  private rejectAndReanchor(player: RenderPlayer, rx: number, ry: number): void {
    this.reanchorTo(rx, ry);
    if (this.unconfirmedSteps.length === 0) {
      this.predictedPos = null;
      this.pendingMove = false;
    } else {
      const latest = this.unconfirmedSteps[this.unconfirmedSteps.length - 1];
      this.predictedPos = { x: latest.targetX, y: latest.targetY };
      this.pendingMove = true;
    }
    this.pendingPathSteps = [];
    this.lastStepTime = performance.now();
    this.retarget(player, rx, ry, false);
  }

  /**
   * Shift every surviving unconfirmed step so its target is recomputed from a
   * given anchor position (used after a rejected step: the server never moved,
   * so every later prediction is one step too far along).
   */
  private reanchorTo(anchorX: number, anchorY: number): void {
    let x = anchorX;
    let y = anchorY;
    for (const step of this.unconfirmedSteps) {
      x += step.dx;
      y += step.dy;
      step.targetX = x;
      step.targetY = y;
    }
  }

  public reconcile(
    serverPosition: { x: number; y: number },
    player: RenderPlayer,
    lastProcessedSeq?: number,
  ): void {
    const sx = Math.round(serverPosition.x);
    const sy = Math.round(serverPosition.y);

    if (lastProcessedSeq !== undefined && lastProcessedSeq > 0) {
      this.unconfirmedSteps = this.unconfirmedSteps.filter(s => s.seq > lastProcessedSeq);
      if (this.unconfirmedSteps.length === 0) {
        this.predictedPos = null;
        this.pendingMove = false;
      } else {
        const latest = this.unconfirmedSteps[this.unconfirmedSteps.length - 1];
        this.predictedPos = { x: latest.targetX, y: latest.targetY };
      }
    }

    if (!this.pendingMove && this.unconfirmedSteps.length === 0) {
      this.confirmedPos = { x: sx, y: sy };
      if (this.isAnimComplete(player) && player.targetPos && (player.targetPos.x !== sx || player.targetPos.y !== sy)) {
        this.retarget(player, sx, sy, false);
      }
      return;
    }

    if (this.predictedPos && sx === this.predictedPos.x && sy === this.predictedPos.y) {
      this.confirmedPos = { x: sx, y: sy };
      this.predictedPos = null;
      this.pendingMove = false;
      this.unconfirmedSteps = [];
      return;
    }

    const caughtUpIdx = this.unconfirmedSteps.findIndex(s => s.targetX === sx && s.targetY === sy);
    if (caughtUpIdx >= 0) {
      this.confirmedPos = { x: sx, y: sy };
      this.unconfirmedSteps = this.unconfirmedSteps.slice(caughtUpIdx + 1);
      if (this.unconfirmedSteps.length === 0) {
        this.predictedPos = null;
        this.pendingMove = false;
      } else {
        const latest = this.unconfirmedSteps[this.unconfirmedSteps.length - 1];
        this.predictedPos = { x: latest.targetX, y: latest.targetY };
      }
      return;
    }

    // Spring-back guard: while a prediction chain is live, a server position
    // within one tile of the last confirmed tile means the server is simply
    // trailing the walk (RTT + frame batching), not diverging from it. Adopt
    // it as the confirmed anchor and keep walking. Without this, the idle
    // check below misses (confirmedPos near but not equal to serverPos) and
    // the hard reset would retarget the hero back a tile -- the "spring-back".
    //
    // Deliberately NOT re-anchoring the surviving steps here: in the normal
    // trailing-server case the chain targets remain valid (the server will step
    // through them), and shrinking them would stall the walk one step per fold.
    // Side effect accepted: a genuine 1-tile divergence (e.g. a 1-tile knockback
    // that didn't consume a client seq) is also folded and the walk continues;
    // the residual chain then self-corrects when the step acks land, which beats
    // a visible snap-back for a rare, small displacement.
    if (
      this.unconfirmedSteps.length > 0 &&
      this.confirmedPos !== null &&
      Math.max(Math.abs(sx - this.confirmedPos.x), Math.abs(sy - this.confirmedPos.y)) <= 1
    ) {
      this.confirmedPos = { x: sx, y: sy };
      return;
    }

    const idleAtConfirmed = this.confirmedPos !== null && sx === this.confirmedPos.x && sy === this.confirmedPos.y;
    if (idleAtConfirmed && performance.now() - this.lastStepTime < PENDING_TIMEOUT_MS) {
      return;
    }

    this.confirmedPos = { x: sx, y: sy };
    this.predictedPos = null;
    this.pendingMove = false;
    this.pendingPathSteps = [];
    this.unconfirmedSteps = [];
    this.lastStepTime = performance.now();
    this.retarget(player, sx, sy, true);
  }

  public clear(): void {
    // Full reset including seqCounter — only used when the entire predictor
    // should be abandoned (e.g. game over, disconnect). Floor transitions use
    // clearInFlight() instead to preserve monotonic sequence numbers across
    // floors so the backend accepts MOVE_STEP packets on the new floor.
    this.seqCounter = 0;
    this.predictedPos = null;
    this.pendingMove = false;
    this.pendingPathSteps = [];
    this.lastStepTime = 0;
    this.confirmedPos = null;
    this.unconfirmedSteps = [];
    resetAttackCooldown();
  }

  /**
   * Clear in-flight movement state (pending steps, predictions, path queue)
   * without resetting the sequence counter. Used on floor transitions so that
   * MOVE_STEP packets sent from the new floor continue to be accepted by the
   * backend's PlayerMovementController, which retains last_processed_seq across
   * floors and rejects any seq <= last_processed_seq as stale/duplicate.
   */
  public clearInFlight(): void {
    this.predictedPos = null;
    this.pendingMove = false;
    this.pendingPathSteps = [];
    this.lastStepTime = 0;
    this.confirmedPos = null;
    this.unconfirmedSteps = [];
    resetAttackCooldown();
    // seqCounter is intentionally NOT reset — must remain monotonically increasing
    // so the backend accepts every new MOVE_STEP on the next floor.
  }
}
