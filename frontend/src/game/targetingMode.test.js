import test from 'node:test';
import assert from 'node:assert/strict';
import { isObjectTargetingMode, isTargetingArmedForItem, isDuelistFinisherArmed } from './targetingMode.ts';

test('isObjectTargetingMode: only truthy object modes count', () => {
  assert.equal(isObjectTargetingMode({ itemId: 'w1', action: 'THROW' }), true);
  assert.equal(isObjectTargetingMode(false), false);
  assert.equal(isObjectTargetingMode(null), false);
  assert.equal(isObjectTargetingMode(undefined), false);
  assert.equal(isObjectTargetingMode('w1'), false);
});

test('isTargetingArmedForItem: matches the armed itemId only', () => {
  assert.equal(isTargetingArmedForItem({ itemId: 'w1', action: 'ZAP' }, 'w1'), true);
  assert.equal(isTargetingArmedForItem({ itemId: 'w1', action: 'ZAP' }, 'w2'), false);
  // Any object mode (incl. duelist finisher) pointing at the id counts, since
  // the toolbar uses this to decide whether re-clicking the item disarms.
  assert.equal(isTargetingArmedForItem({ duelistFinisher: true, itemId: 'w1' }, 'w1'), true);
  assert.equal(isTargetingArmedForItem('w1', 'w1'), false);
  assert.equal(isTargetingArmedForItem(false, 'w1'), false);
});

test('isDuelistFinisherArmed: only duelist finisher modes for the item', () => {
  assert.equal(isDuelistFinisherArmed({ duelistFinisher: true, itemId: 'sword' }, 'sword'), true);
  assert.equal(isDuelistFinisherArmed({ duelistFinisher: true, itemId: 'sword' }, 'axe'), false);
  assert.equal(isDuelistFinisherArmed({ itemId: 'sword', action: 'THROW' }, 'sword'), false);
  assert.equal(isDuelistFinisherArmed({ duelistFinisher: false, itemId: 'sword' }, 'sword'), false);
});