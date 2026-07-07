import { TILE_SIZE, TILE_SCALE } from '../../constants';
import { bombOverlay } from '../tenguEffects';

const spriteSize = TILE_SIZE / TILE_SCALE;

export function drawBombItem(ctx, assetImages, { visionRef }) {
  if (!bombOverlay.active) return;

  const key = `${bombOverlay.x},${bombOverlay.y}`;
  if (visionRef?.current?.visible && !visionRef.current.visible.has(key)) return;

  const itemsImg = assetImages?.items;
  if (!itemsImg) return;

  const sx = 10 * spriteSize;
  const sy = 1 * spriteSize;
  const dx = bombOverlay.x * TILE_SIZE + (TILE_SIZE - 10 * TILE_SCALE) / 2;
  const dy = bombOverlay.y * TILE_SIZE + (TILE_SIZE - 10 * TILE_SCALE) / 2;

  ctx.drawImage(itemsImg, sx, sy, 10, 10, dx, dy, 10 * TILE_SCALE, 10 * TILE_SCALE);
}
