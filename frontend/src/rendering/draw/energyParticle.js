export function spawnEnergyParticle(ref, cx, cy, count = 12) {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 24 + Math.random() * 8;
    const life = 1.0;
    ref.current.push({
      x: cx + (Math.random() - 0.5) * 8,
      y: cy + (Math.random() - 0.5) * 8,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life,
      maxLife: life,
      size: 2,
      color: '#FFFFAA',
      additive: true,
      gravity: false,
    });
  }
}
