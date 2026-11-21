import { TILE_SIZE } from '../../constants';
import { spawnElmo } from './elmoParticle';
import { spawnSparkStatic } from './sparkParticle';
import { spawnBoneRattle, spawnShadowUp } from './particles';

// DwarfKing.Summoning.fx(): every inbound summon pours from its cell until it resolves.
const POURS = {
  spark: { interval: 0.05, spawn: spawnSparkStatic },
  shadow: { interval: 0.1, spawn: spawnShadowUp },
  fire: { interval: 0.1, spawn: spawnElmo },
  bones: { interval: 0.1, spawn: spawnBoneRattle },
};

const emitters = new Map();

export function advanceDwarfKingSummons({ entitiesRef, particlesRef, visionRef }) {
  if (!particlesRef?.current) return;
  const mobs = entitiesRef?.current?.mobs;
  const visible = visionRef?.current?.visible;
  const now = performance.now();
  const live = new Set();

  for (const mob of Object.values(mobs || {})) {
    if (!Array.isArray(mob.pending_summons) || mob.is_alive === false) continue;
    for (const summon of mob.pending_summons) {
      const [x, y] = summon.pos;
      const key = `${mob.id}:${x},${y}`;
      live.add(key);
      const pour = POURS[summon.particle] || POURS.bones;
      let em = emitters.get(key);
      if (!em) {
        em = { last: now, acc: pour.interval };
        emitters.set(key, em);
      }
      em.acc += Math.min((now - em.last) / 1000, 0.05);
      em.last = now;
      if (visible && !visible.has(`${x},${y}`)) {
        em.acc = 0;
        continue;
      }
      while (em.acc >= pour.interval) {
        em.acc -= pour.interval;
        const px = x * TILE_SIZE + Math.random() * TILE_SIZE;
        const py = y * TILE_SIZE + Math.random() * TILE_SIZE;
        pour.spawn(particlesRef, px, py, 1);
      }
    }
  }

  for (const key of emitters.keys()) {
    if (!live.has(key)) emitters.delete(key);
  }
}
