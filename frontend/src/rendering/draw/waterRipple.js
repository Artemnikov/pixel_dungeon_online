import { TILE_SIZE } from '../../constants.js';
import { EFFECTS } from './effectsAtlas.js';

// Port of effects/Ripple.java: a single fading, expanding ring drawn where a
// character just stepped in/through water. TIME_TO_FADE = 0.5f in the
// original; Ripple.update() ties p = time/TIME_TO_FADE (time counts down
// from TIME_TO_FADE to 0), scale = 1-p, alpha = p. Rewritten here in terms
// of age counting up from 0: scale = age/lifespan, alpha = 1 - age/lifespan.
const LIFESPAN = 0.5;

const activeRipples = [];
let lastNow = null;

export function spawnWaterRipple(x, y) {
  activeRipples.push({ x, y, age: 0 });
}

export function rippleVisualState(age, lifespan = LIFESPAN) {
  const t = Math.min(Math.max(age / lifespan, 0), 1);
  return { scale: t, alpha: 1 - t };
}

export function advanceAndDrawWaterRipples(ctx, { assetImages }) {
  const now = performance.now();
  const dt = lastNow == null ? 0 : Math.min((now - lastNow) / 1000, 0.05);
  lastNow = now;

  if (!activeRipples.length) return;

  const effectsImg = assetImages?.effects;
  const rect = EFFECTS.RIPPLE;

  for (let i = activeRipples.length - 1; i >= 0; i--) {
    const r = activeRipples[i];
    r.age += dt;
    if (r.age >= LIFESPAN) {
      activeRipples.splice(i, 1);
      continue;
    }
    if (!effectsImg) continue;

    const { scale, alpha } = rippleVisualState(r.age, LIFESPAN);
    const size = TILE_SIZE * scale;
    if (size <= 0) continue;

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.drawImage(
      effectsImg, rect.x, rect.y, rect.w, rect.h,
      r.x - size / 2, r.y - size / 2, size, size,
    );
    ctx.restore();
  }
}
