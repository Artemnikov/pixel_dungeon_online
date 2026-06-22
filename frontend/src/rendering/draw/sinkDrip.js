import { TILE_SIZE } from '../../constants';
import { BACKEND_TILE } from '../sewers/constants';

// Port of SewerLevel.java's Sink/WaterParticle (lines 246-310): every
// WALL_DECO cell on a sewers floor continuously drips small water-colored
// particles (Sink.pour(factory, 0.1f) ~= 10/s) while in FOV, plus a ripple
// on the floor cell below every 0.4-0.6s. Purely cosmetic.
const DRIP_EMIT_RATE = 10;
const RIPPLE_MIN_DELAY = 0.4;
const RIPPLE_MAX_DELAY = 0.6;
const RIPPLE_LIFESPAN = 0.5;

let cachedGrid = null;
let cachedSinkCells = [];
const activeRipples = [];
let lastNow = performance.now();

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

// WaterParticle: gravity (acc.y=50), 0.4s life, +-2px/s horizontal speed,
// constant size (no shrink), color randomized between light/dark teal-grey.
function spawnWaterDrip(particlesRef, cx, cy) {
  const t = Math.random();
  const lo = [0xb6, 0xcc, 0xc2];
  const hi = [0x3b, 0x66, 0x53];
  const c = lo.map((v, i) => Math.round(v + (hi[i] - v) * t));
  const color = `#${c.map((v) => v.toString(16).padStart(2, '0')).join('')}`;
  particlesRef.current.push({
    x: cx - 2 + Math.random() * 4,
    y: cy + 3,
    vx: (Math.random() - 0.5) * 4,
    vy: 0,
    life: 0.4,
    maxLife: 0.4,
    size: 2,
    _startSize: 2,
    color,
    additive: false,
    accY: 50,
    shrink: false,
  });
}

function drawRipple(ctx, x, y, age, lifespan) {
  const t = age / lifespan;
  const radius = 2 + t * 6;
  ctx.save();
  ctx.globalAlpha = (1 - t) * 0.5;
  ctx.strokeStyle = '#cfe8e0';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}

export function advanceAndDrawSinkDrips(ctx, { grid, depth, visionRef, particlesRef }) {
  if (!grid?.length) return;
  const cells = getSinkCells(grid, depth);

  const now = performance.now();
  const dt = Math.min((now - lastNow) / 1000, 0.05);
  lastNow = now;

  if (cells.length > 0) {
    const visible = visionRef?.current?.visible;
    for (const cell of cells) {
      const key = `${cell.x},${cell.y}`;
      if (visible && !visible.has(key)) continue;

      const cx = cell.x * TILE_SIZE + TILE_SIZE / 2;
      const cy = cell.y * TILE_SIZE;

      if (Math.random() < dt * DRIP_EMIT_RATE) {
        spawnWaterDrip(particlesRef, cx, cy);
      }

      cell.rippleDelay -= dt;
      if (cell.rippleDelay <= 0) {
        activeRipples.push({ x: cx, y: cy + TILE_SIZE, age: 0 });
        cell.rippleDelay = randomRippleDelay();
      }
    }
  }

  for (let i = activeRipples.length - 1; i >= 0; i--) {
    const r = activeRipples[i];
    r.age += dt;
    if (r.age >= RIPPLE_LIFESPAN) {
      activeRipples.splice(i, 1);
      continue;
    }
    drawRipple(ctx, r.x, r.y, r.age, RIPPLE_LIFESPAN);
  }
}
