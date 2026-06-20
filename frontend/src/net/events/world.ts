import { TILE_SIZE } from '../../constants';
import { spawnFlameBurst } from '../../rendering/draw/flameParticle';
import { spawnElmo } from '../../rendering/draw/elmoParticle';
import { spawnStateParticles } from '../../rendering/draw/states';
import { spawnSpellSprite } from '../../rendering/draw/spellSprite';
import { updateBlobArea, removeBlobArea } from '../../rendering/draw/blobArea';
import type { GameEvent } from '../../types/contract';
import type { HandlerCtx } from '../types';

export function handleWorldEvents(event: GameEvent, ctx: HandlerCtx): boolean {
  const { particlesRef, visionRef, stateEffectsRef, spellSpriteEffectsRef, blobAreasRef, setGrid, gridRef } = ctx;

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
          next[y][x] = tile;
        }
      });
      gridRef.current = next;
      return next;
    });
    return true;
  }

  return false;
}
