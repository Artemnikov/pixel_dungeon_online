import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveTargetCrosshairCell, pickAutoAimTarget } from './autoAim.js';

const mob = (id, x, y, hp = 5) => ({ id, renderPos: { x, y }, hp });
const vis = (...cells) => new Set(cells);

test('crosshair cell: visible alive locked target', () => {
  const mobs = { m1: mob('m1', 3, 4) };
  assert.deepEqual(resolveTargetCrosshairCell('m1', mobs, vis('3,4')), { x: 3, y: 4 });
});

test('crosshair cell: null when target not visible', () => {
  const mobs = { m1: mob('m1', 3, 4) };
  assert.equal(resolveTargetCrosshairCell('m1', mobs, vis('9,9')), null);
});

test('crosshair cell: null when target dead or missing', () => {
  assert.equal(resolveTargetCrosshairCell('gone', {}, vis('3,4')), null);
  assert.equal(resolveTargetCrosshairCell('m1', { m1: mob('m1', 3, 4, 0) }, vis('3,4')), null);
});

test('autoaim prefers the locked target when in range/visible', () => {
  const mobs = { m1: mob('m1', 5, 5), m2: mob('m2', 6, 5) };
  const t = pickAutoAimTarget('m1', mobs, vis('5,5', '6,5'), { x: 5, y: 6 }, 4);
  assert.equal(t.id, 'm1');
});

test('autoaim falls back to nearest when no valid lock', () => {
  const mobs = { m1: mob('m1', 5, 5), m2: mob('m2', 6, 6) };
  const t = pickAutoAimTarget(null, mobs, vis('5,5', '6,6'), { x: 6, y: 7 }, 4);
  assert.equal(t.id, 'm2'); // dist 1 vs ~2.2
});

test('autoaim returns null when nothing is in range', () => {
  const mobs = { m1: mob('m1', 50, 50) };
  assert.equal(pickAutoAimTarget('m1', mobs, vis('50,50'), { x: 0, y: 0 }, 4), null);
});
