import test from 'node:test';
import assert from 'node:assert/strict';

import { spawnWaterRipple, getActiveRipples, advanceAndDrawWaterRipples } from './waterRipple';

// Minimal fake canvas context that records drawImage calls so tests can assert
// whether a ripple was drawn.
function makeCtx() {
  const calls = [];
  return {
    calls,
    save() {},
    restore() {},
    globalAlpha: 1,
    drawImage(...args) {
      calls.push(['drawImage', ...args]);
    },
  };
}

// advanceAndDrawWaterRipples accepts an injected `now` (ms) for deterministic
// tests (dt is capped at 0.05s). activeRipples/lastNow are module state, so
// tests share one monotonically increasing clock and clean up their own
// ripples afterwards.
let clock = 0;
const tick = (ctx, visionRef) => {
  clock += 100;
  advanceAndDrawWaterRipples(ctx, { assetImages: { effects: {} }, visionRef, now: clock });
};

const restoreRipples = (before) => getActiveRipples().splice(before);

test('ripple outside FOV is not drawn', () => {
  const before = getActiveRipples().length;
  spawnWaterRipple(16, 48, { clipTop: true, fovCell: '3,2' });
  const ctx = makeCtx();
  const visionRef = { current: { visible: new Set(['1,1', '0,0']) } };

  tick(ctx, visionRef);
  tick(ctx, visionRef);
  assert.equal(ctx.calls.length, 0, 'out-of-FOV ripple must not be drawn');
  restoreRipples(before);
});

test('ripple inside FOV is drawn', () => {
  const before = getActiveRipples().length;
  spawnWaterRipple(16, 48, { clipTop: true, fovCell: '3,2' });
  const ctx = makeCtx();
  const visionRef = { current: { visible: new Set(['3,2']) } };

  tick(ctx, visionRef);
  tick(ctx, visionRef);
  assert.ok(ctx.calls.some((c) => c[0] === 'drawImage'), 'in-FOV ripple should be drawn');
  restoreRipples(before);
});

test('ripple without fovCell is always drawn (not LOS-gated)', () => {
  const before = getActiveRipples().length;
  spawnWaterRipple(16, 48);
  const ctx = makeCtx();
  const visionRef = { current: { visible: new Set(['9,9']) } };

  tick(ctx, visionRef);
  tick(ctx, visionRef);
  assert.ok(ctx.calls.some((c) => c[0] === 'drawImage'), 'un-gated ripple should be drawn');
  restoreRipples(before);
});