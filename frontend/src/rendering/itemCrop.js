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

// SPD anchors each item's art to the top-left of its atlas cell, spanning a
// smaller rect than the full cell (e.g. a key sprite is 8x14 in a 16x16 cell).
// Given that measured rect (or null, before/without measurement), returns the
// source crop and the destination size+offset needed to centre it within a
// `destBoxPx`-sized square, so callers don't have to skew art toward the
// top-left of whatever box they're drawing into.
export function centeredItemCrop(rect, destBoxPx, srcCellPx = 16) {
  const scale = destBoxPx / srcCellPx;
  const sx = rect ? rect.rx : 0;
  const sy = rect ? rect.ry : 0;
  const sw = rect ? rect.w : srcCellPx;
  const sh = rect ? rect.h : srcCellPx;
  const dw = sw * scale;
  const dh = sh * scale;
  return { sx, sy, sw, sh, dw, dh, offsetX: (destBoxPx - dw) / 2, offsetY: (destBoxPx - dh) / 2 };
}
