import { TILE_SIZE, PLAYER_ATTACK_DURATION, FLASH_DURATION } from '../../constants';
import {
  spawnBlood,
  spawnCorrosionSplash,
  spawnCritSparkle,
  spawnGrimShadow,
  spawnWhiteSplash,
  spawnEnergy,
  spawnBombBlast,
} from '../../rendering/draw/particles';
import { TEXT_ICON } from '../../rendering/draw/floatingTextIcons';
import { coordsForItem } from '../../rendering/sprites';
import { playChainPull } from './chainsEffect';
import { spawnSparkMoving } from '../../rendering/draw/sparkParticle';
import { spawnFlameBurst } from '../../rendering/draw/flameParticle';
import { spawnEarthBurst } from '../../rendering/draw/earthParticle';
import { spawnPurpleBurst } from '../../rendering/draw/purpleParticle';
import { spawnRainbowBurst } from '../../rendering/draw/rainbowParticle';
import { spawnElmo } from '../../rendering/draw/elmoParticle';
import { addGameLog } from '../../ui/gameLogHelpers';
import type {
  AttackEvent,
  MissEvent,
  DamageEvent,
  DeathEvent,
  RangedAttackEvent,
  LightningArcEvent,
  ShockingProcEvent,
  SpawnEvent,
  PushEvent,
  GuardChainPullEvent,
  SummonEvent,
  BloomingProcEvent,
  CorruptProcEvent,
  VampiricProcEvent,
  BlockingProcEvent,
  ElasticProcEvent,
  CharmProcEvent,
  ExplosiveProcEvent,
  RepulsionProcEvent,
  ViscosityProcEvent,
  PotentialProcEvent,
  EntanglementProcEvent,
  ThornsProcEvent,
  AntiEntropyProcEvent,
  CorrosionProcEvent,
  DisplacementProcEvent,
  MetabolismProcEvent,
  StenchProcEvent,
} from '../../types/contract';
import type { AnimState, MoveResult, RenderPlayer, Ref } from '../types';
import type { GameEventContext, IGameEventHandler } from './IGameEventHandler';
import { defaultMoveResultDispatcher } from '../movement/MoveResultDispatcher';

const BLOOD_COLORS: Record<string, string> = { Goo: '#000000' };

let nextAttackReadyAt = 0;
let lastAttackCooldownMs = 1000;

export function noteNextAttackReady(inMs?: number): void {
  const cd = inMs ?? lastAttackCooldownMs;
  lastAttackCooldownMs = cd;
  nextAttackReadyAt = performance.now() + cd;
}

export function isAttackReady(): boolean {
  return performance.now() >= nextAttackReadyAt;
}

export function consumeAttackCooldown(cooldownMs?: number): void {
  const cd = cooldownMs ?? lastAttackCooldownMs;
  lastAttackCooldownMs = cd;
  nextAttackReadyAt = performance.now() + cd;
}

export function resetAttackCooldown(): void {
  nextAttackReadyAt = 0;
  lastAttackCooldownMs = 1000;
}

export interface EquippedWeaponMeta {
  name?: string;
  kind?: string;
  hit_sound?: string;
  hit_sound_pitch?: number;
  attack_cooldown?: number;
}

function weaponMeta(me: RenderPlayer | null | undefined): EquippedWeaponMeta | null | undefined {
  return me?.equipped_weapon as EquippedWeaponMeta | null | undefined;
}

export function startLocalPlayerMeleeAnim(
  me: RenderPlayer | null | undefined,
  playerAnimRef: Ref<Record<string, AnimState>> | undefined,
  audioService?: { play: (sound: string, rate?: number) => void },
): void {
  if (!me || me.is_downed || !playerAnimRef) return;
  if (!isAttackReady()) return;

  const now = performance.now();
  const weapon = weaponMeta(me);
  consumeAttackCooldown((weapon?.attack_cooldown ?? 1.0) * 1000);

  if (!playerAnimRef.current[me.id]) playerAnimRef.current[me.id] = {};
  playerAnimRef.current[me.id].attackUntil = now + PLAYER_ATTACK_DURATION;

  audioService?.play(weapon?.hit_sound || 'HIT_BODY', (weapon?.hit_sound_pitch ?? 1.0) * (0.87 + Math.random() * 0.28));
}

export interface BumpCtx {
  me: RenderPlayer | null | undefined;
  playerAnimRef?: Ref<Record<string, AnimState>>;
  onOpenAlchemy?: () => void;
  audio?: { play: (sound: string, rate?: number) => void };
}

export function runLocalBumpFlow(result: MoveResult, ctx: BumpCtx): void {
  defaultMoveResultDispatcher.dispatch(result, {
    myPlayer: ctx.me ?? null,
    playerAnimRef: ctx.playerAnimRef,
    onOpenAlchemyRef: { current: ctx.onOpenAlchemy },
    onMeleeAttack: () => startLocalPlayerMeleeAnim(ctx.me, ctx.playerAnimRef, ctx.audio),
    dx: 0,
    dy: 0,
  });
}

function rasterizeLine(x0: number, y0: number, x1: number, y1: number): Array<{ x: number; y: number }> {
  x0 = Math.round(x0);
  y0 = Math.round(y0);
  x1 = Math.round(x1);
  y1 = Math.round(y1);
  const cells: Array<{ x: number; y: number }> = [];
  const dx = Math.abs(x1 - x0);
  const dy = Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1;
  const sy = y0 < y1 ? 1 : -1;
  let err = dx - dy;
  let cx = x0, cy = y0;
  while (true) {
    if (cx !== x1 || cy !== y1) cells.push({ x: cx, y: cy });
    if (cx === x1 && cy === y1) break;
    const e2 = 2 * err;
    if (e2 > -dy) { err -= dy; cx += sx; }
    if (e2 < dx) { err += dx; cy += sy; }
  }
  return cells;
}

function handleTetherProc(
  event: ElasticProcEvent | RepulsionProcEvent,
  ctx: GameEventContext,
  lightningColor: string,
): boolean {
  const tgt = ctx.entities.getEntity(event.data.target);
  if (tgt && ctx.world.isVisible(event.data.to_x, event.data.to_y)) {
    const fx = event.data.from_x * TILE_SIZE + TILE_SIZE / 2;
    const fy = event.data.from_y * TILE_SIZE + TILE_SIZE / 2;
    const tx = event.data.to_x * TILE_SIZE + TILE_SIZE / 2;
    const ty = event.data.to_y * TILE_SIZE + TILE_SIZE / 2;
    if (ctx.effects.particlesRef) {
      spawnSparkMoving(ctx.effects.particlesRef, tx, ty, 5);
    }
    ctx.effects.spawnLightning(fx, fy, tx, ty, lightningColor);
  }
  return true;
}

function handleGasProc(
  event: CorrosionProcEvent | StenchProcEvent,
  ctx: GameEventContext,
  count: number,
): boolean {
  const x = event.data.x * TILE_SIZE + TILE_SIZE / 2;
  const y = event.data.y * TILE_SIZE + TILE_SIZE / 2;
  if (ctx.effects.particlesRef) {
    spawnCorrosionSplash(ctx.effects.particlesRef, x, y, count);
  }
  ctx.audio.play('GAS');
  return true;
}

const MAGIC_PROJECTILES = new Set([
  'magic_bolt', 'magic_missile', 'fire_bolt', 'frost', 'corrosion',
  'foliage', 'force', 'beacon', 'shadow', 'rainbow', 'earth', 'ward',
  'shaman_red', 'shaman_blue', 'shaman_purple', 'elmo', 'poison', 'light_missile',
  'lightning', 'beam',
]);

export function createCombatEventHandlers(): IGameEventHandler[] {
  return [
    {
      eventType: 'RANGED_ATTACK',
      handle(event: RangedAttackEvent, ctx: GameEventContext) {
        const startX = event.data.x * TILE_SIZE + TILE_SIZE / 2;
        const startY = event.data.y * TILE_SIZE + TILE_SIZE / 2;
        const targetX = event.data.target_x * TILE_SIZE + TILE_SIZE / 2;
        const targetY = event.data.target_y * TILE_SIZE + TILE_SIZE / 2;
        const thrownItem = event.data.item;
        const spriteCoords = thrownItem ? coordsForItem(thrownItem) : null;
        const projType = event.data.projectile || 'arrow';
        const beamType = event.data.beam_type;

        if (!MAGIC_PROJECTILES.has(projType)) {
          ctx.effects.pushProjectile({
            x: startX,
            y: startY,
            startX,
            startY,
            targetX,
            targetY,
            type: projType,
            spriteCoords,
            progress: 0,
            rotation: 0,
            finished: false,
          });
        }

        const src = event.data.source;
        const isLocal = src === ctx.myPlayerId;
        const audible = isLocal || ctx.world.isVisible(event.data.x, event.data.y);

        if (isLocal && event.data.next_attack_in_ms != null) {
          noteNextAttackReady(event.data.next_attack_in_ms);
        }

        const srcPlayer = ctx.entities.getPlayer(src);
        if (srcPlayer && event.data.is_wand) {
          ctx.effects.setPlayerAttack(src, PLAYER_ATTACK_DURATION);
          const dx = event.data.target_x - event.data.x;
          if (dx > 0) { srcPlayer.facing = 'RIGHT'; srcPlayer.flipX = false; }
          else if (dx < 0) { srcPlayer.facing = 'LEFT'; srcPlayer.flipX = true; }
        }

        if (projType === 'lightning') {
          if (audible) ctx.audio.play('LIGHTNING');
          ctx.effects.spawnLightning(startX, startY, targetX, targetY, '#66ccff');
          if (ctx.effects.particlesRef) spawnSparkMoving(ctx.effects.particlesRef, targetX, targetY, 3);
          if (isLocal) ctx.effects.shakeScreen(2, 300);
        } else if (beamType && (projType === 'beam' || projType === 'magic_bolt')) {
          if (audible) ctx.audio.play(event.data.sound ?? 'RAY');
          ctx.effects.spawnBeam(startX, startY, targetX, targetY, beamType, event.data.target_hp_ratio);
        } else if (event.data.is_wand) {
          if (audible) ctx.audio.play(event.data.sound ?? 'ATTACK_MAGIC');
          if (MAGIC_PROJECTILES.has(projType)) ctx.effects.spawnMagicMissile(startX, startY, targetX, targetY, projType);
        } else if (MAGIC_PROJECTILES.has(projType)) {
          if (audible) ctx.audio.play(event.data.sound ?? 'ATTACK_MAGIC');
          ctx.effects.spawnMagicMissile(startX, startY, targetX, targetY, projType);
        } else if (event.data.is_bow) {
          if (audible) ctx.audio.play('ATTACK_BOW');
        } else if (thrownItem) {
          if (audible) ctx.audio.play('THROW');
        } else {
          if (audible) ctx.audio.play('ATTACK_BOW');
        }
        return true;
      },
    },
    {
      eventType: 'ATTACK',
      handle(event: AttackEvent, ctx: GameEventContext) {
        const src = event.data.source;
        const tgt = event.data.target;
        const damage = event.data.damage || 0;

        const srcMob = ctx.entities.getMob(src);
        const srcPlayer = ctx.entities.getPlayer(src);
        const srcEntity = srcMob || srcPlayer;
        const tgtEntity = ctx.entities.getEntity(tgt);

        if (tgt === ctx.myPlayerId) {
          const attackerName = srcMob?.name || srcPlayer?.name || 'Something';
          addGameLog(`${attackerName} hits you for ${damage}`, 'negative');
        } else if (src === ctx.myPlayerId) {
          const targetName = tgtEntity?.name || 'target';
          addGameLog(`You hit ${targetName} for ${damage}`, damage > 0 ? 'positive' : 'default');
        }

        if (src === ctx.myPlayerId && ctx.entities.getMob(tgt)) {
          ctx.entities.setSelectedEnemyId(tgt);
        }

        if (src === ctx.myPlayerId) {
          if (event.data.next_attack_in_ms != null) {
            noteNextAttackReady(event.data.next_attack_in_ms);
          }
          if (event.data.crit || event.data.grim_proc) ctx.audio.play('HIT_STRONG');
        }

        if (srcMob) {
          const attackDuration = srcMob.name === 'Goo' ? 300 : srcMob.name === 'Scorpio' ? 200 : srcMob.name === 'Rat' ? 333 : srcMob.name === 'Snake' ? 333 : 250;
          ctx.effects.setMobAttack(src, attackDuration);
        } else if (srcPlayer) {
          ctx.effects.setPlayerAttack(src, PLAYER_ATTACK_DURATION);
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
          const isMobTarget = Boolean(ctx.entities.getMob(tgt));
          const maxHp = tgtEntity.max_hp || 1;
          const color = BLOOD_COLORS[tgtEntity.name] || '#bb0000';
          const isCrit = event.data.crit;
          const isGrim = event.data.grim_proc;
          const isSurprise = event.data.surprise;
          const hitIcon = isSurprise ? TEXT_ICON.HIT_SUPR
            : src === ctx.myPlayerId ? TEXT_ICON.HIT_WEP
            : TEXT_ICON.HIT_BLS;

          const flashDuration = isCrit ? FLASH_DURATION * 2 : FLASH_DURATION;
          const flashUntil = performance.now() + flashDuration;
          const particlesRef = ctx.effects.particlesRef;

          if (isMobTarget) {
            if (ctx.effects.mobAnimRef) {
              if (!ctx.effects.mobAnimRef.current[tgt]) ctx.effects.mobAnimRef.current[tgt] = {};
              ctx.effects.mobAnimRef.current[tgt].flashUntil = flashUntil;
            }
            if (particlesRef) {
              const awayAngle = sc ? Math.atan2(tc.y - sc.y, tc.x - sc.x) : -Math.PI / 2;
              if (isCrit) {
                const critCount = Math.min(Math.round(14 * Math.sqrt(damage / maxHp)), 14);
                spawnBlood(particlesRef, tc.x, tc.y, awayAngle, critCount, '#ffcc00');
                spawnCritSparkle(particlesRef, tc.x, tc.y, 10);
                ctx.effects.spawnFloatingText(tc.x, tc.y - TILE_SIZE / 2, 'CRIT!', '#ffcc00', hitIcon);
              } else {
                const count = Math.min(Math.round(9 * Math.sqrt(damage / maxHp)), 9);
                spawnBlood(particlesRef, tc.x, tc.y, awayAngle, count, color);
              }
              if (isGrim) spawnGrimShadow(particlesRef, tc.x, tc.y, 8);
            }
          } else {
            if (ctx.effects.playerAnimRef) {
              if (!ctx.effects.playerAnimRef.current[tgt]) ctx.effects.playerAnimRef.current[tgt] = {};
              ctx.effects.playerAnimRef.current[tgt].flashUntil = flashUntil;
            }
            if (isCrit) ctx.effects.spawnFloatingText(tc.x, tc.y - TILE_SIZE / 2, 'CRIT!', '#ffcc00', hitIcon);
            if (isGrim && particlesRef) spawnGrimShadow(particlesRef, tc.x, tc.y, 8);
          }
          if (isSurprise) ctx.effects.spawnSurprise(tc.x, tc.y);
        }
        return true;
      },
    },
    {
      eventType: 'MISS',
      handle(event: MissEvent, ctx: GameEventContext) {
        const tgt = event.data.target;
        const verb = event.data.defense_verb || 'dodged';
        const target = ctx.entities.getEntity(tgt);

        if (tgt === ctx.myPlayerId) {
          addGameLog(`You ${verb}`, 'warning');
        } else if (event.data.source === ctx.myPlayerId) {
          addGameLog(`${target?.name || 'target'} ${verb}`, 'warning');
        }
        if (target) {
          const tx = Math.round(target.renderPos.x);
          const ty = Math.round(target.renderPos.y);
          if (tgt === ctx.myPlayerId || ctx.world.isVisible(tx, ty)) {
            const cx = target.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
            const cy = target.renderPos.y * TILE_SIZE;
            const missIcon = verb === 'blocked' ? TEXT_ICON.MISS_ARM
              : verb === 'dodged' ? TEXT_ICON.MISS_EVA
              : TEXT_ICON.MISS_DEF;
            ctx.effects.spawnFloatingText(cx, cy, verb, '#ffffff', missIcon);
            ctx.audio.play('MISS');
          }
        }
        return true;
      },
    },
    {
      eventType: 'DAMAGE',
      handle(event: DamageEvent, ctx: GameEventContext) {
        const tgt = event.data.target;
        const tgtEntity = ctx.entities.getEntity(tgt) ?? ctx.entities.getDyingMobs()[tgt];
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

        const particlesRef = ctx.effects.particlesRef;
        if (isMagic && particlesRef) {
          const count = event.data.splash_count ?? 3;
          if (projectile === 'beam') {
            const sx = event.data.source_x;
            const sy = event.data.source_y;
            if (sx != null && sy != null) {
              const beamType = event.data.beam_type;
              const cells = rasterizeLine(sx, sy, Math.round(tgtEntity.renderPos.x), Math.round(tgtEntity.renderPos.y));
              for (const cell of cells) {
                if (!ctx.world.isVisible(cell.x, cell.y)) continue;
                const px = cell.x * TILE_SIZE + TILE_SIZE / 2;
                const py = cell.y * TILE_SIZE + TILE_SIZE / 2;
                if (beamType === 'health_ray') {
                  spawnBlood(particlesRef, px, py, -Math.PI / 2, 1, '#cc0000');
                } else if (beamType === 'light_ray') {
                  spawnRainbowBurst(particlesRef, px, py, 2);
                } else {
                  spawnPurpleBurst(particlesRef, px, py, 1);
                }
              }
            }
          } else {
            switch (projectile) {
              case 'fire_bolt':
                spawnFlameBurst(particlesRef, tc.x, tc.y, 5);
                break;
              case 'frost':
                spawnWhiteSplash(particlesRef, tc.x, tc.y, 5);
                break;
              case 'corrosion':
                spawnCorrosionSplash(particlesRef, tc.x, tc.y, 5);
                break;
              case 'earth':
              case 'force':
                spawnEarthBurst(particlesRef, tc.x, tc.y, 8);
                break;
              case 'shadow':
              case 'ward':
                spawnPurpleBurst(particlesRef, tc.x, tc.y, 6);
                break;
              case 'rainbow':
                spawnRainbowBurst(particlesRef, tc.x, tc.y, 10);
                break;
              case 'elmo':
                spawnElmo(particlesRef, tc.x, tc.y, 4);
                break;
              case 'foliage':
                spawnEarthBurst(particlesRef, tc.x, tc.y, 6);
                break;
            }
          }
          spawnWhiteSplash(particlesRef, tc.x, tc.y, count);
          const isAudible = tgt === ctx.myPlayerId
            || ctx.world.isVisible(Math.round(tgtEntity.renderPos.x), Math.round(tgtEntity.renderPos.y));
          if (isAudible) ctx.audio.play('HIT_MAGIC', 0.87 + Math.random() * 0.28);
          if (isAudible) {
            switch (projectile) {
              case 'fire_bolt': ctx.audio.play('BURNING', 1.0, 250); break;
              case 'frost': ctx.audio.play('SHATTER', 0.9, 250); break;
              case 'force': ctx.audio.play('BLAST', 0.9, 250); break;
              case 'corrosion': ctx.audio.play('GAS', 0.9, 250); break;
              case 'earth': ctx.audio.play('HIT_MAGIC', 0.85, 250); break;
              case 'shadow': ctx.audio.play('HIT_MAGIC', 0.8, 250); break;
            }
          }
        }
        if (isMagic) {
          const flashDuration = isCrit ? FLASH_DURATION * 2 : FLASH_DURATION;
          const flashUntil = performance.now() + flashDuration;
          if (ctx.entities.getMob(tgt)) {
            if (ctx.effects.mobAnimRef) {
              if (!ctx.effects.mobAnimRef.current[tgt]) ctx.effects.mobAnimRef.current[tgt] = {};
              ctx.effects.mobAnimRef.current[tgt].flashUntil = flashUntil;
            }
          } else if (ctx.entities.getPlayer(tgt)) {
            if (ctx.effects.playerAnimRef) {
              if (!ctx.effects.playerAnimRef.current[tgt]) ctx.effects.playerAnimRef.current[tgt] = {};
              ctx.effects.playerAnimRef.current[tgt].flashUntil = flashUntil;
            }
          }
        }
        if (amount > 0) {
          const color = isCrit ? '#ffcc00' : '#ff6666';
          const text = isCrit ? `${amount} CRIT!` : `-${amount}`;
          ctx.effects.spawnFloatingText(tc.x, tc.y - TILE_SIZE / 2, text, color, TEXT_ICON.PHYS_DMG);
        }
        if (isGrim && particlesRef) spawnGrimShadow(particlesRef, tc.x, tc.y, 8);
        if (isCrit) ctx.effects.spawnFloatingText(tc.x, tc.y - TILE_SIZE / 2, 'CRIT!', '#ffcc00');
        return true;
      },
    },
    {
      eventType: 'LIGHTNING_ARC',
      handle(event: LightningArcEvent, ctx: GameEventContext) {
        const sx = event.data.source_x * TILE_SIZE + TILE_SIZE / 2;
        const sy = event.data.source_y * TILE_SIZE + TILE_SIZE / 2;
        const tx = event.data.target_x * TILE_SIZE + TILE_SIZE / 2;
        const ty = event.data.target_y * TILE_SIZE + TILE_SIZE / 2;
        if (!ctx.world.isVisible(event.data.source_x, event.data.source_y) && !ctx.world.isVisible(event.data.target_x, event.data.target_y)) {
          return true;
        }
        ctx.effects.spawnLightning(sx, sy, tx, ty, '#66ccff');
        if (ctx.effects.particlesRef) spawnSparkMoving(ctx.effects.particlesRef, tx, ty, 3);
        ctx.audio.play('LIGHTNING');
        return true;
      },
    },
    {
      eventType: 'SHOCKING_PROC',
      handle(event: ShockingProcEvent, ctx: GameEventContext) {
        const dfX = event.data.defender_x * TILE_SIZE + TILE_SIZE / 2;
        const dfY = event.data.defender_y * TILE_SIZE + TILE_SIZE / 2;
        if (ctx.world.isVisible(event.data.defender_x, event.data.defender_y)) {
          if (ctx.effects.particlesRef) spawnSparkMoving(ctx.effects.particlesRef, dfX, dfY, 3);
          ctx.audio.play('LIGHTNING');
          if (event.data.source === ctx.myPlayerId) ctx.effects.shakeScreen(2, 300);
          for (const tgt of event.data.chain_targets || []) {
            const tx = tgt.x * TILE_SIZE + TILE_SIZE / 2;
            const ty = tgt.y * TILE_SIZE + TILE_SIZE / 2;
            ctx.effects.spawnLightning(dfX, dfY, tx, ty, '#66ccff');
          }
        }
        return true;
      },
    },
    {
      eventType: 'EXPLOSIVE_PROC',
      handle(event: ExplosiveProcEvent, ctx: GameEventContext) {
        const ex = event.data.x * TILE_SIZE + TILE_SIZE / 2;
        const ey = event.data.y * TILE_SIZE + TILE_SIZE / 2;
        if (ctx.effects.particlesRef) spawnBombBlast(ctx.effects.particlesRef, ex, ey, 26);
        ctx.effects.shakeScreen(3, 400);
        ctx.audio.play('BLAST');
        return true;
      },
    },
    {
      eventType: 'ANTI_ENTROPY_PROC',
      handle(event: AntiEntropyProcEvent, ctx: GameEventContext) {
        const x = event.data.x * TILE_SIZE + TILE_SIZE / 2;
        const y = event.data.y * TILE_SIZE + TILE_SIZE / 2;
        if (ctx.effects.particlesRef) {
          spawnFlameBurst(ctx.effects.particlesRef, x, y, 6);
          spawnWhiteSplash(ctx.effects.particlesRef, x, y, 6);
        }
        ctx.audio.play('BURNING');
        return true;
      },
    },
    {
      eventType: 'CORROSION_PROC',
      handle(event: CorrosionProcEvent, ctx: GameEventContext) {
        return handleGasProc(event, ctx, 8);
      },
    },
    {
      eventType: 'DISPLACEMENT_PROC',
      handle(event: DisplacementProcEvent, ctx: GameEventContext) {
        const def = ctx.entities.getEntity(event.data.defender);
        if (def && ctx.world.isVisible(Math.round(def.renderPos.x), Math.round(def.renderPos.y))) {
          const px = def.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
          const py = def.renderPos.y * TILE_SIZE + TILE_SIZE / 2;
          if (ctx.effects.particlesRef) spawnPurpleBurst(ctx.effects.particlesRef, px, py, 6);
          ctx.audio.play('TELEPORT');
        }
        return true;
      },
    },
    {
      eventType: 'STENCH_PROC',
      handle(event: StenchProcEvent, ctx: GameEventContext) {
        return handleGasProc(event, ctx, 6);
      },
    },
    {
      eventType: 'DEATH',
      handle(event: DeathEvent, ctx: GameEventContext) {
        const id = event.data.target;
        if (id === ctx.myPlayerId) {
          ctx.ui.playerDeath({
            score_breakdown: event.data.score_breakdown,
            can_resurrect: event.data.can_resurrect,
            has_ankh: event.data.has_ankh,
            victory: event.data.victory,
            respawns_used: event.data.respawns_used,
            max_respawns: event.data.max_respawns,
            loot_dropped: event.data.loot_dropped,
            death_cause: event.data.death_cause,
          });
          return true;
        }
        const mob = ctx.entities.getMob(id);
        if (mob) {
          ctx.entities.recordDyingMob(id, mob);
          if (mob.faction === 'enemy') addGameLog(`${mob.name} defeated!`, 'positive');
        }
        if (ctx.entities.getSelectedEnemyId() === id) {
          ctx.entities.setSelectedEnemyId(null);
        }
        return true;
      },
    },
    {
      eventType: 'SPAWN',
      handle(event: SpawnEvent, ctx: GameEventContext) {
        const id = event.data.target;
        if (event.data.is_resurrect) {
          const entity = ctx.entities.getPlayer(id);
          if (entity) {
            const px = entity.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
            const py = entity.renderPos.y * TILE_SIZE + TILE_SIZE / 2;
            if (id === ctx.myPlayerId || ctx.world.isVisible(Math.round(entity.renderPos.x), Math.round(entity.renderPos.y))) {
              if (ctx.effects.particlesRef) {
                spawnWhiteSplash(ctx.effects.particlesRef, px, py, 12);
                spawnEnergy(ctx.effects.particlesRef, px, py, 10);
              }
              ctx.audio.play('REVIVE');
              if (id !== ctx.myPlayerId) {
                addGameLog(`${entity.name || 'Player'} was resurrected!`, 'positive');
              }
            }
          }
        }
        return true;
      },
    },
    {
      eventType: 'PUSH',
      handle(event: PushEvent, ctx: GameEventContext) {
        const tgt = event.data.target;
        const entity = ctx.entities.getEntity(tgt);
        if (entity) {
          const visible = ctx.world.isVisible(Math.round(entity.renderPos.x), Math.round(entity.renderPos.y));
          if (visible) {
            const px = entity.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
            const py = entity.renderPos.y * TILE_SIZE + TILE_SIZE / 2;
            if (ctx.effects.particlesRef) spawnWhiteSplash(ctx.effects.particlesRef, px, py, 4);
            ctx.audio.play('HIT_BODY');
          }
        }
        return true;
      },
    },
    {
      eventType: 'GUARD_CHAIN_PULL',
      handle(event: GuardChainPullEvent, ctx: GameEventContext) {
        const fromVisible = ctx.world.isVisible(event.data.from_x, event.data.from_y);
        const toVisible = ctx.world.isVisible(event.data.to_x, event.data.to_y);
        if (event.data.target === ctx.myPlayerId || fromVisible || toVisible) {
          playChainPull(ctx.effects.lightningRef, event.data.from_x, event.data.from_y, event.data.to_x, event.data.to_y);
        }
        return true;
      },
    },
    {
      eventType: 'SUMMON',
      handle(event: SummonEvent, ctx: GameEventContext) {
        const px = event.data.x * TILE_SIZE + TILE_SIZE / 2;
        const py = event.data.y * TILE_SIZE + TILE_SIZE / 2;
        const visible = ctx.world.isVisible(event.data.x, event.data.y);
        if (visible) {
          if (ctx.effects.particlesRef) {
            spawnWhiteSplash(ctx.effects.particlesRef, px, py, 8);
            spawnEnergy(ctx.effects.particlesRef, px, py, 6);
          }
          ctx.audio.play('TELEPORT');
        }
        return true;
      },
    },
    {
      eventType: 'BLOOMING_PROC',
      handle(event: BloomingProcEvent, ctx: GameEventContext) {
        const cx = event.data.defender;
        const entity = ctx.entities.getEntity(cx);
        if (entity && ctx.world.isVisible(Math.round(entity.renderPos.x), Math.round(entity.renderPos.y))) {
          const px = entity.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
          const py = entity.renderPos.y * TILE_SIZE + TILE_SIZE / 2;
          if (ctx.effects.particlesRef) spawnEarthBurst(ctx.effects.particlesRef, px, py, 6);
        }
        return true;
      },
    },
    {
      eventType: 'CORRUPT_PROC',
      handle(event: CorruptProcEvent, ctx: GameEventContext) {
        const tgt = event.data.target;
        const entity = ctx.entities.getEntity(tgt);
        if (entity && ctx.world.isVisible(Math.round(entity.renderPos.x), Math.round(entity.renderPos.y))) {
          const px = entity.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
          const py = entity.renderPos.y * TILE_SIZE + TILE_SIZE / 2;
          if (ctx.effects.particlesRef) spawnPurpleBurst(ctx.effects.particlesRef, px, py, 8);
          ctx.audio.play('CURSE');
        }
        return true;
      },
    },
    {
      eventType: 'VAMPIRIC_PROC',
      handle(event: VampiricProcEvent, ctx: GameEventContext) {
        const src = event.data.source;
        const entity = ctx.entities.getEntity(src);
        if (entity && (src === ctx.myPlayerId || ctx.world.isVisible(Math.round(entity.renderPos.x), Math.round(entity.renderPos.y)))) {
          const px = entity.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
          const py = entity.renderPos.y * TILE_SIZE + TILE_SIZE / 2;
          if (ctx.effects.particlesRef) spawnBlood(ctx.effects.particlesRef, px, py, -Math.PI / 2, 4, '#cc0000');
          if (event.data.heal > 0) {
            ctx.effects.spawnFloatingText(px, py - TILE_SIZE / 2, `+${event.data.heal}`, '#2ecc71', TEXT_ICON.HIT_WEP);
          }
        }
        return true;
      },
    },
    {
      eventType: 'BLOCKING_PROC',
      handle(event: BlockingProcEvent, ctx: GameEventContext) {
        if (event.data.source === ctx.myPlayerId) {
          const me = ctx.entities.getPlayer(event.data.source);
          if (me) {
            const px = me.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
            const py = me.renderPos.y * TILE_SIZE;
            if (ctx.effects.particlesRef) spawnWhiteSplash(ctx.effects.particlesRef, px, py + TILE_SIZE / 2, 5);
            ctx.effects.shakeScreen(1, 200);
            if (event.data.shield > 0) {
              ctx.effects.spawnFloatingText(px, py - TILE_SIZE / 2, `block ${event.data.shield}`, '#66ccff', TEXT_ICON.MISS_ARM);
            }
          }
        }
        return true;
      },
    },
    {
      eventType: 'ELASTIC_PROC',
      handle(event: ElasticProcEvent, ctx: GameEventContext) {
        return handleTetherProc(event, ctx, '#66ff99');
      },
    },
    {
      eventType: 'CHARM_PROC',
      handle(event: CharmProcEvent, ctx: GameEventContext) {
        const src = event.data.source;
        const entity = ctx.entities.getEntity(src);
        if (entity && ctx.world.isVisible(Math.round(entity.renderPos.x), Math.round(entity.renderPos.y))) {
          const px = entity.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
          const py = entity.renderPos.y * TILE_SIZE + TILE_SIZE / 2;
          if (ctx.effects.particlesRef) spawnRainbowBurst(ctx.effects.particlesRef, px, py, 6);
          ctx.audio.play('CURSE');
        }
        return true;
      },
    },
    {
      eventType: 'REPULSION_PROC',
      handle(event: RepulsionProcEvent, ctx: GameEventContext) {
        return handleTetherProc(event, ctx, '#ffcc66');
      },
    },
    {
      eventType: 'VISCOSITY_PROC',
      handle(event: ViscosityProcEvent, ctx: GameEventContext) {
        if (event.data.defender === ctx.myPlayerId) {
          const me = ctx.entities.getPlayer(event.data.defender);
          if (me) {
            const px = me.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
            const py = me.renderPos.y * TILE_SIZE;
            if (ctx.effects.particlesRef) spawnWhiteSplash(ctx.effects.particlesRef, px, py + TILE_SIZE / 2, 5);
            if (event.data.deferred > 0) {
              ctx.effects.spawnFloatingText(px, py - TILE_SIZE / 2, `deferred ${event.data.deferred}`, '#66ccff', TEXT_ICON.MISS_ARM);
            }
          }
        }
        return true;
      },
    },
    {
      eventType: 'POTENTIAL_PROC',
      handle(event: PotentialProcEvent, ctx: GameEventContext) {
        const def = ctx.entities.getEntity(event.data.defender);
        if (def && (event.data.defender === ctx.myPlayerId || ctx.world.isVisible(Math.round(def.renderPos.x), Math.round(def.renderPos.y)))) {
          const px = def.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
          const py = def.renderPos.y * TILE_SIZE + TILE_SIZE / 2;
          if (ctx.effects.particlesRef) spawnEnergy(ctx.effects.particlesRef, px, py, 6);
          ctx.audio.play('SPARK');
        }
        return true;
      },
    },
    {
      eventType: 'ENTANGLEMENT_PROC',
      handle(event: EntanglementProcEvent, ctx: GameEventContext) {
        const def = ctx.entities.getEntity(event.data.defender);
        if (def && (event.data.defender === ctx.myPlayerId || ctx.world.isVisible(Math.round(def.renderPos.x), Math.round(def.renderPos.y)))) {
          const px = def.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
          const py = def.renderPos.y * TILE_SIZE + TILE_SIZE / 2;
          if (ctx.effects.particlesRef) spawnEarthBurst(ctx.effects.particlesRef, px, py, 8);
          if (event.data.absorb > 0) {
            ctx.effects.spawnFloatingText(px, py - TILE_SIZE / 2, `absorb ${event.data.absorb}`, '#2ecc71', TEXT_ICON.MISS_ARM);
          }
        }
        return true;
      },
    },
    {
      eventType: 'THORNS_PROC',
      handle(event: ThornsProcEvent, ctx: GameEventContext) {
        const atk = ctx.entities.getEntity(event.data.attacker);
        if (atk && ctx.world.isVisible(Math.round(atk.renderPos.x), Math.round(atk.renderPos.y))) {
          const px = atk.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
          const py = atk.renderPos.y * TILE_SIZE + TILE_SIZE / 2;
          if (ctx.effects.particlesRef) spawnBlood(ctx.effects.particlesRef, px, py, -Math.PI / 2, 4, '#cc0000');
          if (event.data.bleed > 0) {
            ctx.effects.spawnFloatingText(px, py - TILE_SIZE / 2, `bleed ${event.data.bleed}`, '#ff6666', TEXT_ICON.HIT_BLS);
          }
        }
        return true;
      },
    },
    {
      eventType: 'METABOLISM_PROC',
      handle(event: MetabolismProcEvent, ctx: GameEventContext) {
        if (event.data.defender === ctx.myPlayerId) {
          const me = ctx.entities.getPlayer(event.data.defender);
          if (me && event.data.heal > 0) {
            const px = me.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
            const py = me.renderPos.y * TILE_SIZE;
            ctx.effects.spawnFloatingText(px, py - TILE_SIZE / 2, `+${event.data.heal} metabolism`, '#2ecc71', TEXT_ICON.HIT_BLS);
          }
        }
        return true;
      },
    },
  ];
}
