import test from 'node:test';
import assert from 'node:assert/strict';

import { BACKEND_TILE } from '../../constants';
import { advanceWaterFlow } from './waterFlow';

const W = BACKEND_TILE.FLOOR_WATER.id; // 7
const F = BACKEND_TILE.FLOOR.id;        // 2
const C = BACKEND_TILE.CHASM.id;        // 33
const V = BACKEND_TILE.VOID.id;         // 0

// advanceWaterFlow accepts an injected `now` (ms) for deterministic tests.
// dt = min((now - lastNow)/1000, 0.05): primed at now=0 (dt=0, no emission),
// then now=50 gives dt=0.05 so `Math.random() < dt * 20` is always true and
// each in-FOV flow cell emits exactly one particle.
function tick(ctx, now) {
  advanceWaterFlow({ ...ctx, now });
}

const ctx = (grid, visibleKeys = []) => ({
  grid,
  visionRef: { current: { visible: new Set(visibleKeys) } },
  particlesRef: { current: [] },
});

const primeAndEmit = async (state) => {
  tick(state, 0);
  tick(state, 50);
};

test('water above a chasm/void emits a flowing particle on its bottom edge', async () => {
  for (const pit of [C, V]) {
    const grid = [[W], [pit]];
    const state = ctx(grid, ['0,0']);
    primeAndEmit(state);

    assert.equal(state.particlesRef.current.length, 1, `pit tile ${pit} should emit`);
    const p = state.particlesRef.current[0];

    // Flow emitter anchor: pos(p.x, p.y + SIZE - 1, SIZE, 0) -> bottom edge.
    assert.ok(p.x >= 0 && p.x < 32, 'x within the water cell');
    assert.equal(p.y, 32 - 1, 'y at the water cell bottom edge');

    // FlowParticle: lifespan 0.6, acc(0, 32 -> 64), max size (1-p)*4 -> 8.
    assert.equal(p.life, 0.6);
    assert.equal(p.maxLife, 0.6);
    assert.equal(p.accY, 64);
    assert.equal(p.sizeOnAge, 8);
    assert.equal(p.triangleAlphaScale, 0.6);
    assert.equal(p.vx, 0);
    assert.equal(p.vy, 0);
    assert.equal(p.color, '#ffffff'); // PseudoPixel solid white
    assert.equal(p.centered, true);
    assert.equal(p.fovCell, '0,0'); // LOS gate: drawn only while the cell is in FOV
    // angularSpeed = Random.Float(-360, +360) deg/s == ±2π rad/s
    assert.ok(p.angularSpeed >= -2 * Math.PI && p.angularSpeed <= 2 * Math.PI);
  }
});

test('water above solid floor or plain ground does NOT emit', async () => {
  const grid = [
    [W, W, F, C, V],
    [F, F, F, W, F],
  ];
  const state = ctx(grid, ['0,0', '1,0', '2,0', '3,0', '4,0']);
  primeAndEmit(state);
  assert.equal(state.particlesRef.current.length, 0);
});

test('only visible (in-FOV) flow cells update', async () => {
  const grid = [
    [W, W],
    [C, C],
  ];
  // Only (0,0) is in FOV.
  const state = ctx(grid, ['0,0']);
  primeAndEmit(state);

  assert.equal(state.particlesRef.current.length, 1);
  assert.ok(state.particlesRef.current.every((p) => p.y === 32 - 1));
});

test('emission stops when the water cell leaves FOV', async () => {
  const grid = [
    [W, W],
    [C, C],
  ];
  const visible = new Set(['0,0', '1,0']);
  const state = ctx(grid, []);
  state.visionRef.current.visible = visible;

  // In-FOV: both cells emit.
  tick(state, 0);
  tick(state, 50);
  assert.equal(state.particlesRef.current.length, 2);

  // Both cells leave FOV: no further emission.
  visible.clear();
  tick(state, 100);
  assert.equal(state.particlesRef.current.length, 2, 'no new particles once out of FOV');
});