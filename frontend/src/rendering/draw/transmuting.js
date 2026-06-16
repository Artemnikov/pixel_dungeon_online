// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// Transmuting VFX — mirrors SPD's Transmuting.show(): old item sprite cross-dissolves
// into the new item sprite above the reader over ~2 seconds.
//
// Each entry: { x, y, oldCoords, newCoords, startTime }
// Coordinates are world pixels (tile * TILE_SIZE). Rendered inside the camera transform.

import { TILE_SIZE, TILE_SCALE } from '../../constants';

const TOTAL_MS   = 2000;
const FADE_IN_MS =  200;  // phase 1: old item fades in
const HOLD_MS    = 1400;  // phase 2: cross-dissolve old → new
const FADE_OUT_MS =  400; // phase 3: new item fades out

const SPRITE_SRC_SIZE = TILE_SIZE / TILE_SCALE; // source cell size in items.png

export function drawTransmuting(ctx, { transmuteEffectsRef, assetImages }) {
  if (!transmuteEffectsRef?.current?.length) return;
  const img = assetImages?.items;
  if (!img) return;

  const now = performance.now();
  const entries = transmuteEffectsRef.current;

  for (let i = entries.length - 1; i >= 0; i--) {
    const e = entries[i];
    const elapsed = now - e.startTime;
    if (elapsed >= TOTAL_MS) {
      entries.splice(i, 1);
      continue;
    }

    // Position: one tile above the reader's center
    const dx = e.x - TILE_SIZE / 2;
    const dy = e.y - TILE_SIZE;

    ctx.save();
    ctx.imageSmoothingEnabled = false;

    if (elapsed < FADE_IN_MS) {
      // Phase 1: old item fades in
      const alpha = (elapsed / FADE_IN_MS) * 0.8;
      ctx.globalAlpha = alpha;
      drawItemSprite(ctx, img, e.oldCoords, dx, dy);
    } else if (elapsed < FADE_IN_MS + HOLD_MS) {
      // Phase 2: old fades out, new fades in
      const t = (elapsed - FADE_IN_MS) / HOLD_MS;
      ctx.globalAlpha = (1 - t) * 0.8;
      drawItemSprite(ctx, img, e.oldCoords, dx, dy);
      ctx.globalAlpha = t * 0.8;
      drawItemSprite(ctx, img, e.newCoords, dx, dy);
    } else {
      // Phase 3: new item fades out
      const t = (elapsed - FADE_IN_MS - HOLD_MS) / FADE_OUT_MS;
      ctx.globalAlpha = (1 - t) * 0.8;
      drawItemSprite(ctx, img, e.newCoords, dx, dy);
    }

    ctx.restore();
  }
}

function drawItemSprite(ctx, img, coords, dx, dy) {
  const [col, row] = coords;
  ctx.drawImage(
    img,
    col * SPRITE_SRC_SIZE, row * SPRITE_SRC_SIZE, SPRITE_SRC_SIZE, SPRITE_SRC_SIZE,
    dx, dy, TILE_SIZE, TILE_SIZE,
  );
}
