// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
// See the GNU General Public License for more details.
//
import { TILE_SIZE } from '../../constants';
import { resolveTargetCrosshairCell } from '../../game/autoAim';

// Icons.TARGET in icons.png (Icons.java): uvRect(0, 32, 16, 16).
const TARGET_X = 0, TARGET_Y = 32, TARGET_W = 16, TARGET_H = 16;

// SPD InventoryPane.crossM: a steady crosshair locked on the remembered target
// mob while a targeting action is armed. Distinct from targetedCell.js, which
// tracks the cursor cell; this one is non-pulsing so the two reticles read
// differently.
export function drawLastTargetCrosshair(ctx, { targetingModeRef, selectedEnemyIdRef, entitiesRef, visionRef, assetImages }) {
  if (!targetingModeRef?.current || !assetImages.icons) return;
  const cell = resolveTargetCrosshairCell(
    selectedEnemyIdRef?.current,
    entitiesRef.current.mobs,
    visionRef.current.visible,
  );
  if (!cell) return;

  const cx = cell.x * TILE_SIZE + TILE_SIZE / 2;
  const cy = cell.y * TILE_SIZE + TILE_SIZE / 2;
  const scale = 2, dw = TARGET_W * scale, dh = TARGET_H * scale;

  ctx.save();
  ctx.globalAlpha = 0.9;
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(assetImages.icons, TARGET_X, TARGET_Y, TARGET_W, TARGET_H,
    cx - dw / 2, cy - dh / 2, dw, dh);
  ctx.restore();
}
