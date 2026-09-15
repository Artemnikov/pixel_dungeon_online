import { test } from 'node:test';
import assert from 'node:assert/strict';
import { WindowManager } from './WindowManager.ts';
import { WindowLevel } from './WindowTypes.ts';

test('WindowManager: registers and unregisters windows', () => {
  const wm = new WindowManager();
  assert.equal(wm.hasActiveWindows(), false);

  wm.register({ id: 'wnd1', level: WindowLevel.BASE });
  assert.equal(wm.hasActiveWindows(), true);
  assert.equal(wm.getWindows().length, 1);

  wm.unregister('wnd1');
  assert.equal(wm.hasActiveWindows(), false);
  assert.equal(wm.getWindows().length, 0);
});

test('WindowManager: resolves priority by window level (higher level on top)', () => {
  const wm = new WindowManager();
  wm.register({ id: 'base', level: WindowLevel.BASE });
  wm.register({ id: 'dialog', level: WindowLevel.DIALOG });
  wm.register({ id: 'secondary', level: WindowLevel.SECONDARY });

  const windows = wm.getWindows();
  assert.equal(windows[0].id, 'dialog');
  assert.equal(windows[1].id, 'secondary');
  assert.equal(windows[2].id, 'base');

  assert.equal(wm.getTopWindow()?.id, 'dialog');
});

test('WindowManager: resolves LIFO order for windows with same level', () => {
  const wm = new WindowManager();
  wm.register({ id: 'win1', level: WindowLevel.BASE });
  wm.register({ id: 'win2', level: WindowLevel.BASE });
  wm.register({ id: 'win3', level: WindowLevel.BASE });

  const windows = wm.getWindows();
  assert.equal(windows[0].id, 'win3');
  assert.equal(windows[1].id, 'win2');
  assert.equal(windows[2].id, 'win1');
});

test('WindowManager: updating existing window retains order but updates callback', () => {
  const wm = new WindowManager();
  let calls = [];

  wm.register({
    id: 'first',
    level: WindowLevel.BASE,
    onClose: () => calls.push('first-v1'),
  });

  wm.register({
    id: 'second',
    level: WindowLevel.BASE,
    onClose: () => calls.push('second-v1'),
  });

  wm.register({
    id: 'first',
    level: WindowLevel.BASE,
    onClose: () => calls.push('first-v2'),
  });

  assert.equal(wm.getTopWindow()?.id, 'second');

  wm.unregister('second');
  assert.equal(wm.getTopWindow()?.id, 'first');

  const handled = wm.handleEscape();
  assert.equal(handled, true);
  assert.deepEqual(calls, ['first-v2']);
});

test('WindowManager: update() modifies window properties without re-ordering and notifies subscribers', () => {
  const wm = new WindowManager();
  let notifications = 0;
  const unsub = wm.subscribe(() => { notifications++; });

  wm.register({ id: 'win1', level: WindowLevel.BASE, closeOnEscape: true });
  assert.equal(notifications, 1);

  wm.update('win1', { closeOnEscape: false });
  assert.equal(notifications, 2);
  assert.equal(wm.getTopWindow()?.closeOnEscape, false);

  unsub();
});

test('WindowManager: top window with closeOnEscape=false consumes escape and blocks underlying windows', () => {
  const wm = new WindowManager();
  let calls = [];

  wm.register({
    id: 'base',
    level: WindowLevel.BASE,
    onClose: () => calls.push('base'),
  });

  wm.register({
    id: 'modal',
    level: WindowLevel.DIALOG,
    closeOnEscape: false,
    onClose: () => calls.push('modal'),
  });

  const handled = wm.handleEscape();
  assert.equal(handled, true);
  assert.deepEqual(calls, []);
  assert.equal(wm.hasActiveWindows(), true);
});

test('WindowManager: triggers fallback handler when no window is active', () => {
  const wm = new WindowManager();
  let fallbackCalls = 0;

  wm.setFallbackHandler(() => {
    fallbackCalls++;
    return true;
  });

  const handled = wm.handleEscape();
  assert.equal(handled, true);
  assert.equal(fallbackCalls, 1);
});

test('WindowManager: handleKeyDown routes Digit1..Digit3 to digitActions of top window', () => {
  const wm = new WindowManager();
  const calls = [];

  wm.register({
    id: 'castbar',
    level: WindowLevel.FLOATING,
    digitActions: [
      () => calls.push('spell-1'),
      () => calls.push('spell-2'),
      () => calls.push('spell-3'),
    ],
  });

  assert.equal(wm.handleKeyDown('Digit1'), true);
  assert.equal(wm.handleKeyDown('Digit2'), true);
  assert.equal(wm.handleKeyDown('Digit3'), true);
  assert.deepEqual(calls, ['spell-1', 'spell-2', 'spell-3']);
});

test('WindowManager: handleKeyDown preserves dynamic getters across state updates', () => {
  const wm = new WindowManager();
  let state = 'initial';
  const calls = [];

  const entry = {
    id: 'dynamic-window',
    level: WindowLevel.DIALOG,
    get digitActions() {
      return [() => calls.push(state)];
    },
  };

  wm.register(entry);
  state = 'updated';

  assert.equal(wm.handleKeyDown('Digit1'), true);
  assert.deepEqual(calls, ['updated']);
});

test('WindowManager: handleKeyDown handles out-of-bounds digits safely for modal window', () => {
  const wm = new WindowManager();
  const calls = [];

  wm.register({
    id: 'castbar',
    level: WindowLevel.FLOATING,
    modal: true,
    digitActions: [
      () => calls.push('spell-1'),
      () => calls.push('spell-2'),
    ],
  });

  assert.equal(wm.handleKeyDown('Digit3'), true);
  assert.equal(wm.handleKeyDown('Digit0'), true);
  assert.deepEqual(calls, []);
});

test('WindowManager: handleKeyDown non-modal window allows unhandled keys to pass through', () => {
  const wm = new WindowManager();
  const spellsCast = [];

  wm.register({
    id: 'wnd-cleric-castbar',
    level: WindowLevel.SECONDARY,
    modal: false,
    digitActions: [
      () => spellsCast.push('guiding_light'),
      () => spellsCast.push('holy_ward'),
      () => spellsCast.push('radiance'),
    ],
  });

  assert.equal(wm.handleKeyDown('KeyW'), false);
  assert.equal(wm.handleKeyDown('KeyA'), false);
  assert.equal(wm.handleKeyDown('KeyS'), false);
  assert.equal(wm.handleKeyDown('KeyD'), false);
  assert.equal(wm.handleKeyDown('ArrowUp'), false);
  assert.equal(wm.handleKeyDown('Numpad8'), false);

  assert.equal(wm.handleKeyDown('Digit1'), true);
  assert.equal(wm.handleKeyDown('Digit2'), true);
  assert.equal(wm.handleKeyDown('Digit3'), true);
  assert.deepEqual(spellsCast, ['guiding_light', 'holy_ward', 'radiance']);

  assert.equal(wm.handleKeyDown('Digit4'), false);
});

test('WindowManager: handleKeyDown prioritizes top-level window over background window', () => {
  const wm = new WindowManager();
  const calls = [];

  wm.register({
    id: 'base-castbar',
    level: WindowLevel.BASE,
    digitActions: [
      () => calls.push('base-1'),
    ],
  });

  wm.register({
    id: 'top-modal',
    level: WindowLevel.DIALOG,
    digitActions: [
      () => calls.push('top-1'),
    ],
  });

  assert.equal(wm.handleKeyDown('Digit1'), true);
  assert.deepEqual(calls, ['top-1']);

  wm.unregister('top-modal');
  assert.equal(wm.handleKeyDown('Digit1'), true);
  assert.deepEqual(calls, ['top-1', 'base-1']);
});

test('WindowManager: custom onKeyDown and onKeyUp hooks are invoked', () => {
  const wm = new WindowManager();
  const calls = [];

  wm.register({
    id: 'custom-keys',
    level: WindowLevel.DIALOG,
    onKeyDown: (code) => {
      if (code === 'KeyX') {
        calls.push('down-X');
        return true;
      }
      return false;
    },
    onKeyUp: (code) => {
      if (code === 'KeyX') {
        calls.push('up-X');
        return true;
      }
      return false;
    },
  });

  assert.equal(wm.handleKeyDown('KeyX'), true);
  assert.equal(wm.handleKeyUp('KeyX'), true);
  assert.deepEqual(calls, ['down-X', 'up-X']);
});
