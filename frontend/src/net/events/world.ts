import { TILE_SIZE } from '../../constants';
import AudioManager from '../../audio/AudioManager';
import { spawnFlameBurst } from '../../rendering/draw/flameParticle';
import { spawnElmo } from '../../rendering/draw/elmoParticle';
import { spawnWhiteSplash, spawnSewerBarrelBurst, spawnLeafForRegion, spawnEnergy, spawnBoneRattle, spawnCoin, spawnBombBlast, spawnDust, spawnCritSparkle } from '../../rendering/draw/particles';
import { spawnScreenShake } from '../../rendering/draw/screenShake';
import { BACKEND_TILE } from '../../rendering/sewers/constants';
import { regionForDepth } from '../../rendering/regions';
import { spawnStateParticles } from '../../rendering/draw/states';
import { spawnSpellSprite } from '../../rendering/draw/spellSprite';
import { updateBlobArea, removeBlobArea } from '../../rendering/draw/blobArea';
import type { GameEvent } from '../../types/contract';
import type { HandlerCtx } from '../types';

// Per-kind blast tint [hot core, cooled edge]. Default is a fiery orange; the
// enhanced bombs read distinctly. Firebomb keeps the fiery default.
const BOMB_BLAST_TINT: Record<string, [string, string]> = {
  frost_bomb: ['#AEE6FF', '#2C79B8'],
  smoke_bomb: ['#CFCFCF', '#5A5A5A'],
  holy_bomb: ['#FFF3B0', '#C99A00'],
  flashbang_bomb: ['#FFFFFF', '#7FA8FF'],
  arcane_bomb: ['#E4B4FF', '#6A22AA'],
  regrowth_bomb: ['#BFF7A0', '#2E7D32'],
  woolly_bomb: ['#FFFFFF', '#BFBFBF'],
};

export function handleWorldEvents(event: GameEvent, ctx: HandlerCtx): boolean {
  const { particlesRef, visionRef, stateEffectsRef, spellSpriteEffectsRef, blobAreasRef, setGrid, gridRef, depth, screenShakeRef } = ctx;

  if (event.type === 'CHASM_PROMPT') {
    ctx.onChasmPrompt?.(event.data);
    return true;
  }

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

  if (event.type === 'WOOL_BURST' && particlesRef) {
    const { x, y } = event.data;
    if (!visionRef || visionRef.current?.visible?.has(`${x},${y}`)) {
      spawnWhiteSplash(particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 4);
    }
    return true;
  }

  if (event.type === 'FLOCK' && particlesRef && visionRef) {
    const sheep = event.data.sheep || [];
    for (const s of sheep) {
      if (visionRef.current?.visible?.has(`${s.x},${s.y}`)) {
        spawnWhiteSplash(particlesRef, s.x * TILE_SIZE + TILE_SIZE / 2, s.y * TILE_SIZE + TILE_SIZE / 2, 4);
      }
    }
    return true;
  }

  if (event.type === 'BOMB_LIT') {
    const { x, y } = event.data;
    if (particlesRef && (!visionRef || visionRef.current?.visible?.has(`${x},${y}`))) {
      spawnCritSparkle(particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 5, '#FF5522');
    }
    return true;
  }

  if (event.type === 'BOMB_BLAST') {
    const { x, y, kind, cells } = event.data;
    const [core, edge] = BOMB_BLAST_TINT[kind] ?? ['#FFDD66', '#992200'];
    if (particlesRef) {
      if (!visionRef || visionRef.current?.visible?.has(`${x},${y}`)) {
        spawnBombBlast(particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 26, core, edge);
        spawnScreenShake(screenShakeRef, 1, 220);
      }
      for (const cell of cells ?? []) {
        const [cxx, cyy] = cell;
        if (!visionRef || visionRef.current?.visible?.has(`${cxx},${cyy}`)) {
          spawnDust(particlesRef, cxx * TILE_SIZE + TILE_SIZE / 2, cyy * TILE_SIZE + TILE_SIZE / 2, 3, '#8a8a8a');
        }
      }
    }
    return true;
  }

  if (event.type === 'LOCKED') {
    AudioManager.play('LOCKED');
    return true;
  }

  if (event.type === 'OPEN_CHEST' && particlesRef && visionRef) {
    const { x, y, chest_type } = event.data;
    if (visionRef.current?.visible?.has(`${x},${y}`)) {
      const cx = x * TILE_SIZE + TILE_SIZE / 2;
      const cy = y * TILE_SIZE + TILE_SIZE / 2;
      if (chest_type === 'TOMB') {
        spawnScreenShake(screenShakeRef, 1, 500);
        spawnWhiteSplash(particlesRef, cx, cy, 6);
      } else if (chest_type === 'SKELETON' || chest_type === 'REMAINS') {
        spawnBoneRattle(particlesRef, cx, cy);
        spawnWhiteSplash(particlesRef, cx, cy, 4);
      } else {
        spawnWhiteSplash(particlesRef, cx, cy, 4);
      }
    }
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

  if (event.type === 'GOLD_DROP' && particlesRef && visionRef) {
    const { x, y } = event.data;
    if (visionRef.current?.visible?.has(`${x},${y}`)) {
      const cx = x * TILE_SIZE + TILE_SIZE / 2;
      const cy = y * TILE_SIZE + TILE_SIZE / 2;
      spawnCoin(particlesRef, cx, cy);
      AudioManager.play('GOLD');
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
