import { TILE_SIZE } from '../../constants';
import AudioManager from '../../audio/AudioManager';
import { spawnDust, spawnCritSparkle, spawnLight } from '../../rendering/draw/particles';
import { spawnSparkMoving } from '../../rendering/draw/sparkParticle';
import { spawnFloatingText } from '../../rendering/draw/floatingText';
import { spawnBeam } from '../../rendering/draw/beam';
import { spawnLightning } from '../../rendering/draw/lightning';
import { spawnScreenShake } from '../../rendering/draw/screenShake';
import { addFadingTraps, setBombItem, clearBombItem } from '../../rendering/tenguEffects';
import { spawnSmoke } from '../../rendering/draw/smokeParticle';
import type { GameEvent } from '../../types/contract';
import type { HandlerCtx } from '../types';

export function handleBossEvents(event: GameEvent, ctx: HandlerCtx): boolean {
  const { mobAnimRef, particlesRef, floatingTextRef, warnedTilesRef, visionRef, beamRef, screenShakeRef, lightningRef } = ctx;

  const pourBombSmoke = (bx: number, by: number) => {
    if (!particlesRef) return;
    for (let dy = -2; dy <= 2; dy++) {
      for (let dx = -2; dx <= 2; dx++) {
        const x = bx + dx, y = by + dy;
        if (!visionRef?.current?.visible?.has(`${x},${y}`)) continue;
        if (Math.random() > 0.5) continue;
        spawnSmoke(particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 1);
      }
    }
  };

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

  if (event.type === 'TENGU_TRAP_BURST') {
    const cells = event.data.cells;
    if (particlesRef && cells) {
      for (const [x, y] of cells) {
        if (visionRef?.current?.visible?.has(`${x},${y}`)) {
          spawnLight(particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 2);
        }
      }
    }
    if (cells) addFadingTraps(cells, 'tengu_dart');
    return true;
  }

  if (event.type === 'TENGU_BOMB') {
    const now = performance.now();
    if (mobAnimRef.current) {
      if (!mobAnimRef.current[event.data.mob]) mobAnimRef.current[event.data.mob] = {};
      mobAnimRef.current[event.data.mob].attackUntil = now + 400;
    }
    setBombItem(event.data.x, event.data.y);
    pourBombSmoke(event.data.x, event.data.y);
    return true;
  }

  if (event.type === 'TENGU_BOMB_COUNTDOWN') {
    if (floatingTextRef && visionRef?.current?.visible?.has(`${event.data.x},${event.data.y}`)) {
      const cx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
      const cy = event.data.y * TILE_SIZE;
      spawnFloatingText(floatingTextRef, cx, cy, `${event.data.count}...`, '#ff6600');
    }
    pourBombSmoke(event.data.x, event.data.y);
    return true;
  }

  if (event.type === 'TENGU_BLAST') {
    clearBombItem();
    if (particlesRef && visionRef?.current?.visible?.has(`${event.data.x},${event.data.y}`)) {
      const cx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
      const cy = event.data.y * TILE_SIZE + TILE_SIZE / 2;
      spawnCritSparkle(particlesRef, cx, cy, 16, '#ff6600');
    }
    return true;
  }

  if (event.type === 'TENGU_FIRE') {
    if (particlesRef) {
      for (const [x, y] of event.data.cells) {
        if (!visionRef?.current?.visible?.has(`${x},${y}`)) continue;
        const cx = x * TILE_SIZE + TILE_SIZE / 2;
        const cy = y * TILE_SIZE + TILE_SIZE / 2;
        spawnCritSparkle(particlesRef, cx, cy, 8, '#ff6600');
      }
    }
    return true;
  }

  if (event.type === 'TENGU_SHOCKER') {
    if (particlesRef) {
      for (const [x, y] of event.data.cells) {
        if (!visionRef?.current?.visible?.has(`${x},${y}`)) continue;
        const cx = x * TILE_SIZE + TILE_SIZE / 2;
        const cy = y * TILE_SIZE + TILE_SIZE / 2;
        spawnCritSparkle(particlesRef, cx, cy, 8, '#66ccff');

        if (lightningRef) {
          const s = TILE_SIZE;
          const h = s / 2;
          const [bx, by] = [x * s + h, y * s + h];
          spawnLightning(lightningRef, bx - s, by - s, bx + s, by + s, '#88ccff');
          spawnLightning(lightningRef, bx - s, by + s, bx + s, by - s, '#88ccff');
          spawnLightning(lightningRef, bx, by - s, bx, by + s, '#88ccff');
          spawnLightning(lightningRef, bx - s, by, bx + s, by, '#88ccff');
        }
      }
    }
    return true;
  }

  if (event.type === 'EYE_CHARGE') {
    const now = performance.now();
    if (mobAnimRef.current) {
      if (!mobAnimRef.current[event.data.mob]) mobAnimRef.current[event.data.mob] = {};
      mobAnimRef.current[event.data.mob].chargeUntil = now + 1000;
      mobAnimRef.current[event.data.mob].attackUntil = 0;
    }
    if (visionRef?.current?.visible?.has(`${event.data.target_x},${event.data.target_y}`)) {
      AudioManager.play('CHARGEUP');
    }
    return true;
  }

  if (event.type === 'EYE_DEATH_RAY') {
    const sx = event.data.source_x * TILE_SIZE + TILE_SIZE / 2;
    const sy = event.data.source_y * TILE_SIZE + TILE_SIZE / 2;
    const tx = event.data.target_x * TILE_SIZE + TILE_SIZE / 2;
    const ty = event.data.target_y * TILE_SIZE + TILE_SIZE / 2;
    if (beamRef) spawnBeam(beamRef, sx, sy, tx, ty, 'death_ray');
    if (visionRef?.current?.visible?.has(`${event.data.source_x},${event.data.source_y}`)) {
      AudioManager.play('RAY');
    }
    return true;
  }

  if (event.type === 'BOSS_YELL') {
    if (floatingTextRef && visionRef?.current?.visible?.has(`${event.data.x},${event.data.y}`)) {
      const cx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
      const cy = event.data.y * TILE_SIZE - 2;
      spawnFloatingText(floatingTextRef, cx, cy, event.data.text, '#ffff66');
    }
    return true;
  }

  if (event.type === 'DM300_TRAP_STEP') {
    if (visionRef?.current?.visible?.has(`${event.data.x},${event.data.y}`)) {
      const cx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
      const cy = event.data.y * TILE_SIZE + TILE_SIZE / 2;
      if (particlesRef) spawnSparkMoving(particlesRef, cx, cy, 8);
      if (screenShakeRef) spawnScreenShake(screenShakeRef, 8, 200);
    }
    return true;
  }

  return false;
}
