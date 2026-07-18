import { TILE_SIZE } from '../../constants.js';
import { isWaterTile } from '../sewers/constants.js';
import { regionForDepth } from '../regions.js';

// Port of HallsLevel.addHallsVisuals/Stream/FireParticle: every WATER cell
// in the Halls region (depth 21+) continuously emits a rising, decelerating
// steam/ember particle on a Random.Float(2) (0-2s) cycle while in FOV.
// Purely cosmetic.
const STEAM_MAX_DELAY = 2;

let cachedGrid = null;
let cachedCells = [];

const randomSteamDelay = () => Math.random() * STEAM_MAX_DELAY;

export function getHallsSteamCells(grid, depth) {
  if (regionForDepth(depth) !== 'halls') return [];
  if (grid !== cachedGrid) {
    cachedGrid = grid;
    cachedCells = [];
    for (let y = 0; y < grid.length; y++) {
      for (let x = 0; x < grid[y].length; x++) {
        if (isWaterTile(grid[y][x])) {
          cachedCells.push({ x, y, delay: randomSteamDelay() });
        }
      }
    }
  }
  return cachedCells;
}

// FireParticle: color 0xEE7722, 1s lifespan, rises then decelerates
// (speed.set(0,-40), acc.set(0,+80)), shrinks from size 4 (default particle
// behaviour — shrink defaults on unless size explicitly false).
function spawnSteamParticle(particlesRef, cellX, cellY) {
  particlesRef.current.push({
    x: cellX * TILE_SIZE + Math.random() * TILE_SIZE,
    y: cellY * TILE_SIZE + Math.random() * TILE_SIZE,
    vx: 0,
    vy: -40,
    accY: 80,
    life: 1,
    maxLife: 1,
    size: 4,
    color: '#EE7722',
  });
}

let lastNow = null;

export function advanceHallsSteam({ grid, depth, visionRef, particlesRef }) {
  const now = performance.now();
  const dt = lastNow == null ? 0 : Math.min((now - lastNow) / 1000, 0.05);
  lastNow = now;

  if (!grid?.length) return;
  const cells = getHallsSteamCells(grid, depth);
  if (!cells.length) return;

  const visible = visionRef?.current?.visible;
  for (const cell of cells) {
    const key = `${cell.x},${cell.y}`;
    if (visible && !visible.has(key)) continue;

    cell.delay -= dt;
    if (cell.delay <= 0) {
      spawnSteamParticle(particlesRef, cell.x, cell.y);
      cell.delay = randomSteamDelay();
    }
  }
}
