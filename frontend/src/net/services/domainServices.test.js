import test from 'node:test';
import assert from 'node:assert/strict';
import { VisualEffectsManager } from './VisualEffectsManager';
import { WorldManager } from './WorldManager';
import { EntityManager } from './EntityManager';
import { HeroStateSync } from './HeroStateSync';
import { GameCallbacks } from './GameCallbacks';

test('VisualEffectsManager: manages animations, screen shake, and floating text', () => {
  const projectilesRef = { current: [] };
  const particlesRef = { current: [] };
  const floatingTextRef = { current: [] };
  const playerAnimRef = { current: {} };
  const mobAnimRef = { current: {} };
  const screenShakeRef = { current: null };
  const screenFlashRef = { current: null };
  const warnedTilesRef = { current: null };

  const effects = new VisualEffectsManager({
    projectilesRef,
    particlesRef,
    floatingTextRef,
    playerAnimRef,
    mobAnimRef,
    screenShakeRef,
    screenFlashRef,
    warnedTilesRef,
  });

  effects.shakeScreen(3, 400);
  assert.equal(screenShakeRef.current.intensity, 3);

  effects.flashScreen(200);
  assert.ok(screenFlashRef.current.until > performance.now());

  effects.warnTiles([[1, 2]], 1000);
  assert.deepEqual(warnedTilesRef.current.tiles, [[1, 2]]);

  effects.setPlayerOperate('p1', 500);
  assert.ok(playerAnimRef.current.p1.operateUntil > 0);

  effects.setMobAttack('m1', 300);
  assert.ok(mobAnimRef.current.m1.attackUntil > 0);

  effects.clearFloorEffects();
  assert.equal(warnedTilesRef.current, null);
  assert.equal(projectilesRef.current.length, 0);
  assert.equal(particlesRef.current.length, 0);
});

test('VisualEffectsManager: delegates spawn helpers with valid shapes', () => {
  const flyingItemsRef = { current: [] };
  const magicMissileRef = { current: [] };
  const beamRef = { current: [] };
  const flareEffectsRef = { current: [] };
  const spellSpriteEffectsRef = { current: [] };
  const stateEffectsRef = { current: [] };
  const surpriseRef = { current: [] };

  const effects = new VisualEffectsManager({
    flyingItemsRef,
    magicMissileRef,
    beamRef,
    flareEffectsRef,
    spellSpriteEffectsRef,
    stateEffectsRef,
    surpriseRef,
  });

  effects.spawnFlyingItem('Potion of Healing', 'potion', 3, 4);
  assert.equal(flyingItemsRef.current.length, 1);
  assert.ok(Array.isArray(flyingItemsRef.current[0].coords));
  assert.equal(flyingItemsRef.current[0].tileX, 3);
  assert.equal(flyingItemsRef.current[0].tileY, 4);

  effects.spawnBeam(0, 0, 100, 100, 'death_ray');
  assert.equal(beamRef.current.length, 1);
  assert.ok(beamRef.current[0].atlas !== undefined);

  effects.spawnMagicMissile(0, 0, 50, 50, 'magic_missile');
  assert.equal(magicMissileRef.current.length, 1);
  assert.ok(typeof magicMissileRef.current[0].duration === 'number');

  effects.spawnFlare(20, 30, 8, 40, '#ffff00', 600);
  assert.equal(flareEffectsRef.current.length, 1);
  assert.equal(flareEffectsRef.current[0].cx, 20);

  effects.spawnSpellSprite(10, 20, 1);
  assert.equal(spellSpriteEffectsRef.current.length, 1);
  assert.equal(spellSpriteEffectsRef.current[0].cx, 10);

  effects.spawnStateParticles(15, 25, 'burning');
  assert.equal(stateEffectsRef.current.length, 1);
  assert.equal(stateEffectsRef.current[0].cx, 15);

  effects.spawnSurprise(40, 50);
  assert.equal(surpriseRef.current.length, 1);
  assert.equal(surpriseRef.current[0].x, 40);
});

test('WorldManager: handles grid patching, visibility and audibility queries', () => {
  let gridState = [
    [1, 1, 1],
    [1, 2, 1],
    [1, 1, 1],
  ];
  const gridRef = { current: gridState };
  const setGrid = (updater) => {
    gridState = typeof updater === 'function' ? updater(gridState) : updater;
    gridRef.current = gridState;
  };
  const visionRef = { current: { visible: new Set(['1,1']), discovered: new Set() } };
  const openDoorsRef = { current: new Set(['1,0']) };
  const depthRef = { current: 3 };

  const world = new WorldManager({
    gridRef,
    setGrid,
    visionRef,
    openDoorsRef,
    depthRef,
  });

  assert.equal(world.depth, 3);
  assert.equal(world.getTile(1, 1), 2);
  assert.equal(world.isVisible(1, 1), true);
  assert.equal(world.isVisible(0, 0), false);
  assert.equal(world.isAudible(1, 1, 'p1'), true);
  assert.equal(world.isAudible(0, 0, 'p1'), false);
  assert.equal(world.isAudible(undefined, undefined, 'p1'), true);
  assert.equal(world.isOpenDoor(1, 0), true);

  world.patchGrid([{ x: 1, y: 1, tile: 6 }]);
  assert.equal(world.getTile(1, 1), 6);
});

test('EntityManager: tracks entities, traps, plants, items, and dying mobs', () => {
  const entitiesRef = {
    current: {
      players: {
        hero: { id: 'hero', name: 'Warrior', renderPos: { x: 5, y: 5 }, is_alive: true },
      },
      mobs: {
        rat: { id: 'rat', name: 'Rat', pos: { x: 6, y: 5 }, renderPos: { x: 6, y: 5 }, hp: 8, max_hp: 8 },
      },
      items: [],
      traps: [],
      plants: [{ x: 5, y: 6, plant_type: 'sungrass' }],
    },
  };
  const dyingMobsRef = { current: {} };
  const myPlayerIdRef = { current: 'hero' };
  const selectedEnemyIdRef = { current: null };

  const entities = new EntityManager({
    entitiesRef,
    dyingMobsRef,
    myPlayerIdRef,
    selectedEnemyIdRef,
  });

  assert.equal(entities.getMyPlayerId(), 'hero');
  assert.equal(entities.getMyPlayer().name, 'Warrior');
  assert.equal(entities.getMob('rat').name, 'Rat');
  assert.equal(entities.getEntity('rat').name, 'Rat');

  entities.setSelectedEnemyId('rat');
  assert.equal(entities.getSelectedEnemyId(), 'rat');

  entities.recordDyingMob('rat', entities.getMob('rat'));
  assert.ok(dyingMobsRef.current.rat);
  assert.equal(dyingMobsRef.current.rat.name, 'Rat');
  assert.equal(entities.getPlants().length, 1);
  assert.equal(entities.getPlants()[0].plant_type, 'sungrass');
});

test('HeroStateSync: invokes setters correctly for player HUD data', () => {
  let stats = null;
  let inventory = null;
  let equipped = null;
  let gold = 0;
  let energy = 0;
  let bossInfo = null;

  const heroSync = new HeroStateSync({
    setMyStats: (val) => { stats = typeof val === 'function' ? val(stats) : val; },
    setInventory: (val) => { inventory = val; },
    setEquippedItems: (val) => { equipped = val; },
    setGold: (g) => { gold = g; },
    setEnergy: (e) => { energy = e; },
    setBossInfo: (b) => { bossInfo = b; },
  });

  heroSync.syncGold(150);
  assert.equal(gold, 150);

  heroSync.syncEnergy(45);
  assert.equal(energy, 45);

  heroSync.syncSelfPlayer({
    id: 'hero',
    name: 'Mage',
    hp: 20,
    max_hp: 20,
    inventory: [{ id: 'wand1', kind: 'WandOfMagicMissile' }],
    equipped_weapon: { kind: 'MagesStaff' },
    equipped_wearable: null,
  }, null, 'hero');

  assert.equal(stats.name, 'Mage');
  assert.equal(stats.hp, 20);
  assert.equal(inventory.length, 1);
  assert.equal(equipped.weapon.kind, 'MagesStaff');

  heroSync.syncBossInfo([
    { type: 'boss', name: 'Goo', hp: 80, max_hp: 80, is_alive: true },
  ]);
  assert.equal(bossInfo.name, 'Goo');
});

test('GameCallbacks: triggers registered progression and modal callbacks', () => {
  let leveledUp = false;
  let shopData = null;

  const callbacks = new GameCallbacks({
    onLevelUp: () => { leveledUp = true; },
    onShopOpen: (d) => { shopData = d; },
  });

  callbacks.levelUp({ level: 2, can_choose_subclass: false, can_choose_armor_ability: false });
  assert.equal(leveledUp, true);

  callbacks.shopOpen({ npc: 'Shopkeeper', stock: [], gold: 100 });
  assert.equal(shopData.npc, 'Shopkeeper');
});
