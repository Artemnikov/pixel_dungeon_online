import type { AnimState, RenderPlayer } from '../../net/types';
import {
  MOVE_DURATION,
  PLAYER_ATTACK_DURATION,
  PLAYER_OPERATE_DURATION,
  PLAYER_READ_DURATION,
} from '../../constants';

export interface AnimationContext {
  player: RenderPlayer;
  anim: AnimState;
  now: number;
  deathElapsed: number;
}

export interface IHeroAnimationState {
  readonly name: string;
  matches(ctx: AnimationContext): boolean;
  getFrameIndex(ctx: AnimationContext): number;
}

export class DownedAnimationState implements IHeroAnimationState {
  public readonly name = 'downed';
  private static readonly DIE_FRAMES = [8, 9, 10, 11, 12, 11];

  public matches(ctx: AnimationContext): boolean {
    return Boolean(ctx.player.is_downed);
  }

  public getFrameIndex(ctx: AnimationContext): number {
    const fi = Math.max(
      0,
      Math.min(
        Math.floor(ctx.deathElapsed / 50),
        DownedAnimationState.DIE_FRAMES.length - 1,
      ),
    );
    return DownedAnimationState.DIE_FRAMES[fi];
  }
}

export class AttackAnimationState implements IHeroAnimationState {
  public readonly name = 'attack';
  private static readonly ATTACK_FRAMES = [13, 14, 15, 0];

  public matches(ctx: AnimationContext): boolean {
    return !ctx.player.is_downed && Boolean(ctx.anim.attackUntil && ctx.now < ctx.anim.attackUntil);
  }

  public getFrameIndex(ctx: AnimationContext): number {
    const attackUntil = ctx.anim.attackUntil ?? ctx.now;
    const elapsed = ctx.now - (attackUntil - PLAYER_ATTACK_DURATION);
    const fi = Math.max(
      0,
      Math.min(
        Math.floor(elapsed / (PLAYER_ATTACK_DURATION / AttackAnimationState.ATTACK_FRAMES.length)),
        AttackAnimationState.ATTACK_FRAMES.length - 1,
      ),
    );
    return AttackAnimationState.ATTACK_FRAMES[fi];
  }
}

export class OperateAnimationState implements IHeroAnimationState {
  public readonly name = 'operate';
  private static readonly OPERATE_FRAMES = [16, 17, 16, 17];

  public matches(ctx: AnimationContext): boolean {
    return !ctx.player.is_downed && Boolean(ctx.anim.operateUntil && ctx.now < ctx.anim.operateUntil);
  }

  public getFrameIndex(ctx: AnimationContext): number {
    const operateUntil = ctx.anim.operateUntil ?? ctx.now;
    const elapsed = ctx.now - (operateUntil - PLAYER_OPERATE_DURATION);
    const fi = Math.max(
      0,
      Math.min(
        Math.floor(elapsed / (PLAYER_OPERATE_DURATION / OperateAnimationState.OPERATE_FRAMES.length)),
        OperateAnimationState.OPERATE_FRAMES.length - 1,
      ),
    );
    return OperateAnimationState.OPERATE_FRAMES[fi];
  }
}

export class ReadAnimationState implements IHeroAnimationState {
  public readonly name = 'read';
  private static readonly READ_FRAMES = [19, 20, 20, 20, 20, 20, 20, 20, 20, 19];

  public matches(ctx: AnimationContext): boolean {
    return !ctx.player.is_downed && Boolean(ctx.anim.readUntil && ctx.now < ctx.anim.readUntil);
  }

  public getFrameIndex(ctx: AnimationContext): number {
    const readUntil = ctx.anim.readUntil ?? ctx.now;
    const elapsed = ctx.now - (readUntil - PLAYER_READ_DURATION);
    const fi = Math.max(
      0,
      Math.min(
        Math.floor(elapsed / (PLAYER_READ_DURATION / ReadAnimationState.READ_FRAMES.length)),
        ReadAnimationState.READ_FRAMES.length - 1,
      ),
    );
    return ReadAnimationState.READ_FRAMES[fi];
  }
}

export class WalkAnimationState implements IHeroAnimationState {
  public readonly name = 'walk';
  private static readonly RUN_FRAMES = [2, 3, 4, 5, 6, 7];
  private static readonly MIN_MOTION_DELTA = 0.05;

  public matches(ctx: AnimationContext): boolean {
    if (ctx.player.is_downed) return false;
    if (!ctx.player.targetPos) return false;

    const moveDuration = ctx.player.moveDuration || MOVE_DURATION;
    const moveAnimActive =
      ctx.player.animStartTime != null && ctx.now - ctx.player.animStartTime < moveDuration + 50;
    if (!moveAnimActive) return false;

    const dx = Math.abs(ctx.player.targetPos.x - ctx.player.renderPos.x);
    const dy = Math.abs(ctx.player.targetPos.y - ctx.player.renderPos.y);
    return dx > WalkAnimationState.MIN_MOTION_DELTA || dy > WalkAnimationState.MIN_MOTION_DELTA;
  }

  public getFrameIndex(ctx: AnimationContext): number {
    const moveDuration = ctx.player.moveDuration || ctx.player.step_duration_ms || MOVE_DURATION;
    const frameInterval = Math.max(15, Math.round(50 * (moveDuration / MOVE_DURATION)));
    return WalkAnimationState.RUN_FRAMES[
      Math.floor(ctx.now / frameInterval) % WalkAnimationState.RUN_FRAMES.length
    ];
  }
}

export class IdleAnimationState implements IHeroAnimationState {
  public readonly name = 'idle';
  private static readonly IDLE_FRAMES = [0, 0, 0, 1, 0, 0, 1, 1];

  public matches(_ctx: AnimationContext): boolean {
    return true;
  }

  public getFrameIndex(ctx: AnimationContext): number {
    return IdleAnimationState.IDLE_FRAMES[
      Math.floor(ctx.now / 1000) % IdleAnimationState.IDLE_FRAMES.length
    ];
  }
}

export class HeroAnimationPipeline {
  private states: IHeroAnimationState[];

  constructor(states?: IHeroAnimationState[]) {
    this.states = states ?? [
      new DownedAnimationState(),
      new AttackAnimationState(),
      new OperateAnimationState(),
      new ReadAnimationState(),
      new WalkAnimationState(),
      new IdleAnimationState(),
    ];
  }

  public register(state: IHeroAnimationState, atBeginning = false): void {
    if (atBeginning) {
      this.states.unshift(state);
    } else {
      this.states.push(state);
    }
  }

  public getActiveState(ctx: AnimationContext): IHeroAnimationState {
    for (const state of this.states) {
      if (state.matches(ctx)) {
        return state;
      }
    }
    return this.states[this.states.length - 1];
  }

  public getFrameIndex(ctx: AnimationContext): number {
    return this.getActiveState(ctx).getFrameIndex(ctx);
  }
}

export const defaultHeroAnimationPipeline = new HeroAnimationPipeline();
