import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ToolbarClickDispatcher,
  TARGETED_ACTIONS,
  HolyTomeClickHandler,
  PotionClickHandler,
  StaffClickHandler,
  DuelistWeaponClickHandler,
  TargetedWeaponClickHandler,
  EquippableWeaponClickHandler,
  WearableClickHandler,
  ThrowableClickHandler,
  WandClickHandler,
  DefaultActionClickHandler,
} from './ToolbarClickDispatcher.ts';

const item = (patch) => ({ id: 'i1', name: 'Test Item', ...patch });

function makeCtx(overrides = {}) {
  const sent = [];
  const executed = [];
  const equipped = [];
  const state = { calls: [] };
  const ctx = {
    send: (msg) => sent.push(msg),
    equippedItems: overrides.equippedItems,
    belongings: overrides.belongings,
    myStats: overrides.myStats,
    targetingMode: overrides.targetingMode,
    equipItem: (itemId) => equipped.push(itemId),
    executeItemAction: (itemId, action, opts) => executed.push({ itemId, action, opts }),
    onOpenClericCastBar: overrides.onOpenClericCastBar,
  };
  ctx.setTargetingMode = (mode) => {
    state.calls.push(mode);
    if (typeof mode === 'function') {
      ctx.targetingMode = mode(ctx.targetingMode);
    } else {
      ctx.targetingMode = mode;
    }
  };
  return { ctx, sent, executed, equipped, state };
}

test('TARGETED_ACTIONS: exported and contains the arming actions', () => {
  assert.ok(TARGETED_ACTIONS.includes('ZAP'));
  assert.ok(TARGETED_ACTIONS.includes('THROW'));
  assert.ok(TARGETED_ACTIONS.includes('SHOOT'));
});

test('holy tome opens the cleric cast bar', () => {
  let opened = false;
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx } = makeCtx({ onOpenClericCastBar: () => { opened = true; } });
  assert.equal(dispatcher.dispatch(item({ kind: 'holy_tome' }), ctx), true);
  assert.equal(opened, true);
});

test('potion sends USE_ITEM', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx, sent } = makeCtx();
  assert.equal(dispatcher.dispatch(item({ type: 'potion' }), ctx), true);
  assert.deepEqual(sent, [{ type: 'USE_ITEM', item_id: 'i1' }]);
});

test('staff with default_action routes through executeItemAction', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx, executed } = makeCtx();
  assert.equal(dispatcher.dispatch(item({ type: 'weapon', kind: 'staff', default_action: 'ZAP' }), ctx), true);
  assert.deepEqual(executed, [{ itemId: 'i1', action: 'ZAP', opts: { fromQuickbar: true } }]);
});

test('armed staff click disarms targeting instead of re-firing', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx, executed, state } = makeCtx({ targetingMode: { itemId: 'i1', action: 'ZAP', fromQuickbar: true } });
  assert.equal(dispatcher.dispatch(item({ type: 'weapon', kind: 'staff', default_action: 'ZAP' }), ctx), true);
  assert.deepEqual(executed, []);
  assert.deepEqual(state.calls, [false]);
});

test('duelist unequipped weapon equips it', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx, equipped } = makeCtx({
    myStats: { classType: 'duelist', weaponCharge: 3 },
    equippedItems: { weapon: { id: 'other' } },
  });
  assert.equal(dispatcher.dispatch(item({ type: 'weapon', name: 'Rapier', range: 1 }), ctx), true);
  assert.deepEqual(equipped, ['i1']);
});

test('duelist equipped weapon with target skill arms finisher targeting', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx: base, state } = makeCtx();
  const ctx = {
    ...base,
    myStats: { classType: 'duelist', weaponCharge: 1 },
    equippedItems: { weapon: { id: 'i1', name: 'Rapier', range: 1 } },
  };
  assert.equal(dispatcher.dispatch(item({ type: 'weapon', name: 'Rapier', range: 1 }), ctx), true);
  assert.deepEqual(state.calls, [{ duelistFinisher: true, itemId: 'i1', useSecondary: false, fromQuickbar: true }]);
});

test('duelist equipped non-target skill fires primary finisher / secondary weapon ability', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx: primaryCtx, sent } = makeCtx({
    myStats: { classType: 'duelist', weaponCharge: 1 },
    equippedItems: { weapon: { id: 'i1', name: 'Quarterstaff', range: 1 } },
  });
  assert.equal(dispatcher.dispatch(item({ type: 'weapon', name: 'Quarterstaff', range: 1 }), primaryCtx), true);
  assert.deepEqual(sent, [{ type: 'DUELIST_FINISHER' }]);

  const { ctx: secondaryCtx, sent: sent2 } = makeCtx({
    equippedItems: { weapon: { id: 'primary' } },
    belongings: { secondary_weapon: { id: 'i1', name: 'Quarterstaff', range: 1 } },
    myStats: { classType: 'duelist', weaponCharge: 1 },
  });
  assert.equal(dispatcher.dispatch(item({ type: 'weapon', name: 'Quarterstaff', range: 1 }), secondaryCtx), true);
  assert.deepEqual(sent2, [{ type: 'USE_WEAPON_ABILITY', use_secondary: true }]);
});

test('duelist finisher armed for the item disarms on click', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx: base, state } = makeCtx();
  const ctx = {
    ...base,
    myStats: { classType: 'duelist', weaponCharge: 1 },
    equippedItems: { weapon: { id: 'i1', name: 'Rapier', range: 1 } },
    targetingMode: { duelistFinisher: true, itemId: 'i1', useSecondary: false },
  };
  assert.equal(dispatcher.dispatch(item({ type: 'weapon', name: 'Rapier', range: 1 }), ctx), true);
  assert.deepEqual(state.calls, [false]);
});

test('duelist bow falls through to targeted default action (SHOOT)', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx, executed } = makeCtx({
    myStats: { classType: 'duelist', weaponCharge: 1 },
    equippedItems: { weapon: { id: 'i1', name: 'Bow' } },
  });
  const bow = item({ type: 'weapon', name: 'Bow', kind: 'bow', default_action: 'SHOOT', range: 6 });
  assert.equal(dispatcher.dispatch(bow, ctx), true);
  assert.deepEqual(executed, [{ itemId: 'i1', action: 'SHOOT', opts: { fromQuickbar: true } }]);
});

test('ranged weapon with targeted default action fires via executeItemAction', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx, executed } = makeCtx();
  const bow = item({ type: 'weapon', name: 'Bow', kind: 'bow', default_action: 'SHOOT', range: 6 });
  assert.equal(dispatcher.dispatch(bow, ctx), true);
  assert.deepEqual(executed, [{ itemId: 'i1', action: 'SHOOT', opts: { fromQuickbar: true } }]);
});

test('unequipped melee weapon equips and clears targeting', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx, equipped, state } = makeCtx();
  assert.equal(dispatcher.dispatch(item({ type: 'weapon', range: 1 }), ctx), true);
  assert.deepEqual(equipped, ['i1']);
  assert.deepEqual(state.calls, [false]);
});

test('unequipped ranged weapon equips and arms string targeting', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx, equipped, state } = makeCtx();
  assert.equal(dispatcher.dispatch(item({ type: 'weapon', range: 5 }), ctx), true);
  assert.deepEqual(equipped, ['i1']);
  assert.deepEqual(state.calls, ['i1']);
});

test('equipped ranged weapon toggles targeting mode', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx, state } = makeCtx({ targetingMode: true });
  ctx.equippedItems = { weapon: { id: 'i1', range: 5 } };
  assert.equal(dispatcher.dispatch(item({ type: 'weapon', range: 5 }), ctx), true);
  assert.equal(state.calls.length, 1);
  assert.equal(ctx.targetingMode, false);
});

test('wearable equips', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx, equipped } = makeCtx();
  assert.equal(dispatcher.dispatch(item({ type: 'wearable' }), ctx), true);
  assert.deepEqual(equipped, ['i1']);
});

test('throwable arms THROW targeting and disarms on re-click', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx: base, state } = makeCtx();
  const ctx = { ...base };
  assert.equal(dispatcher.dispatch(item({ type: 'throwable' }), ctx), true);
  assert.deepEqual(state.calls, [{ itemId: 'i1', action: 'THROW', fromQuickbar: true }]);

  ctx.targetingMode = { itemId: 'i1', action: 'THROW', fromQuickbar: true };
  assert.equal(dispatcher.dispatch(item({ type: 'throwable' }), ctx), true);
  assert.deepEqual(state.calls[1], false);
});

test('seed item arms THROW targeting too', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx, state } = makeCtx();
  assert.equal(dispatcher.dispatch(item({ type: 'seed', throw_behavior: 'seed' }), ctx), true);
  assert.deepEqual(state.calls, [{ itemId: 'i1', action: 'THROW', fromQuickbar: true }]);
});

test('wand arms ZAP via executeItemAction and disarms on re-click', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx: base, executed, state } = makeCtx();
  const ctx = { ...base };
  assert.equal(dispatcher.dispatch(item({ type: 'wand' }), ctx), true);
  assert.deepEqual(executed, [{ itemId: 'i1', action: 'ZAP', opts: { fromQuickbar: true } }]);

  ctx.targetingMode = { itemId: 'i1', action: 'ZAP', fromQuickbar: true };
  assert.equal(dispatcher.dispatch(item({ type: 'wand' }), ctx), true);
  assert.deepEqual(state.calls[0], false);
});

test('generic default_action item routes through executeItemAction', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx, executed } = makeCtx();
  assert.equal(dispatcher.dispatch(item({ type: 'scroll', default_action: 'READ' }), ctx), true);
  assert.deepEqual(executed, [{ itemId: 'i1', action: 'READ', opts: { fromQuickbar: true } }]);
});

test('unrecognized item is not consumed and null item short-circuits', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx, sent, executed, equipped } = makeCtx();
  assert.equal(dispatcher.dispatch(item({ type: 'scroll' }), ctx), false);
  assert.equal(dispatcher.dispatch(null, ctx), false);
  assert.deepEqual(sent, []);
  assert.deepEqual(executed, []);
  assert.deepEqual(equipped, []);
});

test('weapon with targeted default_action goes to TargetedWeapon, not Throwable/Equippable', () => {
  const dispatcher = new ToolbarClickDispatcher();
  const { ctx, executed } = makeCtx();
  const weapon = item({ type: 'weapon', default_action: 'THROW', range: 1 });
  assert.equal(dispatcher.dispatch(weapon, ctx), true);
  // Precedence: targeted default actions fire before equipping/arming.
  assert.deepEqual(executed, [{ itemId: 'i1', action: 'THROW', opts: { fromQuickbar: true } }]);
});

test('custom handlers can be registered and are consulted (appended last)', () => {
  const handled = [];
  const custom = {
    canHandle: (it) => it.type === 'custom',
    handle: (it) => { handled.push(it.id); return true; },
  };
  const dispatcher = new ToolbarClickDispatcher([]);
  dispatcher.register(custom);
  assert.equal(dispatcher.dispatch(item({ type: 'custom' }), makeCtx().ctx), true);
  assert.deepEqual(handled, ['i1']);
});

test('individual handlers expose their intent', () => {
  const ctx = {
    send: () => {}, setTargetingMode: () => {}, equipItem: () => {}, executeItemAction: () => {},
  };
  const tome = new HolyTomeClickHandler();
  const potion = new PotionClickHandler();
  const staff = new StaffClickHandler();
  const duelist = new DuelistWeaponClickHandler();
  const ranged = new TargetedWeaponClickHandler();
  const equippable = new EquippableWeaponClickHandler();
  const wearable = new WearableClickHandler();
  const throwable = new ThrowableClickHandler();
  const wand = new WandClickHandler();
  const generic = new DefaultActionClickHandler();

  assert.equal(tome.canHandle(item({ kind: 'holy_tome' }), ctx), true);
  assert.equal(potion.canHandle(item({ type: 'potion' }), ctx), true);
  assert.equal(staff.canHandle(item({ type: 'weapon', kind: 'staff' }), ctx), true);
  assert.equal(duelist.canHandle(item({ type: 'weapon' }), { ...ctx, myStats: { classType: 'duelist' } }), true);
  assert.equal(ranged.canHandle(item({ type: 'weapon', default_action: 'SHOOT' }), ctx), true);
  assert.equal(equippable.canHandle(item({ type: 'weapon' }), ctx), true);
  assert.equal(wearable.canHandle(item({ type: 'wearable' }), ctx), true);
  assert.equal(throwable.canHandle(item({ type: 'throwable' }), ctx), true);
  assert.equal(wand.canHandle(item({ type: 'wand' }), ctx), true);
  assert.equal(generic.canHandle(item({ default_action: 'READ' }), ctx), true);
  assert.equal(ranged.canHandle(item({ type: 'weapon' }), ctx), false);
});