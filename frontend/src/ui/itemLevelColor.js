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
// SPD ItemSlot.updateText level tinting, ported to pure logic. `buffed_level`
// (server) differs from `level` only when a temporary modifier is in play (today:
// a Staff with an imbued wand -> ENHANCED). Falls back to `level` when absent, so
// ordinary gear keeps green/red. CURSE_INFUSED/MASTERED are descoped (no backend).

function levels(item) {
  const known = !!item.level_known;
  const trueLvl = known ? (item.level || 0) : 0;
  const buffed = known ? (item.buffed_level ?? item.level ?? 0) : 0;
  return { trueLvl, buffed };
}

export function levelDisplayText(item) {
  if (!item) return null;
  const { trueLvl, buffed } = levels(item);
  if (trueLvl === 0 && buffed === 0) return null;
  return `${buffed > 0 ? '+' : ''}${buffed}`;
}

export function levelColorClass(item) {
  if (!item) return null;
  const { trueLvl, buffed } = levels(item);
  if (trueLvl === 0 && buffed === 0) return null;
  if (buffed > trueLvl) return 'enhanced';
  if (buffed < trueLvl) return 'warning';
  if (buffed < 0) return 'down';
  return 'up';
}
