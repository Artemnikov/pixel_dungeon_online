// Client-side effects for the Yog-Dzewa fight (and the Ripper Demon leap),
// ported from SPD's effects/sprites. Module-level state like tenguEffects.js:
// event handlers push entries, the renderer draws/advances them each frame.

import { TILE_SIZE } from '../constants';
import { spawnLeaf, spawnShadowMissileParticle, spawnCorrosionSplash } from './draw/particles';
import { spawnFlame } from './draw/flameParticle';
import { spawnSparkStatic } from './draw/sparkParticle';
import { spawnToxicGas } from './draw/gasParticle';

// --- TargetedCell (effects/TargetedCell.java) ----------------------------------
// Icons.TARGET hard-lit to a colour, at full alpha/scale, then each frame
// alpha -= elapsed / 2 and scale = alpha: it fades and shrinks over 2 s.
const TARGET_X = 0;
const TARGET_Y = 32;
const TARGET_W = 16;
const TARGET_H = 16;

export const targetedCells = [];

export function addTargetedCells(cells, color = 0xff0000, durationMs = 2000, now = performance.now()) {
  for (const [x, y] of cells || []) {
    targetedCells.push({ x, y, color, start: now, durationMs });
  }
}

export function targetedCellAlpha(entry, now) {
  return Math.max(0, 1 - (now - entry.start) / entry.durationMs);
}

const tintCache = new Map();

function tintedTarget(iconsImage, color) {
  if (!iconsImage || typeof document === 'undefined') return null;
  const key = color;
  if (tintCache.has(key)) return tintCache.get(key);
  const c = document.createElement('canvas');
  c.width = TARGET_W;
  c.height = TARGET_H;
  const g = c.getContext('2d');
  g.imageSmoothingEnabled = false;
  g.drawImage(iconsImage, TARGET_X, TARGET_Y, TARGET_W, TARGET_H, 0, 0, TARGET_W, TARGET_H);
  g.globalCompositeOperation = 'source-in';
  g.fillStyle = `#${color.toString(16).padStart(6, '0')}`;
  g.fillRect(0, 0, TARGET_W, TARGET_H);
  tintCache.set(key, c);
  return c;
}

export function drawTargetedCells(ctx, { assetImages, visionRef }) {
  if (!targetedCells.length) return;
  const now = performance.now();
  const visible = visionRef?.current?.visible;
  ctx.save();
  for (let i = targetedCells.length - 1; i >= 0; i--) {
    const e = targetedCells[i];
    const a = targetedCellAlpha(e, now);
    if (a <= 0) {
      targetedCells.splice(i, 1);
      continue;
    }
    if (visible && !visible.has(`${e.x},${e.y}`)) continue;
    const icon = tintedTarget(assetImages?.icons, e.color);
    const scale = 2 * a;
    const dw = TARGET_W * scale;
    const dh = TARGET_H * scale;
    const cx = e.x * TILE_SIZE + TILE_SIZE / 2;
    const cy = e.y * TILE_SIZE + TILE_SIZE / 2;
    ctx.globalAlpha = a;
    if (icon) {
      ctx.drawImage(icon, cx - dw / 2, cy - dh / 2, dw, dh);
    } else {
      ctx.strokeStyle = `#${e.color.toString(16).padStart(6, '0')}`;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(cx, cy, dw / 2.6, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
  ctx.restore();
}

// --- jumps and pushes (CharSprite.jump / effects/Pushing) ----------------------
// A jump arcs `height` px above the straight line over `durationMs`; a push
// slides with SPD Pushing's deceleration over 0.15 s.
export const mobMotions = new Map();

export const PUSH_DURATION_MS = 150;

export function startMobJump(mobId, from, to, now = performance.now()) {
  const dist = Math.max(1, Math.hypot(to.x - from.x, to.y - from.y));
  mobMotions.set(mobId, {
    kind: 'jump', from, to, start: now, durationMs: dist * 100, height: dist * 2 * 2,
  });
}

export function startMobPush(mobId, from, to, now = performance.now(), delayMs = 0) {
  mobMotions.set(mobId, { kind: 'push', from, to, start: now + delayMs, durationMs: PUSH_DURATION_MS, height: 0 });
}

export function motionPosition(m, now) {
  const t = Math.max(0, Math.min(1, (now - m.start) / m.durationMs));
  const k = m.kind === 'push' ? 1 - (1 - t) * (1 - t) : t;
  return {
    x: m.from.x + (m.to.x - m.from.x) * k,
    y: m.from.y + (m.to.y - m.from.y) * k,
    lift: m.kind === 'jump' ? 4 * m.height * t * (1 - t) : 0,
    done: t >= 1,
  };
}

/** Overrides render positions of mobs mid jump/push; returns nothing. */
export function applyMobMotions(mobs, now = performance.now()) {
  for (const [id, m] of mobMotions) {
    const mob = mobs[id];
    if (!mob) {
      mobMotions.delete(id);
      continue;
    }
    const p = motionPosition(m, now);
    if (now < m.start) {
      mob.renderPos = { x: m.from.x, y: m.from.y };
      mob.jumpLift = 0;
      continue;
    }
    mob.renderPos = { x: p.x, y: p.y };
    mob.jumpLift = p.lift;
    if (p.done) {
      mob.jumpLift = 0;
      mob.animStartPos = { x: m.to.x, y: m.to.y };
      mob.targetPos = { x: m.to.x, y: m.to.y };
      mob.animStartTime = null;
      mobMotions.delete(id);
    }
  }
}

// --- fist ambient emitters (sprites/FistSprite.java createEmitter) -------------
// pour(factory, interval): one particle every `interval` seconds while visible.
export const FIST_EMITTERS = {
  'Burning Fist': { interval: 0.06, spawn: (ref, x, y) => spawnFlame(ref, x, y, 1) },
  'Soiled Fist': { interval: 0.06, spawn: (ref, x, y) => spawnLeaf(ref, x, y, 1) },
  'Rotting Fist': { interval: 0.25, spawn: (ref, x, y) => spawnToxicGas(ref, x, y) },
  'Rusted Fist': { interval: 0.06, spawn: (ref, x, y) => spawnCorrosionSplash(ref, x, y, 1) },
  'Bright Fist': { interval: 0.06, spawn: (ref, x, y) => spawnSparkStatic(ref, x, y, 1) },
  'Dark Fist': { interval: 0.06, spawn: (ref, x, y) => spawnShadowMissileParticle(ref, x, y) },
};

const emitterClock = new Map();

export function pourFistEmitter(mob, particlesRef, now = performance.now()) {
  const def = FIST_EMITTERS[mob.name];
  if (!def || !particlesRef) return 0;
  const last = emitterClock.get(mob.id) ?? now;
  let owed = (now - last) / 1000;
  let n = 0;
  while (owed >= def.interval && n < 8) {
    owed -= def.interval;
    const x = (mob.renderPos.x + 0.5) * TILE_SIZE + (Math.random() - 0.5) * TILE_SIZE * 0.9;
    const y = (mob.renderPos.y + 0.5) * TILE_SIZE + (Math.random() - 0.5) * TILE_SIZE * 0.7 - (mob.jumpLift || 0);
    def.spawn(particlesRef, x, y);
    n++;
  }
  emitterClock.set(mob.id, now - owed * 1000);
  return n;
}

export function forgetFistEmitter(id) {
  emitterClock.delete(id);
}

// --- timed cell emitters (CellEmitter.start(factory, interval, quantity)) -------
export const cellEmitters = [];

export function startCellEmitter(x, y, kind, interval, quantity, now = performance.now()) {
  cellEmitters.push({ x, y, kind, interval: interval * 1000, left: quantity, next: now });
}

const CELL_FACTORIES = {
  flame: (ref, cx, cy) => spawnFlame(ref, cx, cy, 1),
};

export function tickCellEmitters(particlesRef, now = performance.now()) {
  if (!particlesRef) return;
  for (let i = cellEmitters.length - 1; i >= 0; i--) {
    const e = cellEmitters[i];
    while (e.left > 0 && now >= e.next) {
      const factory = CELL_FACTORIES[e.kind];
      if (factory) {
        factory(particlesRef, e.x * TILE_SIZE + Math.random() * TILE_SIZE, e.y * TILE_SIZE + Math.random() * TILE_SIZE);
      }
      e.left -= 1;
      e.next += e.interval;
    }
    if (e.left <= 0) cellEmitters.splice(i, 1);
  }
}

// --- screen flash (PixelScene.Fader) ----------------------------------------------
/** Parse SPD's ARGB int/hex ("0x80FFFFFF") into {r, g, b, a}. */
export function parseArgb(color) {
  if (color == null) return { r: 255, g: 255, b: 255, a: 0.5 };
  const n = typeof color === 'number' ? color : parseInt(String(color).replace(/^0x/i, ''), 16);
  if (Number.isNaN(n)) return { r: 255, g: 255, b: 255, a: 0.5 };
  const v = n >>> 0;
  const hasAlpha = typeof color === 'string' ? String(color).replace(/^0x/i, '').length > 6 : v > 0xffffff;
  const a = hasAlpha ? ((v >>> 24) & 0xff) / 255 : 1;
  return { r: (v >>> 16) & 0xff, g: (v >>> 8) & 0xff, b: v & 0xff, a: a || 1 };
}
