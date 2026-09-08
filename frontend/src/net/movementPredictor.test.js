import test from 'node:test';
import assert from 'node:assert/strict';
import * as movementPredictor from './movementPredictor.ts';
import { BACKEND_TILE } from '../constants.js';

function createMockPlayer(x = 10, y = 10) {
  return {
    id: 'p1',
    name: 'Hero',
    pos: { x, y },
    renderPos: { x, y },
    targetPos: null,
    animStartPos: null,
    animStartTime: null,
    moveDuration: 180,
    facing: 'RIGHT',
    flipX: false,
    hp: 20,
    max_hp: 20,
    buffs: [],
    is_downed: false,
  };
}

// 20x20 open floor (all passable = 2 for FLOOR)
const mockGrid = Array.from({ length: 20 }, () => Array(20).fill(2));
const mockEntities = { players: {}, mobs: {}, items: [] };

function mobAt(x, y, overrides = {}) {
  return { id: 'm1', name: 'Rat', is_alive: true, pos: { x, y }, ...overrides };
}

test('predictMove: starts step from rest', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', mockGrid, mockEntities);
  assert.equal(res.kind, 'moved');
  assert.equal(res.seq, 1);
  assert.equal(movementPredictor.isPending(), true);
  assert.deepEqual(player.targetPos, { x: 10, y: 9 });
});

test('predictMove: redirects in-flight step when diagonal key pressed early', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const initial = movementPredictor.predictMove(player, 0, -1, 'p1', mockGrid, mockEntities);
  assert.equal(initial.kind, 'moved');
  assert.equal(initial.seq, 1);
  assert.deepEqual(player.targetPos, { x: 10, y: 9 });

  const redirected = movementPredictor.predictMove(player, 1, -1, 'p1', mockGrid, mockEntities);
  assert.equal(redirected.kind, 'moved');
  assert.equal(redirected.seq, 2);
  assert.equal(redirected.replacedSeq, 1);
  assert.deepEqual(player.targetPos, { x: 11, y: 9 });
});

test('predictMove: does not stack a second step while animation is in flight', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  movementPredictor.predictMove(player, 0, -1, 'p1', mockGrid, mockEntities);
  player.renderPos = { x: 10, y: 9.8 };
  movementPredictor.reconcile({ x: 10, y: 9 }, player);

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', mockGrid, mockEntities);
  assert.equal(res.kind, 'busy');
  assert.deepEqual(player.targetPos, { x: 10, y: 9 });
});

test('paceStep: chains next step once previous animation finishes', async () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  movementPredictor.predictMove(player, 1, -1, 'p1', mockGrid, mockEntities);
  movementPredictor.reconcile({ x: 11, y: 9 }, player);

  await new Promise(resolve => setTimeout(resolve, 190));

  player.renderPos = { x: 11, y: 9 };
  player.animStartTime = performance.now() - 200;

  const chained = movementPredictor.paceStep(player, 1, -1, 'p1', mockGrid, mockEntities);
  assert.equal(chained.kind, 'moved');
  assert.deepEqual(player.targetPos, { x: 12, y: 8 });
});

// --- living-mob bump (melee-attack) -----------------------------------------

test('predictMove: blocked by a mob does not walk, returns melee-attack bump and faces the mob', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const entities = {
    players: {},
    mobs: { m1: mobAt(10, 9) },
    items: [],
  };

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', mockGrid, entities);

  assert.equal(res.kind, 'bumped');
  assert.equal(res.x, 10);
  assert.equal(res.y, 9);
  assert.deepEqual(res.blockers, [{ kind: 'mob', id: 'm1', name: 'Rat', action: 'melee-attack' }]);
  assert.equal(player.targetPos, null);
  assert.equal(player.animStartTime, null);
  assert.equal(player.facing, 'UP');
});

test('predictMove: mid-step walk into a mob still bumps without mutating the in-flight walk', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);
  player.targetPos = { x: 10, y: 9 };
  player.animStartPos = { x: 10, y: 10 };
  player.animStartTime = performance.now() - 20;
  player.moveDuration = 180;
  player.renderPos = { x: 10, y: 9.5 };

  const entities = {
    players: {},
    mobs: { m1: mobAt(10, 8) },
    items: [],
  };

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', mockGrid, entities);

  assert.equal(res.kind, 'bumped');
  assert.equal(res.blockers[0].action, 'melee-attack');
  assert.deepEqual(player.targetPos, { x: 10, y: 9 });
  assert.notEqual(player.animStartTime, null);
  assert.equal(player.facing, 'UP');
});

test('paceStep: fires melee-attack bump while mid-step toward a mob (keyboard hold path)', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);
  player.targetPos = { x: 10, y: 9 };
  player.animStartPos = { x: 10, y: 10 };
  player.animStartTime = performance.now() - 20;
  player.moveDuration = 180;
  player.renderPos = { x: 10, y: 9.5 };

  const entities = {
    players: {},
    mobs: { m1: mobAt(10, 8) },
    items: [],
  };

  const res = movementPredictor.paceStep(player, 0, -1, 'p1', mockGrid, entities);

  assert.equal(res.kind, 'bumped');
  assert.equal(res.blockers[0].action, 'melee-attack');
  assert.equal(player.facing, 'UP');
  assert.deepEqual(player.targetPos, { x: 10, y: 9 });
  assert.equal(movementPredictor.isPending(), false);
});

test('predictMove: bumps mob at its current target tile, not its stale spawn pos', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const entities = {
    players: {},
    mobs: { m1: mobAt(10, 8, { targetPos: { x: 10, y: 9 } }) },
    items: [],
  };

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', mockGrid, entities);

  assert.equal(res.kind, 'bumped');
  assert.equal(res.x, 10);
  assert.equal(res.y, 9);
  assert.deepEqual(res.blockers, [{ kind: 'mob', id: 'm1', name: 'Rat', action: 'melee-attack' }]);
  assert.equal(player.targetPos, null);
  assert.equal(player.animStartTime, null);
});

test('predictMove: blocked by a wall returns a wall bump with no facing change', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const solidWallGrid = Array.from({ length: 20 }, () => Array(20).fill(BACKEND_TILE.WALL.id));

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', solidWallGrid, mockEntities);

  assert.equal(res.kind, 'bumped');
  assert.deepEqual(res.blockers, [{ kind: 'wall', tile: BACKEND_TILE.WALL.id, action: 'none' }]);
  assert.equal(player.facing, 'RIGHT');
  assert.equal(player.targetPos, null);
});

test('predictMove: blocked by a void tile returns a chasm-jump bump and faces the void', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const voidGrid = Array.from({ length: 20 }, () => Array(20).fill(BACKEND_TILE.VOID.id));

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', voidGrid, mockEntities);

  assert.equal(res.kind, 'bumped');
  assert.deepEqual(res.blockers, [{ kind: 'chasm', tile: BACKEND_TILE.VOID.id, action: 'chasm-jump' }]);
  assert.equal(player.facing, 'UP');
  assert.equal(player.targetPos, null);
});

// --- NPC bump (npc-interact) ------------------------------------------------

test('predictMove: bumping the Shopkeeper returns an npc-interact merchant bump', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const entities = {
    players: {},
    mobs: { m1: mobAt(10, 9, { type: 'npc', name: 'Shopkeeper' }) },
    items: [],
  };

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', mockGrid, entities);

  assert.equal(res.kind, 'bumped');
  assert.deepEqual(res.blockers[0], { kind: 'merchant', id: 'm1', name: 'Shopkeeper', action: 'npc-interact' });
  assert.equal(player.facing, 'UP');
});

test('predictMove: bumping a quest NPC returns an npc-interact quest-npc bump', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const entities = {
    players: {},
    mobs: { m1: mobAt(10, 9, { type: 'npc', name: 'Ghost' }) },
    items: [],
  };

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', mockGrid, entities);

  assert.equal(res.kind, 'bumped');
  assert.deepEqual(res.blockers[0], { kind: 'quest-npc', id: 'm1', name: 'Ghost', action: 'npc-interact' });
  assert.equal(player.facing, 'UP');
});

// --- owned ally walk-through -------------------------------------------------

test('predictMove: owned ally (Ghost/Mirror) is walked through, not bumped', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const entities = {
    players: {},
    mobs: {
      m1: mobAt(10, 9, { type: 'ghost_hero', faction: 'player', owner_id: 'p1' }),
    },
    items: [],
  };

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', mockGrid, entities);
  assert.equal(res.kind, 'moved');
  assert.deepEqual(player.targetPos, { x: 10, y: 9 });
});

test('predictMove: another player is bumped as face-only', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const entities = {
    players: {
      p2: { id: 'p2', name: 'Other', pos: { x: 10, y: 9 }, renderPos: { x: 10, y: 9 }, is_downed: false },
    },
    mobs: {},
    items: [],
  };

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', mockGrid, entities);

  assert.equal(res.kind, 'bumped');
  assert.deepEqual(res.blockers[0], { kind: 'player', id: 'p2', action: 'face-only' });
  assert.equal(player.facing, 'UP');
});

// --- terrain / chest / items / traps ----------------------------------------

test('predictMove: bumping an alchemy pot returns an open-alchemy bump', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const alchemyGrid = mockGrid.map(row => row.slice());
  alchemyGrid[9][10] = BACKEND_TILE.ALCHEMY.id;

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', alchemyGrid, mockEntities);

  assert.equal(res.kind, 'bumped');
  assert.deepEqual(res.blockers[0], { kind: 'alchemy-table', action: 'open-alchemy' });
  assert.equal(player.facing, 'UP');
});

test('predictMove: bumping a closed chest returns an open-chest bump', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const entities = {
    players: {},
    mobs: {},
    items: [{ id: 'c1', type: 'chest', chest_type: 'iron', opened: false, pos: { x: 10, y: 9 } }],
  };

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', mockGrid, entities);

  assert.equal(res.kind, 'bumped');
  assert.deepEqual(res.blockers[0], { id: 'c1', kind: 'chest', chestType: 'iron', opened: false, action: 'open-chest' });
  assert.equal(player.facing, 'UP');
});

test('predictMove: a loose item on the tile does not bump (moves over it)', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const entities = {
    players: {},
    mobs: {},
    items: [{ id: 'i1', pos: { x: 10, y: 9 } }],
  };

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', mockGrid, entities);
  assert.equal(res.kind, 'moved');
  assert.deepEqual(player.targetPos, { x: 10, y: 9 });
});

test('predictMove: a trap on the tile does not bump (moves over it)', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const entities = {
    players: {},
    mobs: {},
    items: [],
    traps: [{ x: 10, y: 9, trap_type: 'poison' }],
  };

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', mockGrid, entities);
  assert.equal(res.kind, 'moved');
  assert.deepEqual(player.targetPos, { x: 10, y: 9 });
});

// --- precedence --------------------------------------------------------------

test('predictMove: bumping a chasm tile returns a chasm-jump bump and faces the chasm', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const gridWithChasm = mockGrid.map(row => row.slice());
  gridWithChasm[9][10] = BACKEND_TILE.CHASM.id;

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', gridWithChasm, mockEntities);

  assert.equal(res.kind, 'bumped');
  assert.deepEqual(res.blockers[0], { kind: 'chasm', tile: BACKEND_TILE.CHASM.id, action: 'chasm-jump' });
  assert.equal(player.facing, 'UP');
});

test('predictMove: bumping a locked door returns an unlock-door bump and faces the door', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const gridWithLockedDoor = mockGrid.map(row => row.slice());
  gridWithLockedDoor[9][10] = BACKEND_TILE.LOCKED_DOOR.id;

  const res = movementPredictor.predictMove(player, 0, -1, 'p1', gridWithLockedDoor, mockEntities);

  assert.equal(res.kind, 'bumped');
  assert.deepEqual(res.blockers[0], { kind: 'door', tile: BACKEND_TILE.LOCKED_DOOR.id, action: 'unlock-door' });
  assert.equal(player.facing, 'UP');
});

test('primaryBlocker: melee-attack beats a same-tile item/face-only blocker', () => {
  const primary = movementPredictor.primaryBlocker([
    { kind: 'item', id: 'i1', action: 'none' },
    { kind: 'mob', id: 'm1', name: 'Rat', action: 'melee-attack' },
    { kind: 'player', id: 'p2', action: 'face-only' },
  ]);
  assert.deepEqual(primary, { kind: 'mob', id: 'm1', name: 'Rat', action: 'melee-attack' });
});

test('primaryBlocker: melee-attack beats chasm-jump', () => {
  const primary = movementPredictor.primaryBlocker([
    { kind: 'chasm', tile: 33, action: 'chasm-jump' },
    { kind: 'mob', id: 'm1', name: 'Bat', action: 'melee-attack' },
  ]);
  assert.deepEqual(primary, { kind: 'mob', id: 'm1', name: 'Bat', action: 'melee-attack' });
});

test('primaryBlocker: open-chest beats a face-only player', () => {
  const primary = movementPredictor.primaryBlocker([
    { kind: 'player', id: 'p2', action: 'face-only' },
    { kind: 'chest', id: 'c1', chestType: 'iron', opened: false, action: 'open-chest' },
  ]);
  assert.equal(primary.action, 'open-chest');
});

test('primaryBlocker: returns null for an empty list', () => {
  assert.equal(movementPredictor.primaryBlocker([]), null);
});

test('onMoveResult: confirms step by sequence number and prunes queue', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const move1 = movementPredictor.predictMove(player, 1, 0, 'p1', mockGrid, mockEntities);
  assert.equal(move1.seq, 1);
  assert.equal(movementPredictor.isPending(), true);

  movementPredictor.onMoveResult({ entity: 'p1', seq: 1, x: 11, y: 10, ok: true }, player);
  assert.equal(movementPredictor.isPending(), false);
});

test('onMoveResult: handles rejection ok=false by rolling back', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  movementPredictor.predictMove(player, 1, 0, 'p1', mockGrid, mockEntities);
  assert.equal(movementPredictor.isPending(), true);

  movementPredictor.onMoveResult({ entity: 'p1', seq: 1, x: 10, y: 10, ok: false }, player);
  assert.equal(movementPredictor.isPending(), false);
  assert.deepEqual(player.targetPos, { x: 10, y: 10 });
});

test('onMoveResult: a single rejected seq step keeps later steps re-anchored to server pos', async () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  // First step succeeds server-side.
  assert.equal(movementPredictor.predictMove(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 1);
  movementPredictor.onMoveResult({ entity: 'p1', seq: 1, x: 11, y: 10, ok: true }, player);
  assert.equal(movementPredictor.isPending(), false);

  // Second step goes in-flight; wait out the step cooldown, then pace a third.
  player.renderPos = { x: 11, y: 10 };
  player.animStartTime = performance.now() - 200;
  await new Promise(resolve => setTimeout(resolve, 190));
  const move2 = movementPredictor.predictMove(player, 1, 0, 'p1', mockGrid, mockEntities);
  assert.equal(move2.seq, 2);

  player.renderPos = { x: 12, y: 10 };
  player.animStartTime = performance.now() - 200;
  await new Promise(resolve => setTimeout(resolve, 190));
  const move3 = movementPredictor.paceStep(player, 1, 0, 'p1', mockGrid, mockEntities);
  assert.equal(move3.seq, 3);
  assert.equal(movementPredictor.isPending(), true);
  assert.deepEqual(movementPredictor.getUnconfirmedSteps().map(s => s.seq), [2, 3]);

  // The server rejects only step 2 -- step 3 must survive, re-anchored to the
  // authoritative position instead of the whole buffer being wiped.
  movementPredictor.onMoveResult({ entity: 'p1', seq: 2, x: 11, y: 10, ok: false }, player);

  assert.equal(movementPredictor.isPending(), true, 'later steps survive one rejected step');
  assert.deepEqual(movementPredictor.getUnconfirmedSteps().map(s => s.seq), [3]);
  assert.equal(movementPredictor.getUnconfirmedSteps()[0].targetX, 12, 'survivor starts from server pos (11,10) + dx');
  assert.equal(movementPredictor.getUnconfirmedSteps()[0].targetY, 10);
  assert.deepEqual(player.targetPos, { x: 11, y: 10 }, 'glides to the server position, no hard snap');
});

test('reconcile: acknowledges steps via lastProcessedSeq', () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  const move1 = movementPredictor.predictMove(player, 1, 0, 'p1', mockGrid, mockEntities);
  assert.equal(move1.seq, 1);

  movementPredictor.reconcile({ x: 11, y: 10 }, player, 1);
  assert.equal(movementPredictor.isPending(), false);
});

test('getStepDuration: adapts dynamically to player step_duration_ms', () => {
  const player = createMockPlayer(10, 10);
  player.step_duration_ms = 75;
  assert.equal(movementPredictor.getStepDuration(player), 75);

  player.step_duration_ms = 300;
  assert.equal(movementPredictor.getStepDuration(player), 300);
});

test('paceStep: buffer holds 3 in-flight steps before going busy', async () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  // Step 1 (from rest).
  assert.equal(movementPredictor.predictMove(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 1);

  // Chain step 2 (anim complete, cooldown elapsed).
  player.renderPos = { x: 11, y: 10 };
  player.animStartTime = performance.now() - 200;
  await new Promise(resolve => setTimeout(resolve, 190));
  assert.equal(movementPredictor.paceStep(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 2);

  // Chain step 3 while step 1 and 2 are still un-acked.
  player.renderPos = { x: 12, y: 10 };
  player.animStartTime = performance.now() - 200;
  await new Promise(resolve => setTimeout(resolve, 190));
  assert.equal(movementPredictor.paceStep(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 3);
  assert.deepEqual(movementPredictor.getUnconfirmedSteps().map(s => s.seq), [1, 2, 3]);

  // A 4th in-flight step is refused while the 3-step buffer is full.
  const busy = movementPredictor.paceStep(player, 1, 0, 'p1', mockGrid, mockEntities);
  assert.equal(busy.kind, 'busy');
});

test('paceStep: chains up to 3 steps without an ack, then caps (live-RTT behavior)', async () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  // Build 3 in-flight steps back-to-back (no acks at all -- worst-case RTT).
  assert.equal(movementPredictor.predictMove(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 1);

  player.renderPos = { x: 11, y: 10 };
  player.animStartTime = performance.now() - 200;
  await new Promise(resolve => setTimeout(resolve, 190));
  assert.equal(movementPredictor.paceStep(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 2);

  player.renderPos = { x: 12, y: 10 };
  player.animStartTime = performance.now() - 200;
  await new Promise(resolve => setTimeout(resolve, 190));
  assert.equal(movementPredictor.paceStep(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 3);

  assert.deepEqual(movementPredictor.getUnconfirmedSteps().map(s => s.seq), [1, 2, 3]);

  // One ack frees a slot immediately -- no stall waits for the whole buffer.
  movementPredictor.onMoveResult({ entity: 'p1', seq: 1, x: 11, y: 10, ok: true }, player);
  player.renderPos = { x: 13, y: 10 };
  player.animStartTime = performance.now() - 200;
  await new Promise(resolve => setTimeout(resolve, 190));
  assert.equal(movementPredictor.paceStep(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 4);
});

test('reconcile: never hard-resets while walking when the server trails a tile', async () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  // Steps 1 and 2 accepted, confirmed at (12,10).
  assert.equal(movementPredictor.predictMove(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 1);
  movementPredictor.onMoveResult({ entity: 'p1', seq: 1, x: 11, y: 10, ok: true }, player);

  player.renderPos = { x: 11, y: 10 };
  player.animStartTime = performance.now() - 200;
  await new Promise(resolve => setTimeout(resolve, 190));
  assert.equal(movementPredictor.paceStep(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 2);
  movementPredictor.onMoveResult({ entity: 'p1', seq: 2, x: 12, y: 10, ok: true }, player);
  assert.equal(movementPredictor.isPending(), false);

  // Chain step 3 off the confirmed anchor.
  player.renderPos = { x: 12, y: 10 };
  player.animStartTime = performance.now() - 200;
  await new Promise(resolve => setTimeout(resolve, 190));
  assert.equal(movementPredictor.paceStep(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 3);
  assert.deepEqual(movementPredictor.getUnconfirmedSteps().map(s => s.seq), [3]);
  assert.deepEqual(player.targetPos, { x: 13, y: 10 });

  // A state frame built one tick earlier arrives behind the fast-lane ack:
  // server pos (11,10), lastProcessedSeq=1, while confirmedPos is already
  // (12,10). This used to register as a mismatch and retarget-glide the hero
  // back a tile ("spring-back"). Now it folds the server tile into the anchor.
  movementPredictor.reconcile({ x: 11, y: 10 }, player, 1);

  assert.equal(movementPredictor.isPending(), true, 'the walk continues');
  assert.deepEqual(player.targetPos, { x: 13, y: 10 }, 'no spring-back retarget');
  assert.deepEqual(movementPredictor.getUnconfirmedSteps().map(s => s.seq), [3]);
});

test('reconcile: still hard-resets on a genuine divergence of more than one tile', async () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  assert.equal(movementPredictor.predictMove(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 1);
  movementPredictor.onMoveResult({ entity: 'p1', seq: 1, x: 11, y: 10, ok: true }, player);

  player.renderPos = { x: 11, y: 10 };
  player.animStartTime = performance.now() - 200;
  await new Promise(resolve => setTimeout(resolve, 190));
  assert.equal(movementPredictor.paceStep(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 2);

  // Server ends up 2 tiles off the confirmed anchor (e.g. knockback that moves
  // the player without consuming a client seq) -- nowhere on the predicted
  // chain. The hard reset stays.
  movementPredictor.reconcile({ x: 14, y: 12 }, player, 1);

  assert.equal(movementPredictor.isPending(), false);
  assert.deepEqual(movementPredictor.getUnconfirmedSteps(), []);
  assert.deepEqual(player.targetPos, { x: 14, y: 12 });
});

test('reconcile: a 1-tile divergence while walking is folded, not hard-reset', async () => {
  // Deliberate tradeoff of the spring-back guard: a 1-tile displacement that
  // didn't consume a client seq (e.g. small knockback) is folded into the
  // confirmed anchor and the walk continues, self-correcting when the step
  // acks land -- instead of snapping the hero back a tile.
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  assert.equal(movementPredictor.predictMove(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 1);
  movementPredictor.onMoveResult({ entity: 'p1', seq: 1, x: 11, y: 10, ok: true }, player);

  player.renderPos = { x: 11, y: 10 };
  player.animStartTime = performance.now() - 200;
  await new Promise(resolve => setTimeout(resolve, 190));
  const m2 = movementPredictor.paceStep(player, 1, 0, 'p1', mockGrid, mockEntities);
  assert.equal(m2.seq, 2);
  assert.deepEqual(player.targetPos, { x: 12, y: 10 });

  // Server moves the hero one tile off the chain (upward) without a seq ack.
  movementPredictor.reconcile({ x: 11, y: 9 }, player, 1);

  assert.equal(movementPredictor.isPending(), true, '1-tile divergence folds, not reset');
  assert.deepEqual(player.targetPos, { x: 12, y: 10 }, 'no snap-back; the walk continues');
  assert.deepEqual(movementPredictor.getUnconfirmedSteps().map(s => s.seq), [2]);
});

test('onMoveResult: no-seq rejection mid-walk re-anchors instead of wiping the chain', async () => {
  movementPredictor.clear();
  const player = createMockPlayer(10, 10);

  assert.equal(movementPredictor.predictMove(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 1);
  movementPredictor.onMoveResult({ entity: 'p1', seq: 1, x: 11, y: 10, ok: true }, player);

  // Step 2 in flight (no ack yet).
  player.renderPos = { x: 11, y: 10 };
  player.animStartTime = performance.now() - 200;
  await new Promise(resolve => setTimeout(resolve, 190));
  assert.equal(movementPredictor.paceStep(player, 1, 0, 'p1', mockGrid, mockEntities).seq, 2);
  assert.deepEqual(movementPredictor.getUnconfirmedSteps().map(s => s.seq), [2]);

  // A no-seq rejection (path/auto-move step blocked server-side) lands while
  // the keyboard walk is still pending. It must re-anchor, not wipe.
  movementPredictor.onMoveResult({ entity: 'p1', x: 11, y: 10, ok: false }, player);

  assert.equal(movementPredictor.isPending(), true, 'live walk survives a no-seq rejection');
  assert.deepEqual(movementPredictor.getUnconfirmedSteps().map(s => s.seq), [2]);
  assert.equal(movementPredictor.getUnconfirmedSteps()[0].targetX, 12, 'survivor continues from server anchor');
  assert.equal(movementPredictor.getUnconfirmedSteps()[0].targetY, 10);
  assert.deepEqual(player.targetPos, { x: 11, y: 10 }, 'glides to the server pos, no wipe');
});