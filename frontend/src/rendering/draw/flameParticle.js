export function spawnFlame(ref, cx, cy, count = 4) {
  for (let i = 0; i < count; i++) {
    const life = 0.6;
    ref.current.push({
      x: cx + (Math.random() - 0.5) * 4,
      y: cy + (Math.random() - 0.5) * 4,
      vx: 0,
      vy: 0,
      life,
      maxLife: life,
      size: 4,
      color: '#EE7722',
      additive: true,
      gravity: true,
      accY: -80,
    });
  }
}

export function spawnFlameBurst(ref, cx, cy, count = 5) {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 20 + Math.random() * 30;
    const life = 0.4 + Math.random() * 0.2;
    ref.current.push({
      x: cx + (Math.random() - 0.5) * 6,
      y: cy + (Math.random() - 0.5) * 6,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life,
      maxLife: life,
      size: 3 + Math.floor(Math.random() * 2),
      color: '#EE7722',
      additive: true,
      gravity: true,
      accY: -60,
    });
  }
}
