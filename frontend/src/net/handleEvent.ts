import AudioManager from '../audio/AudioManager';
import { handleBossEvents } from './events/boss';
import { handleWorldEvents } from './events/world';
import { handleAlchemyEvents } from './events/alchemy';
import { handlePlayerEvents } from './events/player';
import { handleCombatEvents } from './events/combat';
import { handleProgressionEvents } from './events/progression';
import type { GameEvent } from '../types/contract';
import type { HandlerCtx } from './types';

export function handleEvent(event: GameEvent, ctx: HandlerCtx): void {
  if (event.type === 'PLAY_SOUND') {
    const audible = !event.data.x || !event.data.y
      || ctx.myPlayerIdRef.current === null
      || ctx.visionRef?.current?.visible?.has(`${event.data.x},${event.data.y}`);
    if (audible) {
      AudioManager.play(event.data.sound, event.data.rate ?? 1.0);
    }
    return;
  }

  if (handleBossEvents(event, ctx)) return;
  if (handleWorldEvents(event, ctx)) return;
  if (handleAlchemyEvents(event, ctx)) return;
  if (handlePlayerEvents(event, ctx)) return;
  if (handleCombatEvents(event, ctx)) return;
  handleProgressionEvents(event, ctx);
}
