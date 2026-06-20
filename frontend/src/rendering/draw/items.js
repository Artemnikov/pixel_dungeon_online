import { TILE_SIZE, TILE_SCALE } from '../../constants';
import { coordsForItem } from '../sprites';
import { itemRects } from '../spriteRects';
import { centeredItemCrop } from '../itemCrop';

const DROP_DURATION = 400;

function easeOutBounce(t) {
  if (t < 1 / 2.75) return 7.5625 * t * t;
  if (t < 2 / 2.75) { t -= 1.5 / 2.75; return 7.5625 * t * t + 0.75; }
  if (t < 2.5 / 2.75) { t -= 2.25 / 2.75; return 7.5625 * t * t + 0.9375; }
  t -= 2.625 / 2.75; return 7.5625 * t * t + 0.984375;
}

export function drawItems(ctx, { entitiesRef, visionRef, assetImages }) {
  if (!entitiesRef.current.items) return;
  const now = performance.now();
  const glowPhase = Math.sin(now / 400) * 0.15 + 0.15;

  entitiesRef.current.items.forEach(item => {
    if (!visionRef.current.visible.has(`${item.pos.x},${item.pos.y}`)) return;

    let drawY = item.pos.y;
    const dropBounce = item.dropBounce;
    if (dropBounce) {
      const elapsed = now - dropBounce.startTime;
      if (elapsed >= DROP_DURATION) {
        delete item.dropBounce;
      } else {
        const t = easeOutBounce(elapsed / DROP_DURATION);
        drawY = dropBounce.startY + (item.pos.y - dropBounce.startY) * t;
      }
    }

    // Item glow
    ctx.save();
    ctx.globalAlpha = glowPhase;
    ctx.fillStyle = '#ffffbb';
    ctx.beginPath();
    ctx.arc(
      item.pos.x * TILE_SIZE + TILE_SIZE / 2,
      drawY * TILE_SIZE + TILE_SIZE / 2,
      TILE_SIZE * 0.4, 0, Math.PI * 2
    );
    ctx.fill();
    ctx.restore();

    if (assetImages.items) {
      const coords = coordsForItem(item);
      if (!coords) return;
      const cell = TILE_SIZE / TILE_SCALE;
      const rect = itemRects.get(coords[0], coords[1]);
      const { sx, sy, sw, sh, dw, dh, offsetX, offsetY } = centeredItemCrop(rect, TILE_SIZE, cell);
      ctx.drawImage(
        assetImages.items,
        coords[0] * cell + sx,
        coords[1] * cell + sy,
        sw,
        sh,
        item.pos.x * TILE_SIZE + offsetX,
        drawY * TILE_SIZE + offsetY,
        dw,
        dh
      );
    } else {
      ctx.fillStyle = item.type === 'weapon' ? '#f1c40f' : '#9b59b6';
      ctx.beginPath();
      ctx.arc(item.pos.x * TILE_SIZE + TILE_SIZE / 2, drawY * TILE_SIZE + TILE_SIZE / 2, 6, 0, Math.PI * 2);
      ctx.fill();
    }
  });
}
