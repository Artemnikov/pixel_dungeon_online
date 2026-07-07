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
// Tooltip text for a canvas quickslot: item name + its digit hotkey. Pure logic
// so it is unit-tested; the Toolbar renders it as a positioned DOM overlay.
export function slotTooltipText(item, slotIndex) {
  if (!item) return null;
  const name = item.name || item.kind || '';
  return `${name}  [${slotIndex + 1}]`;
}
