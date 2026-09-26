import type { StateUpdateMessage } from '../../types/contract';
import type { WorldManager } from '../services/WorldManager';
import type { EntityManager } from '../services/EntityManager';
import type { HeroStateSync } from '../services/HeroStateSync';
import type { TurnStateSync } from '../services/TurnStateSync';

export interface StateAudioService {
  play(sound: string, rate?: number, timeout?: number): void;
}

export interface StateSyncContext {
  world: WorldManager;
  entities: EntityManager;
  heroState: HeroStateSync;
  turnState: TurnStateSync;
  audio?: StateAudioService;
}

export interface IStateSynchronizer {
  sync(data: StateUpdateMessage, ctx: StateSyncContext): void;
}
