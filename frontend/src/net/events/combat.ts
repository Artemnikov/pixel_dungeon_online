import { TILE_SIZE, PLAYER_ATTACK_DURATION, HIT_CONNECT_DELAY, FLASH_DURATION } from '../../constants';
import AudioManager from '../../audio/AudioManager';
import { spawnBlood, spawnCritSparkle, spawnGrimShadow, spawnWhiteSplash } from '../../rendering/draw/particles';
import { spawnSurprise } from '../../rendering/draw/surprise';
import { spawnFloatingText, TEXT_ICON } from '../../rendering/draw/floatingText';
import { coordsForItem } from '../../rendering/sprites';
import { spawnLightning } from '../../rendering/draw/lightning';
import { spawnMagicMissile, MISSILE_TYPES } from '../../rendering/draw/magicMissile';
import { spawnBeam } from '../../rendering/draw/beam';
import { spawnScreenShake } from '../../rendering/draw/screenShake';
import { spawnSparkMoving } from '../../rendering/draw/sparkParticle';
import { addGameLog } from '../../ui/gameLogHelpers';
import type { GameEvent } from '../../types/contract';
import type { HandlerCtx } from '../types';

const BLOOD_COLORS: Record<string, string> = { Goo: '#000000' };

const MAGIC_PROJECTILES = new Set([
  'magic_bolt', 'magic_missile', 'fire_bolt', 'frost', 'corrosion',
  'foliage', 'force', 'beacon', 'shadow', 'rainbow', 'earth', 'ward',
  'shaman_red', 'shaman_blue', 'shaman_purple', 'elmo', 'poison', 'light_missile',
  'lightning', 'beam',
]);

export function handleCombatEvents(event: GameEvent, ctx: HandlerCtx): boolean {
  const {
    myPlayerIdRef, entitiesRef, visionRef,
    projectilesRef, mobAnimRef, playerAnimRef, particlesRef,
    floatingTextRef, lightningRef, magicMissileRef, beamRef,
    screenShakeRef, surpriseRef, selectedEnemyIdRef, dyingMobsRef,
    onPlayerDeath,
  } = ctx;

  if (event.type === 'RANGED_ATTACK') {
    const startX = event.data.x * TILE_SIZE + TILE_SIZE / 2;
    const startY = event.data.y * TILE_SIZE + TILE_SIZE / 2;
    const targetX = event.data.target_x * TILE_SIZE + TILE_SIZE / 2;
    const targetY = event.data.target_y * TILE_SIZE + TILE_SIZE / 2;
    const thrownItem = event.data.item;
    const spriteCoords = thrownItem ? coordsForItem(thrownItem) : null;
    const projType = event.data.projectile || 'arrow';
    const beamType = event.data.beam_type;

    if (!MAGIC_PROJECTILES.has(projType)) {
      projectilesRef.current.push({ x: startX, y: startY, startX, startY, targetX, targetY, type: projType, spriteCoords, progress: 0, rotation: 0, finished: false });
    }

    const src = event.data.source;
    const isLocal = src === myPlayerIdRef.current;
    const visible = visionRef?.current?.visible;
    const audible = isLocal || visible?.has(`${event.data.x},${event.data.y}`);

    const srcPlayer = entitiesRef.current.players[src];
    if (srcPlayer && playerAnimRef && event.data.is_wand) {
      if (!playerAnimRef.current[src]) playerAnimRef.current[src] = {};
      playerAnimRef.current[src].attackUntil = performance.now() + PLAYER_ATTACK_DURATION;
      const dx = event.data.target_x - event.data.x;
      if (dx > 0) { srcPlayer.facing = 'RIGHT'; srcPlayer.flipX = false; }
      else if (dx < 0) { srcPlayer.facing = 'LEFT'; srcPlayer.flipX = true; }
    }

    if (projType === 'lightning') {
      if (audible) AudioManager.play('LIGHTNING');
      spawnLightning(lightningRef, startX, startY, targetX, targetY, '#66ccff');
      spawnSparkMoving(particlesRef, targetX, targetY, 3);
      if (isLocal) spawnScreenShake(screenShakeRef, 2, 300);
    } else if (beamType && (projType === 'beam' || projType === 'magic_bolt')) {
      if (audible) AudioManager.play('RAY');
      spawnBeam(beamRef, startX, startY, targetX, targetY, beamType);
    } else if (event.data.is_wand) {
      if (audible) AudioManager.play(event.data.sound ?? 'ATTACK_MAGIC');
      if (MAGIC_PROJECTILES.has(projType)) spawnMagicMissile(magicMissileRef, startX, startY, targetX, targetY, projType);
    } else if (MAGIC_PROJECTILES.has(projType)) {
      if (audible) AudioManager.play(event.data.sound ?? 'ATTACK_MAGIC');
      spawnMagicMissile(magicMissileRef, startX, startY, targetX, targetY, projType);
    } else if (thrownItem) {
      if (audible) AudioManager.play('THROW');
    } else {
      if (audible) AudioManager.play('ATTACK_BOW');
    }
    return true;
  }

  if (event.type === 'ATTACK') {
    const src = event.data.source;
    const tgt = event.data.target;
    const damage = event.data.damage || 0;
    const now = performance.now();

    const srcMob = entitiesRef.current.mobs[src];
    const srcPlayer = entitiesRef.current.players[src];
    const srcEntity = srcMob || srcPlayer;
    const tgtEntity = entitiesRef.current.mobs[tgt] || entitiesRef.current.players[tgt];

    if (tgt === myPlayerIdRef.current) {
      const attackerName = srcMob?.name || srcPlayer?.name || 'Something';
      addGameLog(`${attackerName} hits you for ${damage}`, 'negative');
    } else if (src === myPlayerIdRef.current) {
      const targetName = tgtEntity?.name || 'target';
      addGameLog(`You hit ${targetName} for ${damage}`, damage > 0 ? 'positive' : 'default');
    }

    if (src === myPlayerIdRef.current && !!entitiesRef.current.mobs[tgt]) {
      if (selectedEnemyIdRef) selectedEnemyIdRef.current = tgt;
    }

    if (srcMob) {
      if (!mobAnimRef.current[src]) mobAnimRef.current[src] = {};
      const attackDuration = srcMob.name === 'Goo' ? 300 : srcMob.name === 'Scorpio' ? 200 : srcMob.name === 'Rat' ? 333 : srcMob.name === 'Snake' ? 333 : 250;
      mobAnimRef.current[src].attackUntil = now + attackDuration;
    } else if (srcPlayer && playerAnimRef) {
      if (!playerAnimRef.current[src]) playerAnimRef.current[src] = {};
      playerAnimRef.current[src].attackUntil = now + PLAYER_ATTACK_DURATION;
    }

    if (srcEntity && tgtEntity) {
      const dx = tgtEntity.renderPos.x - srcEntity.renderPos.x;
      if (dx > 0) { srcEntity.facing = 'RIGHT'; srcEntity.flipX = false; }
      else if (dx < 0) { srcEntity.facing = 'LEFT'; srcEntity.flipX = true; }
    }

    if (damage > 0 && tgtEntity) {
      const sc = srcEntity ? {
        x: srcEntity.renderPos.x * TILE_SIZE + TILE_SIZE / 2,
        y: srcEntity.renderPos.y * TILE_SIZE + TILE_SIZE / 2,
      } : null;
      const tc = {
        x: tgtEntity.renderPos.x * TILE_SIZE + TILE_SIZE / 2,
        y: tgtEntity.renderPos.y * TILE_SIZE + TILE_SIZE / 2,
      };
      const isMobTarget = !!entitiesRef.current.mobs[tgt];
      const maxHp = tgtEntity.max_hp || 1;
      const color = BLOOD_COLORS[tgtEntity.name] || '#bb0000';
      const isCrit = event.data.crit;
      const isGrim = event.data.grim_proc;
      const isSurprise = event.data.surprise;
      const hitIcon = isSurprise ? TEXT_ICON.HIT_SUPR
        : src === myPlayerIdRef.current ? TEXT_ICON.HIT_WEP
        : TEXT_ICON.HIT_BLS;

      setTimeout(() => {
        const flashDuration = isCrit ? FLASH_DURATION * 2 : FLASH_DURATION;
        const flashUntil = performance.now() + flashDuration;
        if (isMobTarget) {
          if (!mobAnimRef.current[tgt]) mobAnimRef.current[tgt] = {};
          mobAnimRef.current[tgt].flashUntil = flashUntil;
          if (particlesRef) {
            const awayAngle = sc ? Math.atan2(tc.y - sc.y, tc.x - sc.x) : -Math.PI / 2;
            if (isCrit) {
              const critCount = Math.min(Math.round(14 * Math.sqrt(damage / maxHp)), 14);
              spawnBlood(particlesRef, tc.x, tc.y, awayAngle, critCount, '#ffcc00');
              spawnCritSparkle(particlesRef, tc.x, tc.y, 10);
              spawnFloatingText(floatingTextRef, tc.x, tc.y - TILE_SIZE / 2, 'CRIT!', '#ffcc00', hitIcon);
            } else {
              const count = Math.min(Math.round(9 * Math.sqrt(damage / maxHp)), 9);
              spawnBlood(particlesRef, tc.x, tc.y, awayAngle, count, color);
            }
            if (isGrim) spawnGrimShadow(particlesRef, tc.x, tc.y, 8);
          }
        } else if (playerAnimRef) {
          if (!playerAnimRef.current[tgt]) playerAnimRef.current[tgt] = {};
          playerAnimRef.current[tgt].flashUntil = flashUntil;
          if (isCrit && floatingTextRef) spawnFloatingText(floatingTextRef, tc.x, tc.y - TILE_SIZE / 2, 'CRIT!', '#ffcc00', hitIcon);
          if (isGrim && floatingTextRef) spawnGrimShadow(particlesRef, tc.x, tc.y, 8);
        }
        if (isSurprise && surpriseRef) spawnSurprise(surpriseRef, tc.x, tc.y);
      }, HIT_CONNECT_DELAY);
    }
    return true;
  }

  if (event.type === 'MISS') {
    const tgt = event.data.target;
    const verb = event.data.defense_verb || 'dodged';
    const target = entitiesRef.current.mobs[tgt] || entitiesRef.current.players[tgt];

    if (tgt === myPlayerIdRef.current) {
      addGameLog(`You ${verb}`, 'warning');
    } else if (event.data.source === myPlayerIdRef.current) {
      addGameLog(`${target?.name || 'target'} ${verb}`, 'warning');
    }
    if (target) {
      const visible = visionRef?.current?.visible;
      const tx = Math.round(target.renderPos.x);
      const ty = Math.round(target.renderPos.y);
      if (tgt === myPlayerIdRef.current || visible?.has(`${tx},${ty}`)) {
        const cx = target.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
        const cy = target.renderPos.y * TILE_SIZE;
        if (floatingTextRef) {
          const missIcon = verb === 'blocked' ? TEXT_ICON.MISS_ARM
            : verb === 'dodged' ? TEXT_ICON.MISS_EVA
            : TEXT_ICON.MISS_DEF;
          spawnFloatingText(floatingTextRef, cx, cy, verb, '#ffffff', missIcon);
        }
        AudioManager.play('MISS');
      }
    }
    return true;
  }

  if (event.type === 'DAMAGE') {
    const tgt = event.data.target;
    const tgtEntity = entitiesRef.current.mobs[tgt] || entitiesRef.current.players[tgt];
    if (!tgtEntity) return true;
    const isGrim = event.data.grim_proc;
    const isCrit = event.data.crit;
    const amount = event.data.amount || 0;
    const tc = {
      x: tgtEntity.renderPos.x * TILE_SIZE + TILE_SIZE / 2,
      y: tgtEntity.renderPos.y * TILE_SIZE + TILE_SIZE / 2,
    };
    const projectile = event.data.projectile;
    const isMagic = projectile && MAGIC_PROJECTILES.has(projectile);
    const missileDelay = isMagic ? ((MISSILE_TYPES as Record<string, { life: number }>)[projectile]?.life ?? 400) : 0;

    setTimeout(() => {
      if (isMagic && particlesRef) {
        const count = event.data.splash_count ?? 3;
        spawnWhiteSplash(particlesRef, tc.x, tc.y, count);
        const isAudible = tgt === myPlayerIdRef.current
          || visionRef?.current?.visible?.has(`${Math.round(tgtEntity.renderPos.x)},${Math.round(tgtEntity.renderPos.y)}`);
        if (isAudible) AudioManager.play('HIT_MAGIC', 0.87 + Math.random() * 0.28);
      }
      if (isMagic) {
        const flashDuration = isCrit ? FLASH_DURATION * 2 : FLASH_DURATION;
        const flashUntil = performance.now() + flashDuration;
        if (entitiesRef.current.mobs[tgt]) {
          if (!mobAnimRef.current[tgt]) mobAnimRef.current[tgt] = {};
          mobAnimRef.current[tgt].flashUntil = flashUntil;
        } else if (playerAnimRef && entitiesRef.current.players[tgt]) {
          if (!playerAnimRef.current[tgt]) playerAnimRef.current[tgt] = {};
          playerAnimRef.current[tgt].flashUntil = flashUntil;
        }
      }
      if (amount > 0 && floatingTextRef) {
        const color = isCrit ? '#ffcc00' : '#ff6666';
        const text = isCrit ? `${amount} CRIT!` : `-${amount}`;
        spawnFloatingText(floatingTextRef, tc.x, tc.y - TILE_SIZE / 2, text, color, TEXT_ICON.PHYS_DMG);
      }
      if (isGrim && particlesRef) spawnGrimShadow(particlesRef, tc.x, tc.y, 8);
      if (isCrit && floatingTextRef) spawnFloatingText(floatingTextRef, tc.x, tc.y - TILE_SIZE / 2, 'CRIT!', '#ffcc00');
    }, missileDelay);
    return true;
  }

  if (event.type === 'SHOCKING_PROC') {
    const dfX = event.data.defender_x * TILE_SIZE + TILE_SIZE / 2;
    const dfY = event.data.defender_y * TILE_SIZE + TILE_SIZE / 2;
    if (visionRef?.current?.visible?.has(`${event.data.defender_x},${event.data.defender_y}`)) {
      spawnSparkMoving(particlesRef, dfX, dfY, 3);
      AudioManager.play('LIGHTNING');
      if (event.data.source === myPlayerIdRef.current) spawnScreenShake(screenShakeRef, 2, 300);
      for (const tgt of event.data.chain_targets || []) {
        const tx = tgt.x * TILE_SIZE + TILE_SIZE / 2;
        const ty = tgt.y * TILE_SIZE + TILE_SIZE / 2;
        spawnLightning(lightningRef, dfX, dfY, tx, ty, '#66ccff');
      }
    }
    return true;
  }

  if (event.type === 'DEATH') {
    const id = event.data.target;
    if (id === myPlayerIdRef.current) {
      onPlayerDeath?.({
        score_breakdown: event.data.score_breakdown,
        can_resurrect: event.data.can_resurrect,
        victory: event.data.victory,
      });
      return true;
    }
    const mob = entitiesRef.current.mobs[id];
    if (mob) {
      dyingMobsRef.current[id] = { ...mob, renderPos: { ...mob.renderPos }, deathStart: performance.now() };
      if (mob.faction === 'enemy') addGameLog(`${mob.name} defeated!`, 'positive');
    }
    if (selectedEnemyIdRef?.current === id) selectedEnemyIdRef.current = null;
    return true;
  }

  return false;
}
