import test from 'node:test';
import assert from 'node:assert/strict';
import { createDefaultEventDispatcher } from './defaultDispatcher';
import { WorldManager } from '../services/WorldManager';
import { EntityManager } from '../services/EntityManager';
import { VisualEffectsManager } from '../services/VisualEffectsManager';
import { GameCallbacks } from '../services/GameCallbacks';
import { HeroStateSync } from '../services/HeroStateSync';
import { hallsArenaPending } from '../sync/EnvironmentSynchronizer';
import {
  targetedCells, targetedCellAlpha, mobMotions, motionPosition, parseArgb, cellEmitters,
} from '../../rendering/yogEffects';
import {
  getYogFrame, getFistFrame, getRipperFrame, YOG_FW, FIST_FW, RIPPER_FW, FIST_ZAP_MS,
} from '../../rendering/mobs';

function makeCtx({ mobs = {}, visible = ['5,5', '5,9', '5,2', '4,9', '6,9'], ui = {} } = {}) {
  const gridRef = { current: Array.from({ length: 12 }, () => Array(12).fill(1)) };
  const visionRef = { current: { visible: new Set(visible), discovered: new Set() } };
  const customTilesRef = { current: [] };
  const customWallsRef = { current: [] };
  const world = new WorldManager({ gridRef, setGrid: () => {}, visionRef, customTilesRef, customWallsRef });
  const entitiesRef = { current: { players: {}, mobs, items: [], traps: [] } };
  const entities = new EntityManager({ entitiesRef, dyingMobsRef: { current: {} }, myPlayerIdRef: { current: 'hero' } });
  const refs = {
    particlesRef: { current: [] },
    floatingTextRef: { current: [] },
    mobAnimRef: { current: {} },
    beamRef: { current: [] },
    magicMissileRef: { current: [] },
    screenFlashRef: { current: null },
    screenShakeRef: { current: null },
  };
  const effects = new VisualEffectsManager(refs);
  return {
    ctx: { myPlayerId: 'hero', world, entities, effects, ui: new GameCallbacks(ui), audio: { play: () => {} } },
    refs, customTilesRef,
  };
}

const dispatcher = createDefaultEventDispatcher();

test('Yog frames follow YogSprite / FistSprite / RipperSprite timings', () => {
  const mob = { id: 'y', renderPos: { x: 0, y: 0 } };
  const idle = [0, 1, 2, 2, 1, 0, 3, 4, 4, 3, 0, 5, 6, 6, 5];
  idle.forEach((f, i) => assert.equal(getYogFrame(mob, {}, i * 100 + 1), f * YOG_FW));

  const fist = { id: 'f', renderPos: { x: 0, y: 0 } };
  assert.deepEqual([0, 500, 1000].map(t => getFistFrame(fist, {}, t + 1) / FIST_FW), [0, 0, 1]);
  const now = 10_000;
  const anim = { f: { zapUntil: now + FIST_ZAP_MS } };
  assert.deepEqual([1, 126, 251].map(dt => getFistFrame(fist, anim, now + dt) / FIST_FW), [0, 5, 6]);

  const rip = { id: 'r', renderPos: { x: 0, y: 0 } };
  assert.deepEqual([0, 250, 500, 750].map(t => getRipperFrame(rip, {}, t + 1) / RIPPER_FW), [1, 0, 1, 2]);
  assert.equal(getRipperFrame(rip, { r: { prepUntil: now + 100 } }, now) / RIPPER_FW, 9);
  assert.equal(getRipperFrame({ ...rip, jumpLift: 3 }, {}, now) / RIPPER_FW, 12);
});

test('TargetedCell fades and shrinks to nothing over its duration', () => {
  const e = { start: 0, durationMs: 2000 };
  assert.equal(targetedCellAlpha(e, 0), 1);
  assert.equal(targetedCellAlpha(e, 1000), 0.5);
  assert.equal(targetedCellAlpha(e, 2500), 0);
});

test('jump arcs and pushes decelerate toward their target', () => {
  const jump = { kind: 'jump', from: { x: 0, y: 0 }, to: { x: 4, y: 0 }, start: 0, durationMs: 400, height: 16 };
  const mid = motionPosition(jump, 200);
  assert.equal(mid.x, 2);
  assert.equal(mid.lift, 16);
  assert.equal(motionPosition(jump, 400).done, true);
  const push = { kind: 'push', from: { x: 0, y: 0 }, to: { x: 1, y: 0 }, start: 0, durationMs: 150, height: 0 };
  assert.ok(motionPosition(push, 75).x > 0.5);
});

test('parseArgb reads SPD flash colours', () => {
  assert.deepEqual(parseArgb('0x80FFFFFF'), { r: 255, g: 255, b: 255, a: 128 / 255 });
  assert.deepEqual(parseArgb('0xFF000000'), { r: 0, g: 0, b: 0, a: 1 });
});

test('YOG_TARGETED_CELLS and YOG_DEATH_RAY draw markers and beams', () => {
  const { ctx, refs } = makeCtx();
  targetedCells.length = 0;
  dispatcher.dispatch({ type: 'YOG_TARGETED_CELLS', data: { mob: 'y', cells: [[5, 6], [5, 7]], color: 0xff0000, duration_ms: 2000 } }, ctx);
  assert.equal(targetedCells.length, 2);
  dispatcher.dispatch({ type: 'YOG_DEATH_RAY', data: { mob: 'y', sx: 5, sy: 5, ends: [[5, 10], [6, 10]], hits: ['hero'] } }, ctx);
  assert.equal(refs.beamRef.current.length, 2);
  assert.ok(refs.particlesRef.current.length >= 1);
});

test('FIST_ZAP fires a bolt, Bright fist a light ray', () => {
  const { ctx, refs } = makeCtx({ mobs: { f: { id: 'f', name: 'Burning Fist', renderPos: { x: 5, y: 2 }, pos: { x: 5, y: 2 } } } });
  dispatcher.dispatch({ type: 'FIST_ZAP', data: { mob: 'f', kind: 'burning', bolt: 'fire', x: 5, y: 2, target_x: 5, target_y: 9 } }, ctx);
  assert.equal(refs.magicMissileRef.current.length, 1);
  assert.ok(refs.mobAnimRef.current.f.zapUntil > 0);
  dispatcher.dispatch({ type: 'FIST_ZAP', data: { mob: 'f', kind: 'bright', bolt: 'light_ray', x: 5, y: 2, target_x: 5, target_y: 9 } }, ctx);
  assert.equal(refs.beamRef.current.length, 1);
});

test('fist and minion spawns are pushed out from their origin', () => {
  const fist = { id: 'f', name: 'Soiled Fist', renderPos: { x: 5, y: 3 }, pos: { x: 5, y: 3 } };
  const { ctx } = makeCtx({ mobs: { f: fist } });
  mobMotions.clear();
  dispatcher.dispatch({ type: 'YOG_FIST_SPAWN', data: { mob: 'y', fist: 'f', cls: 'SoiledFist', x: 5, y: 3, from_x: 5, from_y: 2 } }, ctx);
  assert.deepEqual(fist.renderPos, { x: 5, y: 2 });
  assert.equal(mobMotions.get('f').kind, 'push');
});

test('mob TELEPORT snaps the sprite to its destination', () => {
  const fist = { id: 'f', name: 'Dark Fist', renderPos: { x: 5, y: 3 }, pos: { x: 5, y: 3 } };
  const { ctx } = makeCtx({ mobs: { f: fist } });
  dispatcher.dispatch({ type: 'TELEPORT', data: { mob: 'f', from_x: 5, from_y: 3, x: 9, y: 9 } }, ctx);
  assert.deepEqual(fist.renderPos, { x: 9, y: 9 });
});

test('Yog party prompt events reach the UI callbacks', () => {
  const seen = [];
  const { ctx } = makeCtx({ ui: {
    onYogJoinPrompt: d => seen.push(['join', d.initiator_name]),
    onYogPartyStatus: d => seen.push(['status', d.can_decide]),
    onYogPromptClose: () => seen.push(['close']),
  } });
  dispatcher.dispatch({ type: 'YOG_JOIN_PROMPT', data: { initiator_id: 'a', initiator_name: 'Ann' } }, ctx);
  dispatcher.dispatch({ type: 'YOG_PARTY_STATUS', data: { initiator_id: 'a', pending_names: [], declined_names: ['Bo'], approved_names: [], can_decide: true } }, ctx);
  dispatcher.dispatch({ type: 'YOG_PROMPT_CLOSE', data: {} }, ctx);
  assert.deepEqual(seen, [['join', 'Ann'], ['status', true], ['close']]);
});

test('arena seal pours flames and unseal swaps the centre piece', () => {
  const { ctx, customTilesRef } = makeCtx();
  cellEmitters.length = 0;
  dispatcher.dispatch({ type: 'YOG_ARENA_SEALED', data: { x: 5, y: 9 } }, ctx);
  assert.equal(cellEmitters.length, 1);
  assert.equal(cellEmitters[0].left, 10);
  const layer = { texture: 'halls_special', x: 12, y: 9, w: 9, h: 8, tiles: [[1]] };
  dispatcher.dispatch({ type: 'YOG_ARENA_UNSEALED', data: { custom_tiles: [layer], custom_walls: [] } }, ctx);
  assert.deepEqual(customTilesRef.current, [layer]);
});

test('boss bar stays on Yog-Dzewa while fists are alive', () => {
  let info = null;
  const sync = new HeroStateSync({ setBossInfo: v => { info = v; } });
  sync.syncBossInfo([
    { id: 'f', type: 'boss', name: 'Burning Fist', hp: 300, max_hp: 300, yog_id: 'y' },
    { id: 'y', type: 'boss', name: 'Yog-Dzewa', hp: 700, max_hp: 1000 },
  ]);
  assert.equal(info.name, 'Yog-Dzewa');
});

test('floor 25 stays silent until Yog notices someone or the arena is won', () => {
  const grid = Array.from({ length: 4 }, () => Array(4).fill(1));
  const ctx = { world: { depth: 25, getGrid: () => grid } };
  assert.equal(hallsArenaPending({ mobs: [] }, ctx), true);
  assert.equal(hallsArenaPending({ mobs: [{ name: 'Yog-Dzewa', fight_started: true }] }, ctx), false);
  grid[1][1] = 5;
  assert.equal(hallsArenaPending({ mobs: [] }, ctx), false);
  assert.equal(hallsArenaPending({ mobs: [] }, { world: { depth: 24, getGrid: () => grid } }), false);
});

test('boss bar waits for Yog-Dzewa to notice someone', () => {
  let info = 'unset';
  const sync = new HeroStateSync({ setBossInfo: v => { info = v; } });
  sync.syncBossInfo([{ id: 'y', type: 'boss', name: 'Yog-Dzewa', hp: 1000, max_hp: 1000, fight_started: false }]);
  assert.equal(info, null);
});
