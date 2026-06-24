import { TILE_SIZE } from '../../constants';
import { setLightMode } from './blending';
import { spawnFlame } from './flameParticle';
import { spawnElmo } from './elmoParticle';
import { spawnSparkMoving } from './sparkParticle';

const BLOB_COLORS = {
  electricity: { fill: '#4488FF', alpha: 0.2, edge: '#88CCFF' },
  toxic_gas: { fill: '#00CC33', alpha: 0.3, edge: '#44FF66' },
  paralytic_gas: { fill: '#9900CC', alpha: 0.3, edge: '#CC44FF' },
  corrosive_gas: { fill: '#88CC00', alpha: 0.3, edge: '#AAFF00' },
  confusion_gas: { fill: '#CC6600', alpha: 0.25, edge: '#FFAA00' },
  tengu_shocker: { fill: '#4488FF', alpha: 0.25, edge: '#88CCFF' },
};

const FIRE_TYPES = new Set(['fire', 'tengu_fire']);
const FIRE_EMIT_RATE = 25;

const ELECTRIC_TYPES = new Set(['electricity', 'tengu_shocker']);
const SPARK_EMIT_RATE = 12;

let lastFireNow = performance.now();

let lastSparkNow = performance.now();

export function advanceAndDrawFireParticles(ctx, { blobAreasRef, visionRef, particlesRef }) {
  if (!blobAreasRef?.current) return;
  const now = performance.now();
  if (lastFireNow == null) lastFireNow = now;
  const dt = Math.min((now - lastFireNow) / 1000, 0.05);
  lastFireNow = now;

  if (lastSparkNow == null) lastSparkNow = now;
  const sparkDt = Math.min((now - lastSparkNow) / 1000, 0.05);
  lastSparkNow = now;

  const visible = visionRef?.current?.visible;
  for (const [, area] of Object.entries(blobAreasRef.current)) {
    if (FIRE_TYPES.has(area.type)) {
      const isTengu = area.type === 'tengu_fire';
      const spawnFn = isTengu ? spawnElmo : spawnFlame;
      for (const [key] of area.cells) {
        if (visible && !visible.has(key)) continue;
        if (Math.random() > dt * FIRE_EMIT_RATE) continue;
        const [x, y] = key.split(',').map(Number);
        const cx = x * TILE_SIZE + TILE_SIZE / 2;
        const cy = y * TILE_SIZE + TILE_SIZE / 2;
        spawnFn(particlesRef, cx, cy, 1);
      }
    }
    if (ELECTRIC_TYPES.has(area.type)) {
      for (const [key] of area.cells) {
        if (visible && !visible.has(key)) continue;
        if (Math.random() > sparkDt * SPARK_EMIT_RATE) continue;
        const [x, y] = key.split(',').map(Number);
        const cx = x * TILE_SIZE + TILE_SIZE / 2;
        const cy = y * TILE_SIZE + TILE_SIZE / 2;
        spawnSparkMoving(particlesRef, cx, cy, 1);
      }
    }
  }
}

export function updateBlobArea(blobAreasRef, id, type, cells) {
  if (!blobAreasRef.current) blobAreasRef.current = {};
  if (!cells || cells.length === 0) {
    delete blobAreasRef.current[id];
    return;
  }
  const cellMap = new Map();
  for (const [x, y, intensity] of cells) {
    cellMap.set(`${x},${y}`, intensity || 1);
  }
  blobAreasRef.current[id] = {
    type,
    cells: cellMap,
    updatedAt: performance.now(),
  };
}

export function removeBlobArea(blobAreasRef, id) {
  if (blobAreasRef.current) {
    delete blobAreasRef.current[id];
  }
}

export function advanceAndDrawBlobAreas(ctx, { blobAreasRef, visionRef }) {
  if (!blobAreasRef?.current) return;
  const areas = Object.entries(blobAreasRef.current);
  if (areas.length === 0) return;
  const visible = visionRef?.current?.visible;

  ctx.save();
  setLightMode(ctx);

  for (const [, area] of areas) {
    const colors = BLOB_COLORS[area.type];
    if (!colors || ELECTRIC_TYPES.has(area.type)) continue;

    for (const [key, intensity] of area.cells) {
      if (visible && !visible.has(key)) continue;
      const [x, y] = key.split(',').map(Number);
      const px = x * TILE_SIZE;
      const py = y * TILE_SIZE;
      const alpha = colors.alpha * Math.min(intensity, 1);

      ctx.globalAlpha = alpha;
      ctx.fillStyle = colors.fill;
      ctx.fillRect(px, py, TILE_SIZE, TILE_SIZE);

      ctx.globalAlpha = alpha * 0.6;
      ctx.strokeStyle = colors.edge;
      ctx.lineWidth = 1;
      ctx.strokeRect(px + 1, py + 1, TILE_SIZE - 2, TILE_SIZE - 2);
    }
  }

  ctx.restore();
}
