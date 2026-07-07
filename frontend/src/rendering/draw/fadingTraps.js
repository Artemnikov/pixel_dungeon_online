import { TILE_SIZE } from '../../constants';
import {
  ATLAS_COLUMNS,
  SOURCE_TILE_SIZE,
  DEST_TILE_SIZE,
  trapSpriteIndex,
} from '../sewers/constants';
import { fadingTraps, clearExpiredFadingTraps } from '../tenguEffects';

const OVERLAY_DURATION = 4000;
const FADE_START = 2000;

export function advanceAndDrawFadingTraps(ctx, assetImages, { visionRef }) {
  if (!fadingTraps.size) return;
  const now = performance.now();
  clearExpiredFadingTraps(now);

  const terrainImg = assetImages?.terrainFeatures;
  if (!terrainImg) return;

  const visible = visionRef?.current?.visible;

  for (const [, trap] of fadingTraps) {
    const elapsed = now - trap.startTime;
    if (elapsed >= OVERLAY_DURATION) continue;

    const key = `${trap.x},${trap.y}`;
    if (visible && !visible.has(key)) continue;

    const srcIndex = trapSpriteIndex(trap.trap_type);
    if (srcIndex == null) continue;

    let alpha;
    if (elapsed < FADE_START) {
      alpha = 0.4;
    } else {
      alpha = 0.4 * (1 - (elapsed - FADE_START) / (OVERLAY_DURATION - FADE_START));
    }

    const sx = (srcIndex % ATLAS_COLUMNS) * SOURCE_TILE_SIZE;
    const sy = Math.floor(srcIndex / ATLAS_COLUMNS) * SOURCE_TILE_SIZE;
    const dx = trap.x * DEST_TILE_SIZE;
    const dy = trap.y * DEST_TILE_SIZE;

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.drawImage(
      terrainImg,
      sx, sy, SOURCE_TILE_SIZE, SOURCE_TILE_SIZE,
      dx, dy, DEST_TILE_SIZE, DEST_TILE_SIZE
    );
    ctx.restore();
  }
}
