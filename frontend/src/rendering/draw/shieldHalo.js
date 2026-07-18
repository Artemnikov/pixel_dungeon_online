import { TILE_SIZE } from '../../constants';

const HALO_COLOR = '#bbaacc';
const HALO_Y_OFFSET = TILE_SIZE * 0.5;
const HALO_RADIUS = TILE_SIZE * 0.7;
const SPAWN_MS = 250;
const BREAK_MS = 450;

// Persistent state: entityId -> { phase, startTime, cx, cy, prevShield }
// phase: 'spawn' | 'active' | 'break'
export function createShieldFxRef() {
  return { current: new Map() };
}

function drawRing(ctx, cx, cy, alpha, scale, lineWidth = 2.5) {
  if (alpha <= 0) return;
  const radius = HALO_RADIUS * scale;
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.globalCompositeOperation = 'lighter';
  ctx.strokeStyle = HALO_COLOR;
  ctx.lineWidth = lineWidth;
  ctx.beginPath();
  ctx.arc(cx, cy + HALO_Y_OFFSET, Math.max(1, radius), 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}

function drawShards(ctx, cx, cy, progress) {
  const baseY = cy + HALO_Y_OFFSET;
  const count = 6;
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < count; i++) {
    const angle = (i / count) * Math.PI * 2 + progress * 0.5;
    const dist = HALO_RADIUS * (0.6 + progress * 0.8);
    const x = cx + Math.cos(angle) * dist;
    const y = baseY + Math.sin(angle) * dist * 0.6;
    const alpha = (1 - progress) * 0.7;
    const size = (1 - progress) * 2.5 + 0.5;
    if (alpha <= 0) continue;
    ctx.globalAlpha = alpha;
    ctx.strokeStyle = HALO_COLOR;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(x, y, Math.max(0.5, size), 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.restore();
}

// Per-entity tracking + draw. Call every frame for each entity.
export function drawShieldFx(ctx, fxRef, entityId, cx, cy, shieldTotal, alphaMultiplier = 1) {
  const now = performance.now();
  const state = fxRef.current;
  let entry = state.get(entityId);

  if (!entry) {
    entry = { phase: 'idle', startTime: 0, cx, cy, prevShield: 0 };
    state.set(entityId, entry);
  }

  const prev = entry.prevShield;
  entry.cx = cx;
  entry.cy = cy;
  entry.prevShield = shieldTotal;

  if (shieldTotal > 0 && prev <= 0) {
    entry.phase = 'spawn';
    entry.startTime = now;
  } else if (shieldTotal <= 0 && prev > 0) {
    entry.phase = 'break';
    entry.startTime = now;
  }

  const elapsed = now - entry.startTime;

  if (entry.phase === 'spawn') {
    const t = Math.min(1, elapsed / SPAWN_MS);
    const ease = 1 - (1 - t) * (1 - t);
    const scale = 0.4 + 0.6 * ease;
    const alpha = ease * 0.45 * alphaMultiplier;
    drawRing(ctx, cx, cy, alpha, scale, 3);
    if (t >= 1) entry.phase = 'active';
  } else if (entry.phase === 'active' && shieldTotal > 0) {
    drawRing(ctx, cx, cy, 0.35 * alphaMultiplier, 1, 2.5);
  }
}

// Draws lingering break animations; call once per frame after all entities.
export function advanceShieldBreakFx(ctx, fxRef) {
  const state = fxRef.current;
  const now = performance.now();
  for (const [id, entry] of state) {
    if (entry.phase !== 'break') {
      if (entry.phase === 'idle' || entry.phase === 'active') {
        if (entry.prevShield <= 0) state.delete(id);
      }
      continue;
    }
    const elapsed = now - entry.startTime;
    const t = Math.min(1, elapsed / BREAK_MS);
    const expandScale = 1 + t * 0.6;
    const ringAlpha = (1 - t) * 0.5;
    drawRing(ctx, entry.cx, entry.cy, ringAlpha, expandScale, 2.5);
    drawShards(ctx, entry.cx, entry.cy, t);
    if (t >= 1) {
      entry.phase = 'idle';
      if (entry.prevShield <= 0) state.delete(id);
    }
  }
}

// Legacy single-shot spawn (kept for callers that only want the flash).
export function spawnShieldHalo(fxRef, cx, cy, entityId) {
  const state = fxRef.current instanceof Map ? fxRef.current : null;
  if (!state) return;
  let entry = state.get(entityId);
  if (!entry) {
    entry = { phase: 'spawn', startTime: performance.now(), cx, cy, prevShield: 0 };
    state.set(entityId, entry);
  } else {
    entry.phase = 'spawn';
    entry.startTime = performance.now();
    entry.cx = cx;
    entry.cy = cy;
  }
}
