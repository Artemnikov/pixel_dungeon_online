import { TILE_SIZE } from '../../constants';
import { BACKEND_TILE } from '../sewers/constants';

// Port of SPD's Alchemy blob + Speck.BUBBLE: each ALCHEMY tile continuously
// emits small bubble sprites that rise upward and fade out.  Purely cosmetic.

const SPECK_SIZE = 8;
const BUBBLE_FRAME_X = 96; // specks.png index 12 → 12 * 8 = 96
const EMIT_INTERVAL = 0.33; // seconds between bubbles (~3/s, matches SPD)
const RISE_SPEED = 15; // px/sec upward
const LIFESPAN_MIN = 0.8;
const LIFESPAN_MAX = 1.5;

let cachedGrid = null;
let cachedAlchemyCells = [];
let lastNow = performance.now();
let emitAccum = 0;
const activeBubbles = [];

function getAlchemyCells(grid) {
  if (grid !== cachedGrid) {
    cachedGrid = grid;
    cachedAlchemyCells = [];
    for (let y = 0; y < grid.length; y++) {
      for (let x = 0; x < grid[y].length; x++) {
        if (grid[y][x] === BACKEND_TILE.ALCHEMY.id) {
          cachedAlchemyCells.push({ x, y });
        }
      }
    }
  }
  return cachedAlchemyCells;
}

export function advanceAndDrawAlchemyBubbles(ctx, { grid, visionRef, assetImages }) {
  if (!grid?.length) return;
  const specks = assetImages?.specks;
  if (!specks) return;

  const cells = getAlchemyCells(grid);
  if (cells.length === 0) return;

  const now = performance.now();
  const dt = Math.min((now - lastNow) / 1000, 0.05);
  lastNow = now;

  const visible = visionRef?.current?.visible;

  // Emit one bubble per ALCHEMY cell on average every EMIT_INTERVAL seconds.
  emitAccum += dt;
  while (emitAccum >= EMIT_INTERVAL) {
    emitAccum -= EMIT_INTERVAL;
    for (const cell of cells) {
      const key = `${cell.x},${cell.y}`;
      if (visible && !visible.has(key)) continue;
      const lifespan = LIFESPAN_MIN + Math.random() * (LIFESPAN_MAX - LIFESPAN_MIN);
      activeBubbles.push({
        x: cell.x * TILE_SIZE + 4 + Math.random() * (TILE_SIZE - 8),
        y: cell.y * TILE_SIZE + 4,
        life: 0,
        maxLife: lifespan,
        scale: 0.8 + Math.random() * 0.4,
      });
    }
  }

  // Advance + draw
  for (let i = activeBubbles.length - 1; i >= 0; i--) {
    const b = activeBubbles[i];
    b.y -= RISE_SPEED * dt;
    b.life += dt;
    if (b.life >= b.maxLife) {
      activeBubbles.splice(i, 1);
      continue;
    }
    const t = b.life / b.maxLife;
    // Fade in over first 20%, full opacity until death (matches Speck.BUBBLE).
    ctx.globalAlpha = t < 0.2 ? t * 5 : 1;
    const size = SPECK_SIZE * b.scale;
    ctx.drawImage(specks, BUBBLE_FRAME_X, 0, SPECK_SIZE, SPECK_SIZE,
      b.x - size / 2, b.y - size / 2, size, size);
  }
  ctx.globalAlpha = 1;
}
