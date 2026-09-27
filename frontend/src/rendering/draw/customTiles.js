import { SOURCE_TILE_SIZE, DEST_TILE_SIZE } from '../sewers/constants';

const ATLAS_COLS = 16;

function getAtlasCols(atlas) {
  const width = atlas.naturalWidth || atlas.width;
  return width ? Math.floor(width / SOURCE_TILE_SIZE) : ATLAS_COLS;
}

// Decorative custom tilemaps (e.g. GooNest, city_boss) -- cosmetic floor texture overlay
// drawn on top of the base grid, gated by the same discovered/visible state.
export function drawCustomTiles(ctx, { customTiles, assetImages, visionRef }) {
  if (!customTiles || !customTiles.length) return;

  for (const layer of customTiles) {
    const atlas = assetImages.customTiles?.[layer.texture];
    if (!atlas) continue;

    const atlasCols = getAtlasCols(atlas);

    for (let row = 0; row < layer.h; row++) {
      const tileRow = layer.tiles[row];
      for (let col = 0; col < layer.w; col++) {
        const idx = tileRow[col];
        if (idx < 0) continue;

        const x = layer.x + col;
        const y = layer.y + row;
        const key = `${x},${y}`;
        if (!visionRef.current.discovered.has(key)) continue;

        const sx = (idx % atlasCols) * SOURCE_TILE_SIZE;
        const sy = Math.floor(idx / atlasCols) * SOURCE_TILE_SIZE;
        ctx.drawImage(
          atlas,
          sx, sy, SOURCE_TILE_SIZE, SOURCE_TILE_SIZE,
          x * DEST_TILE_SIZE, y * DEST_TILE_SIZE, DEST_TILE_SIZE, DEST_TILE_SIZE
        );
      }
    }
  }
}

// Custom wall overlays rendered above characters (e.g. SewerExitOverhang arch, city_boss shadows/pillars),
// matching SPD's level.customWalls layer. Same format as customTiles.
export function drawCustomWalls(ctx, { customWalls, assetImages, visionRef }) {
  if (!customWalls || !customWalls.length) return;

  for (const layer of customWalls) {
    const atlas = assetImages.customTiles?.[layer.texture];
    if (!atlas) continue;

    const atlasCols = getAtlasCols(atlas);

    for (let row = 0; row < layer.h; row++) {
      const tileRow = layer.tiles[row];
      for (let col = 0; col < layer.w; col++) {
        const idx = tileRow[col];
        if (idx < 0) continue;

        const x = layer.x + col;
        const y = layer.y + row;
        const key = `${x},${y}`;
        if (!visionRef.current.discovered.has(key)) continue;

        const sx = (idx % atlasCols) * SOURCE_TILE_SIZE;
        const sy = Math.floor(idx / atlasCols) * SOURCE_TILE_SIZE;
        ctx.drawImage(
          atlas,
          sx, sy, SOURCE_TILE_SIZE, SOURCE_TILE_SIZE,
          x * DEST_TILE_SIZE, y * DEST_TILE_SIZE, DEST_TILE_SIZE, DEST_TILE_SIZE
        );
      }
    }
  }
}
