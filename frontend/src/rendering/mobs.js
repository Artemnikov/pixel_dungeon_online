import { TILE_SIZE, TILE_SCALE } from '../constants';
import { drawWhiteSilhouette } from './draw/flash';

export const FRAME_W = TILE_SIZE / TILE_SCALE;
export const FRAME_H = TILE_SIZE / TILE_SCALE;
export const SCORPIO_FW = 17;

const isEntityMoving = (mob) =>
  mob.targetPos &&
  (Math.abs(mob.targetPos.x - mob.renderPos.x) > 0.05 ||
   Math.abs(mob.targetPos.y - mob.renderPos.y) > 0.05);

export const getGooFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 300);
    const fi = Math.min(Math.floor(elapsed / 100), 2);
    return [8, 9, 10][fi] * FRAME_W;
  }
  if (isEntityMoving(mob)) return [3, 2, 1, 2][Math.floor(now / 67) % 4] * FRAME_W;
  return [2, 1, 0, 0, 1][Math.floor(now / 100) % 5] * FRAME_W;
};

export const getGnollFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 250);
    const fi = Math.min(Math.floor(elapsed / 83), 2);
    return [2, 3, 4][fi] * FRAME_W;
  }
  if (isEntityMoving(mob)) {
    return [4, 5, 4, 6][Math.floor(now / 83) % 4] * FRAME_W;
  }
  return (Math.floor(now / 500) % 2) * FRAME_W;
};

export const getScorpioFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 200);
    const fi = Math.min(Math.floor(elapsed / 67), 2);
    return [0, 3, 4][fi] * SCORPIO_FW;
  }
  if (isEntityMoving(mob)) return [5, 5, 6, 6][Math.floor(now / 125) % 4] * SCORPIO_FW;
  return [0,0,0,0,0,0,0,0,1,2,1,2,1,2][Math.floor(now / 83) % 14] * SCORPIO_FW;
};

export const getRatFrame = (mob, mobAnim, now) => {
  const anim = mobAnim[mob.id] || {};
  const isAttacking = anim.attackUntil && now < anim.attackUntil;
  if (isAttacking) {
    const elapsed = now - (anim.attackUntil - 333);
    const fi = Math.min(Math.floor(elapsed / 67), 4);
    return [2, 3, 4, 5, 0][fi] * FRAME_W;
  }
  if (isEntityMoving(mob)) {
    return [6, 7, 8, 9, 10][Math.floor(now / 100) % 5] * FRAME_W;
  }
  return [0, 0, 0, 1][Math.floor(now / 500) % 4] * FRAME_W;
};

export const drawMobSprite = (ctx, mob, sprite, sx, fw = FRAME_W, fh = FRAME_H, flash = false) => {
  const x = mob.renderPos.x * TILE_SIZE;
  const y = mob.renderPos.y * TILE_SIZE;
  if (sprite) {
    ctx.save();
    if (mob.facing === 'LEFT') {
      ctx.translate(x + TILE_SIZE, y);
      ctx.scale(-1, 1);
      ctx.drawImage(sprite, sx, 0, fw, fh, 0, 0, TILE_SIZE, TILE_SIZE);
      if (flash) drawWhiteSilhouette(ctx, sprite, sx, 0, fw, fh, 0, 0, TILE_SIZE, TILE_SIZE);
    } else {
      ctx.drawImage(sprite, sx, 0, fw, fh, x, y, TILE_SIZE, TILE_SIZE);
      if (flash) drawWhiteSilhouette(ctx, sprite, sx, 0, fw, fh, x, y, TILE_SIZE, TILE_SIZE);
    }
    ctx.restore();
  } else {
    ctx.fillStyle = '#e74c3c';
    ctx.fillRect(x + 4, y + 4, TILE_SIZE - 8, TILE_SIZE - 8);
  }
};
