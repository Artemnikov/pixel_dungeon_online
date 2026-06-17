export function spawnScreenShake(shakeRef, intensity, durationMs) {
  shakeRef.current = {
    intensity,
    until: performance.now() + durationMs,
  };
}

export function advanceAndDrawScreenShake(ctx, { shakeRef }) {
  if (!shakeRef?.current) return;
  const now = performance.now();
  const shake = shakeRef.current;
  if (now >= shake.until) {
    shakeRef.current = null;
    return;
  }
  const ox = (Math.random() - 0.5) * shake.intensity * 2;
  const oy = (Math.random() - 0.5) * shake.intensity * 2;
  ctx.translate(ox, oy);
}
