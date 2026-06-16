import { TILE_SIZE } from '../../constants';

const PARTICLE_LIFETIME = 300;

export function advanceAndDrawMagicMissiles(ctx, magicMissileRef) {
  const active = magicMissileRef.current;
  const now = performance.now();
  const finished = [];

  for (let i = active.length - 1; i >= 0; i--) {
    const m = active[i];
    if (!m) { finished.push(i); continue; }

    const elapsed = now - m.startTime;
    if (elapsed > m.duration) { finished.push(i); continue; }

    const t = elapsed / m.duration;
    const x = m.startX + (m.endX - m.startX) * t;
    const y = m.startY + (m.endY - m.startY) * t - Math.sin(t * Math.PI) * TILE_SIZE * 1.5;

    const headSize = 6 + Math.sin(t * Math.PI) * 3;
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';

    for (let p = 0; p < 4; p++) {
      const pt = Math.max(0, t - p * 0.08);
      if (pt <= 0) continue;
      const px = m.startX + (m.endX - m.startX) * pt;
      const py = m.startY + (m.endY - m.startY) * pt - Math.sin(pt * Math.PI) * TILE_SIZE * 1.5;
      const alpha = (1 - pt) * 0.6;
      const size = 3 + (1 - pt) * 4;
      ctx.globalAlpha = alpha;
      ctx.fillStyle = m.color || '#3498db';
      ctx.beginPath();
      ctx.arc(px, py, size, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.globalAlpha = 1;
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(x, y, headSize, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  for (const i of finished) {
    delete active[i];
  }
}

export function spawnMagicMissile(missileRef, startX, startY, endX, endY, color, duration) {
  const m = {
    startX, startY,
    endX, endY,
    color: color || '#3498db',
    duration: duration || 400,
    startTime: performance.now(),
  };
  missileRef.current.push(m);
}
