import { TILE_SIZE } from '../../constants';
import { setLightMode } from './blending';
import { drawBurning, playIgniteSound } from './burningState';

const FLAME_PARTICLE_DURATION = 600;
const FROST_PARTICLE_DURATION = 800;
const SNOW_PARTICLE_DURATION = 1000;
const MARK_PARTICLE_DURATION = 700;
const HEART_PARTICLE_DURATION = 900;

const CONTINUOUS_EFFECTS = new Set(['burning', 'frozen', 'chilled', 'shielded', 'bleeding', 'levitation', 'stagger', 'illuminated']);

const TORCH_HALO_RADIUS = TILE_SIZE * 1.25;
const TORCH_HALO_BRIGHTNESS = 0.2;
const TORCH_HALO_RISE_MS = 500;
const TORCH_HALO_PUTOUT_MS = 1000;
const TORCH_HALO_KEEP_ALIVE_MS = 800;

let lastNow = null;

export function spawnStateParticles(stateEffectsRef, cx, cy, type, color = '') {
  if (CONTINUOUS_EFFECTS.has(type)) {
    const existing = stateEffectsRef.current.find(e => e.type === type && e.cx === cx && e.cy === cy);
    if (existing) {
      // Buff refresh (STATE_EFFECT fires every tick): only bump the timestamp,
      // keep accumulated particles alive.
      existing.startTime = performance.now();
      if (type === 'illuminated') {
        // The TorchHalo animates once and persists for the buff's lifetime:
        // slide the keep-alive window, and restart the rise if the buff was
        // briefly gone and got re-applied mid-putOut.
        existing.keepAliveUntil = performance.now() + TORCH_HALO_KEEP_ALIVE_MS;
        if (existing.putOutStart != null) {
          existing.putOutStart = null;
          existing.riseStart = performance.now();
        }
      }
      return;
    }
    if (type === 'burning') playIgniteSound();
  }
  const now = performance.now();
  stateEffectsRef.current.push({
    cx, cy, type, color,
    startTime: now,
    particles: [],
    ...(type === 'illuminated' ? {
      riseStart: now,
      keepAliveUntil: now + TORCH_HALO_KEEP_ALIVE_MS,
      putOutStart: null,
    } : {}),
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
        drawIlluminated(ctx, e, now);
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
      case 'bleeding':
        drawBleeding(ctx, e, elapsed, dt);
        break;
      case 'daze':
        drawDaze(ctx, e, elapsed, dt);
        break;
      case 'stagger':
        drawDaze(ctx, e, elapsed, dt);
        break;
      case 'levitation':
        drawLevitation(ctx, e, elapsed, dt);
        break;
      default:
        entries.splice(i, 1);
    }

    if (e.type === 'illuminated') {
      // Start the 1s putOut fade once the server stops refreshing the buff
      // (keep-alive grace), then drop the entry when the fade completes.
      if (now > e.keepAliveUntil && e.putOutStart == null) {
        e.putOutStart = now;
      }
      if (e.putOutStart != null && now - e.putOutStart > TORCH_HALO_PUTOUT_MS) {
        entries.splice(i, 1);
      }
    } else if (CONTINUOUS_EFFECTS.has(e.type)) {
      if (elapsed > 2000) {
        entries.splice(i, 1);
      }
    } else if (elapsed > getDuration(e.type)) {
      entries.splice(i, 1);
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

function drawIlluminated(ctx, e, now) {
  const cx = e.cx;
  const cy = e.cy;

  let phase;
  let am;
  let radius;
  if (e.putOutStart != null) {
    phase = -1 + (now - e.putOutStart) / TORCH_HALO_PUTOUT_MS;
    if (phase >= 0) return; // entry is removed by the caller
    radius = (2 + phase) * TORCH_HALO_RADIUS;
    am = -phase * TORCH_HALO_BRIGHTNESS;
  } else {
    phase = Math.min(1, (now - e.riseStart) / TORCH_HALO_RISE_MS);
    radius = phase * TORCH_HALO_RADIUS;
    am = phase * TORCH_HALO_BRIGHTNESS;
  }

  ctx.save();
  setLightMode(ctx);
  const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.max(1, radius));
  grad.addColorStop(0, `rgba(255,221,204,${am.toFixed(3)})`);
  grad.addColorStop(0.45, `rgba(255,221,204,${(am * 0.55).toFixed(3)})`);
  grad.addColorStop(1, 'rgba(255,221,204,0)');
  ctx.fillStyle = grad;
  ctx.globalAlpha = 1;
  ctx.beginPath();
  ctx.arc(cx, cy, Math.max(1, radius), 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
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

function drawBleeding(ctx, e, elapsed, dt) {
  if (elapsed > 120000) return;
  const cx = e.cx;
  const cy = e.cy;

  if (Math.random() < 0.3) {
    const life = 0.5 + Math.random() * 0.3;
    e.particles.push({
      x: cx + (Math.random() - 0.5) * 16,
      y: cy - Math.random() * 8,
      vx: (Math.random() - 0.5) * 4,
      vy: 12 + Math.random() * 8,
      life, maxLife: life,
      size: 2 + Math.floor(Math.random() * 2),
      alpha: 1,
    });
  }
  for (let i = e.particles.length - 1; i >= 0; i--) {
    const p = e.particles[i];
    p.life -= dt;
    if (p.life <= 0) { e.particles.splice(i, 1); continue; }
    p.vy += 60 * dt;
    p.x += p.vx * dt;
    p.y += p.vy * dt;
    p.alpha = Math.max(0, p.life / p.maxLife);
  }
  ctx.save();
  for (const p of e.particles) {
    ctx.globalAlpha = p.alpha * 0.6;
    ctx.fillStyle = '#cc0000';
    ctx.beginPath();
    ctx.arc(Math.round(p.x), Math.round(p.y), p.size, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function drawDaze(ctx, e, elapsed, dt) {
  const cx = e.cx;
  const cy = e.cy;

  if (Math.random() < 0.2) {
    const life = 0.3 + Math.random() * 0.2;
    e.particles.push({
      cx, cy,
      x: cx + (Math.random() - 0.5) * 20,
      y: cy + (Math.random() - 0.5) * 12,
      vx: (Math.random() - 0.5) * 16,
      vy: (Math.random() - 0.5) * 12,
      life, maxLife: life,
      size: 1,
      alpha: 1,
      angle: Math.random() * Math.PI * 2,
      spin: (Math.random() - 0.5) * 10,
    });
  }
  for (let i = e.particles.length - 1; i >= 0; i--) {
    const p = e.particles[i];
    p.life -= dt;
    if (p.life <= 0) { e.particles.splice(i, 1); continue; }
    p.x += p.vx * dt;
    p.y += p.vy * dt;
    p.angle += p.spin * dt;
    p.alpha = Math.max(0, p.life / p.maxLife);
  }
  ctx.save();
  ctx.font = '6px Arial';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  for (const p of e.particles) {
    ctx.globalAlpha = p.alpha * 0.5;
    ctx.fillStyle = '#ffff00';
    ctx.save();
    ctx.translate(Math.round(p.x), Math.round(p.y));
    ctx.rotate(p.angle);
    ctx.fillText('\u2606', 0, 0);
    ctx.restore();
  }
  ctx.restore();
}

function drawLevitation(ctx, e, elapsed, dt) {
  if (elapsed > 120000) return;
  const cx = e.cx;
  const cy = e.cy;

  if (Math.random() < 0.25) {
    const life = 0.6 + Math.random() * 0.4;
    e.particles.push({
      x: cx + (Math.random() - 0.5) * 20,
      y: cy + Math.random() * 16,
      vx: (Math.random() - 0.5) * 4,
      vy: -12 - Math.random() * 8,
      life, maxLife: life,
      size: 1 + Math.floor(Math.random() * 2),
      alpha: 1,
    });
  }
  for (let i = e.particles.length - 1; i >= 0; i--) {
    const p = e.particles[i];
    p.life -= dt;
    if (p.life <= 0) { e.particles.splice(i, 1); continue; }
    p.vy += -80 * dt;
    p.x += p.vx * dt;
    p.y += p.vy * dt;
    p.alpha = Math.max(0, p.life / p.maxLife);
  }
  ctx.save();
  setLightMode(ctx);
  for (const p of e.particles) {
    ctx.globalAlpha = p.alpha * 0.4;
    ctx.fillStyle = '#aaddff';
    ctx.fillRect(Math.round(p.x), Math.round(p.y), p.size, p.size);
  }
  ctx.restore();
}
