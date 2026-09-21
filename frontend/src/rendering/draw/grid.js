import { BACKEND_TILE, hashCell, isGrassTile, isWallStitcheable, isWallTile, TILE_SIZE } from '../../constants';
import { drawSpriteTile, fallbackTileMap } from '../sprites';
import { drawSewerTileBase, drawSewerTileCap } from '../sewers/draw';
import { tilesForDepth } from '../regions';
import { tileAt, VIS_DISCOVERED, VIS_UNSEEN, wallEdgeDarkness } from './wallFog';

const dimCell = (ctx, x, y) => {
  ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
  ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
};

// Soft diagonal fog edge for wall corners (mirrors SPD FogOfWar's
// left/right half-cell split for wall tiles).
const HALF_TILE = TILE_SIZE / 2;
const dimHalf = (ctx, x, y, side, darkness) => {
  if (darkness === VIS_DISCOVERED) ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
  else if (darkness === VIS_UNSEEN) ctx.fillStyle = 'rgba(0, 0, 0, 1)';
  else return;
  const dx = x * TILE_SIZE + (side === 'right' ? HALF_TILE : 0);
  ctx.fillRect(dx, y * TILE_SIZE, HALF_TILE, TILE_SIZE);
};

const dimWallCell = (ctx, grid, vision, x, y) => {
  const { left, right } = wallEdgeDarkness(grid, vision, x, y);
  dimHalf(ctx, x, y, 'left', left);
  dimHalf(ctx, x, y, 'right', right);
};

// Reused offscreen canvas for the fog overlay. Each map cell is rasterized at
// FOG_SCALE x FOG_SCALE texels (the same 2-per-tile layout as SPD's
// FogOfWar.PIX_PER_TILE). Drawing it scaled up with bilinear smoothing softens
// LOS edges in all directions (including diagonals), mirroring SPD's texture —
// while the extra vertical resolution keeps the alpha of a dark cell from
// bleeding a full half-tile into its visible neighbours.
const FOG_SCALE = 2;
const fogCanvas = document.createElement('canvas');
const fogCtx = fogCanvas.getContext('2d');

const setCellFog = (fogAlpha, cols, x, y, alpha) => {
  for (let dy = 0; dy < FOG_SCALE; dy++) {
    for (let dx = 0; dx < FOG_SCALE; dx++) {
      fogAlpha[
        ((y * FOG_SCALE + dy) * (cols * FOG_SCALE) + x * FOG_SCALE + dx) * 4 + 3
      ] = alpha;
    }
  }
};

const drawFogOverlay = (ctx, fogAlpha, cols, rows) => {
  const texW = cols * FOG_SCALE;
  const texH = rows * FOG_SCALE;
  if (fogCanvas.width !== texW || fogCanvas.height !== texH) {
    fogCanvas.width = texW;
    fogCanvas.height = texH;
  }
  fogCtx.putImageData(new ImageData(fogAlpha, texW, texH), 0, 0);

  ctx.save();
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(
    fogCanvas,
    0, 0, texW, texH,
    0, 0, cols * TILE_SIZE, rows * TILE_SIZE
  );
  ctx.restore();
};

export function drawGrid(ctx, { grid, depth, assetImages, visionRef, openDoorsRef }) {
  // SPD tile-sheets share the same atlas layout per region — pick the
  // right PNG for this depth, then run the same autotiler pipeline.
  const regionTiles = tilesForDepth(assetImages, depth);

  const rows = grid.length;
  const cols = rows > 0 ? grid[0].length : 0;
  const fogAlpha = new Uint8ClampedArray(cols * rows * FOG_SCALE * FOG_SCALE * 4);
  const wallCells = [];
  // Camera-facing wall tiles whose own cell and the floor below are both fully
  // visible. Bilinear upscaling would otherwise smear the dark fog of the
  // unseen cells behind them down onto the wall's face; we clip those tiles
  // out of the fog draw entirely so the wall stays fully clear (SPD parity).
  const clearFogWalls = [];

  for (let y = 0; y < grid.length; y++) {
    for (let x = 0; x < grid[y].length; x++) {
      const tile = grid[y][x];
      if (tile === 0) {
        ctx.fillStyle = 'black';
        ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
        continue;
      }

      const key = `${x},${y}`;
      const isVisible = visionRef.current.visible.has(key);
      const isDiscovered = visionRef.current.discovered.has(key);

      if (!isDiscovered) {
        ctx.fillStyle = 'black';
        ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
        setCellFog(fogAlpha, cols, x, y, 255);
        continue;
      }

      let tileDrawn = false;

      if (regionTiles) {
        tileDrawn = drawSewerTileBase(
          ctx,
          regionTiles,
          grid,
          x,
          y,
          tile,
          openDoorsRef.current,
          depth
        );
      }

      if (!tileDrawn) {
        const tileCoords = fallbackTileMap[tile];
        if (tileCoords && regionTiles) {
          drawSpriteTile(ctx, regionTiles, tileCoords, x, y);
          tileDrawn = true;
        }
      }

      if (!tileDrawn) {
        if (tile === 3) ctx.fillStyle = '#855';
        else if (tile === 4) ctx.fillStyle = '#aa4';
        else if (tile === 5) ctx.fillStyle = '#4aa';
        else if (tile === 6) ctx.fillStyle = '#6f5234';
        else if (tile === 7) ctx.fillStyle = '#2f5f7a';
        else if (tile === 8) ctx.fillStyle = '#666';
        else if (tile === 9) ctx.fillStyle = '#3f7f3f';
        else if (tile === 10) ctx.fillStyle = '#8a5d23';
        else ctx.fillStyle = '#222';
        ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
      }

      if (assetImages?.terrainFeatures && (isGrassTile(tile) || tile === BACKEND_TILE.EMBERS.id)) {
        const stage = Math.min(Math.max(0, Math.floor(((depth || 1) - 1) / 5)), 4);
        const alt = (hashCell(x, y) % 100) >= 50 ? 1 : 0;
        let featureIndex = null;
        if (tile === BACKEND_TILE.HIGH_GRASS.id) {
          featureIndex = 9 + 16 * stage + alt;
        } else if (tile === BACKEND_TILE.FURROWED_GRASS.id) {
          featureIndex = 11 + 16 * stage + alt;
        } else if (tile === BACKEND_TILE.FLOOR_GRASS.id) {
          featureIndex = 13 + 16 * stage + alt;
        } else if (tile === BACKEND_TILE.EMBERS.id) {
          featureIndex = 89 + alt;
        }

        if (featureIndex != null) {
          const fsx = (featureIndex % 16) * 16;
          const fsy = Math.floor(featureIndex / 16) * 16;
          ctx.drawImage(
            assetImages.terrainFeatures,
            fsx, fsy, 16, 16,
            x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE
          );
        }
      }

      setCellFog(fogAlpha, cols, x, y, isVisible ? 0 : 153);
      if (isWallTile(tile)) {
        wallCells.push([x, y]);
        if (isVisible && !isWallStitcheable(tileAt(grid, x, y + 1))) {
          if (y + 1 < grid.length && visionRef.current.visible.has(`${x},${y + 1}`)) {
            clearFogWalls.push([x, y]);
          }
        }
      }
    }
  }

  if (cols > 0 && rows > 0) {
    if (clearFogWalls.length > 0) {
      // Carve the fully-visible camera-facing walls out of the fog overlay so
      // bilinear bleeding from unseen cells behind them never darkens them.
      const fogClip = new Path2D();
      // Slight inflation keeps the outer rect from sharing an edge with a
      // wall hole carved at the very edge of the map (safe with evenodd).
      fogClip.rect(-0.5, -0.5, cols * TILE_SIZE + 1, rows * TILE_SIZE + 1);
      for (const [x, y] of clearFogWalls) {
        fogClip.rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
      }
      ctx.save();
      ctx.clip(fogClip, 'evenodd');
      drawFogOverlay(ctx, fogAlpha, cols, rows);
      ctx.restore();
    } else {
      drawFogOverlay(ctx, fogAlpha, cols, rows);
    }
  }

  // Crisp corner-split darkness for walls, drawn on top of the soft overlay.
  for (const [x, y] of wallCells) {
    dimWallCell(ctx, grid, visionRef.current, x, y);
  }
}

// Second pass: wall overhangs + door caps drawn AFTER items / mobs / players
// so chars are partially obscured by wall tops and door overhangs, mirroring
// the upper half of SPD's DungeonWallsTilemap.
export function drawGridCaps(ctx, { grid, depth, assetImages, visionRef, openDoorsRef }) {
  const regionTiles = tilesForDepth(assetImages, depth);
  if (!regionTiles) return;

  for (let y = 0; y < grid.length; y++) {
    for (let x = 0; x < grid[y].length; x++) {
      const tile = grid[y][x];
      if (tile === 0) continue;

      const key = `${x},${y}`;
      if (!visionRef.current.discovered.has(key)) continue;

      const drew = drawSewerTileCap(ctx, regionTiles, grid, x, y, tile, openDoorsRef?.current);
      if (!drew) continue;

      if (isWallTile(tile)) {
        dimWallCell(ctx, grid, visionRef.current, x, y);
      } else if (!visionRef.current.visible.has(key)) {
        dimCell(ctx, x, y);
      }
    }
  }
}
