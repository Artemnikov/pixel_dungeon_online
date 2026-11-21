import type { GameEvent } from '../../types/contract';
import type { GameEventContext, IGameEventHandler } from './IGameEventHandler';
import { GameEventDispatcher } from './GameEventDispatcher';
import { createBossEventHandlers } from './boss';
import { createWorldEventHandlers } from './world';
import { createAlchemyEventHandlers } from './alchemy';
import { createPlayerEventHandlers } from './player';
import { createCombatEventHandlers } from './combat';
import { createProgressionEventHandlers } from './progression';
import { createChatEventHandlers } from './chat';
import { createYogEventHandlers } from './yog';

const playSoundHandler: IGameEventHandler<Extract<GameEvent, { type: 'PLAY_SOUND' }>> = {
  eventType: 'PLAY_SOUND',
  handle(event, ctx: GameEventContext) {
    const audible = ctx.world.isAudible(event.data.x, event.data.y, ctx.myPlayerId);
    if (audible) {
      ctx.audio.play(event.data.sound, event.data.rate ?? 1.0);
    }
    return true;
  },
};

export function createDefaultEventDispatcher(): GameEventDispatcher {
  const dispatcher = new GameEventDispatcher();
  dispatcher.register(playSoundHandler);
  dispatcher.registerAll(createBossEventHandlers());
  dispatcher.registerAll(createWorldEventHandlers());
  dispatcher.registerAll(createAlchemyEventHandlers());
  dispatcher.registerAll(createPlayerEventHandlers());
  dispatcher.registerAll(createCombatEventHandlers());
  dispatcher.registerAll(createProgressionEventHandlers());
  dispatcher.registerAll(createChatEventHandlers());
  dispatcher.registerAll(createYogEventHandlers());
  return dispatcher;
}

export const defaultEventDispatcher = createDefaultEventDispatcher();
