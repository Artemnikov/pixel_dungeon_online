// Helpers deciding when the in-game "Select target" prompt is shown, and
// whether it should mention double-click auto-aim from the quickbar.

// Does the item support double-click auto-aim toward the closest enemy?
// Shared with handleToolbarDoubleClick (ToolbarDoubleClickDispatcher) so the
// hint and the actual auto-aim gate can never drift apart.
export function canAutoAim(item) {
  if (!item) return false;
  return item.type === 'wand'
    || item.kind === 'staff'
    || item.type === 'throwable'
    || item.throw_behavior === 'missile'
    || (item.type === 'weapon' && item.range && item.range > 1);
}

// Actions that fire a projectile/missile at a chosen tile and thus support
// double-click auto-aim at the closest visible enemy (QuickSlotButton.autoAim).
const AUTO_AIM_ACTIONS = ['THROW', 'ZAP', 'DIRECT', 'SHOOT'];

// Any armed target-selection mode: throwables, wands, staffs, ranged weapons
// (string mode), aimed abilities, combo moves, duelist finisher, cleric spells,
// seeds, unlock/steal, etc.
export function isTargetSelection(tm) {
  return !!tm;
}

// Should the "double click for closest enemy" hint be shown for the currently
// armed mode? Only for modes armed from a quickbar click whose item can
// actually auto-aim. String mode (ranged weapons like the Bow) is only ever
// armed from a quickbar click, so it counts as from-quickbar. Duelist
// finishers auto-aim from any equipped weapon.
export function canAutoAimFromQuickbar(tm, itemsById) {
  if (!tm) return false;
  if (typeof tm === 'string') return canAutoAim(itemsById?.[tm]);
  if (typeof tm !== 'object') return false;
  if (!tm.fromQuickbar) return false;
  if (tm.duelistFinisher) {
    return !!tm.itemId && itemsById?.[tm.itemId]?.type === 'weapon';
  }
  if (typeof tm.action === 'string' && AUTO_AIM_ACTIONS.includes(tm.action)) {
    return !!tm.itemId && canAutoAim(itemsById?.[tm.itemId]);
  }
  return false;
}