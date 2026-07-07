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
// SPD parity helpers for last-target lock-on and auto-aim (QuickSlotButton
// lastTarget / autoAim). Pure logic (no React, no canvas) so it is unit-tested
// with node:test. The server does the real entity->cell + ballistica resolution;
// these only choose *which* mob to lock and its current cell.

const rc = (v) => Math.round(v);

export function resolveTargetCrosshairCell(selectedEnemyId, mobs, visibleSet) {
  if (!selectedEnemyId) return null;
  const mob = mobs?.[selectedEnemyId];
  if (!mob || !(mob.hp > 0)) return null;
  const x = rc(mob.renderPos.x), y = rc(mob.renderPos.y);
  if (!visibleSet.has(`${x},${y}`)) return null;
  return { x, y };
}

export function pickAutoAimTarget(selectedEnemyId, mobs, visibleSet, playerPos, range) {
  const inRange = (mob) => {
    const x = rc(mob.renderPos.x), y = rc(mob.renderPos.y);
    if (!(mob.hp > 0) || !visibleSet.has(`${x},${y}`)) return null;
    const dx = mob.renderPos.x - playerPos.x, dy = mob.renderPos.y - playerPos.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    return dist <= range ? { x, y, dist } : null;
  };

  const locked = selectedEnemyId ? mobs?.[selectedEnemyId] : null;
  if (locked) {
    const hit = inRange(locked);
    if (hit) return { id: selectedEnemyId, x: hit.x, y: hit.y };
  }

  let best = null, bestDist = Infinity;
  for (const [id, mob] of Object.entries(mobs || {})) {
    const hit = inRange(mob);
    if (hit && hit.dist < bestDist) { bestDist = hit.dist; best = { id, x: hit.x, y: hit.y }; }
  }
  return best;
}
