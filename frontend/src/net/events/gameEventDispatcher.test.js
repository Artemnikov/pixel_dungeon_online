import test from 'node:test';
import assert from 'node:assert/strict';
import { GameEventDispatcher } from './GameEventDispatcher';
import { createDefaultEventDispatcher } from './defaultDispatcher';
import { WorldManager } from '../services/WorldManager';
import { EntityManager } from '../services/EntityManager';
import { VisualEffectsManager } from '../services/VisualEffectsManager';
import { GameCallbacks } from '../services/GameCallbacks';

test('GameEventDispatcher: dispatches events to registered handlers', () => {
  const dispatcher = new GameEventDispatcher();
  let handledLevelUp = false;

  dispatcher.register({
    eventType: 'LEVEL_UP',
    handle: (event, ctx) => {
      if (event.data.player === ctx.myPlayerId) {
        handledLevelUp = true;
      }
    },
  });

  const ctx = {
    myPlayerId: 'hero',
    world: {},
    entities: {},
    effects: {},
    ui: {},
    audio: { play: () => {} },
  };

  dispatcher.dispatch({
    type: 'LEVEL_UP',
    data: { player: 'hero', level: 2, can_choose_subclass: false, can_choose_armor_ability: false },
  }, ctx);

  assert.equal(handledLevelUp, true);
});

test('DefaultEventDispatcher: handles combat, world, and boss events correctly', () => {
  const dispatcher = createDefaultEventDispatcher();

  const gridRef = { current: [[1, 2], [1, 2]] };
  const visionRef = { current: { visible: new Set(['1,0', '1,1']), discovered: new Set() } };
  const world = new WorldManager({
    gridRef,
    setGrid: () => {},
    visionRef,
  });

  const entitiesRef = {
    current: {
      players: {
        hero: { id: 'hero', name: 'Warrior', renderPos: { x: 1, y: 0 }, pos: { x: 1, y: 0 }, hp: 20, max_hp: 20 },
      },
      mobs: {
        rat: { id: 'rat', name: 'Rat', renderPos: { x: 1, y: 1 }, pos: { x: 1, y: 1 }, hp: 8, max_hp: 8 },
      },
      items: [],
      traps: [],
    },
  };
  const entities = new EntityManager({
    entitiesRef,
    dyingMobsRef: { current: {} },
    myPlayerIdRef: { current: 'hero' },
  });

  const particlesRef = { current: [] };
  const screenShakeRef = { current: null };
  const floatingTextRef = { current: [] };
  const warnedTilesRef = { current: null };
  const playerAnimRef = { current: {} };
  const mobAnimRef = { current: {} };

  const effects = new VisualEffectsManager({
    particlesRef,
    screenShakeRef,
    floatingTextRef,
    warnedTilesRef,
    playerAnimRef,
    mobAnimRef,
  });

  let bossFought = false;
  const ui = new GameCallbacks({
    onGooFightStarted: () => { bossFought = true; },
  });

  const mockAudio = {
    play: () => {},
    playStep: () => {},
  };

  const ctx = {
    myPlayerId: 'hero',
    world,
    entities,
    effects,
    ui,
    audio: mockAudio,
  };

  // Dispatch GOO_CHARGE
  dispatcher.dispatch({
    type: 'GOO_CHARGE',
    data: { mob: 'rat', tiles: [[1, 1]], duration_ms: 1000 },
  }, ctx);

  assert.deepEqual(warnedTilesRef.current.tiles, [[1, 1]]);

  // Dispatch GOO_FIGHT_STARTED
  dispatcher.dispatch({
    type: 'GOO_FIGHT_STARTED',
    data: { mob: 'Goo' },
  }, ctx);

  assert.equal(bossFought, true);

  // Dispatch SCREEN_SHAKE
  dispatcher.dispatch({
    type: 'SCREEN_SHAKE',
    data: { intensity: 4, duration_ms: 500 },
  }, ctx);

  assert.equal(screenShakeRef.current.intensity, 4);

  // Dispatch HEAL
  dispatcher.dispatch({
    type: 'HEAL',
    data: { target: 'hero', amount: 5, x: 1, y: 0 },
  }, ctx);

  assert.ok(floatingTextRef.current.length > 0);

  // Dispatch PLAY_SOUND (MIMIC with rate)
  let playedSound = null;
  let playedRate = null;
  ctx.audio.play = (sound, rate) => {
    playedSound = sound;
    playedRate = rate;
  };

  dispatcher.dispatch({
    type: 'PLAY_SOUND',
    data: { sound: 'MIMIC', rate: 1.25, x: 1, y: 0 },
  }, ctx);

  assert.equal(playedSound, 'MIMIC');
  assert.equal(playedRate, 1.25);
});

test('DefaultEventDispatcher: LOCKED event plays the locked sound for doors/chests', () => {
  const dispatcher = createDefaultEventDispatcher();

  const gridRef = { current: [[1, 2], [1, 2]] };
  const visionRef = { current: { visible: new Set(['0,0', '1,0', '1,1']), discovered: new Set() } };
  const world = new WorldManager({
    gridRef,
    setGrid: () => {},
    visionRef,
  });

  const entitiesRef = { current: { players: {}, mobs: {}, items: [], traps: [] } };
  const entities = new EntityManager({
    entitiesRef,
    dyingMobsRef: { current: {} },
    myPlayerIdRef: { current: 'hero' },
  });

  const particlesRef = { current: [] };
  const screenShakeRef = { current: null };
  const floatingTextRef = { current: [] };
  const warnedTilesRef = { current: null };
  const playerAnimRef = { current: {} };
  const mobAnimRef = { current: {} };

  const effects = new VisualEffectsManager({
    particlesRef,
    screenShakeRef,
    floatingTextRef,
    warnedTilesRef,
    playerAnimRef,
    mobAnimRef,
  });

  const ui = new GameCallbacks({});

  let playedLocked = false;
  const mockAudio = {
    play: (sound) => { if (sound === 'LOCKED') playedLocked = true; },
    playStep: () => {},
  };

  const ctx = {
    myPlayerId: 'hero',
    world,
    entities,
    effects,
    ui,
    audio: mockAudio,
  };

  dispatcher.dispatch({
    type: 'LOCKED',
    data: { player: 'hero', x: 1, y: 1 },
  }, ctx);

  assert.equal(playedLocked, true, 'LOCKED event must invoke audio.play("LOCKED")');
});

test('DefaultEventDispatcher: PLAY_SOUND PLANT plays plant sound only when tile is in LOS / visible', () => {
  const dispatcher = createDefaultEventDispatcher();

  const gridRef = { current: [[1, 1, 1], [1, 1, 1], [1, 1, 1]] };
  const visionRef = { current: { visible: new Set(['1,1']), discovered: new Set(['1,1', '2,2']) } };
  const world = new WorldManager({
    gridRef,
    setGrid: () => {},
    visionRef,
  });

  const entitiesRef = { current: { players: {}, mobs: {}, items: [], traps: [], plants: [] } };
  const entities = new EntityManager({
    entitiesRef,
    dyingMobsRef: { current: {} },
    myPlayerIdRef: { current: 'hero' },
  });

  const effects = new VisualEffectsManager({
    particlesRef: { current: [] },
    screenShakeRef: { current: null },
    floatingTextRef: { current: [] },
    warnedTilesRef: { current: null },
    playerAnimRef: { current: {} },
    mobAnimRef: { current: {} },
  });

  const ui = new GameCallbacks({});

  let playedSounds = [];
  const mockAudio = {
    play: (sound, rate) => { playedSounds.push({ sound, rate }); },
    playStep: () => {},
  };

  const ctx = {
    myPlayerId: 'hero',
    world,
    entities,
    effects,
    ui,
    audio: mockAudio,
  };

  dispatcher.dispatch({
    type: 'PLAY_SOUND',
    data: { sound: 'PLANT', x: 1, y: 1 },
  }, ctx);

  assert.equal(playedSounds.length, 1);
  assert.equal(playedSounds[0].sound, 'PLANT');

  dispatcher.dispatch({
    type: 'PLAY_SOUND',
    data: { sound: 'PLANT', x: 2, y: 2 },
  }, ctx);

  assert.equal(playedSounds.length, 1);
});

test('DefaultEventDispatcher: RANGED_ATTACK for seed plays THROW on launch and registers onComplete to play PLANT on arrival', () => {
  const dispatcher = createDefaultEventDispatcher();

  const gridRef = { current: [[1, 1, 1], [1, 1, 1], [1, 1, 1]] };
  const visionRef = { current: { visible: new Set(['0,0', '1,1', '2,2']), discovered: new Set() } };
  const world = new WorldManager({
    gridRef,
    setGrid: () => {},
    visionRef,
  });

  const entitiesRef = { current: { players: {}, mobs: {}, items: [], traps: [], plants: [] } };
  const entities = new EntityManager({
    entitiesRef,
    dyingMobsRef: { current: {} },
    myPlayerIdRef: { current: 'hero' },
  });

  const projectilesRef = { current: [] };
  const effects = new VisualEffectsManager({
    particlesRef: { current: [] },
    projectilesRef,
    screenShakeRef: { current: null },
    floatingTextRef: { current: [] },
    warnedTilesRef: { current: null },
    playerAnimRef: { current: {} },
    mobAnimRef: { current: {} },
  });

  const ui = new GameCallbacks({});

  let playedSounds = [];
  const mockAudio = {
    play: (sound, rate) => { playedSounds.push({ sound, rate }); },
    playStep: () => {},
  };

  const ctx = {
    myPlayerId: 'hero',
    world,
    entities,
    effects,
    ui,
    audio: mockAudio,
  };

  dispatcher.dispatch({
    type: 'RANGED_ATTACK',
    data: {
      source: 'hero',
      x: 0,
      y: 0,
      target_x: 2,
      target_y: 2,
      projectile: 'seed',
      item: { id: 's1', type: 'seed', name: 'Sungrass Seed' },
    },
  }, ctx);

  assert.equal(playedSounds.length, 1);
  assert.equal(playedSounds[0].sound, 'THROW');
  assert.equal(projectilesRef.current.length, 1);

  const proj = projectilesRef.current[0];
  assert.equal(typeof proj.onComplete, 'function');

  proj.onComplete();

  assert.equal(playedSounds.length, 2);
  assert.equal(playedSounds[1].sound, 'PLANT');
});

test('DefaultEventDispatcher: PLANT_TRIGGERED event removes plant, plays sound, spawns floating text announcement, and logs action', () => {
  const dispatcher = createDefaultEventDispatcher();

  const gridRef = { current: [[1, 1, 1], [1, 1, 1], [1, 1, 1]] };
  const visionRef = { current: { visible: new Set(['1,1']), discovered: new Set(['1,1']) } };
  const world = new WorldManager({
    gridRef,
    setGrid: () => {},
    visionRef,
  });

  const entitiesRef = {
    current: {
      players: {},
      mobs: {},
      items: [],
      traps: [],
      plants: [{ x: 1, y: 1, plant_type: 'sungrass' }],
    },
  };
  const entities = new EntityManager({
    entitiesRef,
    dyingMobsRef: { current: {} },
    myPlayerIdRef: { current: 'hero' },
  });

  const floatingTextRef = { current: [] };
  const particlesRef = { current: [] };
  const effects = new VisualEffectsManager({
    particlesRef,
    screenShakeRef: { current: null },
    floatingTextRef,
    warnedTilesRef: { current: null },
    playerAnimRef: { current: {} },
    mobAnimRef: { current: {} },
  });

  const ui = new GameCallbacks({});

  let playedSounds = [];
  const mockAudio = {
    play: (sound, rate) => { playedSounds.push({ sound, rate }); },
    playStep: () => {},
  };

  const ctx = {
    myPlayerId: 'hero',
    world,
    entities,
    effects,
    ui,
    audio: mockAudio,
  };

  dispatcher.dispatch({
    type: 'PLANT_TRIGGERED',
    data: {
      plant: 'sungrass',
      x: 1,
      y: 1,
      player: 'hero',
    },
  }, ctx);

  // Plant was removed from entity list
  assert.equal(entities.getPlants().length, 0);

  // SPD fidelity: plant activation is silent (no artificial PLANT_TRIGGER audio)
  assert.equal(playedSounds.some(s => s.sound === 'PLANT_TRIGGER'), false);

  // Particles spawned: 6 general wither leaf particles + 3 light shaft particles for sungrass
  assert.equal(particlesRef.current.length, 9);
  assert.equal(particlesRef.current.some(p => p.isShaft), true);

  // Floating text announcement "Herbal Healing" spawned
  assert.equal(floatingTextRef.current.length, 1);
  assert.equal(floatingTextRef.current[0].text, 'Herbal Healing');
});



