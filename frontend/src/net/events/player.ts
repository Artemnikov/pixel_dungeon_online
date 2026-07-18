import { TILE_SIZE, PLAYER_OPERATE_DURATION, PLAYER_READ_DURATION } from '../../constants';
import AudioManager from '../../audio/AudioManager';
import {
  spawnChange, spawnCurse, spawnDiscover, spawnDust, spawnEnergy,
  spawnHeal, spawnIdentify, spawnLight, spawnNote, spawnScream,
  spawnShadowUp, spawnTerror, spawnUp,
} from '../../rendering/draw/particles';
import { spawnCheckedCells } from '../../rendering/draw/searchEffects';
import { spawnFloatingText } from '../../rendering/draw/floatingText';
import { coordsForKind } from '../../rendering/sprites';
import { spawnFlare } from '../../rendering/draw/flare';
import { spawnFlyingItem } from '../../rendering/draw/flyingItem';
import { spawnSpellSprite, SPELL_CHARGE, SPELL_MAP } from '../../rendering/draw/spellSprite';
import { forceAlertMob } from '../../rendering/draw/mobs';
import { spawnSparkMoving } from '../../rendering/draw/sparkParticle';
import { spawnLightning } from '../../rendering/draw/lightning';
import { spawnToxicGas, spawnCorrosiveGas, spawnConfusionGas } from '../../rendering/draw/gasParticle';
import { spawnWaterRipple } from '../../rendering/draw/waterRipple';
import { isWaterTile } from '../../rendering/sewers/constants';
import { addGameLog } from '../../ui/gameLogHelpers';
import type { GameEvent } from '../../types/contract';
import type { HandlerCtx } from '../types';

export function handlePlayerEvents(event: GameEvent, ctx: HandlerCtx): boolean {
  const {
    myPlayerIdRef, entitiesRef, visionRef,
    playerAnimRef, particlesRef, searchEffectsRef, floatingTextRef, lightningRef,
    screenFlashRef, transmuteEffectsRef, flareEffectsRef, spellSpriteEffectsRef,
    flyingItemsRef,
  } = ctx;

  if (event.type === 'SEARCH') {
    const pid = event.data.player;
    if (playerAnimRef && entitiesRef.current.players[pid]) {
      if (!playerAnimRef.current[pid]) playerAnimRef.current[pid] = {};
      playerAnimRef.current[pid].operateUntil = performance.now() + PLAYER_OPERATE_DURATION;
    }
    if (searchEffectsRef) spawnCheckedCells(searchEffectsRef, event.data.cells, event.data.x, event.data.y);
    return true;
  }

  if (event.type === 'DRINK') {
    const pid = event.data.player;
    const isLocal = pid === myPlayerIdRef.current;
    if (isLocal) addGameLog(`You drink ${event.data.type}`, 'highlight');
    const drinker = entitiesRef.current.players[pid];
    const visible = visionRef?.current?.visible;
    if (isLocal || (drinker && visible?.has(`${drinker.pos.x},${drinker.pos.y}`))) {
      AudioManager.play('DRINK');
    }
    if (playerAnimRef && entitiesRef.current.players[pid]) {
      if (!playerAnimRef.current[pid]) playerAnimRef.current[pid] = {};
      playerAnimRef.current[pid].operateUntil = performance.now() + PLAYER_OPERATE_DURATION;
    }
    return true;
  }

  if (event.type === 'UNLOCK') {
    const pid = event.data.player;
    const unlocker = entitiesRef.current.players[pid];
    const visible = visionRef?.current?.visible;
    const isLocal = pid === myPlayerIdRef.current;
    if (isLocal || (unlocker && visible?.has(`${unlocker.pos.x},${unlocker.pos.y}`))) {
      AudioManager.play('UNLOCK');
    }
    if (playerAnimRef && entitiesRef.current.players[pid]) {
      if (!playerAnimRef.current[pid]) playerAnimRef.current[pid] = {};
      playerAnimRef.current[pid].operateUntil = performance.now() + PLAYER_OPERATE_DURATION;
    }
    return true;
  }

  if (event.type === 'READ') {
    const pid = event.data.player;
    const reader = entitiesRef.current.players[pid];
    const visible = visionRef?.current?.visible;
    const isLocal = pid === myPlayerIdRef.current;
    const readerVisible = isLocal || (reader && visible?.has(`${reader.pos.x},${reader.pos.y}`));
    if (readerVisible) AudioManager.play(event.data.sound ?? 'READ');
    if (playerAnimRef && entitiesRef.current.players[pid]) {
      if (!playerAnimRef.current[pid]) playerAnimRef.current[pid] = {};
      playerAnimRef.current[pid].readUntil = performance.now() + PLAYER_READ_DURATION;
    }
    if (readerVisible && particlesRef && reader) {
      const cx = reader.pos.x * TILE_SIZE + TILE_SIZE / 2;
      const cy = reader.pos.y * TILE_SIZE + TILE_SIZE / 2;
      const visual = event.data.visual;
      switch (visual) {
        case 'IDENTIFY': spawnIdentify(particlesRef, cx, cy); break;
        case 'UP':
          spawnUp(particlesRef, cx, cy);
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          if ((event.data as any).shadow_particles) spawnShadowUp(particlesRef, cx, cy, 5);
          break;
        case 'CURSE':
          spawnCurse(particlesRef, cx, cy);
          spawnShadowUp(particlesRef, cx, cy, 10);
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          if (flareEffectsRef) spawnFlare(flareEffectsRef as any, cx, cy, 6, 64, '#ffffff', 800);
          break;
        case 'SCREAM': {
          spawnScream(particlesRef, cx, cy);
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const beckonedIds: string[] = (event.data as any).beckoned_ids ?? [];
          for (const id of beckonedIds) forceAlertMob(id);
          break;
        }
        case 'ENERGY':
          spawnEnergy(particlesRef, cx, cy);
          if (floatingTextRef) spawnFloatingText(floatingTextRef, cx, cy - TILE_SIZE, 'CHARGED!', '#44ccff');
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          if (spellSpriteEffectsRef) spawnSpellSprite(spellSpriteEffectsRef as any, cx, cy, SPELL_CHARGE);
          break;
        case 'NOTE': {
          spawnNote(particlesRef, cx, cy);
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const mobs = (event.data as any).affected_mobs ?? [];
          const vis = visionRef?.current?.visible;
          for (const m of mobs) {
            if (vis?.has(`${m.x},${m.y}`)) {
              spawnNote(particlesRef, m.x * TILE_SIZE + TILE_SIZE / 2, m.y * TILE_SIZE + TILE_SIZE / 2);
            }
          }
          break;
        }
        case 'TERROR':
          spawnTerror(particlesRef, cx, cy);
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          if (flareEffectsRef) spawnFlare(flareEffectsRef as any, cx, cy, 5, 64, '#ff0000', 800);
          break;
        case 'CHANGE': {
          spawnChange(particlesRef, cx, cy);
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const oldKind = (event.data as any).old_kind;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const newKind = (event.data as any).new_kind;
          if (transmuteEffectsRef && oldKind && newKind) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (transmuteEffectsRef.current as any[]).push({
              x: cx, y: cy,
              oldCoords: coordsForKind(oldKind),
              newCoords: coordsForKind(newKind),
              startTime: performance.now(),
            });
          }
          break;
        }
        case 'MAP': {
          if (floatingTextRef) spawnFloatingText(floatingTextRef, cx, cy - TILE_SIZE, 'MAPPED!', '#ffdd44');
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          if (spellSpriteEffectsRef) spawnSpellSprite(spellSpriteEffectsRef as any, cx, cy, SPELL_MAP);
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const discoverPos = (event.data as any).discover_positions ?? [];
          const vis = visionRef?.current?.visible;
          for (const pos of discoverPos) {
            if (vis?.has(`${pos.x},${pos.y}`)) {
              spawnDiscover(particlesRef, pos.x * TILE_SIZE + TILE_SIZE / 2, pos.y * TILE_SIZE + TILE_SIZE / 2);
            }
          }
          break;
        }
        case 'FLASH':
          if (screenFlashRef) screenFlashRef.current = { until: performance.now() + 350 };
          break;
      }
    }
    return true;
  }

  if (event.type === 'TELEPORT') {
    const visible = visionRef?.current?.visible;
    const pid = event.data.player;
    const isLocal = pid === myPlayerIdRef.current;
    const fromKey = `${event.data.from_x},${event.data.from_y}`;
    const toKey = `${event.data.x},${event.data.y}`;
    if (isLocal || visible?.has(fromKey)) {
      AudioManager.play('TELEPORT');
      if (particlesRef) spawnLight(particlesRef, event.data.from_x * TILE_SIZE + TILE_SIZE / 2, event.data.from_y * TILE_SIZE + TILE_SIZE / 2);
    }
    if ((isLocal || visible?.has(toKey)) && particlesRef) {
      spawnLight(particlesRef, event.data.x * TILE_SIZE + TILE_SIZE / 2, event.data.y * TILE_SIZE + TILE_SIZE / 2);
    }
    return true;
  }

  if (event.type === 'MIRROR_IMAGE') {
    const visible = visionRef?.current?.visible;
    const pid = event.data.player;
    const isLocal = pid === myPlayerIdRef.current;
    const clones = event.data.clones || [];
    for (const clone of clones) {
      if (isLocal || visible?.has(`${clone.x},${clone.y}`)) {
        if (particlesRef) spawnLight(particlesRef, clone.x * TILE_SIZE + TILE_SIZE / 2, clone.y * TILE_SIZE + TILE_SIZE / 2);
        AudioManager.play('TELEPORT');
      }
    }
    return true;
  }

  if (event.type === 'HEAL') {
    const cx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
    const cy = event.data.y * TILE_SIZE;
    if (floatingTextRef) spawnFloatingText(floatingTextRef, cx, cy, `+${event.data.amount}`, '#2ecc71');
    if (particlesRef) spawnHeal(particlesRef, cx, cy + TILE_SIZE / 2, 4);
    if (event.data.target === myPlayerIdRef.current) addGameLog(`You heal for ${event.data.amount}`, 'positive');
    return true;
  }

  if (event.type === 'TRAP_TRIGGERED') {
    const entity = entitiesRef.current.players[event.data.player] || entitiesRef.current.mobs[event.data.player];
    const isElectric = event.data.trap === 'shocking_trap' || event.data.trap === 'storm_trap';
    if (event.data.player === myPlayerIdRef.current) {
      addGameLog(`You trigger a ${event.data.trap} trap${event.data.damage ? ` for ${event.data.damage} damage` : ''}`, 'negative');
    }
    if (entity) {
      const cx = entity.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
      const cy = entity.renderPos.y * TILE_SIZE;
      if (isElectric) {
        AudioManager.play('LIGHTNING');
        if (event.data.x != null && event.data.y != null) {
          const tx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
          const ty = event.data.y * TILE_SIZE + TILE_SIZE / 2;
          spawnLightning(lightningRef, tx, ty, cx, cy, '#66ccff');
        }
        if (particlesRef) spawnSparkMoving(particlesRef, cx, cy + TILE_SIZE / 2, 6);
        if (floatingTextRef) spawnFloatingText(floatingTextRef, cx, cy, 'ZAP!', '#66ccff');
      } else {
        AudioManager.play('TRAP');
        if (event.data.damage > 0 && floatingTextRef) spawnFloatingText(floatingTextRef, cx, cy, `-${event.data.damage}`, '#e74c3c');
        if (particlesRef) {
          const trap = event.data.trap;
          if (trap === 'toxic_trap' || trap === 'poison_dart_trap') {
            for (let i = 0; i < 6; i++) spawnToxicGas(particlesRef, cx + (Math.random() - 0.5) * 32, cy + TILE_SIZE / 2 + (Math.random() - 0.5) * 32);
          } else if (trap === 'confusion_trap') {
            for (let i = 0; i < 6; i++) spawnConfusionGas(particlesRef, cx + (Math.random() - 0.5) * 32, cy + TILE_SIZE / 2 + (Math.random() - 0.5) * 32);
          } else if (trap === 'corrosion_trap') {
            for (let i = 0; i < 6; i++) spawnCorrosiveGas(particlesRef, cx + (Math.random() - 0.5) * 32, cy + TILE_SIZE / 2 + (Math.random() - 0.5) * 32);
          } else if (trap === 'chilling_trap' || trap === 'frost_trap') {
            for (let i = 0; i < 8; i++) {
              particlesRef.current.push({
                x: cx + (Math.random() - 0.5) * 32, y: cy + TILE_SIZE / 2 + (Math.random() - 0.5) * 32,
                vx: (Math.random() - 0.5) * 20, vy: -10 - Math.random() * 20,
                life: 0.6 + Math.random() * 0.4, maxLife: 1.0, size: 3,
                color: '#aaddff', gravity: false, additive: true, triangleAlpha: true, shrink: false,
              });
            }
          } else {
            spawnDust(particlesRef, cx, cy + TILE_SIZE / 2, 8);
          }
        }
      }
    }
    return true;
  }

  if (event.type === 'MOVE') {
    const tileX = event.data.x;
    const tileY = event.data.y;
    const tileType = ctx.gridRef.current[tileY]?.[tileX];
    const isDoor = tileType === 3;
    const isMe = event.data.entity === myPlayerIdRef.current;
    if (isMe) {
      if (isDoor) AudioManager.play('DOOR_OPEN');
      else if (tileType) AudioManager.playStep(tileType);
      else AudioManager.play('MOVE');
    } else {
      const visible = visionRef?.current?.visible;
      if (visible?.has(`${tileX},${tileY}`)) {
        if (isDoor) AudioManager.play('DOOR_OPEN');
        else AudioManager.play(event.type);
      }
    }
    // Port of CharSprite.move()'s `if (water[from] && !ch.flying) GameScene.ripple(from)`.
    // Uses the arrival tile (what this event carries, and what STEP_WATER
    // sound above already keys off) rather than SPD's departure tile.
    if (isWaterTile(tileType)) {
      const entityVisible = isMe || !!visionRef?.current?.visible?.has(`${tileX},${tileY}`);
      if (entityVisible) {
        const entityId = event.data.entity;
        const playerEnt = entitiesRef.current?.players?.[entityId];
        const mobEnt = entitiesRef.current?.mobs?.[entityId];
        const flying = playerEnt
          ? (playerEnt.active_effects || []).some((e) => e.key === 'levitation')
          : !!mobEnt?.flying;
        if (!flying) {
          spawnWaterRipple(tileX * TILE_SIZE + TILE_SIZE / 2, tileY * TILE_SIZE + TILE_SIZE / 2);
        }
      }
    }
    return true;
  }

  if (event.type === 'DROP' && event.data.player === myPlayerIdRef.current) {
    AudioManager.play('PICKUP');
    addGameLog(`You drop the ${event.data.item_name}`, 'neutral');
    const me = entitiesRef.current?.players?.[myPlayerIdRef.current];
    if (me && floatingTextRef) spawnFloatingText(floatingTextRef, me.renderPos.x * TILE_SIZE + TILE_SIZE / 2, me.renderPos.y * TILE_SIZE, `${event.data.item_name}`, '#ffffff', 18);
    return true;
  }

  if (event.type === 'PICKUP' && event.data.player === myPlayerIdRef.current) {
    AudioManager.play('PICKUP');
    addGameLog(`You picked up ${event.data.item}`, 'positive');
    if (flyingItemsRef) spawnFlyingItem(flyingItemsRef, event.data.item, event.data.item_type, event.data.x, event.data.y);
    return true;
  }

  if (event.type === 'PICKUP_GOLD' && event.data.player === myPlayerIdRef.current) {
    AudioManager.play('GOLD');
    addGameLog(`You picked up ${event.data.amount} gold`, 'positive');
    return true;
  }

  if (event.type === 'PICKUP_KEY' && event.data.player === myPlayerIdRef.current) {
    AudioManager.play('PICKUP');
    addGameLog(`You picked up ${event.data.name}`, 'positive');
    const me = entitiesRef.current?.players?.[myPlayerIdRef.current];
    if (me) spawnFloatingText(floatingTextRef, me.renderPos.x * TILE_SIZE + TILE_SIZE / 2, me.renderPos.y * TILE_SIZE, `${event.data.name}`, '#ffffff', 18);
    return true;
  }

  if (event.type === 'STAIRS_DOWN' && event.data.player === myPlayerIdRef.current) {
    if (event.data.first_visit) AudioManager.play('STAIRS_DOWN');
    return true;
  }

  return false;
}
