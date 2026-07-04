import { setLightMode } from './blending';
import { EFFECTS } from './effectsAtlas';

const BEAM_TYPES = {
  death_ray:   { atlas: EFFECTS.DEATH_RAY,  duration: 500, tint: null },
  light_ray:   { atlas: EFFECTS.LIGHT_RAY,  duration: 1000, tint: null },
  sun_ray:     { atlas: EFFECTS.LIGHT_RAY,  duration: 1000, tint: '#FFFF40' },
  health_ray:  { atlas: EFFECTS.HEALTH_RAY,  duration: 750, tint: '#FF4444', tintHigh: '#FF8888' },
};

function lerpColor(c1, c2, t) {
  const r = parseInt(c1.slice(1, 3), 16), g = parseInt(c1.slice(3, 5), 16), b = parseInt(c1.slice(5, 7), 16);
  const r2 = parseInt(c2.slice(1, 3), 16), g2 = parseInt(c2.slice(3, 5), 16), b2 = parseInt(c2.slice(5, 7), 16);
  return `#${Math.round(r + (r2 - r) * t).toString(16).padStart(2, '0')}${Math.round(g + (g2 - g) * t).toString(16).padStart(2, '0')}${Math.round(b + (b2 - b) * t).toString(16).padStart(2, '0')}`;
}

export function spawnBeam(beamRef, startX, startY, endX, endY, type, hpRatio) {
  const cfg = BEAM_TYPES[type] || BEAM_TYPES.death_ray;
  let tint = cfg.tint;
  if (type === 'health_ray' && hpRatio != null) {
    tint = lerpColor(cfg.tint, cfg.tintHigh, hpRatio);
  }
  beamRef.current.push({
    startX, startY, endX, endY,
    type,
    duration: cfg.duration,
    atlas: cfg.atlas,
    tint,
    startTime: performance.now(),
  });
}

export function advanceAndDrawBeams(ctx, { beamRef, assetImages }) {
  const active = beamRef.current;
  if (!active?.length) return;
  const now = performance.now();
  const effectsImg = assetImages?.effects;

  for (let i = active.length - 1; i >= 0; i--) {
    const b = active[i];
    const elapsed = now - b.startTime;
    if (elapsed >= b.duration) {
      active.splice(i, 1);
      continue;
    }

    const alpha = 1 - elapsed / b.duration;
    const dx = b.endX - b.startX;
    const dy = b.endY - b.startY;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    const angle = Math.atan2(dy, dx) * (180 / Math.PI);

    ctx.save();
    setLightMode(ctx);
    ctx.globalAlpha = alpha;

    if (effectsImg) {
      const sw = b.atlas.w;
      const sh = b.atlas.h;
      const sx = b.atlas.x;
      const sy = b.atlas.y;
      const scaleY = sh > 0 ? alpha : 1;

      ctx.translate(b.startX, b.startY);
      ctx.rotate(angle * Math.PI / 180);

      if (b.tint) {
        ctx.drawImage(effectsImg, sx, sy, sw, sh, 0, -sh / 2 * scaleY, dist, sh * scaleY);
        ctx.globalCompositeOperation = 'source-atop';
        ctx.fillStyle = b.tint;
        ctx.fillRect(0, -sh / 2 * scaleY, dist, sh * scaleY);
      } else {
        ctx.drawImage(effectsImg, sx, sy, sw, sh, 0, -sh / 2 * scaleY, dist, sh * scaleY);
      }
    }

    ctx.restore();
  }
}
