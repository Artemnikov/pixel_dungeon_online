import test from 'node:test';
import assert from 'node:assert/strict';
import { slotTooltipText } from './slotTooltip.js';

test('empty slot: null', () => {
  assert.equal(slotTooltipText(null, 0), null);
});

test('item slot shows name and 1-based hotkey', () => {
  assert.equal(slotTooltipText({ name: 'Potion of Healing' }, 0), 'Potion of Healing  [1]');
  assert.equal(slotTooltipText({ name: 'Dart' }, 3), 'Dart  [4]');
});

test('falls back to kind when name missing', () => {
  assert.equal(slotTooltipText({ kind: 'scroll_of_upgrade' }, 1), 'scroll_of_upgrade  [2]');
});
