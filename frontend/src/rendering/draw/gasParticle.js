function spawnGasParticle(particlesRef, cx, cy, color, {
  colorEnd = null,
  size = 1,
  life = null,
  count = 1,
} = {}) {
  for (let i = 0; i < count; i++) {
    const l = life ?? 0.8 + Math.random() * 2.2;
    const ox = (Math.random() - 0.5) * 8;
    const oy = (Math.random() - 0.5) * 8;
    particlesRef.current.push({
      x: cx + ox,
      y: cy + oy,
      vx: (Math.random() - 0.5) * 4,
      vy: -4 - Math.random() * 8,
      life: l,
      maxLife: l,
      size: size + Math.random(),
      color,
      gravity: false,
      additive: true,
      triangleAlpha: true,
      growWithAge: true,
    });
    if (colorEnd) particlesRef.current[particlesRef.current.length - 1].colorEnd = colorEnd;
  }
}

export function spawnToxicGas(particlesRef, cx, cy) {
  spawnGasParticle(particlesRef, cx, cy, '#50FF60', {
    count: 3 + Math.floor(Math.random() * 3),
  });
}

export function spawnParalyticGas(particlesRef, cx, cy) {
  spawnGasParticle(particlesRef, cx, cy, '#FFFF66', {
    count: 3 + Math.floor(Math.random() * 3),
  });
}

export function spawnCorrosiveGas(particlesRef, cx, cy) {
  spawnGasParticle(particlesRef, cx, cy, '#AAAAAA', {
    colorEnd: '#FF8800',
    count: 3 + Math.floor(Math.random() * 3),
  });
  spawnGasParticle(particlesRef, cx, cy, '#FF8800', {
    size: 2,
    life: 0.2 + Math.random() * 0.2,
    count: 1,
  });
}

export function spawnConfusionGas(particlesRef, cx, cy) {
  const r = Math.floor(Math.random() * 256);
  const g = Math.floor(Math.random() * 256);
  const b = Math.floor(Math.random() * 128) + 128;
  const color = `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  spawnGasParticle(particlesRef, cx, cy, color, {
    count: 3 + Math.floor(Math.random() * 3),
  });
}
