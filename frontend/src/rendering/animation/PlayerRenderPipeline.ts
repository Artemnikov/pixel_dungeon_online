import type { AnimState, RenderPlayer } from '../../net/types';
import {
  TILE_SIZE,
  TILE_SCALE,
  DEATH_ANIMATION_DURATION,
  DEATH_FADE_START_MS,
} from '../../constants';
import { drawWhiteSilhouette } from '../draw/flash';
import { drawShieldFx } from '../draw/shieldHalo';
import { defaultHeroAnimationPipeline } from './HeroAnimationPipeline';

export interface PlayerRenderContext {
  player: RenderPlayer;
  anim?: AnimState;
  now: number;
  deathElapsed: number;
  x: number;
  y: number;
  myPlayerId?: string;
  playerSprite: CanvasImageSource | null;
  shieldFxRef?: { current: Map<string, unknown> } | null;
}

function pixelRound(value: number, pixelWidth: number): number {
  return Math.ceil(value * pixelWidth) / pixelWidth;
}

export function drawPlayerSprite(
  ctx2d: CanvasRenderingContext2D,
  ctx: PlayerRenderContext,
  frameIndex: number,
  alpha: number,
): void {
  const { player, playerSprite, anim, now, x, y } = ctx;
  if (!playerSprite) return;

  const isFlashing = Boolean(anim?.flashUntil && now < anim.flashUntil);
  const sx = frameIndex * 12;
  const sWidth = 12;
  const dWidth = sWidth * TILE_SCALE;
  const xOffset = (TILE_SIZE - dWidth) / 2;
  const SRC_FRAME_H = 15;
  const armorTier = (player.equipped_wearable as { tier?: number } | undefined)?.tier ?? 0;
  const sy = Math.max(0, Math.min(armorTier, 6)) * SRC_FRAME_H;

  ctx2d.save();
  ctx2d.globalAlpha = alpha;

  if (player.flipX) {
    ctx2d.translate(x + TILE_SIZE - xOffset, y);
    ctx2d.scale(-1, 1);
    ctx2d.drawImage(playerSprite, sx, sy, sWidth, SRC_FRAME_H, 0, 0, dWidth, TILE_SIZE);
    if (isFlashing) {
      drawWhiteSilhouette(ctx2d, playerSprite, sx, sy, sWidth, SRC_FRAME_H, 0, 0, dWidth, TILE_SIZE);
    }
  } else {
    ctx2d.drawImage(playerSprite, sx, sy, sWidth, SRC_FRAME_H, x + xOffset, y, dWidth, TILE_SIZE);
    if (isFlashing) {
      drawWhiteSilhouette(ctx2d, playerSprite, sx, sy, sWidth, SRC_FRAME_H, x + xOffset, y, dWidth, TILE_SIZE);
    }
  }
  ctx2d.restore();
}

export function drawPlayerHealthBar(
  ctx2d: CanvasRenderingContext2D,
  player: RenderPlayer,
  x: number,
  y: number,
): void {
  const hp = player.hp || 0;
  const maxHp = player.max_hp || 1;
  const shield = (player.shields || []).reduce((sum, s) => sum + (s.amount || 0), 0);

  const max = Math.max(hp + shield, maxHp);
  const healthPct = hp / max;
  const shieldPct = (hp + shield) / max;

  const barW = TILE_SIZE * (4 / 6);
  const barX = x + (TILE_SIZE - barW) / 2;
  const barY = y - 8;
  const pxW = barW;

  ctx2d.fillStyle = '#cc0000';
  ctx2d.fillRect(barX, barY, barW, 2);

  const shldW = barW * pixelRound(shieldPct, pxW);
  ctx2d.fillStyle = '#ffffff';
  ctx2d.fillRect(barX, barY, shldW, 2);

  const hpW = barW * pixelRound(healthPct, pxW);
  ctx2d.fillStyle = '#00ee00';
  ctx2d.fillRect(barX, barY, hpW, 2);
}

export function drawPlayerNamePlate(
  ctx2d: CanvasRenderingContext2D,
  player: RenderPlayer,
  x: number,
  y: number,
): void {
  ctx2d.fillStyle = 'white';
  ctx2d.font = '10px Arial';
  ctx2d.textAlign = 'center';
  ctx2d.fillText(player.name, x + TILE_SIZE / 2, y - 15);

  if (player.is_afk) {
    ctx2d.font = 'bold 10px Arial';
    ctx2d.fillStyle = '#ffdd55';
    ctx2d.strokeStyle = '#000000';
    ctx2d.lineWidth = 3;
    ctx2d.strokeText('(AFK)', x + TILE_SIZE / 2, y - 26);
    ctx2d.fillText('(AFK)', x + TILE_SIZE / 2, y - 26);
  }
}

export function drawPlayerShieldHalo(
  ctx2d: CanvasRenderingContext2D,
  shieldFxRef: { current: Map<string, unknown> } | null | undefined,
  player: RenderPlayer,
  x: number,
  y: number,
  alphaMultiplier: number,
): void {
  if (!shieldFxRef) return;
  const totalShield = (player.shields || []).reduce((sum, s) => sum + (s.amount || 0), 0);
  drawShieldFx(ctx2d, shieldFxRef, player.id, x + TILE_SIZE / 2, y, totalShield, alphaMultiplier);
}

export interface IPlayerRenderState {
  readonly name: string;
  matches(ctx: PlayerRenderContext): boolean;
  render(ctx2d: CanvasRenderingContext2D, ctx: PlayerRenderContext): void;
}

export class DownedPlayerRenderState implements IPlayerRenderState {
  public readonly name = 'downed';

  public matches(ctx: PlayerRenderContext): boolean {
    return Boolean(ctx.player.is_downed);
  }

  public getDeathFadeAlpha(deathElapsed: number): number {
    return deathElapsed <= DEATH_FADE_START_MS
      ? 1
      : Math.max(0, 1 - (deathElapsed - DEATH_FADE_START_MS) / (DEATH_ANIMATION_DURATION - DEATH_FADE_START_MS));
  }

  public render(ctx2d: CanvasRenderingContext2D, ctx: PlayerRenderContext): void {
    if (ctx.deathElapsed >= DEATH_ANIMATION_DURATION) {
      return;
    }

    const deathFade = this.getDeathFadeAlpha(ctx.deathElapsed);
    const baseAlpha = ctx.player.fadeAlpha ?? 1;
    const finalAlpha = baseAlpha * deathFade;

    const frameIndex = defaultHeroAnimationPipeline.getFrameIndex({
      player: ctx.player,
      anim: ctx.anim ?? {},
      now: ctx.now,
      deathElapsed: ctx.deathElapsed,
    });

    drawPlayerSprite(ctx2d, ctx, frameIndex, finalAlpha);
    drawPlayerShieldHalo(ctx2d, ctx.shieldFxRef, ctx.player, ctx.x, ctx.y, finalAlpha);
  }
}

export class AlivePlayerRenderState implements IPlayerRenderState {
  public readonly name = 'alive';

  public matches(ctx: PlayerRenderContext): boolean {
    return !ctx.player.is_downed;
  }

  public render(ctx2d: CanvasRenderingContext2D, ctx: PlayerRenderContext): void {
    const baseAlpha = ctx.player.fadeAlpha ?? 1;

    const frameIndex = defaultHeroAnimationPipeline.getFrameIndex({
      player: ctx.player,
      anim: ctx.anim ?? {},
      now: ctx.now,
      deathElapsed: ctx.deathElapsed,
    });

    drawPlayerSprite(ctx2d, ctx, frameIndex, baseAlpha);

    if (ctx.player.id !== ctx.myPlayerId) {
      drawPlayerHealthBar(ctx2d, ctx.player, ctx.x, ctx.y);
      drawPlayerNamePlate(ctx2d, ctx.player, ctx.x, ctx.y);
    }

    drawPlayerShieldHalo(ctx2d, ctx.shieldFxRef, ctx.player, ctx.x, ctx.y, baseAlpha);
  }
}

export class PlayerRenderPipeline {
  private states: IPlayerRenderState[];

  constructor(states?: IPlayerRenderState[]) {
    this.states = states ?? [
      new DownedPlayerRenderState(),
      new AlivePlayerRenderState(),
    ];
  }

  public register(state: IPlayerRenderState, atBeginning = false): void {
    if (atBeginning) {
      this.states.unshift(state);
    } else {
      this.states.push(state);
    }
  }

  public getActiveState(ctx: PlayerRenderContext): IPlayerRenderState | undefined {
    for (const state of this.states) {
      if (state.matches(ctx)) {
        return state;
      }
    }
    return this.states[this.states.length - 1];
  }

  public render(ctx2d: CanvasRenderingContext2D, ctx: PlayerRenderContext): void {
    const state = this.getActiveState(ctx);
    state?.render(ctx2d, ctx);
  }
}

export const defaultPlayerRenderPipeline = new PlayerRenderPipeline();
