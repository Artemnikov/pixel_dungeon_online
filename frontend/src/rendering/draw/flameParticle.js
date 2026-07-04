export function spawnFlame(ref, cx, cy, count = 4) {
  for (let i = 0; i < count; i++) {
    const life = 0.6;
    const size = 8;
    ref.current.push({
      x: cx + (Math.random() - 0.5) * 6,
      y: cy + (Math.random() - 0.5) * 6,
      vx: (Math.random() - 0.5) * 8,
      vy: -(8 + Math.random() * 16),
      life,
      maxLife: life,
      size,
      _startSize: size,
      color: '#EE7722',
      additive: true,
      accY: -40,
      shrink: true,
    });
  }
}

export function spawnFlameBurst(ref, cx, cy, count = 12) {
  for (let i = 0; i < count; i++) {
    const angle = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI;
    const speed = 40 + Math.random() * 40;
    const life = 0.5 + Math.random() * 0.5;
    const size = 6 + Math.floor(Math.random() * 3);
    ref.current.push({
      x: cx + (Math.random() - 0.5) * 8,
      y: cy + (Math.random() - 0.5) * 8,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life,
      maxLife: life,
      size,
      _startSize: size,
      color: '#FF4400',
      additive: true,
      accY: 100,
      shrink: true,
    });
  }
}
