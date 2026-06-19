import { TILE_SIZE } from '../../constants';
import AudioManager from '../../audio/AudioManager';
import { spawnDust, spawnCritSparkle } from '../../rendering/draw/particles';
import { spawnFloatingText } from '../../rendering/draw/floatingText';
import type { GameEvent } from '../../types/contract';
import type { HandlerCtx } from '../types';

export function handleBossEvents(event: GameEvent, ctx: HandlerCtx): boolean {
  const { mobAnimRef, particlesRef, floatingTextRef, warnedTilesRef, visionRef } = ctx;

  if (event.type === 'GOO_CHARGE') {
    const now = performance.now();
    const tiles = event.data.tiles || [];
    if (warnedTilesRef) {
      warnedTilesRef.current = tiles.length
        ? { tiles, untilMs: now + (event.data.duration_ms ?? 1500) }
        : null;
    }
    if (mobAnimRef) {
      if (!mobAnimRef.current[event.data.mob]) mobAnimRef.current[event.data.mob] = {};
      mobAnimRef.current[event.data.mob].pumpUntil = tiles.length
        ? now + (event.data.duration_ms ?? 1500)
        : 0;
    }
    return true;
  }

  if (event.type === 'GOO_ENRAGE') {
    return true;
  }

  if (event.type === 'GOO_FIGHT_STARTED') {
    ctx.onGooFightStarted?.(event.data);
    return true;
  }

  if (event.type === 'TENGU_FIGHT_STARTED') {
    ctx.onTenguFightStarted?.(event.data);
    return true;
  }

  if (event.type === 'DM300_FIGHT_STARTED') {
    ctx.onDM300FightStarted?.(event.data);
    return true;
  }

  if (event.type === 'DWARF_KING_FIGHT_STARTED') {
    ctx.onDwarfKingFightStarted?.(event.data);
    return true;
  }

  if (event.type === 'DWARF_KING_PHASE2') {
    ctx.onDwarfKingPhase2?.(event.data);
    return true;
  }

  if (event.type === 'YOG_FIGHT_STARTED') {
    ctx.onYogFightStarted?.(event.data);
    return true;
  }

  if (event.type === 'YOG_FINAL_PHASE') {
    ctx.onYogFinalPhase?.(event.data);
    return true;
  }

  if (event.type === 'ZAP_SUMMON') {
    const now = performance.now();
    if (mobAnimRef.current) {
      if (!mobAnimRef.current[event.data.mob]) mobAnimRef.current[event.data.mob] = {};
      mobAnimRef.current[event.data.mob].attackUntil = now + 400;
    }
    if (visionRef?.current?.visible?.has(`${event.data.x},${event.data.y}`)) {
      AudioManager.play('RAY');
    }
    return true;
  }

  if (event.type === 'NECRO_SUMMON') {
    if (particlesRef && visionRef?.current?.visible?.has(`${event.data.x},${event.data.y}`)) {
      const cx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
      const cy = event.data.y * TILE_SIZE + TILE_SIZE / 2;
      spawnDust(particlesRef, cx, cy, 8);
    }
    return true;
  }

  if (event.type === 'TENGU_JUMP') {
    if (particlesRef && visionRef?.current?.visible?.has(`${event.data.x},${event.data.y}`)) {
      const cx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
      const cy = event.data.y * TILE_SIZE + TILE_SIZE / 2;
      spawnDust(particlesRef, cx, cy, 12);
    }
    return true;
  }

  if (event.type === 'TENGU_BOMB') {
    const now = performance.now();
    if (mobAnimRef.current) {
      if (!mobAnimRef.current[event.data.mob]) mobAnimRef.current[event.data.mob] = {};
      mobAnimRef.current[event.data.mob].attackUntil = now + 400;
    }
    if (floatingTextRef && visionRef?.current?.visible?.has(`${event.data.x},${event.data.y}`)) {
      const cx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
      const cy = event.data.y * TILE_SIZE;
      spawnFloatingText(floatingTextRef, cx, cy, '!', '#ff6600');
    }
    return true;
  }

  if (event.type === 'TENGU_BOMB_COUNTDOWN') {
    if (floatingTextRef && visionRef?.current?.visible?.has(`${event.data.x},${event.data.y}`)) {
      const cx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
      const cy = event.data.y * TILE_SIZE;
      spawnFloatingText(floatingTextRef, cx, cy, `${event.data.count}...`, '#ff6600');
    }
    return true;
  }

  if (event.type === 'TENGU_BLAST') {
    if (particlesRef && visionRef?.current?.visible?.has(`${event.data.x},${event.data.y}`)) {
      const cx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
      const cy = event.data.y * TILE_SIZE + TILE_SIZE / 2;
      spawnCritSparkle(particlesRef, cx, cy, 16, '#ff6600');
    }
    return true;
  }

  if (event.type === 'TENGU_FIRE' || event.type === 'TENGU_SHOCKER') {
    if (particlesRef) {
      const color = event.type === 'TENGU_FIRE' ? '#ff6600' : '#66ccff';
      for (const [x, y] of event.data.cells) {
        if (!visionRef?.current?.visible?.has(`${x},${y}`)) continue;
        const cx = x * TILE_SIZE + TILE_SIZE / 2;
        const cy = y * TILE_SIZE + TILE_SIZE / 2;
        spawnCritSparkle(particlesRef, cx, cy, 8, color);
      }
    }
    return true;
  }

  return false;
}
