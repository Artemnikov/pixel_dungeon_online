import { TILE_SIZE, ENTITY_LIFT } from '../../constants';
import { setLightMode } from './blending';

const AMBIENT_COLOR = '#ffffff';
const AMBIENT_ALPHA = 0.3;
const LIFESPAN = 1.0;
const DRIFT_SPEED = 2;
const SPAWN_INTERVAL = 0.1;

let lastSpawn = 0;

export function advanceAndDrawStaffAmbient(ctx, ref, entitiesRef, visionRef, myPlayerId) {
  if (!ref?.current) return;
  const particles = ref.current;
  const now = performance.now();

  // Spawn new particles around players wielding a staff
  if (now - lastSpawn > SPAWN_INTERVAL * 1000) {
    lastSpawn = now;
    const players = entitiesRef?.current?.players;
    if (players) {
      for (const id of Object.keys(players)) {
        const p = players[id];
        if (p.is_downed) continue;
        if (p.belongings?.weapon?.kind === 'staff' && (id === myPlayerId || visionRef?.current?.visible?.has(`${Math.round(p.renderPos.x)},${Math.round(p.renderPos.y)}`))) {
          const cx = p.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
          const cy = p.renderPos.y * TILE_SIZE + TILE_SIZE / 2 - ENTITY_LIFT;
          // 1-2 particles per tick around the weapon side
          const count = 1 + Math.floor(Math.random() * 2);
          for (let i = 0; i < count; i++) {
            particles.push({
              x: cx + (Math.random() - 0.5) * TILE_SIZE * 0.5,
              y: cy + (Math.random() - 0.5) * TILE_SIZE * 0.3 - TILE_SIZE * 0.3,
              vx: (Math.random() - 0.5) * DRIFT_SPEED,
              vy: -DRIFT_SPEED - Math.random() * DRIFT_SPEED,
              life: LIFESPAN,
              maxLife: LIFESPAN,
              size: 1 + Math.floor(Math.random() * 2),
              color: AMBIENT_COLOR,
            });
          }
        }
      }
    }
  }

  const dt = 1 / 60;
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.life -= dt;
    if (p.life <= 0) { particles.splice(i, 1); continue; }
    p.x += p.vx;
    p.y += p.vy;

    ctx.save();
    setLightMode(ctx);
    ctx.globalAlpha = (p.life / p.maxLife) * AMBIENT_ALPHA;
    ctx.fillStyle = p.color;
    ctx.fillRect(Math.round(p.x), Math.round(p.y), p.size, p.size);
    ctx.restore();
  }
}
