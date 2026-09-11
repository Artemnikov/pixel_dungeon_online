import {
  ATLAS_COLUMNS,
  DEST_TILE_SIZE,
  SOURCE_TILE_SIZE,
} from '../sewers/constants';
import { plantSpriteIndex } from '../../constants.js';

const GROW_FADE_DURATION = 200;

const getSourceXY = (srcIndex) => ({
  sx: (srcIndex % ATLAS_COLUMNS) * SOURCE_TILE_SIZE,
  sy: Math.floor(srcIndex / ATLAS_COLUMNS) * SOURCE_TILE_SIZE,
});

export function drawPlants(ctx, { entitiesRef, visionRef, assetImages }) {
  const terrainFeaturesImg = assetImages?.terrainFeatures;
  const plants = entitiesRef?.current?.plants;
  if (!terrainFeaturesImg || !plants || plants.length === 0) return;

  const now = performance.now();
  const visible = visionRef?.current?.visible;

  for (const plant of plants) {
    const { x, y, plant_type, revealStartTime } = plant;
    const key = `${x},${y}`;
    if (visible && !visible.has(key)) continue;

    const srcIndex = plantSpriteIndex(plant_type);
    if (srcIndex == null) continue;

    const { sx, sy } = getSourceXY(srcIndex);
    const dx = x * DEST_TILE_SIZE;
    const dy = y * DEST_TILE_SIZE;

    let scale = 1.0;
    let alpha = 1.0;
    if (revealStartTime) {
      const elapsed = now - revealStartTime;
      if (elapsed < GROW_FADE_DURATION) {
        const progress = Math.max(0, Math.min(1, elapsed / GROW_FADE_DURATION));
        scale = progress;
        alpha = progress;
      }
    }

    if (scale < 1.0) {
      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.translate(dx + DEST_TILE_SIZE / 2, dy + DEST_TILE_SIZE);
      ctx.scale(scale, scale);
      ctx.drawImage(
        terrainFeaturesImg,
        sx, sy, SOURCE_TILE_SIZE, SOURCE_TILE_SIZE,
        -DEST_TILE_SIZE / 2, -DEST_TILE_SIZE, DEST_TILE_SIZE, DEST_TILE_SIZE
      );
      ctx.restore();
    } else {
      ctx.drawImage(
        terrainFeaturesImg,
        sx, sy, SOURCE_TILE_SIZE, SOURCE_TILE_SIZE,
        dx, dy, DEST_TILE_SIZE, DEST_TILE_SIZE
      );
    }
  }
}
