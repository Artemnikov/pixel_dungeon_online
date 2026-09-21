import type { StateUpdateMessage } from '../../types/contract';
import type { RenderPlayer } from '../types';
import type { IStateSynchronizer, StateSyncContext } from './IStateSynchronizer';
import { INVIS_ALPHA } from '../../constants';
import * as movementPredictor from '../movementPredictor';
import { applyInvisFade, glideDuration } from './syncUtils';

export class PlayersSynchronizer implements IStateSynchronizer {
  public sync(data: StateUpdateMessage, ctx: StateSyncContext): void {
    const playersState = ctx.entities.getPlayers();
    const myId = ctx.entities.getMyPlayerId();

    if (data.players && data.players.length > 0) {
      const currentServerPlayerIds = new Set(data.players.map(p => p.id));
      Object.keys(playersState).forEach(id => {
        if (!currentServerPlayerIds.has(id)) delete playersState[id];
      });
    }

    (data.players || []).forEach(p => {
      if (p.id === myId && !data.self_player) {
        if (ctx.entities.wasDownedRef) {
          ctx.entities.wasDownedRef.current = p.is_downed;
        }
        ctx.heroState.syncStatsFromPlayer(p);
      }

      if (!playersState[p.id]) {
        playersState[p.id] = {
          ...p,
          renderPos: { x: p.pos.x, y: p.pos.y },
          animStartPos: { x: p.pos.x, y: p.pos.y },
          animStartTime: null,
          facing: 'RIGHT',
          flipX: false,
          deathStart: p.is_downed ? performance.now() : null,
          fadeAlpha: (p.invisible || 0) > 0 || p.is_afk ? INVIS_ALPHA : 1,
          faded: (p.invisible || 0) > 0 || !!p.is_afk,
          fadeStartTime: null,
        } as RenderPlayer;
      } else {
        const existing = playersState[p.id];
        const isLocalPlayer = p.id === myId;
        const hasPendingPrediction = isLocalPlayer && movementPredictor.isPending();

        const moved = !existing.targetPos
          || existing.targetPos.x !== p.pos.x || existing.targetPos.y !== p.pos.y;

        const isFloorTransition = Math.abs(p.pos.x - existing.renderPos.x) > 2 ||
          Math.abs(p.pos.y - existing.renderPos.y) > 2;

        if (isFloorTransition) {
          existing.renderPos = { x: p.pos.x, y: p.pos.y };
          existing.targetPos = { x: p.pos.x, y: p.pos.y };
          existing.animStartPos = { x: p.pos.x, y: p.pos.y };
          existing.animStartTime = null;
        } else if (moved && !hasPendingPrediction) {
          const currentTarget = existing.targetPos || existing.renderPos;
          const dx = p.pos.x - currentTarget.x;
          const dy = p.pos.y - currentTarget.y;
          if (Math.abs(dx) >= Math.abs(dy)) {
            if (dx > 0) { existing.facing = 'RIGHT'; existing.flipX = false; }
            else if (dx < 0) { existing.facing = 'LEFT'; existing.flipX = true; }
          } else {
            if (dy > 0) existing.facing = 'DOWN';
            else if (dy < 0) existing.facing = 'UP';
          }
          existing.animStartPos = { x: existing.renderPos.x, y: existing.renderPos.y };
          existing.animStartTime = performance.now();
          existing.targetPos = p.pos;
          existing.moveDuration = glideDuration(existing.renderPos.x, existing.renderPos.y, p.pos.x, p.pos.y);
        }

        existing.name = p.name;
        existing.hp = p.hp;
        existing.max_hp = p.max_hp;
        existing.shields = p.shields;
        existing.equipped_wearable = p.equipped_wearable;

        if (isLocalPlayer) {
          if (data.self_player && 'equipped_weapon' in data.self_player) {
            existing.equipped_weapon = data.self_player.equipped_weapon;
          }
        } else {
          existing.equipped_weapon = p.equipped_weapon;
        }

        applyInvisFade(existing, p.invisible || 0, !!p.is_afk);

        if (p.is_downed && !existing.is_downed) {
          existing.deathStart = performance.now();
          if (p.id === myId) ctx.audio?.play('DEATH');
        }

        existing.is_downed = p.is_downed;
        existing.heal_left = p.heal_left;
        existing.class_type = p.class_type;
        existing.level = p.level;
        existing.strength = p.strength;
        existing.faction = p.faction;
        existing.step_duration_ms =
          (isLocalPlayer ? (data.self_player as { step_duration_ms?: number })?.step_duration_ms : undefined)
          ?? (p as { step_duration_ms?: number }).step_duration_ms;
      }
    });

    if (myId) {
      const serverMe = data.players?.find(p => p.id === myId);
      const lastSeq = (data.self_player as { last_processed_seq?: number })?.last_processed_seq
        ?? (serverMe as { last_processed_seq?: number })?.last_processed_seq;
      if (serverMe?.pos) {
        ctx.entities.reconcileLocalMovement(serverMe.pos, lastSeq);
      }
    }
  }
}
