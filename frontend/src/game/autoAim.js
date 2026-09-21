const rc = (v) => Math.round(v);

export function resolveTargetCrosshairCell(selectedEnemyId, mobs, visibleSet) {
  if (!selectedEnemyId) return null;
  const mob = mobs?.[selectedEnemyId];
  if (!mob || !(mob.hp > 0)) return null;
  const x = rc(mob.renderPos.x), y = rc(mob.renderPos.y);
  if (!visibleSet.has(`${x},${y}`)) return null;
  return { x, y };
}

export function pickAutoAimTarget(selectedEnemyId, mobs, visibleSet, playerPos, range, playerFaction = 'player') {
  const inRange = (mob) => {
    const x = rc(mob.renderPos.x), y = rc(mob.renderPos.y);
    if (!(mob.hp > 0) || !visibleSet.has(`${x},${y}`) || ((mob.faction || 'dungeon') === playerFaction)) return null;
    const dx = mob.renderPos.x - playerPos.x, dy = mob.renderPos.y - playerPos.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    return dist <= range ? { x, y, dist } : null;
  };

  const locked = selectedEnemyId ? mobs?.[selectedEnemyId] : null;
  if (locked) {
    const hit = inRange(locked);
    if (hit) return { id: selectedEnemyId, x: hit.x, y: hit.y };
  }

  let best = null, bestDist = Infinity;
  for (const [id, mob] of Object.entries(mobs || {})) {
    const hit = inRange(mob);
    if (hit && hit.dist < bestDist) { bestDist = hit.dist; best = { id, x: hit.x, y: hit.y }; }
  }
  return best;
}
