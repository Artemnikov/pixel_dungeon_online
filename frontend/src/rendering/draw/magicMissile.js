import { TILE_SIZE } from '../../constants';
import { setLightMode, setNormalMode } from './blending';

export const MISSILE_TYPES = {
  magic_missile: { color: '#FFFFFF', size: 4, life: 400, trailCount: 4, arcHeight: 1.5 },
  magic_bolt:    { color: '#FFFFFF', size: 4, life: 400, trailCount: 4, arcHeight: 1.5 },
  frost:         { color: '#88CCFF', size: 4, life: 500, trailCount: 4, arcHeight: 1.5 },
  fire:          { color: '#EE7722', size: 4, life: 600, trailCount: 5, arcHeight: 1.0, driftY: -1.2 },
  fire_bolt:     { color: '#EE7722', size: 4, life: 600, trailCount: 5, arcHeight: 1.0, driftY: -1.2 },
  corrosion:     { color: '#888888', size: 3, life: 600, trailCount: 3, arcHeight: 1.5, colorEnd: '#FF8844' },
  foliage:       { color: '#004400', size: 4, life: 1200, trailCount: 6, arcHeight: 1.5, colorEnd: '#88CC44' },
  force:         { color: '#664422', size: 4, life: 600, trailCount: 4, arcHeight: 0.5 },
  beacon:        { color: '#FFFFFF', size: 4, life: 500, trailCount: 8, arcHeight: 1.5, orbit: true },
  shadow:        { color: '#440066', size: 4, life: 500, trailCount: 4, arcHeight: 1.5, colorEnd: '#000000' },
  rainbow:       { color: null, size: 4, life: 500, trailCount: 4, arcHeight: 1.5, rainbow: true },
  earth:         { color: '#805500', size: 4, life: 500, trailCount: 4, arcHeight: 1.0, gravityY: 40 },
  ward:          { color: '#8822FF', size: 4, life: 600, trailCount: 4, arcHeight: 1.5, shrink: true },
  shaman_red:    { color: '#FF4D4D', size: 2, life: 600, trailCount: 3, arcHeight: 1.5, colorEnd: '#801A1A' },
  shaman_blue:   { color: '#6699FF', size: 2, life: 600, trailCount: 3, arcHeight: 1.5, colorEnd: '#1A3C80' },
  shaman_purple: { color: '#BB33FF', size: 2, life: 600, trailCount: 3, arcHeight: 1.5, colorEnd: '#5E1A80' },
  elmo:          { color: '#22EE66', size: 5, life: 600, trailCount: 5, arcHeight: 1.0, driftY: -1.2 },
  poison:        { color: '#8844AA', size: 3, life: 600, trailCount: 3, arcHeight: 1.5, colorEnd: '#44AA44' },
  toxic_gas:     { color: '#44BB44', size: 5, life: 800, trailCount: 5, arcHeight: 1.5, colorEnd: '#88FF44', driftY: -0.5 },
  light_missile: { color: '#FFFF40', size: 4, life: 400, trailCount: 4, arcHeight: 1.5 },
};

const RAINBOW_COLORS = ['#FF0000', '#FF8800', '#FFFF00', '#00FF00', '#0088FF', '#8800FF'];

function getType(typeName) {
  const isCone = typeName.endsWith('_cone');
  const baseName = isCone ? typeName.slice(0, -5) : typeName;
  const cfg = MISSILE_TYPES[baseName] || MISSILE_TYPES.magic_missile;
  return {
    ...cfg,
    size: isCone ? 10 : cfg.size,
    life: isCone ? cfg.life : cfg.life,
    isCone,
  };
}

function lerpColor(c1, c2, t) {
  const r = parseInt(c1.slice(1, 3), 16), g = parseInt(c1.slice(3, 5), 16), b = parseInt(c1.slice(5, 7), 16);
  const r2 = parseInt(c2.slice(1, 3), 16), g2 = parseInt(c2.slice(3, 5), 16), b2 = parseInt(c2.slice(5, 7), 16);
  const rr = Math.round(r + (r2 - r) * t), gg = Math.round(g + (g2 - g) * t), bb = Math.round(b + (b2 - b) * t);
  return `#${rr.toString(16).padStart(2, '0')}${gg.toString(16).padStart(2, '0')}${bb.toString(16).padStart(2, '0')}`;
}

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
    const arc = Math.sin(t * Math.PI) * TILE_SIZE * m.arcHeight;
    let driftY = 0;
    if (m.driftY) driftY = (1 - Math.abs(2 * t - 1)) * TILE_SIZE * m.driftY;

    const x = m.startX + (m.endX - m.startX) * t;
    const y = m.startY + (m.endY - m.startY) * t - arc + driftY;

    const headSize = m.size + Math.sin(t * Math.PI) * (m.size * 0.5);

    ctx.save();
    setLightMode(ctx);

    const trailCount = m.trailCount || 4;
    for (let p = 0; p < trailCount; p++) {
      const pt = Math.max(0, t - p * (0.1 / (trailCount / 4)));
      if (pt <= 0) continue;
      const px = m.startX + (m.endX - m.startX) * pt;
      const py = m.startY + (m.endY - m.startY) * pt - Math.sin(pt * Math.PI) * TILE_SIZE * m.arcHeight + (m.driftY || 0) * (1 - Math.abs(2 * pt - 1)) * TILE_SIZE;
      const alpha = t * (1 - pt) * 0.6;
      const size = m.size * 0.5 + (1 - pt) * m.size * 0.8;
      ctx.globalAlpha = alpha;
      if (m.rainbow) {
        ctx.fillStyle = RAINBOW_COLORS[Math.floor(p * pt * 10) % RAINBOW_COLORS.length];
      } else if (m.colorEnd) {
        ctx.fillStyle = lerpColor(m.color, m.colorEnd, pt);
      } else {
        ctx.fillStyle = m.color;
      }
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

export function spawnMagicMissile(missileRef, startX, startY, endX, endY, typeName) {
  const cfg = getType(typeName);
  const m = {
    startX, startY,
    endX, endY,
    color: cfg.color,
    size: cfg.size,
    duration: cfg.life,
    trailCount: cfg.trailCount,
    arcHeight: cfg.arcHeight,
    driftY: cfg.driftY,
    colorEnd: cfg.colorEnd,
    rainbow: cfg.rainbow,
    startTime: performance.now(),
  };
  missileRef.current.push(m);
}
