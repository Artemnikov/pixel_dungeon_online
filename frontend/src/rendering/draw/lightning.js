import { EFFECTS } from './effectsAtlas';
import { setLightMode } from './blending';

const ARC_DURATION = 300;
const JITTER = 4;

export function spawnLightning(lightningRef, startX, startY, endX, endY, color = '#66ccff') {
  lightningRef.current.push({
    startX, startY, endX, endY, color,
    startTime: performance.now(),
    arcs: [
      { startX, startY, endX: 0, endY: 0 },
      { startX: 0, startY: 0, endX, endY },
    ],
  });
}

export function spawnChainLightning(lightningRef, segments, color = '#66ccff') {
  const startTime = performance.now();
  for (const seg of segments) {
    lightningRef.current.push({
      startX: seg.startX, startY: seg.startY,
      endX: seg.endX, endY: seg.endY,
      color: color,
      startTime,
      arcs: [
        { startX: seg.startX, startY: seg.startY, endX: 0, endY: 0 },
        { startX: 0, startY: 0, endX: seg.endX, endY: seg.endY },
      ],
    });
  }
}

export function advanceAndDrawLightning(ctx, { lightningRef, assetImages }) {
  if (!lightningRef?.current?.length) return;
  const now = performance.now();

  for (let i = 0; i < lightningRef.current.length; i++) {
    const l = lightningRef.current[i];
    const elapsed = now - l.startTime;
    if (elapsed >= ARC_DURATION) {
      lightningRef.current.splice(i, 1);
      i--;
      continue;
    }

    const alpha = 1 - elapsed / ARC_DURATION;
    const midX = (l.startX + l.endX) / 2 + (Math.random() - 0.5) * JITTER * 2;
    const midY = (l.startY + l.endY) / 2 + (Math.random() - 0.5) * JITTER * 2;

    l.arcs[0].endX = midX;
    l.arcs[0].endY = midY;
    l.arcs[1].startX = midX;
    l.arcs[1].startY = midY;

    ctx.save();
    setLightMode(ctx);
    ctx.globalAlpha = alpha;

    const effectsImg = assetImages?.effects;
    if (effectsImg) {
      const rect = EFFECTS.LIGHTNING;
      const sx = rect.x, sy = rect.y, sw = rect.w, sh = rect.h;

      for (const arc of l.arcs) {
        const dx = arc.endX - arc.startX;
        const dy = arc.endY - arc.startY;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const angle = Math.atan2(dy, dx) * (180 / Math.PI);

        ctx.save();
        ctx.translate(arc.startX, arc.startY);
        ctx.rotate(angle * Math.PI / 180);
        ctx.drawImage(effectsImg, sx, sy, sw, sh, 0, -sh / 2, dist, sh);
        ctx.restore();
      }

      if (l.color) {
        ctx.globalCompositeOperation = 'source-atop';
        ctx.fillStyle = l.color;
        ctx.globalAlpha = alpha * 0.5;
        for (const arc of l.arcs) {
          const dx = arc.endX - arc.startX;
          const dy = arc.endY - arc.startY;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const angle = Math.atan2(dy, dx) * (180 / Math.PI);
          ctx.save();
          ctx.translate(arc.startX, arc.startY);
          ctx.rotate(angle * Math.PI / 180);
          ctx.fillRect(0, -4, dist, 8);
          ctx.restore();
        }
      }
    } else {
      ctx.strokeStyle = l.color;
      ctx.lineWidth = 2;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(l.startX, l.startY);
      ctx.lineTo(midX, midY);
      ctx.lineTo(l.endX, l.endY);
      ctx.stroke();

      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(l.startX, l.startY);
      ctx.lineTo(midX, midY);
      ctx.lineTo(l.endX, l.endY);
      ctx.stroke();
    }

    ctx.restore();
  }
}
