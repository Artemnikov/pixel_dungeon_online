import test, { beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { resetAttackCooldown, consumeAttackCooldown } from '../../net/events/combat';
import {
  TargetingTapDispatcher,
  ArmorAbilityTapHandler,
  ComboMoveTapHandler,
  PrepStrikeTapHandler,
  DuelistFinisherTapHandler,
  ClericSpellTapHandler,
  ItemActionTapHandler,
  RangedWeaponTapHandler,
} from './TargetingTapDispatcher.ts';

function makeCtx(overrides = {}) {
  const sent = [];
  const calls = [];
  const ctx = {
    send: (msg) => sent.push(msg),
    equippedItems: { weapon: { id: 'w1', attack_cooldown: 0.5 } },
    entitiesRef: { current: { mobs: {} } },
    selectedEnemyIdRef: { current: null },
    setTargetingMode: (mode) => calls.push(mode),
    ...overrides,
  };
  return { ctx, sent, calls };
}

beforeEach(() => {
  resetAttackCooldown();
});

test('armor ability tap sends USE_ARMOR_ABILITY and disarms', () => {
  const dispatcher = new TargetingTapDispatcher();
  const { ctx, sent, calls } = makeCtx();
  assert.equal(dispatcher.dispatch({ ability: 'heroic_leap' }, 3, 4, ctx), true);
  assert.deepEqual(sent, [{ type: 'USE_ARMOR_ABILITY', ability: 'heroic_leap', target_x: 3, target_y: 4 }]);
  assert.deepEqual(calls, [false]);
});

test('combo move tap sends USE_COMBO_MOVE and disarms', () => {
  const dispatcher = new TargetingTapDispatcher();
  const { ctx, sent, calls } = makeCtx();
  assert.equal(dispatcher.dispatch({ comboMove: 'fencer_dash' }, 5, 6, ctx), true);
  assert.deepEqual(sent, [{ type: 'USE_COMBO_MOVE', move: 'fencer_dash', target_x: 5, target_y: 6 }]);
  assert.deepEqual(calls, [false]);
});

test('prep strike tap sends PREPARATION_STRIKE and disarms', () => {
  const dispatcher = new TargetingTapDispatcher();
  const { ctx, sent, calls } = makeCtx();
  assert.equal(dispatcher.dispatch({ prepStrike: true }, 1, 2, ctx), true);
  assert.deepEqual(sent, [{ type: 'PREPARATION_STRIKE', target_x: 1, target_y: 2 }]);
  assert.deepEqual(calls, [false]);
});

test('duelist finisher tap sends DUELIST_FINISHER or secondary weapon ability', () => {
  const dispatcher = new TargetingTapDispatcher();
  const { ctx: primary, sent: sent1, calls: calls1 } = makeCtx();
  assert.equal(dispatcher.dispatch({ duelistFinisher: true, itemId: 'sword' }, 7, 8, primary), true);
  assert.deepEqual(sent1, [{ type: 'DUELIST_FINISHER', target_x: 7, target_y: 8 }]);
  assert.deepEqual(calls1, [false]);

  const { ctx: secondary, sent: sent2 } = makeCtx();
  assert.equal(dispatcher.dispatch({ duelistFinisher: true, itemId: 'sword', useSecondary: true }, 7, 8, secondary), true);
  assert.deepEqual(sent2, [{ type: 'USE_WEAPON_ABILITY', target_x: 7, target_y: 8, use_secondary: true }]);
});

test('cleric spell tap sends CAST_CLERIC_SPELL and disarms', () => {
  const dispatcher = new TargetingTapDispatcher();
  const { ctx, sent, calls } = makeCtx();
  assert.equal(dispatcher.dispatch({ clericSpell: 'guiding_light' }, 9, 10, ctx), true);
  assert.deepEqual(sent, [{ type: 'CAST_CLERIC_SPELL', spell: 'guiding_light', target_x: 9, target_y: 10 }]);
  assert.deepEqual(calls, [false]);
});

test('item action tap with combat action ready consumes cooldown and executes', () => {
  const dispatcher = new TargetingTapDispatcher();
  const { ctx, sent, calls } = makeCtx();
  assert.equal(dispatcher.dispatch({ itemId: 'i1', action: 'THROW', fromQuickbar: true }, 2, 2, ctx), true);
  assert.deepEqual(sent, [
    { type: 'EXECUTE_ITEM_ACTION', item_id: 'i1', action: 'THROW', target_x: 2, target_y: 2 },
  ]);
  assert.deepEqual(calls, [false]);
});

test('item action tap with combat action on cooldown is swallowed', () => {
  const dispatcher = new TargetingTapDispatcher();
  const { ctx, sent, calls } = makeCtx();
  consumeAttackCooldown(100000);
  assert.equal(dispatcher.dispatch({ itemId: 'i1', action: 'ZAP' }, 2, 2, ctx), true);
  assert.deepEqual(sent, []);
  assert.deepEqual(calls, []);
});

test('non-combat item action bypasses the cooldown gate', () => {
  const dispatcher = new TargetingTapDispatcher();
  const { ctx, sent, calls } = makeCtx();
  consumeAttackCooldown(100000);
  assert.equal(dispatcher.dispatch({ itemId: 's1', action: 'PLANT_SEED' }, 2, 2, ctx), true);
  assert.deepEqual(sent, [
    { type: 'EXECUTE_ITEM_ACTION', item_id: 's1', action: 'PLANT_SEED', target_x: 2, target_y: 2 },
  ]);
  assert.deepEqual(calls, [false]);
});

test('string weapon mode fires RANGED_ATTACK and disarms', () => {
  const dispatcher = new TargetingTapDispatcher();
  const { ctx, sent, calls } = makeCtx();
  assert.equal(dispatcher.dispatch('w1', 3, 4, ctx), true);
  assert.deepEqual(sent, [
    { type: 'RANGED_ATTACK', item_id: 'w1', target_x: 3, target_y: 4, target_entity_id: null },
  ]);
  assert.deepEqual(calls, [false]);
});

test('string weapon mode tags the locked target via target_entity_id', () => {
  const dispatcher = new TargetingTapDispatcher();
  const { ctx, sent } = makeCtx({
    selectedEnemyIdRef: { current: 'm1' },
    entitiesRef: { current: { mobs: { m1: { renderPos: { x: 3, y: 4 } } } } },
  });
  assert.equal(dispatcher.dispatch('w1', 3, 4, ctx), true);
  assert.deepEqual(sent, [
    { type: 'RANGED_ATTACK', item_id: 'w1', target_x: 3, target_y: 4, target_entity_id: 'm1' },
  ]);
});

test('object mode without discriminator falls back to equipped ranged weapon', () => {
  const dispatcher = new TargetingTapDispatcher();
  const { ctx, sent, calls } = makeCtx();
  assert.equal(dispatcher.dispatch({ itemId: 'w1' }, 3, 4, ctx), true);
  assert.deepEqual(sent, [
    { type: 'RANGED_ATTACK', item_id: 'w1', target_x: 3, target_y: 4, target_entity_id: null },
  ]);
  // Mode wasn't a string, so targeting stays armed (setTargetingMode(true)).
  assert.deepEqual(calls, [true]);
});

test('unhandled mode returns false', () => {
  const dispatcher = new TargetingTapDispatcher();
  const { ctx, sent } = makeCtx({ equippedItems: { weapon: null } });
  assert.equal(dispatcher.dispatch({ itemId: 'x' }, 3, 4, ctx), false);
  assert.deepEqual(sent, []);
});

test('custom handlers can be registered and are consulted (appended last)', () => {
  const handled = [];
  const custom = {
    canHandle: (tm) => tm && tm.custom,
    handle: (tm, tx, ty) => { handled.push({ tm, tx, ty }); return true; },
  };
  const dispatcher = new TargetingTapDispatcher([]);
  dispatcher.register(custom);
  const { ctx } = makeCtx();
  assert.equal(dispatcher.dispatch({ custom: true }, 3, 4, ctx), true);
  assert.deepEqual(handled, [{ tm: { custom: true }, tx: 3, ty: 4 }]);
});

test('individual tap handlers expose their intent', () => {
  const ctx = { send: () => {}, equippedItems: {}, setTargetingMode: () => {} };
  const armor = new ArmorAbilityTapHandler();
  const combo = new ComboMoveTapHandler();
  const prep = new PrepStrikeTapHandler();
  const fs = new DuelistFinisherTapHandler();
  const cleric = new ClericSpellTapHandler();
  const action = new ItemActionTapHandler();
  const ranged = new RangedWeaponTapHandler();

  assert.equal(armor.canHandle({ ability: 'x' }, ctx), true);
  assert.equal(combo.canHandle({ comboMove: 'x' }, ctx), true);
  assert.equal(prep.canHandle({ prepStrike: true }, ctx), true);
  assert.equal(fs.canHandle({ duelistFinisher: true }, ctx), true);
  assert.equal(cleric.canHandle({ clericSpell: 'x' }, ctx), true);
  assert.equal(action.canHandle({ action: 'THROW' }, ctx), true);
  assert.equal(ranged.canHandle('w1', ctx), true);
  assert.equal(armor.canHandle({ comboMove: 'x' }, ctx), false);
  assert.equal(action.canHandle('w1', ctx), false);
});