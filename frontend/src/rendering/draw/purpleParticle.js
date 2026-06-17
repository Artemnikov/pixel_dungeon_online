export function spawnPurpleBurst(ref, cx, cy, count = 8) {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 30 + Math.random() * 40;
    const life = 0.4 + Math.random() * 0.2;
    const t = Math.random();
    ref.current.push({
      x: cx + (Math.random() - 0.5) * 8,
      y: cy + (Math.random() - 0.5) * 8,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life,
      maxLife: life,
      size: 3,
      color: t < 0.5 ? '#8822FF' : '#440066',
      additive: true,
      gravity: false,
    });
  }
}
