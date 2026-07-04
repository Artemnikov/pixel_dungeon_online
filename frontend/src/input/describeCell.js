import i18n from '../i18n';

// Describe whatever occupies a cell, for the examine-mode "inspect" action.
// Mirrors the spirit of GameScene.examineCell() in the original Shattered Pixel
// Dungeon (look at a mob, item, trap, or tile). Returns a structured payload
// that the caller uses to dispatch to the right WndInfo* popup.
//
// Tile ids match the backend TileType enum (app/engine/dungeon/constants.py).
const TILE_NAMES = {
  0: 'tile.chasm',
  1: 'tile.wall',
  2: 'tile.floor',
  3: 'tile.closedDoor',
  4: 'tile.stairsUp',
  5: 'tile.stairsDown',
  6: 'tile.woodenFloor',
  7: 'tile.water',
  8: 'tile.cobbledFloor',
  9: 'tile.grass',
  10: 'tile.lockedDoor',
  13: 'tile.inactiveTrap',
  14: 'tile.embers',
  17: 'tile.wall',
  18: 'tile.floor',
  19: 'tile.highGrass',
  20: 'tile.wall',
  21: 'tile.lockedExit',
  22: 'tile.openDoor',
  30: 'tile.furrowedGrass',
  31: 'tile.crystalDoor',
  32: 'tile.barricade',
  33: 'tile.chasm',
};

const TILE_DESC = {
  0: 'tile.desc.chasm', 7: 'tile.desc.water',
  4: 'tile.desc.stairsUp', 5: 'tile.desc.stairsDown',
  10: 'tile.desc.lockedDoor', 21: 'tile.desc.lockedExit',
  19: 'tile.desc.highGrass', 30: 'tile.desc.highGrass',
  14: 'tile.desc.embers', 32: 'tile.desc.barricade',
  13: 'tile.desc.inactiveTrap', 31: 'tile.desc.crystalDoor',
};

// Logical tile of an animated entity: prefer its server destination (targetPos),
// fall back to where it currently renders. The per-tick sync updates targetPos but
// not pos, so targetPos is the freshest logical cell.
function entityTile(e) {
  const p = e.targetPos || e.renderPos || e.pos;
  return p ? { x: Math.round(p.x), y: Math.round(p.y) } : null;
}

// Returns a payload describing the cell, or null if out of bounds:
//   { kind: 'mob'|'item'|'trap'|'tile'|'player'|'darkness',
//     name, sub, anchor, mob?, item?, trapType?, tileId? }
export function describeCell({ tileX, tileY, gridRef, entitiesRef, visionRef, myPlayerId, trapsRef }) {
  const grid = gridRef.current;
  if (!grid || tileY < 0 || tileY >= grid.length || tileX < 0 || tileX >= (grid[0]?.length || 0)) {
    return null;
  }

  const tileAnchor = { type: 'tile', x: tileX, y: tileY };

  const visible = visionRef.current.visible.has(`${tileX},${tileY}`);
  const discovered = visible || visionRef.current.discovered.has(`${tileX},${tileY}`);
  if (!discovered) {
    return { kind: 'darkness', name: i18n.t('tile.darkness'), sub: null, anchor: tileAnchor };
  }

  const ents = entitiesRef.current;

  // Mobs and players are only identifiable while currently visible.
  if (visible) {
    for (const mob of Object.values(ents.mobs || {})) {
      const t = entityTile(mob);
      if (t && t.x === tileX && t.y === tileY) {
        const hp = mob.hp != null && mob.max_hp != null ? `HP ${mob.hp}/${mob.max_hp}` : null;
        const mobName = mob.locale_key
          ? i18n.t(mob.locale_key, { defaultValue: mob.name || '' })
          : (mob.name || i18n.t('entity.creature'));
        return { kind: 'mob', name: mobName, sub: hp, anchor: { type: 'mob', id: mob.id }, mob };
      }
    }
    for (const pl of Object.values(ents.players || {})) {
      const t = entityTile(pl);
      if (t && t.x === tileX && t.y === tileY) {
        const plName = pl.id === myPlayerId
          ? i18n.t('entity.you')
          : (pl.name || i18n.t('entity.adventurer'));
        return { kind: 'player', name: plName, sub: null, anchor: tileAnchor, player: pl };
      }
    }
    for (const item of ents.items || []) {
      if (item.pos && item.pos.x === tileX && item.pos.y === tileY) {
        const itemName = item.locale_key
          ? i18n.t(item.locale_key, { defaultValue: item.name || '' })
          : (item.name || i18n.t('tile.item'));
        return { kind: 'item', name: itemName, sub: null, anchor: tileAnchor, item };
      }
    }
    // Traps (visible only — server only sends visible traps for non-admins).
    const traps = trapsRef?.current || [];
    for (const tr of traps) {
      if (tr.x === tileX && tr.y === tileY) {
        const trapName = i18n.t(`trap.${tr.trap_type}`, { defaultValue: tr.trap_type });
        return { kind: 'trap', name: trapName, sub: null, anchor: tileAnchor, trapType: tr.trap_type };
      }
    }
  }

  const tileId = grid[tileY][tileX];
  const tileKey = TILE_NAMES[tileId];
  const name = tileKey ? i18n.t(tileKey) : i18n.t('tile.floor');
  const descKey = TILE_DESC[tileId];
  const description = descKey ? i18n.t(descKey) : '';
  return { kind: 'tile', name, sub: null, anchor: tileAnchor, tileId, description };
}
