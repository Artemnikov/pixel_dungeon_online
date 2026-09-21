import { TILE_SIZE } from '../../constants.js';
import { EFFECTS } from './effectsAtlas.js';

// Port of effects/Ripple.java: a single fading, expanding ring drawn where a
// character just stepped in/through water, or where a sewer drain drips.
// TIME_TO_FADE = 0.5f in the original; Ripple.update() ties
// p = time/TIME_TO_FADE (time counts down from TIME_TO_FADE to 0),
// scale = 1-p, alpha = p. Rewritten here in terms of age counting up from 0:
// scale = age/lifespan, alpha = 1 - age/lifespan.
// The original expands its 16px sprite in 0.5s; on the remake's 32px tiles
// that ring would animate 2x too fast (→ 1.0s), and it is slowed a further
// 50% per tuning to read as a calm water splash.
const LIFESPAN = 1.5;

const activeRipples = [];
let lastNow = null;

export function spawnWaterRipple(x, y, options = {}) {
  activeRipples.push({
    x,
    y,
    age: 0,
    clipTop: options.clipTop ?? false,
    fovCell: options.fovCell,
  });
}

// Test accessor — returns the internal array (tests use splice() to unwind
// module-level state between cases).
export const getActiveRipples = () => activeRipples;

export function rippleVisualState(age, lifespan = LIFESPAN) {
  const t = Math.min(Math.max(age / lifespan, 0), 1);
  return { scale: t, alpha: 1 - t };
}

export function advanceAndDrawWaterRipples(ctx, { assetImages, visionRef, now }) {
  const current = now ?? performance.now();
  const dt = lastNow == null ? 0 : Math.min((current - lastNow) / 1000, 0.05);
  lastNow = current;

  if (!activeRipples.length) return;

  const effectsImg = assetImages?.effects;
  const rect = EFFECTS.RIPPLE;
  const visible = visionRef?.current?.visible;

  for (let i = activeRipples.length - 1; i >= 0; i--) {
    const r = activeRipples[i];
    r.age += dt;
    if (r.age >= LIFESPAN) {
      activeRipples.splice(i, 1);
      continue;
    }
    // Ripples keep advancing but are only drawn while their tile is in FOV,
    // so an out-of-LOS ring never renders brighter than the dim environment
    // around it (matching how the remake hides non-visible entities).
    if (r.fovCell && visible && !visible.has(r.fovCell)) continue;
    if (!effectsImg) continue;

    const { scale, alpha } = rippleVisualState(r.age, LIFESPAN);
    const size = TILE_SIZE * scale;
    if (size <= 0) continue;

    ctx.save();
    ctx.globalAlpha = alpha;
    if (r.clipTop) {
      // Drain ripples pivot on the water surface (the water cell's top
      // edge); draw only the bottom half of the sprite so the splash stays
      // on the water instead of spilling over the wall above.
      ctx.drawImage(
        effectsImg, rect.x, rect.y + rect.h / 2, rect.w, rect.h / 2,
        r.x - size / 2, r.y, size, size / 2,
      );
    } else {
      ctx.drawImage(
        effectsImg, rect.x, rect.y, rect.w, rect.h,
        r.x - size / 2, r.y - size / 2, size, size,
      );
    }
    ctx.restore();
  }
}
