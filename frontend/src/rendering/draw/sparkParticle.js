import { TILE_SIZE } from '../../constants';

const BASE_SIZE = 2;

function spawnParticle(ref, x, y, vx, vy, life, maxLife, size, additive) {
  ref.current.push({
    x, y, vx, vy, life, maxLife,
    size,
    color: '#ffffff',
    additive: additive !== false,
    gravity: false,
  });
}

export function spawnSparkMoving(ref, cx, cy, count = 8) {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 20 + Math.random() * 20;
    const life = 0.5 + Math.random() * 0.5;
    spawnParticle(ref, cx, cy, Math.cos(angle) * speed, Math.sin(angle) * speed, life, life, 5, true);
  }
}

export function spawnSparkStatic(ref, cx, cy, count = 6) {
  for (let i = 0; i < count; i++) {
    const life = 0.25 + Math.random() * 0.25;
    spawnParticle(ref, cx, cy, 0, 0, life, life, 5, true);
  }
}

export function spawnSparkAttracting(ref, cx, cy, targetX, targetY, count = 4) {
  const dx = targetX - cx;
  const dy = targetY - cy;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const speed = 3 * TILE_SIZE;
  for (let i = 0; i < count; i++) {
    const life = 0.2 + Math.random() * 0.15;
    const offX = (Math.random() - 0.5) * TILE_SIZE;
    const offY = (Math.random() - 0.5) * TILE_SIZE;
    spawnParticle(ref, cx + offX, cy + offY, (dx / dist) * speed, (dy / dist) * speed, life, life, 5, true);
  }
}
