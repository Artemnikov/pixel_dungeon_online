import test from 'node:test';
import assert from 'node:assert/strict';
import {
  MoveResultDispatcher,
  defaultMoveResultDispatcher,
  MovedResultHandler,
  BumpedResultHandler,
  BusyResultHandler,
  BumpStrategyRegistry,
  MeleeAttackBumpStrategy,
  OpenAlchemyBumpStrategy,
  PassiveBumpStrategy,
} from './MoveResultDispatcher.ts';

function createMockPlayer() {
  return {
    id: 'p1',
    name: 'Hero',
    pos: { x: 10, y: 10 },
    renderPos: { x: 10, y: 10 },
    is_downed: false,
    facing: 'RIGHT',
    flipX: false,
  };
}

test('MoveResultDispatcher: MovedResultHandler dispatches MOVE_STEP to socket', () => {
  const sentMessages = [];
  const mockSocket = {
    readyState: 1,
    send: (msg) => sentMessages.push(JSON.parse(msg)),
  };

  const player = createMockPlayer();
  const ctx = {
    myPlayer: player,
    socket: mockSocket,
    dx: 1,
    dy: 0,
  };

  defaultMoveResultDispatcher.dispatch({ kind: 'moved', seq: 5 }, ctx);

  assert.equal(sentMessages.length, 1);
  assert.deepEqual(sentMessages[0], { type: 'MOVE_STEP', seq: 5, dx: 1, dy: 0 });
});

test('MoveResultDispatcher: BumpedResultHandler executes MeleeAttackBumpStrategy and sends MOVE_STEP for mob', () => {
  const sentMessages = [];
  const mockSocket = {
    readyState: 1,
    send: (msg) => sentMessages.push(JSON.parse(msg)),
  };

  const animState = {};
  const player = createMockPlayer();
  const ctx = {
    myPlayer: player,
    playerAnimRef: { current: animState },
    onMeleeAttack: () => { animState.p1 = { attackUntil: Date.now() + 250 }; },
    socket: mockSocket,
    dx: 0,
    dy: -1,
  };

  const bumpRes = {
    kind: 'bumped',
    x: 10,
    y: 9,
    seq: 7,
    blockers: [{ kind: 'mob', id: 'm1', name: 'Rat', action: 'melee-attack' }],
  };

  defaultMoveResultDispatcher.dispatch(bumpRes, ctx);

  assert.ok(animState.p1?.attackUntil > 0);
  assert.equal(sentMessages.length, 1);
  assert.deepEqual(sentMessages[0], { type: 'MOVE_STEP', seq: 7, dx: 0, dy: -1 });
});

test('MoveResultDispatcher: Passive wall bump does not send MOVE_STEP', () => {
  const sentMessages = [];
  const mockSocket = {
    readyState: 1,
    send: (msg) => sentMessages.push(JSON.parse(msg)),
  };

  const player = createMockPlayer();
  const ctx = {
    myPlayer: player,
    socket: mockSocket,
    dx: 1,
    dy: 0,
  };

  const wallBumpRes = {
    kind: 'bumped',
    x: 11,
    y: 10,
    seq: 8,
    blockers: [{ kind: 'wall', tile: 1, action: 'none' }],
  };

  defaultMoveResultDispatcher.dispatch(wallBumpRes, ctx);

  assert.equal(sentMessages.length, 0);
});

test('MoveResultDispatcher: Alchemy bump triggers onOpenAlchemy callback', () => {
  let alchemyOpened = false;
  const player = createMockPlayer();
  const ctx = {
    myPlayer: player,
    onOpenAlchemyRef: { current: () => { alchemyOpened = true; } },
    dx: 0,
    dy: 1,
  };

  const alchemyBumpRes = {
    kind: 'bumped',
    x: 10,
    y: 11,
    blockers: [{ kind: 'alchemy-table', action: 'open-alchemy' }],
  };

  defaultMoveResultDispatcher.dispatch(alchemyBumpRes, ctx);

  assert.equal(alchemyOpened, true);
});

test('MoveResultDispatcher: Chasm bump executes ChasmJumpBumpStrategy and sends MOVE_STEP', () => {
  const sentMessages = [];
  const mockSocket = {
    readyState: 1,
    send: (msg) => sentMessages.push(JSON.parse(msg)),
  };

  const player = createMockPlayer();
  const ctx = {
    myPlayer: player,
    socket: mockSocket,
    dx: 0,
    dy: 1,
  };

  const chasmBumpRes = {
    kind: 'bumped',
    x: 10,
    y: 11,
    seq: 9,
    blockers: [{ kind: 'chasm', tile: 33, action: 'chasm-jump' }],
  };

  defaultMoveResultDispatcher.dispatch(chasmBumpRes, ctx);

  assert.equal(sentMessages.length, 1);
  assert.deepEqual(sentMessages[0], { type: 'MOVE_STEP', seq: 9, dx: 0, dy: 1 });
});

test('MoveResultDispatcher: Door bump executes UnlockDoorBumpStrategy and sends MOVE_STEP', () => {
  const sentMessages = [];
  const mockSocket = {
    readyState: 1,
    send: (msg) => sentMessages.push(JSON.parse(msg)),
  };

  const player = createMockPlayer();
  const ctx = {
    myPlayer: player,
    socket: mockSocket,
    dx: 1,
    dy: 0,
  };

  const doorBumpRes = {
    kind: 'bumped',
    x: 11,
    y: 10,
    seq: 10,
    blockers: [{ kind: 'door', tile: 10, action: 'unlock-door' }],
  };

  defaultMoveResultDispatcher.dispatch(doorBumpRes, ctx);

  assert.equal(sentMessages.length, 1);
  assert.deepEqual(sentMessages[0], { type: 'MOVE_STEP', seq: 10, dx: 1, dy: 0 });
});

test('MoveResultDispatcher: Enemy player bump executes MeleeAttackBumpStrategy and sends MOVE_STEP', () => {
  const sentMessages = [];
  const mockSocket = {
    readyState: 1,
    send: (msg) => sentMessages.push(JSON.parse(msg)),
  };

  const animState = {};
  const player = createMockPlayer();
  const ctx = {
    myPlayer: player,
    playerAnimRef: { current: animState },
    onMeleeAttack: () => { animState.p1 = { attackUntil: Date.now() + 250 }; },
    socket: mockSocket,
    dx: 0,
    dy: -1,
  };

  const enemyPlayerBumpRes = {
    kind: 'bumped',
    x: 10,
    y: 9,
    seq: 11,
    blockers: [{ kind: 'player', id: 'p2', action: 'melee-attack' }],
  };

  defaultMoveResultDispatcher.dispatch(enemyPlayerBumpRes, ctx);

  assert.ok(animState.p1?.attackUntil > 0);
  assert.equal(sentMessages.length, 1);
  assert.deepEqual(sentMessages[0], { type: 'MOVE_STEP', seq: 11, dx: 0, dy: -1 });
});

test('MoveResultDispatcher: Same-faction player bump with face-only does not send MOVE_STEP', () => {
  const sentMessages = [];
  const mockSocket = {
    readyState: 1,
    send: (msg) => sentMessages.push(JSON.parse(msg)),
  };

  const player = createMockPlayer();
  const ctx = {
    myPlayer: player,
    socket: mockSocket,
    dx: 0,
    dy: 1,
  };

  const allyPlayerBumpRes = {
    kind: 'bumped',
    x: 10,
    y: 11,
    seq: 12,
    blockers: [{ kind: 'player', id: 'p2', action: 'face-only' }],
  };

  defaultMoveResultDispatcher.dispatch(allyPlayerBumpRes, ctx);

  assert.equal(sentMessages.length, 0);
});
