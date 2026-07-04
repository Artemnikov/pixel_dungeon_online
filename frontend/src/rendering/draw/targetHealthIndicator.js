import { TILE_SIZE, ENTITY_LIFT } from '../../constants';

const INDICATOR_HEIGHT = 2; // SPD TargetHealthIndicator: 2px tall

function pixelRound(value, pixelWidth) {
  return Math.ceil(value * pixelWidth) / pixelWidth;
}

export function drawTargetHealthIndicator(ctx, { entitiesRef, visionRef, selectedEnemyIdRef }) {
  if (!selectedEnemyIdRef?.current) return;

  const id = selectedEnemyIdRef.current;
  const mob = entitiesRef.current.mobs[id];
  if (!mob || !mob.is_alive) return;

  const mx = Math.round(mob.renderPos.x);
  const my = Math.round(mob.renderPos.y);
  const visible = visionRef?.current?.visible;
  if (visible && !visible.has(`${mx},${my}`)) return;

  const x = mob.renderPos.x * TILE_SIZE;
  const y = mob.renderPos.y * TILE_SIZE - ENTITY_LIFT;

  const hp = mob.hp || 0;
  const maxHp = mob.max_hp || 1;
  const shield = (mob.shields || []).reduce((sum, s) => sum + (s.amount || 0), 0);
  const max = Math.max(hp + shield, maxHp);
  let healthPct = hp / max;
  let shieldPct = (hp + shield) / max;

  const barW = TILE_SIZE;
  const barX = x;
  const barY = y - 8;

  const pxW = barW;

  ctx.fillStyle = '#cc0000';
  ctx.fillRect(barX, barY, barW, INDICATOR_HEIGHT);

  const shldW = barW * pixelRound(shieldPct, pxW);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(barX, barY, shldW, INDICATOR_HEIGHT);

  const hpW = barW * pixelRound(healthPct, pxW);
  ctx.fillStyle = '#00ee00';
  ctx.fillRect(barX, barY, hpW, INDICATOR_HEIGHT);
}
