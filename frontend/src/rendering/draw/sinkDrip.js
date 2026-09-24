import { TILE_SIZE } from '../../constants';
import { BACKEND_TILE } from '../../constants';
import { isWallTile } from '../../constants';
import { spawnWaterRipple } from './waterRipple';

// Port of SewerLevel.java's Sink/WaterParticle (lines 246-310): every
// WALL_DECO cell on a sewers floor continuously drips small water-colored
// particles (Sink.pour(factory, 0.1f) ~= 10/s) while in FOV, plus a ripple
// on the water cell below every 0.8-1.2s (the original's 0.4-0.6s interval
// is doubled per tuning to halve how many ripples appear). Purely cosmetic.
//
// All sizes/speeds from the original are in a 16px-tile world and get
// doubled here (32px tiles): drip origin at the drain's CENTER + 3px below
// (-> center + 6), acc.y 50 -> 100, size 2 -> 4, horizontal speed ±2 -> ±4.
// The ripple reuses effects/Ripple.java's sprite via waterRipple.js.
const DRIP_EMIT_RATE = 10;
const RIPPLE_MIN_DELAY = 0.8;
const RIPPLE_MAX_DELAY = 1.2;

let cachedGrid = null;
let cachedSinkCells = [];
let lastNow = null;

const randomRippleDelay = () => RIPPLE_MIN_DELAY + Math.random() * (RIPPLE_MAX_DELAY - RIPPLE_MIN_DELAY);

// SewerLevel.addVisuals/addSewerVisuals only ever runs for SewerLevel, so
// the Sink emitter is sewers-only (depth 1-5) even though WALL_DECO tiles
// exist in other regions too.
function getSinkCells(grid, depth) {
  if (depth > 5) return [];
  if (grid !== cachedGrid) {
    cachedGrid = grid;
    cachedSinkCells = [];
    for (let y = 0; y < grid.length; y++) {
      for (let x = 0; x < grid[y].length; x++) {
        if (grid[y][x] === BACKEND_TILE.WALL_DECO.id) {
          cachedSinkCells.push({ x, y, rippleDelay: randomRippleDelay() });
        }
      }
    }
  }
  return cachedSinkCells;
}

// WaterParticle: gravity (acc.y=50 -> 100), 0.4s life, +-2px/s horizontal
// speed (-> +-4), constant size (no shrink), color randomized between
// light/dark teal-grey. Emission line at drain tile CENTER + 3px below
// (-> center + 6), 4px wide (-> 8px), as in Sink.pos(p.x-2, p.y+3, 4, 0).
function spawnWaterDrip(particlesRef, cx, cy, cellKey) {
  const t = Math.random();
  const lo = [0xb6, 0xcc, 0xc2];
  const hi = [0x3b, 0x66, 0x53];
  const c = lo.map((v, i) => Math.round(v + (hi[i] - v) * t));
  const color = `#${c.map((v) => v.toString(16).padStart(2, '0')).join('')}`;
  particlesRef.current.push({
    x: cx - 4 + Math.random() * 8,
    y: cy + TILE_SIZE / 2 + 6,
    vx: (Math.random() - 0.5) * 8,
    vy: 0,
    life: 0.4,
    maxLife: 0.4,
    size: 4,
    color,
    additive: false,
    accY: 100,
    shrink: false,
    fovCell: cellKey, // drawn only while the cell the drop falls into is in FOV
  });
}

export function advanceSinkDrips({ grid, depth, visionRef, particlesRef, now }) {
  if (!grid?.length) return;
  const cells = getSinkCells(grid, depth);

  const current = now ?? performance.now();
  const dt = lastNow == null ? 0 : Math.min((current - lastNow) / 1000, 0.05);
  lastNow = current;

  if (cells.length > 0) {
    const visible = visionRef?.current?.visible;
    for (const cell of cells) {
      // Gate on the cell the drops fall INTO, not on the drain wall itself.
      // WALL_DECO drains are walls, and WorldManager.updateVision shell-adds
      // every wall/door tile adjacent to a visible tile, so gating on the
      // drain cell keeps drops visible around corners and beyond direct LOS.
      // The cell below (floor/water) is never a shell wall: it is only
      // "visible" when the player truly sees it.
      const below = grid[cell.y + 1]?.[cell.x];
      const belowKey = `${cell.x},${cell.y + 1}`;
      const dropsIntoWalkable = below != null && !isWallTile(below);
      const seesBelow = !visible || visible.has(belowKey);
      if (!dropsIntoWalkable || !seesBelow) continue;

      const cx = cell.x * TILE_SIZE + TILE_SIZE / 2;
      const cy = cell.y * TILE_SIZE;

      if (Math.random() < dt * DRIP_EMIT_RATE) {
        spawnWaterDrip(particlesRef, cx, cy, belowKey);
      }

      cell.rippleDelay -= dt;
      if (cell.rippleDelay <= 0) {
        // SewerLevel.Sink.update() ripples (pos + width) — the water cell
        // directly below the drain — then lifts it by SIZE/2. With Noosa's
        // pivot maths (a visual's local origin point lands on (x,y)+(origin)),
        // that lift exactly cancels the ripple sprite's centered origin, so
        // the ring expands around the WATER cell's top-center: the point on
        // the water surface directly below the drain. Recreated here by
        // centering the ring on the drain column and the water cell's top,
        // with the top half of the ring clipped away so it stays on the
        // water instead of spilling over the wall above.
        if (below === BACKEND_TILE.FLOOR_WATER.id) {
          spawnWaterRipple(cx, (cell.y + 1) * TILE_SIZE, {
            clipTop: true,
            fovCell: belowKey, // drawn only while the water below is in FOV
          });
        }
        cell.rippleDelay = randomRippleDelay();
      }
    }
  }
}
