import AudioManager from '../audio/AudioManager';
import { handleBossEvents } from './events/boss';
import { handleWorldEvents } from './events/world';
import { handlePlayerEvents } from './events/player';
import { handleCombatEvents } from './events/combat';
import { handleProgressionEvents } from './events/progression';
import type { GameEvent } from '../types/contract';
import type { HandlerCtx } from './types';

export function handleEvent(event: GameEvent, ctx: HandlerCtx): void {
  if (event.type === 'PLAY_SOUND') {
    AudioManager.play(event.data.sound, event.data.rate ?? 1.0);
    return;
  }

  if (handleBossEvents(event, ctx)) return;
  if (handleWorldEvents(event, ctx)) return;
  if (handlePlayerEvents(event, ctx)) return;
  if (handleCombatEvents(event, ctx)) return;
  handleProgressionEvents(event, ctx);
}
