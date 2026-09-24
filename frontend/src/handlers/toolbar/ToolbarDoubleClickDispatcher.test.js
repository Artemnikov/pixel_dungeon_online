import test, { beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { resetAttackCooldown, consumeAttackCooldown } from '../../net/events/combat';
import { buildCandidateTargets, ToolbarDoubleClickDispatcher } from './ToolbarDoubleClickDispatcher.ts';

const item = (patch) => ({ id: 'i1', name: 'Test Item', ...patch });

function makeCtx(overrides = {}) {
  const sent = [];
  const calls = [];
  const ctx = {
    send: (msg) => sent.push(msg),
    entitiesRef: { current: { mobs: {}, players: {} } },
    myPlayerIdRef: { current: 'me' },
    visionRef: { current: { visible: new Set() } },
    selectedEnemyIdRef: { current: null },
    myStats: undefined,
    equippedItems: { weapon: null },
    belongings: {},
    setTargetingMode: (mode) => calls.push(mode),
    ...overrides,
  };
  return { ctx, sent, calls };
}

function withCombatScene(ctx, { playerX = 10, playerY = 10, mobX = 12, mobY = 10 } = {}) {
  ctx.entitiesRef.current.players.me = { id: 'me', faction: 'player', renderPos: { x: playerX, y: playerY } };
  ctx.entitiesRef.current.mobs.m1 = { id: 'm1', hp: 10, faction: 'enemy', renderPos: { x: mobX, y: mobY } };
  ctx.visionRef.current.visible.add(`${mobX},${mobY}`);
  ctx.selectedEnemyIdRef.current = 'm1';
  return ctx;
}

const rapier = item({ type: 'weapon', name: 'Rapier', range: 1 });
const quarterstaff = item({ type: 'weapon', name: 'Quarterstaff', range: 1 });

beforeEach(() => {
  resetAttackCooldown();
});

test('duelist non-target skill fires DUELIST_FINISHER and disarms targeting', () => {
  const dispatcher = new ToolbarDoubleClickDispatcher();
  const { ctx, sent, calls } = makeCtx({
    myStats: { classType: 'duelist', weaponCharge: 1 },
    equippedItems: { weapon: quarterstaff },
  });
  assert.equal(dispatcher.dispatch(quarterstaff, ctx), true);
  assert.deepEqual(sent, [{ type: 'DUELIST_FINISHER' }]);
  assert.deepEqual(calls, [false]);
});

test('duelist secondary weapon fires USE_WEAPON_ABILITY', () => {
  const dispatcher = new ToolbarDoubleClickDispatcher();
  const { ctx, sent, calls } = makeCtx({
    myStats: { classType: 'duelist', weaponCharge: 1 },
    equippedItems: { weapon: { id: 'primary' } },
    belongings: { secondary_weapon: quarterstaff },
  });
  assert.equal(dispatcher.dispatch(quarterstaff, ctx), true);
  assert.deepEqual(sent, [{ type: 'USE_WEAPON_ABILITY', use_secondary: true }]);
  assert.deepEqual(calls, [false]);
});

test('duelist target skill with enemy in reach fires finisher at the nearest enemy', () => {
  const dispatcher = new ToolbarDoubleClickDispatcher();
  const { ctx, sent, calls } = makeCtx({
    myStats: { classType: 'duelist', weaponCharge: 1 },
    equippedItems: { weapon: rapier },
  });
  withCombatScene(ctx);
  assert.equal(dispatcher.dispatch(rapier, ctx), true);
  assert.deepEqual(sent, [{ type: 'DUELIST_FINISHER', target_x: 12, target_y: 10 }]);
  assert.deepEqual(calls, [false]);
});

test('duelist target skill with no enemy in reach arms finisher targeting', () => {
  const dispatcher = new ToolbarDoubleClickDispatcher();
  const { ctx, sent, calls } = makeCtx({
    myStats: { classType: 'duelist', weaponCharge: 1 },
    equippedItems: { weapon: rapier },
  });
  withCombatScene(ctx, { mobX: 2, mobY: 2 }); // out of the lunge reach-2 window
  assert.equal(dispatcher.dispatch(rapier, ctx), true);
  assert.deepEqual(sent, []);
  assert.deepEqual(calls, [{ duelistFinisher: true, itemId: 'i1', useSecondary: false }]);
});

test('reach-2 skill does not auto-fire at distance 1 (only exact reach 2)', () => {
  const dispatcher = new ToolbarDoubleClickDispatcher();
  const { ctx, sent, calls } = makeCtx({
    myStats: { classType: 'duelist', weaponCharge: 1 },
    equippedItems: { weapon: rapier },
  });
  withCombatScene(ctx, { mobX: 11, mobY: 10 }); // adjacent: dist === 1
  assert.equal(dispatcher.dispatch(rapier, ctx), true);
  assert.deepEqual(sent, []);
  assert.deepEqual(calls, [{ duelistFinisher: true, itemId: 'i1', useSecondary: false }]);
});

test('sneak never auto-aims; it always arms finisher targeting', () => {
  const dispatcher = new ToolbarDoubleClickDispatcher();
  const dagger = item({ type: 'weapon', name: 'Dagger', range: 1 });
  const { ctx, sent, calls } = makeCtx({
    myStats: { classType: 'duelist', weaponCharge: 1 },
    equippedItems: { weapon: dagger },
  });
  withCombatScene(ctx, { mobX: 12, mobY: 10 }); // enemy would be auto-aimable for other skills
  assert.equal(dispatcher.dispatch(dagger, ctx), true);
  assert.deepEqual(sent, []);
  assert.deepEqual(calls, [{ duelistFinisher: true, itemId: 'i1', useSecondary: false }]);
});

test('duelist weapon with insufficient charges is consumed without firing', () => {
  const dispatcher = new ToolbarDoubleClickDispatcher();
  const { ctx, sent, calls } = makeCtx({
    myStats: { classType: 'duelist', weaponCharge: 0 },
    equippedItems: { weapon: rapier },
  });
  assert.equal(dispatcher.dispatch(rapier, ctx), true);
  assert.deepEqual(sent, []);
  assert.deepEqual(calls, []);
});

test('duelist bow (no melee skill) falls through to ranged auto-aim', () => {
  const dispatcher = new ToolbarDoubleClickDispatcher();
  const bow = item({ type: 'weapon', name: 'Bow', kind: 'bow', default_action: 'SHOOT', range: 6, attack_cooldown: 0.4 });
  const { ctx, sent } = makeCtx({
    myStats: { classType: 'duelist', weaponCharge: 1 },
    equippedItems: { weapon: bow },
  });
  withCombatScene(ctx);
  assert.equal(dispatcher.dispatch(bow, ctx), true);
  assert.deepEqual(sent, [
    { type: 'RANGED_ATTACK', item_id: 'i1', target_x: 12, target_y: 10, target_entity_id: 'm1' },
  ]);
});

test('non-duelist ranged item auto-aims the nearest visible enemy', () => {
  const dispatcher = new ToolbarDoubleClickDispatcher();
  const wand = item({ type: 'wand', range: 6, attack_cooldown: 0.4 });
  const { ctx, sent } = makeCtx({ equippedItems: { weapon: wand } });
  withCombatScene(ctx);
  assert.equal(dispatcher.dispatch(wand, ctx), true);
  assert.deepEqual(sent, [
    { type: 'RANGED_ATTACK', item_id: 'i1', target_x: 12, target_y: 10, target_entity_id: 'm1' },
  ]);
});

test('ranged auto-aim is swallowed while attack is on cooldown', () => {
  const dispatcher = new ToolbarDoubleClickDispatcher();
  const wand = item({ type: 'wand', range: 6 });
  const { ctx, sent } = makeCtx({ equippedItems: { weapon: wand } });
  withCombatScene(ctx);
  consumeAttackCooldown(100000);
  assert.equal(dispatcher.dispatch(wand, ctx), true);
  assert.deepEqual(sent, []);
});

test('non-auto-aim item (melee, non-duelist) is not consumed', () => {
  const dispatcher = new ToolbarDoubleClickDispatcher();
  const sword = item({ type: 'weapon', range: 1 });
  const { ctx } = makeCtx({ equippedItems: { weapon: sword } });
  assert.equal(dispatcher.dispatch(sword, ctx), false);
  assert.equal(dispatcher.dispatch(null, ctx), false);
});

test('custom handlers can be registered and are consulted (appended last)', () => {
  const handled = [];
  const custom = {
    canHandle: (it) => it.type === 'custom',
    handle: (it) => { handled.push(it.id); return true; },
  };
  const dispatcher = new ToolbarDoubleClickDispatcher([]);
  dispatcher.register(custom);
  assert.equal(dispatcher.dispatch(item({ type: 'custom' }), makeCtx().ctx), true);
  assert.deepEqual(handled, ['i1']);
});

test('buildCandidateTargets merges hostile mobs and enemy players, skips self/allies', () => {
  const entitiesRef = {
    current: {
      mobs: { m1: { id: 'm1', hp: 5, faction: 'enemy' }, m2: { id: 'm2', hp: 5, faction: 'player' } },
      players: {
        me: { id: 'me', faction: 'player' },
        red: { id: 'red', faction: 'enemy' },
        downed: { id: 'downed', faction: 'enemy', is_downed: true },
      },
    },
  };
  const targets = buildCandidateTargets(entitiesRef, 'me', 'player');
  assert.deepEqual(Object.keys(targets).sort(), ['m1', 'm2', 'red']);
  assert.equal(targets.red.faction, 'enemy');
});