// SPD item comparison: side-by-side stats for inspected vs equipped gear.
// Ported from SPD's WndInfoItem / item info() text.

const wTypes = ['weapon', 'melee_weapon', 'staff', 'missile_weapon'];

export function comparisonLines(item, equippedItem, t) {
  if (!item || !equippedItem) return null;

  const isWeapon = wTypes.includes(item.type) || wTypes.includes(item.kind);
  const isEquipWeapon = wTypes.includes(equippedItem.type) || wTypes.includes(equippedItem.kind);

  if (isWeapon && isEquipWeapon) {
    return weaponComparison(item, equippedItem, t);
  }

  const isArmor = item.type === 'wearable' || item.kind === 'armor';
  const isEquipArmor = equippedItem.type === 'wearable' || equippedItem.kind === 'armor';
  if (isArmor && isEquipArmor) {
    return armorComparison(item, equippedItem, t);
  }

  return null;
}

function weaponComparison(item, equipped, t) {
  const itemLvl = item.level_known ? (item.level || 0) : 0;
  const eqLvl = equipped.level_known ? (equipped.level || 0) : 0;

  const rows = [];

  if (item.tier != null && equipped.tier != null) {
    rows.push({
      label: t('ui.tier'),
      itemVal: `${item.tier}`,
      eqVal: `${equipped.tier}`,
    });
  }

  const itemDmg = itemDmgStr(item, itemLvl, t);
  const eqDmg = itemDmgStr(equipped, eqLvl, t);
  if (itemDmg && eqDmg) {
    rows.push({ label: t('ui.damageStat'), itemVal: itemDmg, eqVal: eqDmg });
  }

  if (item.strength_requirement != null && equipped.strength_requirement != null) {
    rows.push({
      label: t('ui.strengthReq'),
      itemVal: `${item.strength_requirement}`,
      eqVal: `${equipped.strength_requirement}`,
    });
  }

  return rows.length > 0 ? rows : null;
}

function armorComparison(item, equipped, t) {
  const itemLvl = item.level_known ? Math.max(0, item.level || 0) : 0;
  const eqLvl = equipped.level_known ? Math.max(0, equipped.level || 0) : 0;

  const rows = [];

  if (item.tier != null && equipped.tier != null) {
    rows.push({
      label: t('ui.tier'),
      itemVal: `${item.tier}`,
      eqVal: `${equipped.tier}`,
    });
  }

  const itemDR = `${itemLvl}-${item.tier * (2 + itemLvl)}`;
  const eqDR = `${eqLvl}-${equipped.tier * (2 + eqLvl)}`;
  rows.push({
    label: t('ui.defenseStat'),
    itemVal: itemDR,
    eqVal: eqDR,
  });

  if (item.strength_requirement != null && equipped.strength_requirement != null) {
    rows.push({
      label: t('ui.strengthReq'),
      itemVal: `${item.strength_requirement}`,
      eqVal: `${equipped.strength_requirement}`,
    });
  }

  return rows.length > 0 ? rows : null;
}

function itemDmgStr(item, lvl) {
  if (item.damage != null) return `${item.damage}`;

  if (item.type === 'weapon' || item.kind === 'melee_weapon') {
    if (item.dmg_min != null && item.dmg_max != null) {
      return `${item.dmg_min}-${item.dmg_max}`;
    }
    if (item.tier != null) {
      const min = item.tier + lvl;
      let max = item.dmg_max;
      if (max == null) {
        max = 5 * (item.tier + 1) + lvl * (item.tier + 1);
      }
      return `${min}-${max}`;
    }
  }
  return null;
}
