import { TILE_SIZE } from '../../constants';
import {
  FRAME_W,
  SCORPIO_FW,
  drawMobSprite,
  getGnollFrame,
  getGooFrame,
  getRatFrame,
  getScorpioFrame,
} from '../mobs';

export function drawMobs(ctx, { entitiesRef, visionRef, assetImages, mobAnimRef, dyingMobsRef }) {
  const now = performance.now();

  Object.values(entitiesRef.current.mobs).forEach(mob => {
    if (!visionRef.current.visible.has(`${Math.round(mob.renderPos.x)},${Math.round(mob.renderPos.y)}`)) return;

    let mobSprite = assetImages.rat;
    let sx = 0;
    if (mob.name === 'Rat') {
      mobSprite = assetImages.rat;
      sx = getRatFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Bat') {
      mobSprite = assetImages.bat;
    } else if (mob.name === 'Gnoll') {
      mobSprite = assetImages.gnoll;
      sx = getGnollFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Goo') {
      mobSprite = assetImages.goo;
      sx = getGooFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Scorpio') {
      mobSprite = assetImages.scorpio;
      sx = getScorpioFrame(mob, mobAnimRef.current, now);
    }

    const isScorpio = mob.name === 'Scorpio';
    const flash = !!(mobAnimRef.current[mob.id]?.flashUntil && now < mobAnimRef.current[mob.id].flashUntil);
    drawMobSprite(ctx, mob, mobSprite, sx,
      isScorpio ? SCORPIO_FW : FRAME_W,
      isScorpio ? SCORPIO_FW : FRAME_W,
      flash);

    const x = mob.renderPos.x * TILE_SIZE;
    const y = mob.renderPos.y * TILE_SIZE;
    const mobHpBarWidth = TILE_SIZE - 8;
    const mobHpPercent = (mob.hp || 0) / (mob.max_hp || 1);
    ctx.fillStyle = '#111';
    ctx.fillRect(x + 4, y - 4, mobHpBarWidth, 3);
    ctx.fillStyle = '#e74c3c';
    ctx.fillRect(x + 4, y - 4, mobHpBarWidth * mobHpPercent, 3);
  });

  Object.entries(dyingMobsRef.current).forEach(([id, mob]) => {
    const elapsed = now - mob.deathStart;
    const isScorpioDeath = mob.name === 'Scorpio';
    const isGooDeath = mob.name === 'Goo';
    const isRatDeath = mob.name === 'Rat';
    const deathDuration = isScorpioDeath ? 417 : isGooDeath ? 300 : isRatDeath ? 400 : 625;
    if (elapsed > deathDuration) { delete dyingMobsRef.current[id]; return; }
    if (!visionRef.current.visible.has(`${Math.round(mob.renderPos.x)},${Math.round(mob.renderPos.y)}`)) return;
    if (isScorpioDeath) {
      const fi = Math.min(Math.floor(elapsed / 83), 4);
      drawMobSprite(ctx, mob, assetImages.scorpio, [0, 7, 8, 9, 10][fi] * SCORPIO_FW, SCORPIO_FW, SCORPIO_FW);
    } else if (isGooDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 2);
      drawMobSprite(ctx, mob, assetImages.goo, [5, 6, 7][fi] * FRAME_W);
    } else if (isRatDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 3);
      drawMobSprite(ctx, mob, assetImages.rat, [11, 12, 13, 14][fi] * FRAME_W);
    } else {
      const fi = Math.min(Math.floor(elapsed / 125), 4);
      const sx = [7, 8, 9, 10, 11][fi] * FRAME_W;
      drawMobSprite(ctx, mob, assetImages.gnoll, sx);
    }
  });
}
