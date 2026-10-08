import { INVIS_ALPHA, MOVE_DURATION } from '../../constants';

export type Fadeable = {
  invisible?: number;
  is_afk?: boolean;
  fadeAlpha?: number;
  fadeStartAlpha?: number;
  fadeTargetAlpha?: number;
  fadeStartTime?: number | null;
  faded?: boolean;
};

export function glideDuration(fromX: number, fromY: number, toX: number, toY: number, stepDurationMs = MOVE_DURATION): number {
  return Math.min(4, Math.max(1, Math.round(Math.max(Math.abs(toX - fromX), Math.abs(toY - fromY))))) * stepDurationMs;
}

export function applyInvisFade(entity: Fadeable, newInvis: number, afk = false): void {
  const prev = entity.faded ?? false;
  const next = newInvis > 0 || afk;
  if (!prev && next) {
    entity.fadeStartAlpha = entity.fadeAlpha ?? 1;
    entity.fadeTargetAlpha = INVIS_ALPHA;
    entity.fadeStartTime = performance.now();
  } else if (prev && !next) {
    entity.fadeStartAlpha = entity.fadeAlpha ?? INVIS_ALPHA;
    entity.fadeTargetAlpha = 1;
    entity.fadeStartTime = performance.now();
  }
  entity.invisible = newInvis;
  entity.is_afk = afk;
  entity.faded = next;
}
