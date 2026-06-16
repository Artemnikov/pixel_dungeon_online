// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenheim
//
// TargetedCell: crosshair reticle on the hovered cell during targeting mode.
// Port of SPD's TargetedCell.java. Draws Icons.TARGET (icons.png 0,32,16,16)
// at the cell under the cursor with a pulsing alpha.

import { TILE_SIZE } from '../../constants';

// Icons.TARGET in icons.png (Icons.java): uvRect(0, 32, 16, 16).
const TARGET_X = 0;
const TARGET_Y = 32;
const TARGET_W = 16;
const TARGET_H = 16;

export function drawTargetedCell(ctx, { hoveredCellRef, assetImages }) {
  const cell = hoveredCellRef?.current;
  if (!cell || !assetImages.icons) return;

  const pulse = 0.4 + 0.6 * (Math.sin(performance.now() * 0.004) * 0.5 + 0.5);

  const cx = cell.x * TILE_SIZE + TILE_SIZE / 2;
  const cy = cell.y * TILE_SIZE + TILE_SIZE / 2;

  ctx.save();
  ctx.globalAlpha = pulse;
  ctx.imageSmoothingEnabled = false;

  const scale = 2;
  const dw = TARGET_W * scale;
  const dh = TARGET_H * scale;
  ctx.drawImage(assetImages.icons,
    TARGET_X, TARGET_Y, TARGET_W, TARGET_H,
    cx - dw / 2, cy - dh / 2, dw, dh);

  ctx.restore();
}
