export function spawnFlare(flareRef, cx, cy, nRays, radius, color, durationMs = 800) {
  flareRef.current.push({ cx, cy, nRays, radius, color, startTime: performance.now(), durationMs });
}

export function advanceAndDrawFlares(ctx, { flareRef }) {
  if (!flareRef?.current?.length) return;
  const now = performance.now();
  const entries = flareRef.current;

  for (let i = entries.length - 1; i >= 0; i--) {
    const e = entries[i];
    const elapsed = now - e.startTime;
    if (elapsed >= e.durationMs) {
      entries.splice(i, 1);
      continue;
    }

    const t = elapsed / e.durationMs;
    const currentRadius = t * e.radius;
    const alpha = 1 - t;

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.globalCompositeOperation = 'lighter';
    ctx.strokeStyle = e.color;
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';

    for (let r = 0; r < e.nRays; r++) {
      const angle = (r / e.nRays) * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(e.cx, e.cy);
      ctx.lineTo(e.cx + Math.cos(angle) * currentRadius, e.cy + Math.sin(angle) * currentRadius);
      ctx.stroke();
    }

    ctx.restore();
  }
}

// CharSprite.aura(color, nRays): a Flare of `nRays` rays spinning at 90°/s
// behind the sprite for as long as the state lasts.
export function drawAura(ctx, cx, cy, nRays, radius, color, now = performance.now()) {
  const spin = ((now / 1000) * 90 * Math.PI) / 180;
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  for (let r = 0; r < nRays; r++) {
    const angle = spin + (r / nRays) * Math.PI * 2;
    const grad = ctx.createLinearGradient(cx, cy, cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius);
    grad.addColorStop(0, color);
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    const half = Math.PI / nRays / 2;
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(angle - half) * radius, cy + Math.sin(angle - half) * radius);
    ctx.lineTo(cx + Math.cos(angle + half) * radius, cy + Math.sin(angle + half) * radius);
    ctx.closePath();
    ctx.fill();
  }
  ctx.restore();
}
