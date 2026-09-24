import test from 'node:test';
import assert from 'node:assert/strict';

import { drawInstructions, drawSewerTileBase, buildWaterClipPath, buildWaterClipPaths, drawWaterBackground } from './draw.js';
import { BACKEND_TILE } from '../../constants.js';
import { QUADRANT, DEST_TILE_SIZE, WATER_SCROLL_PX_PER_SEC } from './constants.js';

const makeCtx = () => {
  const calls = [];
  return {
    calls,
    globalAlpha: 1,
    drawImage: (...args) => {
      calls.push(args);
    },
    save: () => {},
    restore: () => {},
  };
};

test('drawInstructions renders full and quarter tiles', () => {
  const ctx = makeCtx();
  const image = { width: 256, height: 256 };

  drawInstructions(
    ctx,
    image,
    [
      { srcIndex: 0, quadrant: QUADRANT.FULL },
      { srcIndex: 1, quadrant: QUADRANT.TR, alpha: 0.5 },
    ],
    2,
    3
  );

  assert.equal(ctx.calls.length, 2);

  const full = ctx.calls[0];
  assert.equal(full[5], 64);
  assert.equal(full[6], 96);

  const quarter = ctx.calls[1];
  assert.equal(quarter[5], 80);
  assert.equal(quarter[6], 96);
});

test('drawSewerTileBase draws instructions for floor water cells', () => {
  const ctx = makeCtx();
  const atlas = { width: 256, height: 256 };
  const grid = [[BACKEND_TILE.FLOOR_WATER.id]];

  const drawn = drawSewerTileBase(ctx, atlas, grid, 0, 0, BACKEND_TILE.FLOOR_WATER.id);

  assert.equal(drawn, true);
});

test('buildWaterClipPath limits the animated water clip to in-FOV cells', () => {
  // Path2D is not available in the Node test runtime; shim it so the builder
  // records the rects instead.
  class FakePath2D {
    constructor() {
      this.rects = [];
    }
    rect(x, y, w, h) {
      this.rects.push([x, y, w, h]);
    }
  }
  const realPath2D = globalThis.Path2D;
  globalThis.Path2D = FakePath2D;
  try {
    const W = BACKEND_TILE.FLOOR_WATER.id;
    const F = BACKEND_TILE.FLOOR.id;
    const grid = [
      [W, F],
      [W, W],
    ];

    const all = buildWaterClipPath(grid);
    assert.equal(all.rects.length, 3);
    assert.deepEqual(
      all.rects.sort((a, b) => a[1] - b[1] || a[0] - b[0]),
      [
        [0, 0, DEST_TILE_SIZE, DEST_TILE_SIZE],
        [0, DEST_TILE_SIZE, DEST_TILE_SIZE, DEST_TILE_SIZE],
        [DEST_TILE_SIZE, DEST_TILE_SIZE, DEST_TILE_SIZE, DEST_TILE_SIZE],
      ]
    );

    const visible = buildWaterClipPath(grid, new Set(['0,0', '1,1']));
    assert.equal(visible.rects.length, 2);
    const visibleCells = visible.rects.map((r) => `${r[0] / DEST_TILE_SIZE},${r[1] / DEST_TILE_SIZE}`);
    assert.deepEqual([...visibleCells].sort(), ['0,0', '1,1']);

    const noneVisible = buildWaterClipPath(grid, new Set(['9,9']));
    assert.equal(noneVisible, null);
  } finally {
    globalThis.Path2D = realPath2D;
  }
});

test('buildWaterClipPaths splits water into in-FOV and calm beyond-LOS paths', () => {
  class FakePath2D {
    constructor() {
      this.rects = [];
    }
    rect(x, y, w, h) {
      this.rects.push([x, y, w, h]);
    }
  }
  const realPath2D = globalThis.Path2D;
  globalThis.Path2D = FakePath2D;
  try {
    const W = BACKEND_TILE.FLOOR_WATER.id;
    const F = BACKEND_TILE.FLOOR.id;
    const grid = [
      [W, F],
      [F, W],
    ];
    const vision = {
      discovered: new Set(['0,0', '1,1']), // (0,1) water unexplored -> skipped
      visible: new Set(['0,0']),
    };

    const { visible, hidden } = buildWaterClipPaths(grid, vision);
    assert.equal(visible.rects.length, 1);
    assert.deepEqual(visible.rects[0], [0, 0, DEST_TILE_SIZE, DEST_TILE_SIZE]);
    assert.equal(hidden.rects.length, 1);
    assert.deepEqual(hidden.rects[0], [DEST_TILE_SIZE, DEST_TILE_SIZE, DEST_TILE_SIZE, DEST_TILE_SIZE]);

    const empty = buildWaterClipPaths([], vision);
    assert.equal(empty.visible, null);
    assert.equal(empty.hidden, null);
  } finally {
    globalThis.Path2D = realPath2D;
  }
});

test('drawWaterBackground draws calm dark water beyond LOS and scrolls only in-FOV cells', () => {
  // Shim Path2D/DOMMatrix: neither exists in the Node test runtime.
  class FakePath2D {
    constructor() {
      this.id = Math.random();
    }
    rect() {}
  }
  class FakeDOMMatrix {
    constructor() {
      this.scale = 1;
      this.tx = 0;
      this.ty = 0;
    }
    scaleSelf(s) {
      this.scale *= s;
      return this;
    }
    translateSelf(x, y) {
      this.tx += x;
      this.ty += y;
      return this;
    }
  }
  const realPath2D = globalThis.Path2D;
  const realDOMMatrix = globalThis.DOMMatrix;
  globalThis.Path2D = FakePath2D;
  globalThis.DOMMatrix = FakeDOMMatrix;

  try {
    const clips = [];
    const fills = [];
    const patternTransforms = [];
    const ctx = {
      save() {},
      restore() {},
      clip(p) {
        clips.push(p);
      },
      set fillStyle(v) {
        patternTransforms.push(v);
      },
      fillRect(x, y, w, h) {
        fills.push([x, y, w, h]);
      },
      createPattern() {
        return {
          setTransform(m) {
            this.transform = m;
          },
        };
      },
    };

    const waterTex = { width: 64, height: 64 };
    const hiddenClip = new FakePath2D();
    const visibleClip = new FakePath2D();
    const bounds = { x: 0, y: 0, w: 320, h: 320 };

    drawWaterBackground(ctx, waterTex, visibleClip, hiddenClip, bounds, 5000);

    // Calm pass fills the beyond-LOS clip with a flat colour; the animated
    // pass restricts the scrolling texture to the visible clip.
    assert.equal(clips.length, 2);
    assert.equal(clips[0], hiddenClip);
    assert.equal(clips[1], visibleClip);
    assert.equal(fills.length, 2);
    // The calm pass fills with the flat dark water colour (no texture).
    assert.equal(patternTransforms[0], '#2f5f7a');

    // The animated scroll transform carries a vertical scroll offset derived
    // from elapsed time.
    const scale = DEST_TILE_SIZE / waterTex.width;
    const scrollPx = -(5000 / 1000) * WATER_SCROLL_PX_PER_SEC;
    const animatedTransform = patternTransforms[1].transform;
    assert.equal(animatedTransform.scale, scale);
    assert.equal(animatedTransform.ty, scrollPx / scale);
  } finally {
    globalThis.Path2D = realPath2D;
    globalThis.DOMMatrix = realDOMMatrix;
  }
});
