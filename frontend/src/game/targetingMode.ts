// Shared targeting-mode shape + predicates used by the toolbar click/double-click
// dispatchers and the targeting tap dispatcher.

export interface ObjectTargetingMode {
  ability?: string;
  comboMove?: string;
  prepStrike?: boolean;
  duelistFinisher?: boolean;
  useSecondary?: boolean;
  clericSpell?: string;
  action?: string;
  itemId?: string;
  fromQuickbar?: boolean;
}

export type TargetingMode = false | string | ObjectTargetingMode;

/** True for any armed object-targeting mode (throwables, wands, abilities, ...). */
export function isObjectTargetingMode(tm: unknown): tm is ObjectTargetingMode {
  return Boolean(tm) && typeof tm === 'object';
}

/**
 * Is the currently armed targeting mode pointed at this item via `itemId`?
 * Covers the repeated "disarm if you click the item you're aiming with" toggle
 * that used to be copy-pasted across every toolbar item branch.
 */
export function isTargetingArmedForItem(targetingMode: unknown, itemId: string | undefined): boolean {
  return isObjectTargetingMode(targetingMode) && targetingMode.itemId === itemId;
}

/** Armed duelist-finisher mode for a specific equipped weapon. */
export function isDuelistFinisherArmed(targetingMode: unknown, itemId: string | undefined): boolean {
  return isObjectTargetingMode(targetingMode)
    && targetingMode.duelistFinisher === true
    && targetingMode.itemId === itemId;
}