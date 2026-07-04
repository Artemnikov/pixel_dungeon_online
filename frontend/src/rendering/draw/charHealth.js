import { TILE_SIZE, ENTITY_LIFT } from '../../constants';

const INDICATOR_HEIGHT = 1; // SPD CharHealthIndicator: 1px tall
const BAR_WIDTH_FRAC = 4 / 6; // centered, 4/6 of tile width

function pixelRound(value, pixelWidth) {
  return Math.ceil(value * pixelWidth) / pixelWidth;
}

export function drawCharHealth(ctx, { entitiesRef, visionRef }) {
  const mobs = entitiesRef.current.mobs;
  const visible = visionRef?.current?.visible;

  Object.values(mobs).forEach(mob => {
    if (!mob.is_alive) return;

    const hp = mob.hp || 0;
    const maxHp = mob.max_hp || 1;
    const shield = (mob.shields || []).reduce((sum, s) => sum + (s.amount || 0), 0);

    if (hp >= maxHp && shield === 0) return;

    const mx = Math.round(mob.renderPos.x);
    const my = Math.round(mob.renderPos.y);
    if (visible && !visible.has(`${mx},${my}`)) return;

    const x = mob.renderPos.x * TILE_SIZE;
    const y = mob.renderPos.y * TILE_SIZE - ENTITY_LIFT;

    let healthPct = hp / maxHp;
    let shieldPct = Math.min(1, (hp + shield) / maxHp);

    const barW = TILE_SIZE * BAR_WIDTH_FRAC;
    const barX = x + (TILE_SIZE - barW) / 2;
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
  });
}
