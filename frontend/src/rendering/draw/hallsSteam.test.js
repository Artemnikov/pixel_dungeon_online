import test from 'node:test';
import assert from 'node:assert/strict';

import { getHallsSteamCells } from './hallsSteam.js';

const W = 7; // BACKEND_TILE.FLOOR_WATER.id
const F = 2; // some non-water floor tile id

test('returns no cells outside the halls region', () => {
  const grid = [[W, W], [W, F]];
  assert.deepEqual(getHallsSteamCells(grid, 10), []); // depth 10 -> prison
});

test('returns one cell per water tile inside the halls region', () => {
  const grid = [[W, F], [F, W]];
  const cells = getHallsSteamCells(grid, 22); // depth 22 -> halls
  assert.equal(cells.length, 2);
  const coords = cells.map((c) => `${c.x},${c.y}`).sort();
  assert.deepEqual(coords, ['0,0', '1,1']);
  for (const c of cells) {
    assert.ok(c.delay >= 0 && c.delay < 2);
  }
});

test('a grid with no water tiles in halls yields no cells', () => {
  const grid = [[F, F], [F, F]];
  assert.deepEqual(getHallsSteamCells(grid, 23), []);
});
