export function getPopupPos(anchor, width, fallbackBottom = 50) {
  if (typeof window === 'undefined') return { left: 8, bottom: fallbackBottom };
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const w = Math.min(width, vw - 16);
  if (anchor && typeof anchor.x === 'number') {
    const slotCenterX = anchor.x + (anchor.w || 0) / 2;
    return {
      left: Math.max(8, Math.min(vw - w - 8, slotCenterX - w / 2)),
      bottom: Math.max(8, vh - anchor.y + 6),
    };
  }
  return {
    left: Math.max(8, (vw - w) / 2),
    bottom: fallbackBottom,
  };
}

export function getSpellLabel(t, spell) {
  return t(`spells.${spell.id}.name`, { defaultValue: spell.label });
}

export function getSpellTitle(t, spell, cd) {
  const label = getSpellLabel(t, spell);
  if (cd > 0) {
    return t('combat.spellCooldown', {
      defaultValue: `${label} (${Math.ceil(cd)}s)`,
      spell: label,
      secs: Math.ceil(cd),
    });
  }
  return label;
}