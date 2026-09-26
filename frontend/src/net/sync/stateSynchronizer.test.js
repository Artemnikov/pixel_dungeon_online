import test from 'node:test';
import assert from 'node:assert/strict';
import { StateSynchronizer } from './StateSynchronizer';
import { PlantsSynchronizer } from './PlantsSynchronizer';
import { WorldManager } from '../services/WorldManager';
import { EntityManager } from '../services/EntityManager';
import { HeroStateSync } from '../services/HeroStateSync';
import { TurnStateSync } from '../services/TurnStateSync';
import { TurnSynchronizer } from './TurnSynchronizer';

test('StateSynchronizer: reconciles players, mobs, items, traps, plants, and vision', () => {
  let gridState = [
    [1, 1, 1, 1],
    [1, 2, 2, 1],
    [1, 2, 2, 1],
    [1, 1, 1, 1],
  ];
  const gridRef = { current: gridState };
  const visionRef = { current: { visible: new Set(), discovered: new Set() } };
  const openDoorsRef = { current: new Set() };
  const depthRef = { current: 1 };

  const entitiesRef = {
    current: {
      players: {},
      mobs: {},
      items: [],
      traps: [],
      plants: [],
    },
  };
  const dyingMobsRef = { current: {} };
  const myPlayerIdRef = { current: 'player_1' };

  let statsState = {};
  let invState = [];
  let equippedState = {};
  let goldState = 0;
  let energyState = 0;
  let bossInfoState = null;

  const world = new WorldManager({
    gridRef,
    setGrid: (u) => { gridState = typeof u === 'function' ? u(gridState) : u; },
    visionRef,
    openDoorsRef,
    depthRef,
  });

  const entities = new EntityManager({
    entitiesRef,
    dyingMobsRef,
    myPlayerIdRef,
  });

  const heroState = new HeroStateSync({
    setMyStats: (val) => { statsState = typeof val === 'function' ? val(statsState) : val; },
    setInventory: (val) => { invState = val; },
    setEquippedItems: (val) => { equippedState = val; },
    setGold: (g) => { goldState = g; },
    setEnergy: (e) => { energyState = e; },
    setBossInfo: (b) => { bossInfoState = b; },
  });

  const turnState = new TurnStateSync({});

  const synchronizer = new StateSynchronizer();

  const updateMessage = {
    type: 'STATE_UPDATE',
    depth: 2,
    gold: 50,
    energy: 10,
    players: [
      { id: 'player_1', name: 'Rogue', pos: { x: 1, y: 1 }, hp: 20, max_hp: 20 },
      { id: 'player_2', name: 'Mage', pos: { x: 2, y: 1 }, hp: 15, max_hp: 15 },
    ],
    self_player: {
      id: 'player_1',
      name: 'Rogue',
      pos: { x: 1, y: 1 },
      hp: 20,
      max_hp: 20,
      inventory: [{ id: 'dagger1', kind: 'Dagger' }],
      equipped_weapon: { kind: 'Dagger' },
      equipped_wearable: null,
    },
    mobs: [
      { id: 'mob_1', name: 'Gnoll', pos: { x: 2, y: 2 }, hp: 12, max_hp: 12 },
    ],
    items: [
      { id: 'item_1', kind: 'Gold', pos: { x: 1, y: 2 } },
    ],
    traps: [
      { x: 2, y: 1, trap_type: 'toxic_trap' },
    ],
    plants: [
      { x: 1, y: 2, plant_type: 'sungrass' },
    ],
    visible_tiles: [[1, 1], [2, 1]],
    open_doors: [[1, 0]],
    events: [],
  };

  synchronizer.sync(updateMessage, { world, entities, heroState, turnState });

  assert.equal(world.depth, 2);
  assert.equal(goldState, 50);
  assert.equal(energyState, 10);
  assert.equal(statsState.name, 'Rogue');
  assert.equal(invState.length, 1);
  assert.equal(equippedState.weapon?.kind, 'Dagger');
  assert.equal(bossInfoState, null);
  assert.equal(Object.keys(entities.getPlayers()).length, 2);
  assert.ok(entities.getPlayer('player_1'));
  assert.ok(entities.getPlayer('player_2'));
  assert.ok(entities.getMob('mob_1'));
  assert.equal(entities.getItems().length, 1);
  assert.equal(entities.getTraps().length, 1);
  assert.equal(entities.getPlants().length, 1);
  assert.equal(entities.getPlants()[0].plant_type, 'sungrass');
  assert.equal(world.isVisible(1, 1), true);
  assert.equal(world.isOpenDoor(1, 0), true);

  // Second update where mob_1 dies
  const update2 = {
    type: 'STATE_UPDATE',
    players: [
      { id: 'player_1', name: 'Rogue', pos: { x: 1, y: 1 }, hp: 20, max_hp: 20 },
    ],
    mobs: [],
    events: [
      { type: 'DEATH', data: { target: 'mob_1' } },
    ],
  };

  synchronizer.sync(update2, { world, entities, heroState, turnState });
  assert.equal(Object.keys(entities.getMobs()).length, 0);
  assert.ok(dyingMobsRef.current.mob_1);
  assert.equal(dyingMobsRef.current.mob_1.name, 'Gnoll');
});

test('PlantsSynchronizer: updates existing plant types and adds new ones with reveal timestamp', () => {
  const entitiesRef = {
    current: {
      players: {},
      mobs: {},
      items: [],
      traps: [],
      plants: [
        { x: 3, y: 3, plant_type: 'sungrass', renderPos: { x: 3, y: 3 }, revealStartTime: null },
      ],
    },
  };
  const entities = new EntityManager({
    entitiesRef,
    dyingMobsRef: { current: {} },
    myPlayerIdRef: { current: 'p1' },
  });

  const synchronizer = new PlantsSynchronizer();
  const ctx = {
    world: {},
    entities,
    heroState: {},
  };

  synchronizer.sync({
    type: 'STATE_UPDATE',
    players: [],
    mobs: [],
    events: [],
    plants: [
      { x: 3, y: 3, plant_type: 'earthroot' },
      { x: 4, y: 4, plant_type: 'firebloom' },
    ],
  }, ctx);

  const plants = entities.getPlants();
  assert.equal(plants.length, 2);
  const plant1 = plants.find(p => p.x === 3 && p.y === 3);
  const plant2 = plants.find(p => p.x === 4 && p.y === 4);
  assert.ok(plant1);
  assert.equal(plant1.plant_type, 'earthroot');
  assert.equal(plant1.revealStartTime, null);

  assert.ok(plant2);
  assert.equal(plant2.plant_type, 'firebloom');
  assert.equal(plant2.renderPos?.x, 4);
  assert.equal(plant2.renderPos?.y, 4);
  assert.ok(typeof plant2.revealStartTime === 'number');
});

test('TurnSynchronizer: applies the turn payload and clears it when it disappears', () => {
  const seen = { mode: 'realtime', turn: 'stale' };
  const turnState = new TurnStateSync({
    setGameMode: (m) => { seen.mode = m; },
    setTurnState: (v) => { seen.turn = v; },
  });
  const synchronizer = new TurnSynchronizer();
  const ctx = { turnState };

  synchronizer.sync({
    type: 'STATE_UPDATE',
    turn: {
      turn: 7,
      is_my_turn: true,
      timer: 60,
      order: [
        { id: 'player_1', kind: 'hero' },
        { id: 'mob_1', kind: 'mob' },
      ],
    },
  }, ctx);
  assert.equal(seen.turn.turn, 7);
  assert.equal(seen.turn.is_my_turn, true);
  assert.equal(seen.turn.timer, 60);
  assert.equal(seen.turn.order.length, 2);

  // A real-time room sends no turn payload, so a stale turn must not linger.
  synchronizer.sync({ type: 'STATE_UPDATE' }, ctx);
  assert.equal(seen.turn, null);
  // A STATE_UPDATE never re-asserts the mode: only INIT does.
  assert.equal(seen.mode, 'realtime');
});

test('TurnStateSync: the room mode comes from INIT and defaults to real-time', () => {
  let mode = 'stale';
  const turnState = new TurnStateSync({
    setGameMode: (m) => { mode = m; },
    setTurnState: () => {},
  });
  turnState.setGameMode('turnbased');
  assert.equal(mode, 'turnbased');
  turnState.setGameMode(null);
  assert.equal(mode, 'realtime');
});

test('canActNow: turn rooms gate on the payload, real-time rooms never do', async () => {
  const { canActNow } = await import('../services/TurnStateSync');
  assert.equal(canActNow('realtime', null), true);
  assert.equal(canActNow('realtime', { is_my_turn: false }), true);
  // Before the first frame there is no turn payload, so a turn room starts closed.
  assert.equal(canActNow('turnbased', null), false);
  assert.equal(canActNow('turnbased', { is_my_turn: false }), false);
  assert.equal(canActNow('turnbased', { is_my_turn: true }), true);
});
