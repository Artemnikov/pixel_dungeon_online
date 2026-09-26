import test from 'node:test';
import assert from 'node:assert/strict';
import { isTurnRoom, sendTurnRoomTap } from './turnTap.ts';

function fakeSocket() {
  const sent = [];
  return { sent, socket: { send: (payload) => sent.push(JSON.parse(payload)) } };
}

test('isTurnRoom: only the turnbased mode counts', () => {
  assert.equal(isTurnRoom({ current: 'turnbased' }), true);
  assert.equal(isTurnRoom({ current: 'realtime' }), false);
  assert.equal(isTurnRoom(undefined), false);
  assert.equal(isTurnRoom(null), false);
});

test('sendTurnRoomTap: an adjacent tap is one MOVE, not the MOVE_STEP plumbing', () => {
  const { sent, socket } = fakeSocket();
  sendTurnRoomTap(socket, { type: 'MOVE', direction: 'UP_LEFT' });
  assert.deepEqual(sent, [{ type: 'MOVE', direction: 'UP_LEFT' }]);
});

test('sendTurnRoomTap: a far tap asks the server to walk the path', () => {
  const { sent, socket } = fakeSocket();
  sendTurnRoomTap(socket, { type: 'PATH_STEPS', steps: [[0, -1], [1, 0]] });
  assert.deepEqual(sent, [{ type: 'PATH_STEPS', steps: [[0, -1], [1, 0]] }]);
});

test('sendTurnRoomTap: a far tap with no route spends no turn', () => {
  const { sent, socket } = fakeSocket();
  sendTurnRoomTap(socket, { type: 'PATH_STEPS', steps: [] });
  assert.deepEqual(sent, []);
});

test('sendTurnRoomTap: WAIT and NPC_INTERACT pass through unchanged', () => {
  const { sent, socket } = fakeSocket();
  sendTurnRoomTap(socket, { type: 'WAIT' });
  sendTurnRoomTap(socket, { type: 'NPC_INTERACT', npc_id: 'npc1' });
  assert.deepEqual(sent, [{ type: 'WAIT' }, { type: 'NPC_INTERACT', npc_id: 'npc1' }]);
});

test('sendTurnRoomTap: a MOVE with no direction sends nothing', () => {
  const { sent, socket } = fakeSocket();
  sendTurnRoomTap(socket, { type: 'MOVE' });
  assert.deepEqual(sent, []);
});
