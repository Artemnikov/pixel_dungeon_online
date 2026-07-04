// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// SpellSprite overlay — mirrors SPD's SpellSprite.show(char, index).
// A 16×16 icon from spell_icons.png fades in above the character, holds, then fades out.
//
// Timeline matches SPD: fade-in 200 ms → static 800 ms → fade-out 400 ms = 1400 ms total.
// Drawn at 2× scale (32×32) centered one tile above the character's center.
//
// Entry shape: { cx, cy, index, startTime }

import { TILE_SIZE } from '../../constants';

const SPELL_SIZE = 16; // source px per icon cell
const FADE_IN_MS  = 200;
const STATIC_MS   = 800;
const FADE_OUT_MS = 400;
const TOTAL_MS = FADE_IN_MS + STATIC_MS + FADE_OUT_MS;

// Icon indices matching SpellSprite.java constants.
export const SPELL_MAP    = 1;
export const SPELL_CHARGE = 2;

export function spawnSpellSprite(spellSpriteRef, cx, cy, index) {
  spellSpriteRef.current.push({ cx, cy, index, startTime: performance.now() });
}

export function advanceAndDrawSpellSprites(ctx, { spellSpriteRef, assetImages }) {
  if (!spellSpriteRef?.current?.length) return;
  const img = assetImages?.spellIcons;
  if (!img) return;

  const now = performance.now();
  const entries = spellSpriteRef.current;

  for (let i = entries.length - 1; i >= 0; i--) {
    const e = entries[i];
    const elapsed = now - e.startTime;
    if (elapsed >= TOTAL_MS) {
      entries.splice(i, 1);
      continue;
    }

    let alpha;
    if (elapsed < FADE_IN_MS) {
      alpha = elapsed / FADE_IN_MS;
    } else if (elapsed < FADE_IN_MS + STATIC_MS) {
      alpha = 1;
    } else {
      alpha = 1 - (elapsed - FADE_IN_MS - STATIC_MS) / FADE_OUT_MS;
    }

    const dw = SPELL_SIZE * 2;
    const dh = SPELL_SIZE * 2;
    const dx = e.cx - dw / 2;
    const dy = e.cy - TILE_SIZE - dh;

    ctx.save();
    ctx.globalAlpha = Math.max(0, Math.min(1, alpha));
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(img, e.index * SPELL_SIZE, 0, SPELL_SIZE, SPELL_SIZE, dx, dy, dw, dh);
    ctx.restore();
  }
}
