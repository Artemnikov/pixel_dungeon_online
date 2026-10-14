import test from 'node:test';
import assert from 'node:assert/strict';
import { DirectionalMoveCommand } from './DirectionalMoveCommand.ts';
import * as movementPredictor from '../../../net/movementPredictor';

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
    grid: Array.from({ length: 25 }, () => Array(25).fill(2)),
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
    isCameraDetachedRef: { current: false },
    panOffsetRef: { current: { x: 0, y: 0 } },
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

test('DirectionalMoveCommand: a held key continues moving as each turn arrives', () => {
  const pressedKeys = new Set(['KeyD']);
  const command = new DirectionalMoveCommand(pressedKeys);
  const ctx = createContext({
    gameModeRef: { current: 'turnbased' },
    canActRef: { current: true },
    // Zero step duration so animation pacing never gates the synthetic
    // same-millisecond turn transitions below.
    myPlayer: { ...createPlayer(), step_duration_ms: 0 },
  });

  command.syncMoveIntent(ctx, true);
  assert.equal(ctx.socket.sent.filter((m) => m.type === 'MOVE').length, 1);
  // Spending the turn locks input until the next STATE_UPDATE re-allows it.
  assert.equal(ctx.canActRef.current, false);

  // The next turn arriving looks like canAct flipping back to true while the
  // same vector is still held: paceStep (driven by the pump) takes the step.
  ctx.canActRef.current = true;
  command.paceStep(ctx);
  assert.equal(ctx.socket.sent.filter((m) => m.type === 'MOVE').length, 2);
  assert.equal(ctx.canActRef.current, false);

  // Releasing and pressing again is a new turn's worth of movement.
  pressedKeys.delete('KeyD');
  command.syncMoveIntent(ctx, false);
  ctx.canActRef.current = true;
  pressedKeys.add('KeyD');
  command.syncMoveIntent(ctx, true);
  assert.equal(ctx.socket.sent.filter((m) => m.type === 'MOVE').length, 3);
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

test('DirectionalMoveCommand: canExecute registers direction keys even when it is not my turn', () => {
  const command = new DirectionalMoveCommand(new Set());
  // Ungated so chorded diagonals and keyups are never swallowed while waiting;
  // syncMoveIntent/paceStep decide whether a turn may actually be spent.
  const waiting = createContext({
    gameModeRef: { current: 'turnbased' },
    canActRef: { current: false },
  });
  assert.equal(command.canExecute('KeyD', waiting), true);

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

test('DirectionalMoveCommand: paceStep auto-walks a held key in a turn room when it can act', () => {
  const pressedKeys = new Set(['KeyD']);
  const command = new DirectionalMoveCommand(pressedKeys);
  const ctx = createContext({
    gameModeRef: { current: 'turnbased' },
    canActRef: { current: true },
    myPlayer: { ...createPlayer(), step_duration_ms: 0 },
  });

  command.paceStep(ctx);
  const moves = ctx.socket.sent.filter((m) => m.type === 'MOVE');
  assert.equal(moves.length, 1);
  assert.equal(moves[0].direction, 'RIGHT');
  assert.equal(ctx.canActRef.current, false);
});

test('DirectionalMoveCommand: paceStep stays quiet while waiting for the turn', () => {
  const pressedKeys = new Set(['KeyD']);
  const command = new DirectionalMoveCommand(pressedKeys);
  const ctx = createContext({
    gameModeRef: { current: 'turnbased' },
    canActRef: { current: false },
  });

  command.paceStep(ctx);
  assert.deepEqual(ctx.socket.sent, []);
  assert.equal(ctx.canActRef.current, false);
});

test('DirectionalMoveCommand: paceStep does not outpace the walk animation in a turn room', () => {
  const pressedKeys = new Set(['KeyD']);
  const command = new DirectionalMoveCommand(pressedKeys);
  const ctx = createContext({
    gameModeRef: { current: 'turnbased' },
    canActRef: { current: true },
    myPlayer: { ...createPlayer(), step_duration_ms: 60000 },
  });

  command.syncMoveIntent(ctx, true);
  assert.equal(ctx.socket.sent.filter((m) => m.type === 'MOVE').length, 1);

  // A turn arriving before the previous step's animation finished is not spent.
  ctx.canActRef.current = true;
  command.paceStep(ctx);
  assert.equal(ctx.socket.sent.filter((m) => m.type === 'MOVE').length, 1);
  assert.equal(ctx.canActRef.current, true);
});

test('DirectionalMoveCommand: a chorded diagonal continues as a diagonal next turn', () => {
  const pressedKeys = new Set();
  const command = new DirectionalMoveCommand(pressedKeys);
  const ctx = createContext({
    gameModeRef: { current: 'turnbased' },
    canActRef: { current: true },
    myPlayer: { ...createPlayer(), step_duration_ms: 0 },
  });

  // First chord key lands and spends the turn on a cardinal step...
  pressedKeys.add('KeyW');
  command.execute('KeyW', ctx, true);
  assert.equal(ctx.socket.sent.filter((m) => m.type === 'MOVE').length, 1);
  assert.equal(ctx.canActRef.current, false);

  // ...the second key is pressed while the turn is spent: no extra MOVE, but
  // the keydown must register so the combined vector survives.
  pressedKeys.add('KeyD');
  command.execute('KeyD', ctx, true);
  assert.equal(ctx.socket.sent.filter((m) => m.type === 'MOVE').length, 1);

  // Next turn: the held chord steps diagonally.
  ctx.canActRef.current = true;
  command.paceStep(ctx);
  const moves = ctx.socket.sent.filter((m) => m.type === 'MOVE');
  assert.equal(moves.length, 2);
  assert.equal(moves[1].direction, 'UP_RIGHT');
  assert.equal(ctx.canActRef.current, false);
});

test('DirectionalMoveCommand: reattaches camera and clears panOffset on move intent', () => {
  const pressedKeys = new Set(['KeyD']);
  const command = new DirectionalMoveCommand(pressedKeys);
  const isCameraDetachedRef = { current: true };
  const panOffsetRef = { current: { x: 50, y: -20 } };
  const ctx = createContext({
    isCameraDetachedRef,
    panOffsetRef,
  });

  command.syncMoveIntent(ctx, true);
  assert.equal(isCameraDetachedRef.current, false);
  assert.deepEqual(panOffsetRef.current, { x: 0, y: 0 });
});

test('DirectionalMoveCommand: canExecute refuses movement when player is downed or dead', () => {
  const command = new DirectionalMoveCommand(new Set());
  const downedCtx = createContext({
    myPlayer: { ...createPlayer(), is_downed: true },
  });
  assert.equal(command.canExecute('KeyD', downedCtx), false);

  const deadCtx = createContext({
    myPlayer: { ...createPlayer(), is_alive: false },
  });
  assert.equal(command.canExecute('KeyD', deadCtx), false);
});

test('DirectionalMoveCommand: chorded diagonal keys within chord window send exactly 1 diagonal step in turn mode', () => {
  const pressedKeys = new Set();
  const command = new DirectionalMoveCommand(pressedKeys, undefined, 35);
  const ctx = createContext({
    gameModeRef: { current: 'turnbased' },
    canActRef: { current: true },
    myPlayer: { ...createPlayer(), step_duration_ms: 0 },
  });

  // First key lands and is buffered in chord window:
  pressedKeys.add('KeyW');
  command.execute('KeyW', ctx, true);
  assert.equal(ctx.socket.sent.filter((m) => m.type === 'MOVE').length, 0);
  assert.equal(ctx.canActRef.current, true);

  // Second key lands within chord window: forms UP_RIGHT diagonal and fires immediately!
  pressedKeys.add('KeyD');
  command.execute('KeyD', ctx, true);
  const moves = ctx.socket.sent.filter((m) => m.type === 'MOVE');
  assert.equal(moves.length, 1);
  assert.equal(moves[0].direction, 'UP_RIGHT');
  assert.equal(ctx.canActRef.current, false);

  // Next turn continues walking diagonally:
  ctx.canActRef.current = true;
  command.paceStep(ctx);
  const movesAfter = ctx.socket.sent.filter((m) => m.type === 'MOVE');
  assert.equal(movesAfter.length, 2);
  assert.equal(movesAfter[1].direction, 'UP_RIGHT');
  assert.equal(ctx.canActRef.current, false);
});

test('DirectionalMoveCommand: chorded diagonal keys within chord window send 1 MOVE_STEP in real-time mode', () => {
  movementPredictor.clear();
  const pressedKeys = new Set();
  const command = new DirectionalMoveCommand(pressedKeys, undefined, 35);
  const ctx = createContext({
    gameModeRef: { current: 'realtime' },
  });

  pressedKeys.add('KeyW');
  command.execute('KeyW', ctx, true);
  assert.equal(ctx.socket.sent.length, 0);

  pressedKeys.add('KeyD');
  command.execute('KeyD', ctx, true);
  assert.equal(ctx.socket.sent.length, 1);
  assert.equal(ctx.socket.sent[0].type, 'MOVE_STEP');
  assert.equal(ctx.socket.sent[0].dx, 1);
  assert.equal(ctx.socket.sent[0].dy, -1);
});

test('DirectionalMoveCommand: quick tap flushes cardinal step immediately on keyup', () => {
  movementPredictor.clear();
  const pressedKeys = new Set();
  const command = new DirectionalMoveCommand(pressedKeys, undefined, 35);
  const ctx = createContext({
    gameModeRef: { current: 'realtime' },
  });

  pressedKeys.add('KeyW');
  command.execute('KeyW', ctx, true);
  assert.equal(ctx.socket.sent.length, 0);

  pressedKeys.delete('KeyW');
  command.execute('KeyW', ctx, false);
  assert.equal(ctx.socket.sent.length, 2);
  assert.equal(ctx.socket.sent[0].type, 'MOVE_STEP');
  assert.equal(ctx.socket.sent[0].dx, 0);
  assert.equal(ctx.socket.sent[0].dy, -1);
  assert.equal(ctx.socket.sent[1].type, 'MOVE_STOP');
});

test('DirectionalMoveCommand: single cardinal key held past chord delay sends move', async () => {
  movementPredictor.clear();
  const pressedKeys = new Set();
  const command = new DirectionalMoveCommand(pressedKeys, undefined, 35);
  const ctx = createContext({
    gameModeRef: { current: 'realtime' },
  });

  pressedKeys.add('KeyW');
  command.execute('KeyW', ctx, true);
  assert.equal(ctx.socket.sent.length, 0);

  await new Promise((resolve) => setTimeout(resolve, 50));
  assert.equal(ctx.socket.sent.length, 1);
  assert.equal(ctx.socket.sent[0].type, 'MOVE_STEP');
  assert.equal(ctx.socket.sent[0].dx, 0);
  assert.equal(ctx.socket.sent[0].dy, -1);
});
