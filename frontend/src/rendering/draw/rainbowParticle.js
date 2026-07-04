const COLORS = ['#FF0000', '#FF8800', '#FFFF00', '#00FF00', '#0088FF', '#8800FF', '#FF00FF'];

export function spawnRainbowBurst(ref, cx, cy, count = 10) {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 30 + Math.random() * 50;
    const life = 0.4 + Math.random() * 0.3;
    ref.current.push({
      x: cx + (Math.random() - 0.5) * 10,
      y: cy + (Math.random() - 0.5) * 10,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life,
      maxLife: life,
      size: 2 + Math.floor(Math.random() * 2),
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      additive: true,
      gravity: false,
    });
  }
}
