import type { StateUpdateMessage } from '../../types/contract';
import type { RenderMob } from '../types';
import type { IStateSynchronizer, StateSyncContext } from './IStateSynchronizer';
import { INVIS_ALPHA } from '../../constants';
import { applyInvisFade, glideDuration } from './syncUtils';

export class MobsSynchronizer implements IStateSynchronizer {
  public sync(data: StateUpdateMessage, ctx: StateSyncContext): void {
    const mobsState = ctx.entities.getMobs();

    if (data.events) {
      data.events.forEach(ev => {
        if (ev.type !== 'DEATH') return;
        const id = ev.data.target;
        const mob = mobsState[id];
        if (mob) {
          ctx.entities.recordDyingMob(id, mob);
        }
      });
    }

    const currentServerMobIds = new Set((data.mobs || []).map(m => m.id));
    Object.keys(mobsState).forEach(id => {
      if (!currentServerMobIds.has(id)) delete mobsState[id];
    });

    (data.mobs || []).forEach(m => {
      if (!mobsState[m.id]) {
        mobsState[m.id] = {
          ...m,
          renderPos: { x: m.pos.x, y: m.pos.y },
          animStartPos: { x: m.pos.x, y: m.pos.y },
          animStartTime: null,
          facing: 'RIGHT',
          fadeAlpha: (m.invisible || 0) > 0 ? INVIS_ALPHA : 1,
          fadeStartTime: null,
        } as RenderMob;
      } else {
        const existing = mobsState[m.id];
        const moved = !existing.targetPos
          || existing.targetPos.x !== m.pos.x || existing.targetPos.y !== m.pos.y;
        if (moved) {
          const currentTarget = existing.targetPos || existing.renderPos;
          if (m.pos.x > currentTarget.x) existing.facing = 'RIGHT';
          else if (m.pos.x < currentTarget.x) existing.facing = 'LEFT';
          existing.animStartPos = { x: existing.renderPos.x, y: existing.renderPos.y };
          existing.animStartTime = performance.now();
          existing.targetPos = m.pos;
          existing.moveDuration = glideDuration(existing.renderPos.x, existing.renderPos.y, m.pos.x, m.pos.y);
        }
        existing.hp = m.hp;
        existing.ai_state = m.ai_state;
        existing.faction = m.faction;
        applyInvisFade(existing, m.invisible || 0);
      }
    });
  }
}
