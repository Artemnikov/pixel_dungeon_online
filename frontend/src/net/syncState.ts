import type { StateUpdateMessage } from '../types/contract';
import type { SyncCtx } from './types';
import { WorldManager } from './services/WorldManager';
import { EntityManager } from './services/EntityManager';
import { HeroStateSync } from './services/HeroStateSync';
import { TurnStateSync } from './services/TurnStateSync';
import { defaultStateSynchronizer } from './sync/StateSynchronizer';

export function syncState(data: StateUpdateMessage, ctx: SyncCtx): void {
  const world = new WorldManager({
    gridRef: ctx.gridRef,
    setGrid: () => {},
    visionRef: ctx.visionRef,
    openDoorsRef: ctx.openDoorsRef,
  });

  const entities = new EntityManager({
    entitiesRef: ctx.entitiesRef,
    dyingMobsRef: ctx.dyingMobsRef,
    myPlayerIdRef: ctx.myPlayerIdRef,
    wasDownedRef: ctx.wasDownedRef,
  });

  const heroState = new HeroStateSync({
    setMyStats: ctx.setMyStats,
    setInventory: ctx.setInventory,
    setEquippedItems: ctx.setEquippedItems,
    setBelongings: ctx.setBelongings,
    setQuickslot: ctx.setQuickslot,
    setGold: ctx.setGold,
    setEnergy: ctx.setEnergy,
    setHasAmulet: ctx.setHasAmulet,
    setBossInfo: ctx.setBossInfo,
    setBossLurking: ctx.setBossLurking,
  });

  defaultStateSynchronizer.sync(data, {
    world,
    entities,
    heroState,
    turnState: new TurnStateSync({ setGameMode: ctx.setGameMode, setTurnState: ctx.setTurnState }),
  });
}
