import test from 'node:test';
import assert from 'node:assert/strict';
import { DirectionalMoveCommand } from './DirectionalMoveCommand.ts';

function createSocket() {
  const sent = [];
  return {
    sent,
    readyState: 1,
    send: (msg) => sent.push(JSON.parse(msg)),
  };
}

function createPlayer() {
  return {
    id: 'p1',
    name: 'Hero',
    pos: { x: 10, y: 10 },
    renderPos: { x: 10, y: 10 },
    is_downed: false,
  };
}

/** A context complete enough for both branches to run. */
function createContext(overrides = {}) {
  const socket = createSocket();
  return {
    socket,
    myPlayer: createPlayer(),
    myPlayerId: 'p1',
    grid: { get: () => 1, isWalkable: () => true, isBlockingEntity: () => false, at: () => 1 },
    entities: {
      players: {},
      mobs: {},
      items: [],
      traps: [],
      getEntityAt: () => null,
      getPlayers: () => ({}),
      getMobs: () => ({}),
    },
    playerAnimRef: { current: null },
    isRefocusingRef: { current: false },
    isDraggingRef: { current: false },
    ...overrides,
  };
}

test('DirectionalMoveCommand: a turn room sends one plain MOVE per press', () => {
  const pressedKeys = new Set();
  const command = new DirectionalMoveCommand(pressedKeys);
  const ctx = createContext({
    gameModeRef: { current: 'turnbased' },
    canActRef: { current: true },
  });

  pressedKeys.add('KeyD');
  command.execute('KeyD', ctx, true);

  const moves = ctx.socket.sent.filter((m) => m.type === 'MOVE');
  assert.equal(moves.length, 1);
  assert.equal(moves[0].direction, 'RIGHT');
  // No real-time plumbing may leak into a turn room: its dispatcher drops these.
  const forbidden = ['MOVE_INTENT', 'MOVE_STEP', 'MOVE_STOP'];
  assert.deepEqual(ctx.socket.sent.filter((m) => forbidden.includes(m.type)), []);
});

test('DirectionalMoveCommand: a held key does not repeat moves in a turn room', () => {
  const pressedKeys = new Set(['KeyD']);
  const command = new DirectionalMoveCommand(pressedKeys);
  const ctx = createContext({
    gameModeRef: { current: 'turnbased' },
    canActRef: { current: true },
  });

  command.syncMoveIntent(ctx, true);
  // Auto-repeat and the next turn arriving both look like this: same vector held.
  command.syncMoveIntent(ctx, true);
  assert.equal(ctx.socket.sent.filter((m) => m.type === 'MOVE').length, 1);

  // Releasing and pressing again is a new turn's worth of movement.
  pressedKeys.delete('KeyD');
  command.syncMoveIntent(ctx, false);
  pressedKeys.add('KeyD');
  command.syncMoveIntent(ctx, true);
  assert.equal(ctx.socket.sent.filter((m) => m.type === 'MOVE').length, 2);
});

test('DirectionalMoveCommand: releasing a key is silent in a turn room', () => {
  const pressedKeys = new Set(['KeyD']);
  const command = new DirectionalMoveCommand(pressedKeys);
  const ctx = createContext({
    gameModeRef: { current: 'turnbased' },
    canActRef: { current: true },
  });

  command.syncMoveIntent(ctx, true);
  pressedKeys.delete('KeyD');
  command.syncMoveIntent(ctx, false);

  assert.deepEqual(ctx.socket.sent.filter((m) => m.type === 'MOVE_STOP'), []);
  assert.equal(ctx.socket.sent.filter((m) => m.type === 'MOVE').length, 1);
});

test('DirectionalMoveCommand: canExecute refuses movement when it is not my turn', () => {
  const command = new DirectionalMoveCommand(new Set());
  const waiting = createContext({
    gameModeRef: { current: 'turnbased' },
    canActRef: { current: false },
  });
  assert.equal(command.canExecute('KeyD', waiting), false);

  const mine = createContext({
    gameModeRef: { current: 'turnbased' },
    canActRef: { current: true },
  });
  assert.equal(command.canExecute('KeyD', mine), true);
});

test('DirectionalMoveCommand: a real-time room is never gated and never sends a turn MOVE', () => {
  const pressedKeys = new Set();
  const command = new DirectionalMoveCommand(pressedKeys);
  // canActRef is always defined (App owns it), so it must not imply turn mode.
  const ctx = createContext({
    gameModeRef: { current: 'realtime' },
    canActRef: { current: false },
  });

  assert.equal(command.canExecute('KeyD', ctx), true);

  pressedKeys.add('KeyD');
  command.syncMoveIntent(ctx, true);
  assert.deepEqual(ctx.socket.sent.filter((m) => m.type === 'MOVE'), []);

  pressedKeys.delete('KeyD');
  command.syncMoveIntent(ctx, false);
  assert.equal(ctx.socket.sent.filter((m) => m.type === 'MOVE_STOP').length, 1);
});

test('DirectionalMoveCommand: paceStep never auto-walks in a turn room', () => {
  const pressedKeys = new Set(['KeyD']);
  const command = new DirectionalMoveCommand(pressedKeys);
  const ctx = createContext({
    gameModeRef: { current: 'turnbased' },
    canActRef: { current: true },
  });

  command.paceStep(ctx);
  assert.deepEqual(ctx.socket.sent, []);
});
