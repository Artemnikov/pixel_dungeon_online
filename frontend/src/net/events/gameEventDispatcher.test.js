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

test('DefaultEventDispatcher: PLAY_ANIMATION animates visible players and spawns the glow', () => {
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
        hero: { id: 'hero', name: 'Cleric', renderPos: { x: 1, y: 0 }, pos: { x: 1, y: 0 }, hp: 20, max_hp: 20 },
        ally: { id: 'ally', name: 'Warrior', renderPos: { x: 2, y: 2 }, pos: { x: 2, y: 2 }, hp: 20, max_hp: 20 },
      },
      mobs: {},
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
  const flareEffectsRef = { current: [] };
  const playerAnimRef = { current: {} };
  const effects = new VisualEffectsManager({
    particlesRef,
    flareEffectsRef,
    playerAnimRef,
  });

  const ctx = {
    myPlayerId: 'hero',
    world,
    entities,
    effects,
    ui: new GameCallbacks({}),
    audio: { play: () => {}, playStep: () => {} },
  };

  // Local, visible hero casting Holy Weapon: operate animation + golden glow + sparks
  dispatcher.dispatch({
    type: 'PLAY_ANIMATION',
    data: { player: 'hero', animation: 'operate', glow: 'golden', spell: 'holy_weapon', x: 1, y: 0 },
  }, ctx);

  assert.ok(playerAnimRef.current.hero.operateUntil > 0, 'operate animation set on local hero');
  assert.equal(flareEffectsRef.current.length, 1, 'golden flare spawned for the glow');
  assert.ok(particlesRef.current.length >= 6, 'spark burst spawned for the glow');

  // 'read' animation maps to the read sprite state
  dispatcher.dispatch({
    type: 'PLAY_ANIMATION',
    data: { player: 'hero', animation: 'read' },
  }, ctx);
  assert.ok(playerAnimRef.current.hero.readUntil > 0, 'read animation set');

  // Remote player outside LOS: no animation, no glow
  const sparksBefore = particlesRef.current.length;
  dispatcher.dispatch({
    type: 'PLAY_ANIMATION',
    data: { player: 'ally', animation: 'operate', glow: 'golden', x: 2, y: 2 },
  }, ctx);
  assert.equal(playerAnimRef.current.ally, undefined, 'out-of-LOS player is not animated');
  assert.equal(particlesRef.current.length, sparksBefore, 'no glow for out-of-LOS player');
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

test('Guiding Light: burst/sound/damage text defer until the light_missile lands', () => {
  const dispatcher = createDefaultEventDispatcher();

  const gridRef = { current: [[1, 2], [1, 2]] };
  const visionRef = { current: { visible: new Set(['1,0', '1,1']), discovered: new Set() } };
  const world = new WorldManager({ gridRef, setGrid: () => {}, visionRef });

  const entitiesRef = {
    current: {
      players: {
        hero: { id: 'hero', name: 'Cleric', renderPos: { x: 1, y: 0 }, pos: { x: 1, y: 0 }, hp: 20, max_hp: 20 },
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
  const floatingTextRef = { current: [] };
  const magicMissileRef = { current: [] };
  const mobAnimRef = { current: {} };
  const playerAnimRef = { current: {} };

  const effects = new VisualEffectsManager({
    particlesRef,
    floatingTextRef,
    magicMissileRef,
    mobAnimRef,
    playerAnimRef,
  });

  const played = [];
  const mockAudio = {
    play: (name, rate) => played.push({ name, rate }),
    playStep: () => {},
  };

  const ctx = {
    myPlayerId: 'hero',
    world,
    entities,
    effects,
    ui: new GameCallbacks({}),
    audio: mockAudio,
  };

  // Cast: RANGED_ATTACK light_missile from hero (1,0) to rat (1,1)
  dispatcher.dispatch({
    type: 'RANGED_ATTACK',
    data: {
      source: 'hero',
      x: 1,
      y: 0,
      target_x: 1,
      target_y: 1,
      projectile: 'light_missile',
      sound: 'ATTACK_MAGIC',
      is_wand: true,
      is_bow: false,
      crit: false,
      grim_proc: false,
      beam_type: null,
    },
  }, ctx);

  const missile = magicMissileRef.current[0];
  assert.ok(missile, 'bolt spawned');
  assert.equal(typeof missile.onImpact, 'function');
  assert.equal(missile.endX, 1 * 32 + 16);
  assert.equal(missile.endY, 1 * 32 + 16);
  // cast zap sound played immediately
  assert.ok(played.some(p => p.name === 'ATTACK_MAGIC'));
  const playsBeforeDamage = played.length;

  // Impact: DAMAGE arrives at cast-time, but visuals must be deferred
  dispatcher.dispatch({
    type: 'DAMAGE',
    data: {
      target: 'rat',
      amount: 5,
      projectile: 'light_missile',
      splash_count: 3,
      holy: true,
      crit: false,
      grim_proc: false,
    },
  }, ctx);

  // Nothing rendered yet (bolt still in flight)
  assert.equal(missile.impactData.amount, 5);
  assert.equal(particlesRef.current.length, 0);
  assert.equal(floatingTextRef.current.length, 0);
  assert.equal(played.length, playsBeforeDamage);

  // ... let it fly: call onImpact on missile completion
  missile.onImpact(missile.impactData);

  assert.ok(particlesRef.current.length >= 3, 'yellow splash at impact');
  assert.equal(particlesRef.current[0].color, '#FFFF44');
  assert.ok(floatingTextRef.current.some(t => t.text === '-5'));
  assert.ok(played.some(p => p.name === 'HIT_MAGIC' && p.rate >= 0.87 && p.rate <= 1.15));
});

test('DefaultEventDispatcher: SUBCLASS_CHOSEN plays MASTERY sound, operates player, and spawns spiral star particles', () => {
  const dispatcher = createDefaultEventDispatcher();

  const gridRef = { current: [[1, 2], [1, 2]] };
  const visionRef = { current: { visible: new Set(['1,0']), discovered: new Set() } };
  const world = new WorldManager({
    gridRef,
    setGrid: () => {},
    visionRef,
  });

  const entitiesRef = {
    current: {
      players: {
        hero: { id: 'hero', name: 'Warrior', renderPos: { x: 1, y: 0 }, pos: { x: 1, y: 0 }, hp: 20, max_hp: 20 },
        remoteVisible: { id: 'remoteVisible', name: 'Rogue', renderPos: { x: 1, y: 0 }, pos: { x: 1, y: 0 }, hp: 20, max_hp: 20 },
        remoteHidden: { id: 'remoteHidden', name: 'Mage', renderPos: { x: 0, y: 1 }, pos: { x: 0, y: 1 }, hp: 20, max_hp: 20 },
      },
      mobs: {},
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
  const playerAnimRef = { current: {} };

  const effects = new VisualEffectsManager({
    particlesRef,
    playerAnimRef,
  });

  const soundsPlayed = [];
  const mockAudio = {
    play: (name, rate) => { soundsPlayed.push({ name, rate }); },
    playStep: () => {},
  };

  const ctx = {
    myPlayerId: 'hero',
    world,
    entities,
    effects,
    ui: new GameCallbacks({}),
    audio: mockAudio,
  };

  // 1. Dispatch SUBCLASS_CHOSEN for local player 'hero'
  dispatcher.dispatch({
    type: 'SUBCLASS_CHOSEN',
    data: { player: 'hero', subclass: 'berserker' },
  }, ctx);

  assert.ok(soundsPlayed.some(s => s.name === 'MASTERY'), 'MASTERY sound played for local player');
  assert.ok(playerAnimRef.current.hero?.operateUntil > performance.now(), 'Player operate animation started');
  assert.equal(particlesRef.current.length, 20, 'Spawns 20 star particles');

  // Verify spiral particle physics
  const p0 = particlesRef.current[0];
  assert.equal(p0.speckFrame, 1, 'Uses STAR speck frame 1');
  assert.equal(p0.quadraticFade, true, 'Uses quadratic fade');
  assert.equal(p0.life, 1.0, 'Lifespan is 1.0s');
  assert.equal(p0.delay, 0, 'First particle has 0 delay');
  assert.equal(p0.accX, -p0.vx, 'Opposing X deceleration');
  assert.equal(p0.accY, -p0.vy, 'Opposing Y deceleration');
  assert.equal(p0.angularSpeed, 2 * Math.PI, 'Rotates 360 deg/s');

  const p19 = particlesRef.current[19];
  assert.ok(Math.abs(p19.delay - 0.95) < 1e-4, 'Last particle has 0.95s delay');

  // 2. Dispatch for hidden remote player
  soundsPlayed.length = 0;
  particlesRef.current = [];
  dispatcher.dispatch({
    type: 'SUBCLASS_CHOSEN',
    data: { player: 'remoteHidden', subclass: 'warlock' },
  }, ctx);

  assert.equal(soundsPlayed.length, 0, 'No sound for hidden remote player');
  assert.equal(particlesRef.current.length, 0, 'No particles for hidden remote player');

  // 3. Dispatch for visible remote player
  dispatcher.dispatch({
    type: 'SUBCLASS_CHOSEN',
    data: { player: 'remoteVisible', subclass: 'assassin' },
  }, ctx);

  assert.ok(soundsPlayed.some(s => s.name === 'MASTERY'), 'MASTERY sound played for visible remote player');
  assert.equal(particlesRef.current.length, 20, 'Particles spawned for visible remote player');
  assert.ok(playerAnimRef.current.remoteVisible?.operateUntil > performance.now(), 'Operate animation set for visible remote player');
});
