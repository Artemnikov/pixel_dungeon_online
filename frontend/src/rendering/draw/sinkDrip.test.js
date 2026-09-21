import test from 'node:test';
import assert from 'node:assert/strict';

import { BACKEND_TILE } from '../../constants';
import { advanceSinkDrips } from './sinkDrip';
import { getActiveRipples } from './waterRipple';

const WD = BACKEND_TILE.WALL_DECO.id; // 17 — sewers drain grate
const W = BACKEND_TILE.FLOOR_WATER.id; // 7
const WALL = BACKEND_TILE.WALL.id;     // 1
const F = BACKEND_TILE.FLOOR.id;       // 2

// advanceSinkDrips accepts an injected `now` (ms) for deterministic
// tests. dt is capped at 0.05 s; rippleDelay starts at Random.Float(0.8, 1.2)
// so ~1.5s of ticks is needed before a ripple can spawn.
function tick(ctx, now) {
  advanceSinkDrips({ ...ctx, now });
}

const ctx = (grid, visibleKeys = []) => ({
  grid,
  depth: 2, // sewers
  visionRef: { current: { visible: new Set(visibleKeys) } },
  particlesRef: { current: [] },
});

// Prime the clock, then run 30 frames of 0.05s (1.5s total).
function tickFrames(state) {
  tick(state, 0);
  for (let i = 1; i <= 30; i += 1) tick(state, i * 50);
}

test('drain ripple spawns centered on the water cell below the drain', () => {
  const grid = [[WD], [W]];
  const state = ctx(grid, ['0,0', '0,1']);

  const before = getActiveRipples().length;
  tickFrames(state);

  const spawned = getActiveRipples().slice(before);
  assert.ok(spawned.length >= 1, 'a drain above water should spawn ripples');
  for (const r of spawned) {
    // Ring center = point on the water surface below the drain: drain
    // column center x (16), water cell top y ((0+1)*32 = 32); top half
    // clipped so the ring stays on the water; drawn only while the water
    // cell below is in FOV.
    assert.equal(r.x, 16);
    assert.equal(r.y, 32);
    assert.equal(r.clipTop, true);
    assert.equal(r.fovCell, '0,1');
  }
});

test('drain with no water below spawns no ripple', () => {
  const grid = [[WD], [F]];
  const state = ctx(grid, ['0,0', '0,1']);

  const before = getActiveRipples().length;
  tickFrames(state);

  assert.equal(getActiveRipples().length - before, 0);
});

test('drips are gated on the cell below the drain, not the drain wall', () => {
  // Regression: WALL_DECO drains are walls, and the vision system shell-adds
  // walls adjacent to visible tiles. Gating drips on the drain cell kept the
  // drops visible beyond direct LOS. Drops must only spawn when the cell they
  // fall into (the floor/water below) is actually seen.
  const grid = [[WD], [W]];

  // Drain '0,0' is "visible" (as if shell-added) but the water below '0,1'
  // is not -> no drops spawn.
  const hiddenBelow = ctx(grid, ['0,0']);
  tickFrames(hiddenBelow);
  assert.equal(hiddenBelow.particlesRef.current.length, 0, 'no drips when the cell below is out of LOS');

  // Water below '0,1' visible -> drops spawn and are tagged to that cell so
  // the draw pass hides them the moment it leaves LOS.
  const seenBelow = ctx(grid, ['0,1']);
  tickFrames(seenBelow);
  assert.ok(seenBelow.particlesRef.current.length > 0, 'drips spawn when the water below is in LOS');
  for (const p of seenBelow.particlesRef.current) {
    assert.equal(p.fovCell, '0,1');
  }
});

test('drain whose below cell is a wall never drips', () => {
  const grid = [[WD], [WALL]];
  const state = ctx(grid, ['0,0', '0,1']);

  tickFrames(state);

  assert.equal(state.particlesRef.current.length, 0);
});