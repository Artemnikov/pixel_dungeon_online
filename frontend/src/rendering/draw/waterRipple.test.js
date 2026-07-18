import test from 'node:test';
import assert from 'node:assert/strict';

import { rippleVisualState } from './waterRipple.js';

test('rippleVisualState at spawn: no scale, full alpha', () => {
  assert.deepEqual(rippleVisualState(0, 0.5), { scale: 0, alpha: 1 });
});

test('rippleVisualState halfway: half scale, half alpha', () => {
  assert.deepEqual(rippleVisualState(0.25, 0.5), { scale: 0.5, alpha: 0.5 });
});

test('rippleVisualState at/after lifespan: full scale, zero alpha, clamped', () => {
  assert.deepEqual(rippleVisualState(0.5, 0.5), { scale: 1, alpha: 0 });
  assert.deepEqual(rippleVisualState(10, 0.5), { scale: 1, alpha: 0 });
});

test('rippleVisualState defaults lifespan to 0.5', () => {
  assert.deepEqual(rippleVisualState(0.5), { scale: 1, alpha: 0 });
});
