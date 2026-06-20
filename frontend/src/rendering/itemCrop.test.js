import test from 'node:test';
import assert from 'node:assert/strict';

import { centeredItemCrop } from './itemCrop.js';

test('no measured rect falls back to the full cell with no offset', () => {
  const result = centeredItemCrop(null, 32, 16);
  assert.deepEqual(result, { sx: 0, sy: 0, sw: 16, sh: 16, dw: 32, dh: 32, offsetX: 0, offsetY: 0 });
});

test('a rect smaller than the cell (e.g. a key sprite) is scaled and centred', () => {
  // key art is 8x14 anchored top-left of a 16x16 cell
  const rect = { rx: 0, ry: 0, w: 8, h: 14 };
  const result = centeredItemCrop(rect, 32, 16);
  assert.equal(result.dw, 16); // 8 * scale(2)
  assert.equal(result.dh, 28); // 14 * scale(2)
  assert.equal(result.offsetX, 8); // (32-16)/2
  assert.equal(result.offsetY, 2); // (32-28)/2
});

test('preserves the rect source offset for atlas cropping', () => {
  const rect = { rx: 3, ry: 1, w: 10, h: 10 };
  const result = centeredItemCrop(rect, 20, 16);
  assert.equal(result.sx, 3);
  assert.equal(result.sy, 1);
  assert.equal(result.sw, 10);
  assert.equal(result.sh, 10);
});
