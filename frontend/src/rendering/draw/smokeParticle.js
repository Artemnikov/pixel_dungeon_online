// SmokeParticle (SPD effects/particles/SmokeParticle.java): grey puffs that
// drift upward and fade — used for Tengu's bomb fuse and fire-ability steam.
export function spawnSmoke(ref, cx, cy, count = 4) {
  for (let i = 0; i < count; i++) {
    const life = 0.9 + Math.random() * 0.4;
    const size = 6 + Math.floor(Math.random() * 3);
    ref.current.push({
      x: cx + (Math.random() - 0.5) * 8,
      y: cy + (Math.random() - 0.5) * 8,
      vx: (Math.random() - 0.5) * 6,
      vy: -(6 + Math.random() * 8),
      life,
      maxLife: life,
      size,
      _startSize: size,
      color: Math.random() < 0.5 ? '#888888' : '#aaaaaa',
      additive: false,
      accY: -6,
    });
  }
}
