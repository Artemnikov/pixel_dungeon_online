import { TILE_SIZE } from '../../constants';
import { setLightMode } from './blending';

const BLOB_COLORS = {
  fire:      { fill: '#FF4400', alpha: 0.25, edge: '#FF8800' },
  electricity: { fill: '#4488FF', alpha: 0.2, edge: '#88CCFF' },
  toxic_gas: { fill: '#00CC33', alpha: 0.3, edge: '#44FF66' },
  paralytic_gas: { fill: '#9900CC', alpha: 0.3, edge: '#CC44FF' },
  corrosive_gas: { fill: '#88CC00', alpha: 0.3, edge: '#AAFF00' },
  confusion_gas: { fill: '#CC6600', alpha: 0.25, edge: '#FFAA00' },
  tengu_fire: { fill: '#FF4400', alpha: 0.3, edge: '#FF8800' },
  tengu_shocker: { fill: '#4488FF', alpha: 0.25, edge: '#88CCFF' },
};

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
    if (!colors) continue;

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
