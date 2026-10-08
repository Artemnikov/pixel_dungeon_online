import test from 'node:test';
import assert from 'node:assert/strict';
import { QuickslotCommand } from './QuickslotCommand.ts';
import { WaitEmergencyDrinkCommand } from './WaitEmergencyDrinkCommand.ts';

function turnContext(mode, canAct) {
  return {
    gameModeRef: { current: mode },
    canActRef: { current: canAct },
    itemsById: { potion: { id: 'potion', kind: 'Potion' } },
    quickslot: { slots: [{ item_id: 'potion' }] },
    handleToolbarClick: () => { clicks += 1; },
    triggerWait: () => { waits += 1; },
  };
}

let clicks = 0;
let waits = 0;

test.beforeEach(() => { clicks = 0; waits = 0; });

test('QuickslotCommand: a turn room refuses item use when it is not my turn', () => {
  const command = new QuickslotCommand();
  assert.equal(command.canExecute('Digit1', turnContext('turnbased', false)), false);
  assert.equal(command.canExecute('Digit1', turnContext('turnbased', true)), true);
  // Real-time rooms are never gated.
  assert.equal(command.canExecute('Digit1', turnContext('realtime', false)), true);
});

test('QuickslotCommand: only a digit key is handled', () => {
  const command = new QuickslotCommand();
  assert.equal(command.canExecute('KeyQ', turnContext('realtime', true)), false);
});

test('QuickslotCommand: an empty slot does nothing', () => {
  const command = new QuickslotCommand();
  const ctx = { ...turnContext('turnbased', true), quickslot: { slots: [{ item_id: null }] } };
  command.execute('Digit1', ctx, true);
  assert.equal(clicks, 0);
});

test('WaitEmergencyDrinkCommand: a turn room refuses Wait when it is not my turn', () => {
  const command = new WaitEmergencyDrinkCommand();
  assert.equal(command.canExecute('Space', turnContext('turnbased', false)), false);
  assert.equal(command.canExecute('Space', turnContext('turnbased', true)), true);
  assert.equal(command.canExecute('Space', turnContext('realtime', false)), true);
  assert.equal(command.canExecute('KeyW', turnContext('realtime', true)), false);
});

test('WaitEmergencyDrinkCommand: Space waits when no emergency potion is carried', () => {
  const command = new WaitEmergencyDrinkCommand();
  const ctx = { ...turnContext('turnbased', true), emergencyDrinkItem: null };
  command.execute('Space', ctx, true);
  assert.equal(waits, 1);
  assert.equal(clicks, 0);
});

test('WaitEmergencyDrinkCommand: Space drinks the emergency potion when carried', () => {
  const command = new WaitEmergencyDrinkCommand();
  let drank = 0;
  const ctx = {
    ...turnContext('turnbased', true),
    emergencyDrinkItem: { id: 'potion', kind: 'Potion' },
    onEmergencyDrink: () => { drank += 1; },
  };
  command.execute('Space', ctx, true);
  assert.equal(drank, 1);
  assert.equal(waits, 0);
});
