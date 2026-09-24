import test from 'node:test';
import assert from 'node:assert/strict';
import { isTargetSelection, canAutoAim, canAutoAimFromQuickbar } from './targetingModeInfo.js';

const item = (patch) => ({ id: 'i1', name: 'test', ...patch });

test('isTargetSelection: disarmed falsy modes', () => {
  assert.equal(isTargetSelection(false), false);
  assert.equal(isTargetSelection(null), false);
  assert.equal(isTargetSelection(undefined), false);
});

test('isTargetSelection: any armed mode counts', () => {
  assert.equal(isTargetSelection('w1'), true); // ranged weapon string mode
  assert.equal(isTargetSelection({ itemId: 'w1', action: 'THROW' }), true);
  assert.equal(isTargetSelection({ itemId: 'w1', action: 'ZAP', fromQuickbar: true }), true);
  assert.equal(isTargetSelection({ ability: 'heroic_leap' }), true);
  assert.equal(isTargetSelection({ duelistFinisher: true }), true);
  assert.equal(isTargetSelection({ clericSpell: 'guiding_light' }), true);
  assert.equal(isTargetSelection(true), true);
});

test('canAutoAim: wand, staff, throwable, missile, ranged weapon', () => {
  assert.equal(canAutoAim(item({ type: 'wand' })), true);
  assert.equal(canAutoAim(item({ type: 'weapon', kind: 'staff' })), true);
  assert.equal(canAutoAim(item({ type: 'throwable' })), true);
  assert.equal(canAutoAim(item({ type: 'weapon', throw_behavior: 'missile' })), true);
  assert.equal(canAutoAim(item({ type: 'weapon', range: 5 })), true);
});

test('canAutoAim: melee weapons, seeds, bags and missing items do not', () => {
  assert.equal(canAutoAim(item({ type: 'weapon', range: 1 })), false);
  assert.equal(canAutoAim(item({ type: 'seed', throw_behavior: 'seed' })), false);
  assert.equal(canAutoAim(item({ type: 'potion' })), false);
  assert.equal(canAutoAim(null), false);
});

test('canAutoAimFromQuickbar: only from-quickbar shoot actions with auto-aim item', () => {
  const items = { w1: item({ type: 'wand' }), thr: item({ type: 'throwable' }), seed: item({ type: 'seed' }) };
  assert.equal(canAutoAimFromQuickbar({ itemId: 'w1', action: 'ZAP', fromQuickbar: true }, items), true);
  assert.equal(canAutoAimFromQuickbar({ itemId: 'thr', action: 'THROW', fromQuickbar: true }, items), true);
  // Not from quickbar, or a non-auto-aim item => no hint.
  assert.equal(canAutoAimFromQuickbar({ itemId: 'w1', action: 'ZAP' }, items), false);
  assert.equal(canAutoAimFromQuickbar({ itemId: 'seed', action: 'THROW', fromQuickbar: true }, items), false);
  // Unlock/steal/plant carry no auto-aim double-click.
  assert.equal(canAutoAimFromQuickbar({ itemId: 'w1', action: 'PLANT_SEED', fromQuickbar: true }, items), false);
  // Non-targeted modes without fromQuickbar never hint.
  assert.equal(canAutoAimFromQuickbar({ ability: 'heroic_leap' }, items), false);
  assert.equal(canAutoAimFromQuickbar(false, items), false);
});

test('canAutoAimFromQuickbar: string mode (Bow) is always quickbar-armed and auto-aims', () => {
  const items = { bow: item({ type: 'weapon', range: 6 }), sword: item({ type: 'weapon', range: 1 }), ghost: null };
  assert.equal(canAutoAimFromQuickbar('bow', items), true);
  assert.equal(canAutoAimFromQuickbar('sword', items), false);
  assert.equal(canAutoAimFromQuickbar('ghost', items), false);
});

test('canAutoAimFromQuickbar: duelist finisher hints for equipped weapons', () => {
  const items = { sword: item({ type: 'weapon', range: 1 }) };
  assert.equal(canAutoAimFromQuickbar({ duelistFinisher: true, itemId: 'sword', fromQuickbar: true }, items), true);
  assert.equal(canAutoAimFromQuickbar({ duelistFinisher: true, itemId: 'sword' }, items), false);
  assert.equal(canAutoAimFromQuickbar({ duelistFinisher: true, itemId: 'unknown', fromQuickbar: true }, items), false);
});