const ARC_DURATION = 300;
const JITTER_AMOUNT = 4;

export function spawnLightning(lightningRef, startX, startY, endX, endY, color = '#66ccff') {
  lightningRef.current.push({
    startX, startY, endX, endY, color,
    startTime: performance.now(),
  });
}

export function advanceAndDrawLightning(ctx, { lightningRef }) {
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
    const midX = (l.startX + l.endX) / 2 + (Math.random() - 0.5) * JITTER_AMOUNT * 2;
    const midY = (l.startY + l.endY) / 2 + (Math.random() - 0.5) * JITTER_AMOUNT * 2;

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.globalCompositeOperation = 'lighter';
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

    ctx.restore();
  }
}
