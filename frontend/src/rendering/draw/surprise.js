// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// Surprise.java: exclamation mark displayed on surprise attacks.
// Draws Effects.Type.EXCLAMATION (effects.png 0,16,6,9) at target position.
// 800ms lifecycle: fade-in 100ms, hold, fade-out 200ms, scale 1→1.5.

const LIFESPAN = 800;
const EXCL_X = 0;
const EXCL_Y = 16;
const EXCL_W = 6;
const EXCL_H = 9;

let effectsImg = null;
(() => {
  const img = new Image();
  img.onload = () => { effectsImg = img; };
  img.onerror = () => {};
  img.src = new URL('../../assets/pixel-dungeon/effects/effects.png', import.meta.url).href;
})();

export function spawnSurprise(surpriseRef, cx, cy) {
  surpriseRef.current.push({
    x: cx,
    y: cy,
    startTime: performance.now(),
  });
}

export function advanceAndDrawSurprises(ctx, { surpriseRef }) {
  const entries = surpriseRef.current;
  for (let i = entries.length - 1; i >= 0; i--) {
    const e = entries[i];
    const elapsed = now - e.startTime;

    if (elapsed > LIFESPAN) {
      entries.splice(i, 1);
      continue;
    }

    const alpha = elapsed < 100 ? elapsed / 100
      : elapsed > LIFESPAN - 200 ? (LIFESPAN - elapsed) / 200
      : 1;
    const scale = 1 + 0.5 * (elapsed / LIFESPAN);

    if (effectsImg?.complete && effectsImg?.naturalWidth > 0) {
      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.imageSmoothingEnabled = false;

      const dw = EXCL_W * 2 * scale;
      const dh = EXCL_H * 2 * scale;
      ctx.drawImage(effectsImg,
        EXCL_X, EXCL_Y, EXCL_W, EXCL_H,
        e.x - dw / 2, e.y - dh / 2, dw, dh);

      ctx.restore();
    }
  }
}
