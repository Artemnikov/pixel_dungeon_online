import { TILE_SIZE } from '../../constants.js';
import { BACKEND_TILE } from '../../constants';
import { isWaterTile } from '../../constants';

// Port of effects/particles/FlowParticle.java (Flow emitter + particle),
// spawned from Level.addVisuals() in the original for every region the same
// way: a continuous stream of small rotating white specks pours off the
// bottom edge of any WATER cell whose neighbor BELOW it is a pit/chasm/void.
//
// Original behaviour, line by line:
//   - Level.addVisuals(): for each cell with pit[i] and water[i - width()],
//     create new FlowParticle.Flow(i - width()).
//   - Flow(FlowParticle.java:71-95): emitter anchored at the water cell's
//     bottom edge (pos(p.x, p.y + SIZE - 1, SIZE, 0)), pour(FACTORY, 0.05f)
//     = 20 particles/s, FOV-gated per cell.
//   - FlowParticle(FlowParticle.java:41-69): lifespan 0.6s, acc(0, 32)
//     [64 in 32px world], angularSpeed Random.Float(-360, +360)°/s,
//     alpha (p<0.5 ? p : 1-p)*0.6 (triangle, peak 0.6, fade-in AND out),
//     size((1-p)*4) [swells to 8 in 32px world], solid white PseudoPixel.
//
// Purely cosmetic. Emitters die automatically when the tile stops being
// water in the original; here the cell cache re-scans whenever the grid
// reference changes, which covers terrain changes between turns.
//
// Known deviations (intentional):
//   - isPitTile() accepts CHASM and VOID. The original's pit[] flag only
//     covers Terrain.CHASM; VOID (the unpainted/out-of-bounds tile in this
//     port) is included so water on the map edge still pours off the border.
//   - Particles go through the shared particlesRef pass and render above
//     items/mobs, matching the existing sinkDrip/hallsSteam convention
//     (the original draws Flow below heaps/chars).
const FLOW_RATE = 20;            // pour(FACTORY, 0.05f) == 20/s
const FLOW_LIFESPAN = 0.6;       // left = lifespan = 0.6f
const FLOW_ACC_Y = 64;           // acc.set(0, 32) at 16px tiles -> 64 at 32px
const FLOW_MAX_SIZE = 8;         // size((1-p)*4) at 16px tiles -> max 8 at 32px
const FLOW_PEAK_ALPHA = 0.6;     // (p < 0.5f ? p : 1 - p) * 0.6f
const FLOW_MAX_SPIN = 2 * Math.PI; // Random.Float(-360, +360) °/s == ±2π rad/s

const isPitTile = (tile) =>
  tile === BACKEND_TILE.CHASM.id || tile === BACKEND_TILE.VOID.id;

let cachedGrid = null;
let cachedCells = [];

function getWaterFlowCells(grid) {
  if (grid !== cachedGrid) {
    cachedGrid = grid;
    cachedCells = [];
    if (!grid?.length) return cachedCells;
    for (let y = 0; y < grid.length; y++) {
      const below = grid[y + 1];
      if (!below) continue;
      for (let x = 0; x < grid[y].length; x++) {
        if (isWaterTile(grid[y][x]) && isPitTile(below[x])) {
          cachedCells.push({ x, y });
        }
      }
    }
  }
  return cachedCells;
}

// FlowParticle: white rotating pixel-square, drifts slightly downward
// (acc 0,64), spawns at the water cell's bottom edge, alpha peaks at the
// midpoint of life (triangle, 0 -> 0.6 -> 0), size swells to its max as the
// particle dies, spin ±360°/s.
function spawnFlowParticle(particlesRef, cellX, cellY) {
  particlesRef.current.push({
    x: cellX * TILE_SIZE + Math.random() * TILE_SIZE,
    y: cellY * TILE_SIZE + TILE_SIZE - 1, // pos(p.x, p.y + SIZE - 1, SIZE, 0)
    vx: 0,
    vy: 0,
    accY: FLOW_ACC_Y,
    life: FLOW_LIFESPAN,
    maxLife: FLOW_LIFESPAN,
    sizeOnAge: FLOW_MAX_SIZE, // size swells from 0 -> max as the particle ages
    color: '#ffffff', // PseudoPixel solid 0xFFFFFFFF
    centered: true,
    angle: 0,
    angularSpeed: (Math.random() - 0.5) * 2 * FLOW_MAX_SPIN,
    triangleAlphaScale: FLOW_PEAK_ALPHA,
    shrink: false,
    fovCell: `${cellX},${cellY}`, // drawn only while the water cell is in FOV
  });
}

let lastNow = null;

export function advanceWaterFlow({ grid, visionRef, particlesRef, now }) {
  const t = now ?? performance.now();
  const dt = lastNow == null ? 0 : Math.min((t - lastNow) / 1000, 0.05);
  lastNow = t;

  if (!grid?.length) return;
  const cells = getWaterFlowCells(grid);
  if (!cells.length) return;

  const visible = visionRef?.current?.visible;
  for (const cell of cells) {
    const key = `${cell.x},${cell.y}`;
    if (visible && !visible.has(key)) continue;

    // pour(FACTORY, 0.05f): ~20 particles/s while in FOV
    if (Math.random() < dt * FLOW_RATE) {
      spawnFlowParticle(particlesRef, cell.x, cell.y);
    }
  }
}