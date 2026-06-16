import { TILE_SIZE, TILE_SCALE } from '../../constants';
import { coordsForItem } from '../sprites';

export function drawItems(ctx, { entitiesRef, visionRef, assetImages }) {
  if (!entitiesRef.current.items) return;
  const now = performance.now();
  const glowPhase = Math.sin(now / 400) * 0.15 + 0.15;

  entitiesRef.current.items.forEach(item => {
    if (!visionRef.current.visible.has(`${item.pos.x},${item.pos.y}`)) return;

    // Item glow
    ctx.save();
    ctx.globalAlpha = glowPhase;
    ctx.fillStyle = '#ffffbb';
    ctx.beginPath();
    ctx.arc(
      item.pos.x * TILE_SIZE + TILE_SIZE / 2,
      item.pos.y * TILE_SIZE + TILE_SIZE / 2,
      TILE_SIZE * 0.4, 0, Math.PI * 2
    );
    ctx.fill();
    ctx.restore();

    if (assetImages.items) {
      const coords = coordsForItem(item);
      if (!coords) return;
      ctx.drawImage(
        assetImages.items,
        coords[0] * (TILE_SIZE / TILE_SCALE),
        coords[1] * (TILE_SIZE / TILE_SCALE),
        TILE_SIZE / TILE_SCALE,
        TILE_SIZE / TILE_SCALE,
        item.pos.x * TILE_SIZE,
        item.pos.y * TILE_SIZE,
        TILE_SIZE,
        TILE_SIZE
      );
    } else {
      ctx.fillStyle = item.type === 'weapon' ? '#f1c40f' : '#9b59b6';
      ctx.beginPath();
      ctx.arc(item.pos.x * TILE_SIZE + TILE_SIZE / 2, item.pos.y * TILE_SIZE + TILE_SIZE / 2, 6, 0, Math.PI * 2);
      ctx.fill();
    }
  });
}
