export function spawnElmo(ref, cx, cy, count = 4) {
  for (let i = 0; i < count; i++) {
    const life = 0.6;
    ref.current.push({
      x: cx + (Math.random() - 0.5) * 4,
      y: cy + (Math.random() - 0.5) * 4,
      vx: 0,
      vy: 0,
      life,
      maxLife: life,
      size: 5,
      color: '#22EE66',
      additive: true,
      gravity: true,
      accY: -80,
    });
  }
}
