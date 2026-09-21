import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PlayerRenderPipeline,
  defaultPlayerRenderPipeline,
  DownedPlayerRenderState,
  AlivePlayerRenderState,
} from './PlayerRenderPipeline.ts';
import {
  DEATH_ANIMATION_DURATION,
  DEATH_FADE_START_MS,
} from '../../constants.js';

function createMockPlayer(overrides = {}) {
  return {
    id: 'player-1',
    name: 'Hero',
    pos: { x: 5, y: 5 },
    renderPos: { x: 5, y: 5 },
    targetPos: null,
    animStartPos: { x: 5, y: 5 },
    animStartTime: null,
    moveDuration: 150,
    is_downed: false,
    class_type: 'warrior',
    hp: 20,
    max_hp: 20,
    shields: [],
    is_afk: false,
    ...overrides,
  };
}

function createMockCanvasCtx() {
  const calls = [];
  return {
    calls,
    save: () => calls.push({ type: 'save' }),
    restore: () => calls.push({ type: 'restore' }),
    translate: (x, y) => calls.push({ type: 'translate', x, y }),
    scale: (x, y) => calls.push({ type: 'scale', x, y }),
    drawImage: (...args) => calls.push({ type: 'drawImage', args }),
    fillRect: (x, y, w, h) => calls.push({ type: 'fillRect', x, y, w, h }),
    fillText: (text, x, y) => calls.push({ type: 'fillText', text, x, y }),
    strokeText: (text, x, y) => calls.push({ type: 'strokeText', text, x, y }),
    beginPath: () => calls.push({ type: 'beginPath' }),
    stroke: () => calls.push({ type: 'stroke' }),
    arc: (...args) => calls.push({ type: 'arc', args }),
    globalAlpha: 1,
    fillStyle: '#000000',
    strokeStyle: '#000000',
    lineWidth: 1,
    font: '10px Arial',
    textAlign: 'left',
  };
}

test('PlayerRenderPipeline: selects DownedPlayerRenderState when player is downed', () => {
  const player = createMockPlayer({ is_downed: true });
  const ctx = {
    player,
    anim: {},
    now: 1000,
    deathElapsed: 200,
    x: 160,
    y: 148,
    myPlayerId: 'player-1',
    playerSprite: {},
  };

  const state = defaultPlayerRenderPipeline.getActiveState(ctx);
  assert.equal(state.name, 'downed');
  assert.ok(state instanceof DownedPlayerRenderState);
});

test('PlayerRenderPipeline: selects AlivePlayerRenderState when player is active', () => {
  const player = createMockPlayer({ is_downed: false });
  const ctx = {
    player,
    anim: {},
    now: 1000,
    deathElapsed: 0,
    x: 160,
    y: 148,
    myPlayerId: 'player-1',
    playerSprite: {},
  };

  const state = defaultPlayerRenderPipeline.getActiveState(ctx);
  assert.equal(state.name, 'alive');
  assert.ok(state instanceof AlivePlayerRenderState);
});

test('DownedPlayerRenderState: computes death fade alpha correctly over time', () => {
  const state = new DownedPlayerRenderState();

  assert.equal(state.getDeathFadeAlpha(0), 1);
  assert.equal(state.getDeathFadeAlpha(DEATH_FADE_START_MS), 1);

  const midElapsed = (DEATH_FADE_START_MS + DEATH_ANIMATION_DURATION) / 2;
  const midAlpha = state.getDeathFadeAlpha(midElapsed);
  assert.ok(midAlpha > 0.45 && midAlpha < 0.55);

  assert.equal(state.getDeathFadeAlpha(DEATH_ANIMATION_DURATION), 0);
  assert.equal(state.getDeathFadeAlpha(DEATH_ANIMATION_DURATION + 500), 0);
});

test('DownedPlayerRenderState: skips rendering once death animation duration has elapsed', () => {
  const state = new DownedPlayerRenderState();
  const player = createMockPlayer({ is_downed: true });
  const mockCtx = createMockCanvasCtx();

  const ctx = {
    player,
    anim: {},
    now: 5000,
    deathElapsed: DEATH_ANIMATION_DURATION + 100,
    x: 160,
    y: 148,
    myPlayerId: 'other-player',
    playerSprite: {},
  };

  state.render(mockCtx, ctx);
  assert.equal(mockCtx.calls.length, 0);
});

test('DownedPlayerRenderState: renders death sprite without health bar or nameplate', () => {
  const player = createMockPlayer({ is_downed: true, id: 'other-player' });
  const mockCtx = createMockCanvasCtx();

  const ctx = {
    player,
    anim: {},
    now: 1200,
    deathElapsed: 200,
    x: 160,
    y: 148,
    myPlayerId: 'local-player',
    playerSprite: {},
  };

  defaultPlayerRenderPipeline.render(mockCtx, ctx);

  const drawImageCalls = mockCtx.calls.filter(c => c.type === 'drawImage');
  assert.ok(drawImageCalls.length >= 1);

  const fillTextCalls = mockCtx.calls.filter(c => c.type === 'fillText');
  assert.equal(fillTextCalls.length, 0);
});

test('AlivePlayerRenderState: renders sprite, health bar, and nameplate for non-local players', () => {
  const player = createMockPlayer({ is_downed: false, id: 'remote-hero', name: 'Friend' });
  const mockCtx = createMockCanvasCtx();

  const ctx = {
    player,
    anim: {},
    now: 1000,
    deathElapsed: 0,
    x: 160,
    y: 148,
    myPlayerId: 'local-hero',
    playerSprite: {},
  };

  defaultPlayerRenderPipeline.render(mockCtx, ctx);

  const drawImageCalls = mockCtx.calls.filter(c => c.type === 'drawImage');
  assert.ok(drawImageCalls.length >= 1);

  const fillRectCalls = mockCtx.calls.filter(c => c.type === 'fillRect');
  assert.equal(fillRectCalls.length, 3);

  const nameTextCalls = mockCtx.calls.filter(c => c.type === 'fillText' && c.text === 'Friend');
  assert.equal(nameTextCalls.length, 1);
});

test('AlivePlayerRenderState: omits health bar and nameplate for local player (myPlayerId)', () => {
  const player = createMockPlayer({ is_downed: false, id: 'local-hero', name: 'Me' });
  const mockCtx = createMockCanvasCtx();

  const ctx = {
    player,
    anim: {},
    now: 1000,
    deathElapsed: 0,
    x: 160,
    y: 148,
    myPlayerId: 'local-hero',
    playerSprite: {},
  };

  defaultPlayerRenderPipeline.render(mockCtx, ctx);

  const drawImageCalls = mockCtx.calls.filter(c => c.type === 'drawImage');
  assert.ok(drawImageCalls.length >= 1);

  const fillRectCalls = mockCtx.calls.filter(c => c.type === 'fillRect');
  assert.equal(fillRectCalls.length, 0);

  const fillTextCalls = mockCtx.calls.filter(c => c.type === 'fillText');
  assert.equal(fillTextCalls.length, 0);
});

test('PlayerRenderPipeline: allows custom state registration with high priority', () => {
  const customGhostState = {
    name: 'ghost-form',
    matches: (ctx) => ctx.player.is_ghost === true,
    render: (ctx2d, ctx) => {
      ctx2d.save();
      ctx2d.globalAlpha = 0.3;
      ctx2d.fillText('GHOST', ctx.x, ctx.y);
      ctx2d.restore();
    },
  };

  const pipeline = new PlayerRenderPipeline();
  pipeline.register(customGhostState, true);

  const player = createMockPlayer({ is_ghost: true });
  const mockCtx = createMockCanvasCtx();

  const ctx = {
    player,
    anim: {},
    now: 1000,
    deathElapsed: 0,
    x: 100,
    y: 100,
    myPlayerId: 'p1',
    playerSprite: {},
  };

  assert.equal(pipeline.getActiveState(ctx)?.name, 'ghost-form');
  pipeline.render(mockCtx, ctx);

  const ghostTextCalls = mockCtx.calls.filter(c => c.type === 'fillText' && c.text === 'GHOST');
  assert.equal(ghostTextCalls.length, 1);
});

test('PlayerRenderPipeline: safely handles empty state list', () => {
  const emptyPipeline = new PlayerRenderPipeline([]);
  const mockCtx = createMockCanvasCtx();
  const ctx = {
    player: createMockPlayer(),
    anim: {},
    now: 1000,
    deathElapsed: 0,
    x: 100,
    y: 100,
    myPlayerId: 'p1',
    playerSprite: {},
  };

  assert.equal(emptyPipeline.getActiveState(ctx), undefined);
  assert.doesNotThrow(() => emptyPipeline.render(mockCtx, ctx));
  assert.equal(mockCtx.calls.length, 0);
});
