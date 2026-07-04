import AudioManager from '../../audio/AudioManager';
import { spawnFloatingText } from '../../rendering/draw/floatingText';
import type { GameEvent } from '../../types/contract';
import type { HandlerCtx } from '../types';

export function handleAlchemyEvents(event: GameEvent, ctx: HandlerCtx): boolean {
  const { myPlayerIdRef, entitiesRef, floatingTextRef } = ctx;

  if (event.type === 'PICKUP_ENERGY') {
    const pid = event.data.player;
    if (pid === myPlayerIdRef.current) {
      AudioManager.play('PICKUP');
      const me = entitiesRef.current.players[pid];
      if (me && floatingTextRef) {
        spawnFloatingText(floatingTextRef, me.pos.x, me.pos.y, `+${event.data.amount}`, '#44ccff');
      }
    }
    return true;
  }

  if (event.type === 'ALCHEMY_PREVIEW_RESULT') {
    if (event.data.player === myPlayerIdRef.current) ctx.onAlchemyPreviewResult?.(event.data);
    return true;
  }

  if (event.type === 'ALCHEMY_BREWED') {
    if (event.data.player === myPlayerIdRef.current) {
      AudioManager.play('PUFF');
      ctx.onAlchemyBrewed?.(event.data);
    }
    return true;
  }

  if (event.type === 'ALCHEMY_ENERGIZED') {
    if (event.data.player === myPlayerIdRef.current) {
      AudioManager.play('LIGHTNING');
      ctx.onAlchemyEnergized?.(event.data);
    }
    return true;
  }

  if (event.type === 'TRINKET_CHOICE') {
    if (event.data.player === myPlayerIdRef.current) ctx.onTrinketChoice?.(event.data);
    return true;
  }

  if (event.type === 'TOOLKIT_BREW') {
    if (event.data.player === myPlayerIdRef.current) ctx.onOpenAlchemy?.();
    return true;
  }

  if (event.type === 'TOOLKIT_ENERGIZE_PROMPT') {
    if (event.data.player === myPlayerIdRef.current) ctx.onToolkitEnergizePrompt?.(event.data);
    return true;
  }

  if (event.type === 'TOOLKIT_ENERGIZED') {
    if (event.data.player === myPlayerIdRef.current) {
      AudioManager.play('DRINK');
      setTimeout(() => AudioManager.play('PUFF'), 500);
    }
    return true;
  }

  return false;
}
