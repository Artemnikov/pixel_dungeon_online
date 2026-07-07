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
// Item stat lines (tier / damage / STR / defense / charges / curse / glyph) shown
// in the info + use windows. Kept in its own module so the window components can
// export only components (React Fast Refresh boundary).
export function statLines(item, t) {
  const lines = [];
  const wTypes = ['weapon', 'melee_weapon', 'staff', 'missile_weapon'];
  if (wTypes.includes(item.type) || wTypes.includes(item.kind)) {
    if (item.tier != null) lines.push(t('ui.tier', { tier: item.tier }));
    if (item.damage != null) lines.push(`${t('ui.damageStat')}: ${item.damage}`);
    if (item.strength_requirement != null)
      lines.push(t('ui.strengthReq', { str: item.strength_requirement }));
  }
  if (item.type === 'wearable' || item.kind === 'armor') {
    if (item.tier != null) lines.push(t('ui.tier', { tier: item.tier }));
    if (item.strength_requirement != null)
      lines.push(t('ui.strengthReq', { str: item.strength_requirement }));
    const bufLvl = item.level_known ? Math.max(0, item.level || 0) : 0;
    const drMin = bufLvl;
    const drMax = item.tier * (2 + bufLvl);
    lines.push(`${t('ui.defenseStat')}: ${drMin}-${drMax}`);
  }
  if (item.kind === 'ring' || item.type === 'ring') {
    if (item.level_known && item.level != null)
      lines.push(item.level >= 0 ? `+${item.level}` : `${item.level}`);
  }
  if (item.kind === 'artifact' || item.type === 'artifact') {
    if (item.charge != null && item.charge_cap != null)
      lines.push(t('ui.artifactCharge', { charge: item.charge, cap: item.charge_cap }));
  }
  if (item.kind === 'wand' || item.type === 'wand') {
    if (item.charges != null && item.max_charges != null)
      lines.push(t('ui.wandCharges', { charges: item.charges, max: item.max_charges }));
  }
  if (item.cursed_known && item.cursed) lines.push(t('ui.cursed'));
  if (item.cursed_known === false && (wTypes.includes(item.type) || item.type === 'wearable'
      || item.kind === 'ring' || item.kind === 'artifact' || item.kind === 'wand'))
    lines.push(t('ui.cursedUnknown'));
  if (item.enchantment && item.enchantment.type && item.enchantment.type !== 'none') {
    const glyphLabel = item.enchantment.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    lines.push(`Glyph of ${glyphLabel}`);
  }
  return lines;
}
