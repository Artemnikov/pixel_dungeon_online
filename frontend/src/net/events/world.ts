import { TILE_SIZE } from '../../constants';
import AudioManager from '../../audio/AudioManager';
import { spawnFlameBurst } from '../../rendering/draw/flameParticle';
import { spawnElmo } from '../../rendering/draw/elmoParticle';
import { spawnEnergy } from '../../rendering/draw/particles';
import { spawnWhiteSplash, spawnSewerBarrelBurst, spawnLeafForRegion } from '../../rendering/draw/particles';
import { BACKEND_TILE } from '../../rendering/sewers/constants';
import { regionForDepth } from '../../rendering/regions';
import { spawnStateParticles } from '../../rendering/draw/states';
import { spawnSpellSprite } from '../../rendering/draw/spellSprite';
import { updateBlobArea, removeBlobArea } from '../../rendering/draw/blobArea';
import type { GameEvent } from '../../types/contract';
import type { HandlerCtx } from '../types';

export function handleWorldEvents(event: GameEvent, ctx: HandlerCtx): boolean {
  const { particlesRef, visionRef, stateEffectsRef, spellSpriteEffectsRef, blobAreasRef, setGrid, gridRef, depth } = ctx;

  if (event.type === 'BLOB_UPDATE') {
    const { id, type, cells } = event.data;
    if (blobAreasRef) updateBlobArea(blobAreasRef, id, type, cells);
    return true;
  }

  if (event.type === 'BLOB_DEPLETED') {
    if (blobAreasRef) removeBlobArea(blobAreasRef, event.data.id);
    return true;
  }

  if (event.type === 'STATE_EFFECT') {
    const { effect, x, y } = event.data;
    if (stateEffectsRef && visionRef?.current?.visible?.has(`${x},${y}`)) {
      spawnStateParticles(stateEffectsRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, effect);
    }
    return true;
  }

  if (event.type === 'SPELL_SPRITE') {
    const { x, y, index } = event.data;
    if (spellSpriteEffectsRef && visionRef?.current?.visible?.has(`${x},${y}`)) {
      spawnSpellSprite(spellSpriteEffectsRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, index);
    }
    return true;
  }

  if (event.type === 'FIRE_IMBUE_ACTIVATED') {
    const { x, y } = event.data;
    if (visionRef?.current?.visible?.has(`${x},${y}`)) {
      spawnFlameBurst(particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 16);
    }
    return true;
  }

  if (event.type === 'FLAME_BURST') {
    const { x, y } = event.data;
    if (visionRef?.current?.visible?.has(`${x},${y}`)) {
      spawnFlameBurst(particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 8);
    }
    return true;
  }

  if (event.type === 'INFERNO_ACTIVATED') {
    const { x, y } = event.data;
    if (visionRef?.current?.visible?.has(`${x},${y}`)) {
      spawnElmo(particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 12);
    }
    return true;
  }

  if (event.type === 'SACRIFICIAL_FIRE') {
    const { x, y } = event.data;
    if (visionRef?.current?.visible?.has(`${x},${y}`)) {
      spawnElmo(particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 8);
    }
    return true;
  }

  if (event.type === 'MAP_PATCH' && event.data?.tiles) {
    setGrid(prev => {
      if (!prev || prev.length === 0) return prev;
      const next = prev.map(row => row.slice());
      event.data.tiles.forEach(tilePatch => {
        const { x, y, tile } = tilePatch;
        if (y >= 0 && y < next.length && x >= 0 && x < next[y].length) {
          const wasBarrel = next[y][x] === BACKEND_TILE.REGION_DECO.id
            || next[y][x] === BACKEND_TILE.REGION_DECO_ALT.id;
          next[y][x] = tile;
          if (wasBarrel && particlesRef && visionRef?.current?.visible?.has(`${x},${y}`)) {
            spawnSewerBarrelBurst(particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2);
          }
        }
      });
      gridRef.current = next;
      return next;
    });
    return true;
  }

  if (event.type === 'LOCKED') {
    AudioManager.play('LOCKED');
    return true;
  }

  if (event.type === 'LEAF_BURST' && particlesRef) {
    const { x, y } = event.data;
    if (!visionRef || visionRef.current?.visible?.has(`${x},${y}`)) {
      const region = regionForDepth(depth || 1);
      spawnLeafForRegion(particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 4, region);
    }
    return true;
  }

  if (event.type === 'CRYSTAL_CHEST_SHATTER' && particlesRef && visionRef) {
    const { x, y } = event.data;
    if (visionRef.current?.visible?.has(`${x},${y}`)) {
      const cx = x * TILE_SIZE + TILE_SIZE / 2;
      const cy = y * TILE_SIZE + TILE_SIZE / 2;
      spawnWhiteSplash(particlesRef, cx, cy, 6);
      spawnEnergy(particlesRef, cx, cy, 10);
    }
    return true;
  }

  return false;
}
