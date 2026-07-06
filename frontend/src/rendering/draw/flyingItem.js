// SPDX-License-Identifier: GPL-3.0-or-later
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// Flying item pickup animation — mirrors SPD's Toolbar.PickedUpItem.
// Items fly from their floor tile to the inventory button (bottom-right).

import { TILE_SIZE, ENTITY_LIFT } from '../../constants';
import { getItemSpriteCoords } from '../sprites';
import { itemRects } from '../spriteRects';
import { centeredItemCrop } from '../itemCrop';

export const FLY_DURATION = 500;

export function spawnFlyingItem(flyingItemsRef, itemName, itemType, tileX, tileY) {
  const coords = getItemSpriteCoords(itemName, itemType);
  if (!coords) return;
  flyingItemsRef.current.push({
    coords,
    tileX,
    tileY,
    startTime: performance.now(),
  });
}

export function advanceAndDrawFlyingItems(ctx, canvas, { flyingItemsRef, cameraLerpRef, zoomRef, assetImage }) {
  if (!flyingItemsRef?.current?.length) return;
  if (!assetImage) return;
  const now = performance.now();
  const entries = flyingItemsRef.current;

  const rect = canvas.getBoundingClientRect();
  const lw = rect.width;
  const lh = rect.height;
  const cw = canvas.width;
  const ch = canvas.height;
  const camX = cameraLerpRef.current.x;
  const camY = cameraLerpRef.current.y;
  const z = zoomRef.current;

  // Target: inventory button area (bottom-right)
  const endCSS_X = lw - 40;
  const endCSS_Y = lh - 100;

  const cell = 16;

  for (let i = entries.length - 1; i >= 0; i--) {
    const e = entries[i];
    const elapsed = now - e.startTime;
    if (elapsed >= FLY_DURATION) {
      entries.splice(i, 1);
      continue;
    }

    // SPD: p = left / DURATION, goes 1->0
    const p = 1 - elapsed / FLY_DURATION;

    // Start: world tile center → CSS layout coords (matching camera transform)
    const wx = e.tileX * TILE_SIZE + TILE_SIZE / 2;
    const wy = e.tileY * TILE_SIZE + TILE_SIZE / 2 - ENTITY_LIFT;
    const startCSS_X = (wx - camX - lw / 2) * z + lw / 2;
    const startCSS_Y = (wy - camY - lh / 2) * z + lh / 2;

    // Linear interpolation in CSS space (SPD: x = startX * p + endX * (1-p))
    const cssX = startCSS_X * p + endCSS_X * (1 - p);
    const cssY = startCSS_Y * p + endCSS_Y * (1 - p);

    // Convert CSS → canvas pixel space
    const px = cssX * (cw / lw);
    const py = cssY * (ch / lh);

    // Scale shrinks via sqrt(p) (SPD: scale.set(startScale * sqrt(p)))
    const scale = Math.sqrt(p);

    const [col, row] = e.coords;
    const sprRect = itemRects.get(col, row);
    const { sx, sy, sw, sh } = centeredItemCrop(sprRect, TILE_SIZE, cell);

    const sc = cw / lw;
    const dw = sw * scale * sc;
    const dh = sh * scale * sc;

    ctx.save();
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(
      assetImage,
      col * cell + sx,
      row * cell + sy,
      sw, sh,
      px - dw / 2, py - dh / 2,
      dw, dh,
    );
    ctx.restore();
  }
}
