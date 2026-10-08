import { TILE_SIZE } from '../../constants';

const BASE_SIZE = 2;

function spawnParticle(ref, x, y, vx, vy, life, maxLife, size, additive, color = '#ffffff') {
  ref.current.push({
    x, y, vx, vy, life, maxLife,
    size,
    color,
    additive: additive !== false,
    gravity: false,
    centered: true,
    shrink: true,
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

// SparkParticle.resetAttracting (SparkParticle.java:84): electric sparks flowing
// across energized tiles in the exact direction of the active pylon.
export function spawnSparkAttracting(ref, cx, cy, targetX, targetY, count = 1) {
  if (!ref?.current) return;
  const dx = targetX - cx;
  const dy = targetY - cy;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const speed = 3 * TILE_SIZE; // 96 px/s (matches SPD DungeonTilemap.SIZE * 3f)
  const vx = (dx / dist) * speed;
  const vy = (dy / dist) * speed;

  for (let i = 0; i < count; i++) {
    const life = 0.20 + Math.random() * 0.15;
    // Offset slightly so particles don't spill outside the cell
    const startX = cx + (Math.random() - 0.5) * (TILE_SIZE * 0.8) - vx / 8;
    const startY = cy + (Math.random() - 0.5) * (TILE_SIZE * 0.8) - vy / 8;
    const size = 3 + Math.floor(Math.random() * 3);
    const color = Math.random() < 0.5 ? '#ffffff' : '#b8e4ff';
    spawnParticle(ref, startX, startY, vx, vy, life, life, size, true, color);
  }
}
