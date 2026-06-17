import { TILE_SIZE } from '../../constants';

export function drawShieldHalo(ctx, cx, cy, shieldTotal) {
  if (!shieldTotal || shieldTotal <= 0) return;
  const radius = TILE_SIZE * 0.7;
  ctx.save();
  ctx.globalAlpha = 0.35;
  ctx.globalCompositeOperation = 'lighter';
  ctx.strokeStyle = '#bbaacc';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.arc(cx, cy + TILE_SIZE * 0.2, radius, 0, Math.PI * 2);
  ctx.stroke();
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.arc(cx, cy + TILE_SIZE * 0.2, radius * 0.75, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}

export function spawnShieldHalo(haloRef, cx, cy, entityId) {
  const now = performance.now();
  const existing = haloRef.current.find(e => e.entityId === entityId && e.active);
  if (existing) {
    existing.startTime = now;
    existing.active = true;
    return;
  }
  haloRef.current.push({ cx, cy, entityId, startTime: now, active: true });
}

export function removeShieldHalo(haloRef, entityId) {
  const entry = haloRef.current.find(e => e.entityId === entityId);
  if (entry) entry.active = false;
}

export function advanceAndDrawShieldHalos(ctx, { haloRef }) {
  if (!haloRef?.current?.length) return;
  const now = performance.now();
  const entries = haloRef.current;

  for (let i = entries.length - 1; i >= 0; i--) {
    const e = entries[i];
    if (!e.active) {
      const elapsed = now - e.startTime;
      if (elapsed > 999) { entries.splice(i, 1); continue; }
      const fade = 1 - elapsed / 999;
      const scale = 1 + elapsed / 999 * 0.5;
      drawHalo(ctx, e.cx, e.cy, fade, scale);
      continue;
    }
    drawHalo(ctx, e.cx, e.cy, 1, 1);
  }
}

function drawHalo(ctx, cx, cy, alpha, scale) {
  const radius = TILE_SIZE * 0.7 * scale;
  ctx.save();
  ctx.globalAlpha = alpha * 0.45;
  ctx.globalCompositeOperation = 'lighter';
  ctx.strokeStyle = '#bbaacc';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(cx, cy + TILE_SIZE * 0.15, radius, 0, Math.PI * 2);
  ctx.stroke();
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(cx, cy + TILE_SIZE * 0.15, radius * 0.8, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}
