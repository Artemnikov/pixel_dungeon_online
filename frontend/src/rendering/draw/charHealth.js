// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenheim
//
// CharHealthIndicator: mini HP bars above all visible mobs where hp < max_hp.
// Port of SPD's CharHealthIndicator.java.
// 2px-tall bar, 4/6 of tile width, centered above each mob sprite.

import { TILE_SIZE } from '../../constants';

const INDICATOR_HEIGHT = 2;
const BAR_WIDTH_FRAC = 4 / 6; // 4/6 of tile width

export function drawCharHealth(ctx, { entitiesRef, visionRef }) {
  const mobs = entitiesRef.current.mobs;
  const visible = visionRef?.current?.visible;

  Object.values(mobs).forEach(mob => {
    if (!mob.is_alive) return;

    const hp = mob.hp || 0;
    const maxHp = mob.max_hp || 1;
    const shield = (mob.shields || []).reduce((sum, s) => sum + (s.amount || 0), 0);

    // Skip if at full health and no shield
    if (hp >= maxHp && shield === 0) return;

    // Check visibility
    const mx = Math.round(mob.renderPos.x);
    const my = Math.round(mob.renderPos.y);
    if (visible && !visible.has(`${mx},${my}`)) return;

    const x = mob.renderPos.x * TILE_SIZE;
    const y = mob.renderPos.y * TILE_SIZE;

    const total = Math.max(hp + shield, maxHp);
    const hpPct = hp / total;
    const shieldPct = (hp + shield) / total;

    const barW = TILE_SIZE * BAR_WIDTH_FRAC;
    const barX = x + (TILE_SIZE - barW) / 2;
    const barY = y - 8;

    // Red background for full bar
    ctx.fillStyle = '#cc0000';
    ctx.fillRect(barX, barY, barW, INDICATOR_HEIGHT);

    // White shield overlay
    if (shieldPct > hpPct) {
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(barX, barY, barW * shieldPct, INDICATOR_HEIGHT);
    }

    // Green HP fill
    ctx.fillStyle = '#00ee00';
    ctx.fillRect(barX, barY, barW * hpPct, INDICATOR_HEIGHT);
  });
}
