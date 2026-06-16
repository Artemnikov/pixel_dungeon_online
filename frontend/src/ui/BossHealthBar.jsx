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
// Top-of-screen boss HP bar, shown while a boss (e.g. Goo) is alive on the floor.
// Mirrors the original SPD's BossHealthBar HUD element.
export default function BossHealthBar({ boss }) {
  if (!boss) return null;
  const hp = Math.max(0, boss.hp || 0);
  const maxHp = Math.max(1, boss.maxHp || 1);
  const shield = boss.shield || 0;
  const hpPct = Math.min(1, hp / maxHp);
  const shieldPct = Math.min(1, (hp + shield) / maxHp);
  const effects = boss.effects || [];

  return (
    <div className="boss-health-bar">
      <div className="boss-health-bar__box">
        <div className="boss-health-bar__name">{boss.name}</div>
        <div className="boss-health-bar__track">
          <div className="boss-health-bar__bg" style={{ width: '100%' }} />
          {shieldPct > 0 && shieldPct > hpPct && (
            <div className="boss-health-bar__shield" style={{ width: `${shieldPct * 100}%` }} />
          )}
          <div className="boss-health-bar__fill" style={{ width: `${hpPct * 100}%` }} />
        </div>
        <div className="boss-health-bar__hp-text">
          {hp}{shield > 0 ? `+${shield}` : ''}/{maxHp}
        </div>
        {effects.length > 0 && (
          <div className="boss-health-bar__buffs">
            {effects.slice(0, 6).map((eff, i) => (
              <span key={i} className="boss-health-bar__buff" title={eff.name || ''}>
                {eff.icon != null ? `[${eff.icon}]` : '?'}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
