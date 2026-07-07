export const fadingTraps = new Map();

export function addFadingTrap(x, y, trapType) {
  const key = `${x},${y}`;
  fadingTraps.set(key, { x, y, trap_type: trapType, startTime: performance.now() });
}

export function addFadingTraps(cells, trapType) {
  const now = performance.now();
  for (const [x, y] of cells) {
    const key = `${x},${y}`;
    fadingTraps.set(key, { x, y, trap_type: trapType, startTime: now });
  }
}

export function clearExpiredFadingTraps(now) {
  for (const [key, trap] of fadingTraps) {
    if (now - trap.startTime > 4000) fadingTraps.delete(key);
  }
}

export const bombOverlay = { active: false, x: 0, y: 0 };

export function setBombItem(x, y) {
  bombOverlay.active = true;
  bombOverlay.x = x;
  bombOverlay.y = y;
}

export function clearBombItem() {
  bombOverlay.active = false;
}
