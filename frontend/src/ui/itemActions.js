export const ACTION_KEYS = {
  EQUIP: 'action.equip',
  UNEQUIP: 'action.unequip',
  DROP: 'action.drop',
  THROW: 'action.throw',
  DRINK: 'action.drink',
  READ: 'action.read',
  ZAP: 'action.zap',
  IMBUE: 'action.imbue',
  EAT: 'action.eat',
  OPEN: 'action.open',
  AFFIX: 'action.affix',
  STEALTH: 'action.stealth',
  GHOST_GEAR: 'action.ghostGear',
  SUMMON: 'action.summon',
  DIRECT: 'action.direct',
};

export const actionLabel = (a, t) => {
  const key = ACTION_KEYS[a];
  return key ? t(key) : a;
};

export function orderedActions(item) {
  const actions = [...(item.actions || [])];
  const def = item.default_action;
  if (def && actions.includes(def)) {
    return [def, ...actions.filter(a => a !== def)];
  }
  return actions;
}

export function titleColor(item) {
  if (item.level_known && item.level > 0) return '#44ff44';
  if (item.level_known && item.level < 0) return '#ff4444';
  return '#f1c40f';
}
