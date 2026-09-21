import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveTargetCrosshairCell, pickAutoAimTarget } from './autoAim.js';

const mob = (id, x, y, hp = 5, faction = 'enemy') => ({ id, renderPos: { x, y }, hp, faction });
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

test('autoaim skips player-faction mobs (npcs, ghosts, mirror images)', () => {
  const friendly = mob('shopkeeper', 5, 5, 10, 'player');
  const hostile  = mob('rat', 6, 6, 3, 'enemy');
  const mobs = { shopkeeper: friendly, rat: hostile };
  const t = pickAutoAimTarget(null, mobs, vis('5,5', '6,6'), { x: 5, y: 6 }, 5);
  assert.equal(t.id, 'rat');
});

test('autoaim skips locked target if it has player faction', () => {
  const friendly = mob('ghost', 5, 5, 10, 'player');
  const mobs = { ghost: friendly };
  assert.equal(pickAutoAimTarget('ghost', mobs, vis('5,5'), { x: 5, y: 6 }, 5), null);
});

test('autoaim with dungeon faction targets player faction and skips dungeon faction mobs', () => {
  const dungeonMob = mob('rat', 5, 5, 10, 'dungeon');
  const heroSummon = mob('mirror_image', 6, 6, 3, 'player');
  const mobs = { rat: dungeonMob, mirror_image: heroSummon };
  const t = pickAutoAimTarget(null, mobs, vis('5,5', '6,6'), { x: 5, y: 6 }, 5, 'dungeon');
  assert.equal(t.id, 'mirror_image');
});
