import { TILE_SIZE } from '../../constants';

const FLAME_PARTICLE_DURATION = 600;
const FROST_PARTICLE_DURATION = 800;
const SNOW_PARTICLE_DURATION = 1000;
const MARK_PARTICLE_DURATION = 700;
const HEART_PARTICLE_DURATION = 900;

let lastNow = null;

export function spawnStateParticles(stateEffectsRef, cx, cy, type, color = null) {
  stateEffectsRef.current.push({
    cx, cy, type, color,
    startTime: performance.now(),
    particles: [],
  });
}

export function advanceAndDrawStateEffects(ctx, { stateEffectsRef }) {
  if (!stateEffectsRef?.current?.length) return;

  const now = performance.now();
  if (lastNow == null) lastNow = now;
  const dt = Math.min((now - lastNow) / 1000, 0.05);
  lastNow = now;

  const entries = stateEffectsRef.current;
  for (let i = entries.length - 1; i >= 0; i--) {
    const e = entries[i];
    const elapsed = now - e.startTime;

    switch (e.type) {
      case 'burning':
        drawBurning(ctx, e, elapsed, dt);
        break;
      case 'frozen':
        drawFrozen(ctx, e, elapsed, dt);
        break;
      case 'chilled':
        drawChilled(ctx, e, elapsed, dt);
        break;
      case 'illuminated':
        drawIlluminated(ctx, e, elapsed, dt);
        break;
      case 'marked':
        drawMarked(ctx, e, elapsed, dt);
        break;
      case 'hearts':
        drawHearts(ctx, e, elapsed, dt);
        break;
      case 'shielded':
        drawShielded(ctx, e, elapsed, dt);
        break;
      default:
        entries.splice(i, 1);
    }

    if (e.type !== 'burning' && e.type !== 'frozen' && e.type !== 'chilled' && e.type !== 'shielded') {
      if (elapsed > getDuration(e.type)) {
        entries.splice(i, 1);
      }
    }
  }
}

function getDuration(type) {
  switch (type) {
    case 'marked': return MARK_PARTICLE_DURATION;
    case 'hearts': return HEART_PARTICLE_DURATION;
    case 'illuminated': return 1200;
    default: return 1000;
  }
}

function emitParticle(e, count, spawnFn) {
  for (let i = 0; i < count; i++) {
    spawnFn(e);
  }
}

function updateParticles(e, dt, gravity) {
  for (let i = e.particles.length - 1; i >= 0; i--) {
    const p = e.particles[i];
    p.life -= dt;
    if (p.life <= 0) { e.particles.splice(i, 1); continue; }
    if (gravity) p.vy += 160 * dt;
    p.x += p.vx * dt;
    p.y += p.vy * dt;
    p.alpha = Math.max(0, p.life / p.maxLife);
  }
}

function drawParticles(ctx, e, color) {
  ctx.save();
  for (const p of e.particles) {
    ctx.globalAlpha = p.alpha;
    ctx.fillStyle = color;
    ctx.fillRect(Math.round(p.x), Math.round(p.y), p.size, p.size);
  }
  ctx.restore();
}

function drawBurning(ctx, e, elapsed, dt) {
  if (elapsed > 120000) return;
  const cx = e.cx;
  const cy = e.cy;

  if (Math.random() < 0.3) {
    const life = 0.3 + Math.random() * 0.3;
    e.particles.push({
      x: cx + (Math.random() - 0.5) * 12,
      y: cy + (Math.random() - 0.5) * 4 - 4,
      vx: (Math.random() - 0.5) * 8,
      vy: -16 - Math.random() * 16,
      life, maxLife: life,
      size: 2 + Math.floor(Math.random() * 2),
      alpha: 1,
    });
  }
  updateParticles(e, dt, false);

  ctx.save();
  ctx.globalAlpha = 0.15 + 0.08 * Math.sin(elapsed * 0.01);
  ctx.fillStyle = '#ff4400';
  ctx.fillRect(cx - TILE_SIZE / 2, cy - TILE_SIZE / 2, TILE_SIZE, TILE_SIZE);
  ctx.restore();

  drawParticles(ctx, e, '#ff6622');
}

function drawFrozen(ctx, e, elapsed, dt) {
  if (elapsed > 120000) return;
  const cx = e.cx;
  const cy = e.cy;

  if (Math.random() < 0.15) {
    const life = 0.4 + Math.random() * 0.4;
    e.particles.push({
      x: cx + (Math.random() - 0.5) * 20,
      y: cy - Math.random() * 16,
      vx: (Math.random() - 0.5) * 4,
      vy: -4 - Math.random() * 4,
      life, maxLife: life,
      size: 1 + Math.floor(Math.random() * 2),
      alpha: 1,
    });
  }
  updateParticles(e, dt, false);

  const phase = Math.sin(elapsed * 0.003) * 0.5 + 0.5;
  ctx.save();
  ctx.globalAlpha = 0.15 + 0.1 * phase;
  ctx.fillStyle = '#4488ff';
  ctx.fillRect(cx - TILE_SIZE / 2, cy - TILE_SIZE / 2, TILE_SIZE, TILE_SIZE);
  ctx.restore();

  drawParticles(ctx, e, '#88ccff');
}

function drawChilled(ctx, e, elapsed, dt) {
  if (elapsed > 120000) return;
  const cx = e.cx;
  const cy = e.cy;

  if (Math.random() < 0.2) {
    const life = 0.6 + Math.random() * 0.4;
    e.particles.push({
      x: cx + (Math.random() - 0.5) * 20,
      y: cy - Math.random() * 10,
      vx: (Math.random() - 0.5) * 6,
      vy: -8 - Math.random() * 8,
      life, maxLife: life,
      size: 1 + Math.floor(Math.random() * 2),
      alpha: 1,
    });
  }
  updateParticles(e, dt, false);

  ctx.save();
  ctx.globalAlpha = 0.08 + 0.05 * Math.sin(elapsed * 0.005);
  ctx.fillStyle = '#66aaff';
  ctx.fillRect(cx - TILE_SIZE / 2, cy - TILE_SIZE / 2, TILE_SIZE, TILE_SIZE);
  ctx.restore();

  drawParticles(ctx, e, '#aaddff');
}

function drawIlluminated(ctx, e, elapsed, dt) {
  const cx = e.cx;
  const cy = e.cy;

  if (Math.random() < 0.4) {
    const life = 0.3 + Math.random() * 0.3;
    const angle = Math.random() * Math.PI * 2;
    const speed = 8 + Math.random() * 16;
    e.particles.push({
      x: cx + (Math.random() - 0.5) * 16,
      y: cy + (Math.random() - 0.5) * 8,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - 12,
      life, maxLife: life,
      size: 2,
      alpha: 1,
    });
  }
  updateParticles(e, dt, false);

  const glow = 0.12 + 0.06 * Math.sin(elapsed * 0.004);
  ctx.save();
  ctx.globalAlpha = glow;
  ctx.fillStyle = '#ffff88';
  ctx.beginPath();
  ctx.arc(cx, cy + TILE_SIZE / 4, TILE_SIZE * 0.6, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  drawParticles(ctx, e, '#ffffaa');
}

function drawMarked(ctx, e, elapsed, dt) {
  const cx = e.cx;
  const cy = e.cy;

  if (Math.random() < 0.35) {
    const life = 0.4 + Math.random() * 0.3;
    e.particles.push({
      x: cx + (Math.random() - 0.5) * 14,
      y: cy + (Math.random() - 0.5) * 4,
      vx: (Math.random() - 0.5) * 12,
      vy: -20 - Math.random() * 16,
      life, maxLife: life,
      size: 3 + Math.floor(Math.random() * 3),
      alpha: 1,
    });
  }
  updateParticles(e, dt, false);
  drawParticles(ctx, e, '#440044');
}

function drawHearts(ctx, e, elapsed, dt) {
  const cx = e.cx;
  const cy = e.cy;

  if (Math.random() < 0.25) {
    const life = 0.5 + Math.random() * 0.4;
    e.particles.push({
      x: cx + (Math.random() - 0.5) * 14,
      y: cy + (Math.random() - 0.5) * 6,
      vx: (Math.random() - 0.5) * 8,
      vy: -12 - Math.random() * 8,
      life, maxLife: life,
      size: 2,
      alpha: 1,
    });
  }
  updateParticles(e, dt, false);

  ctx.save();
  ctx.font = '8px Arial';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  for (const p of e.particles) {
    ctx.globalAlpha = p.alpha * 0.6;
    ctx.fillStyle = '#ff4466';
    ctx.fillText('\u2665', Math.round(p.x), Math.round(p.y));
  }
  ctx.restore();
}

function drawShielded(ctx, e, elapsed, dt) {
  const cx = e.cx;
  const cy = e.cy;

  if (Math.random() < 0.2) {
    const life = 0.4 + Math.random() * 0.3;
    const angle = Math.random() * Math.PI * 2;
    const speed = 8 + Math.random() * 12;
    e.particles.push({
      x: cx + (Math.random() - 0.5) * 18,
      y: cy + (Math.random() - 0.5) * 8,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - 8,
      life, maxLife: life,
      size: 1 + Math.floor(Math.random() * 2),
      alpha: 1,
    });
  }
  updateParticles(e, dt, false);
  drawParticles(ctx, e, '#bbaacc');
}
