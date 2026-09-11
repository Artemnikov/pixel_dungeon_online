import { TILE_SIZE, isWaterTile } from '../../constants';
import {
  spawnChange, spawnCurse, spawnDiscover, spawnDust, spawnEnergy,
  spawnHeal, spawnIdentify, spawnLeaf, spawnLight, spawnNote, spawnScream,
  spawnShadowUp, spawnShaft, spawnTerror, spawnUp,
} from '../../rendering/draw/particles';
import { coordsForKind } from '../../rendering/sprites';
import { SPELL_CHARGE, SPELL_MAP } from '../../rendering/draw/spellSprite';
import { forceAlertMob } from '../../rendering/draw/mobs';
import { spawnSparkMoving } from '../../rendering/draw/sparkParticle';
import { playChainPull } from './chainsEffect';
import { spawnToxicGas, spawnCorrosiveGas, spawnConfusionGas } from '../../rendering/draw/gasParticle';
import { spawnFlameBurst } from '../../rendering/draw/flameParticle';
import { spawnEarthBurst } from '../../rendering/draw/earthParticle';
import * as movementPredictor from '../movementPredictor';
import { spawnWaterRipple } from '../../rendering/draw/waterRipple';
import { addGameLog } from '../../ui/gameLogHelpers';
import i18n from '../../i18n';
import type { GameEvent } from '../../types/contract';
import type { GameEventContext, IGameEventHandler } from './IGameEventHandler';

const PLANT_ANNOUNCEMENTS: Record<string, { text: string; color: string }> = {
  sungrass: { text: 'Herbal Healing', color: '#2ecc71' },
  earthroot: { text: 'Herbal Armor', color: '#e67e22' },
  swiftthistle: { text: 'Time Bubble', color: '#f1c40f' },
  starflower: { text: 'Blessed', color: '#f39c12' },
};

export function createPlayerEventHandlers(): IGameEventHandler[] {
  return [
    {
      eventType: 'SEARCH',
      handle(event: Extract<GameEvent, { type: 'SEARCH' }>, ctx: GameEventContext) {
        const pid = event.data.player;
        if (ctx.entities.getPlayer(pid)) {
          ctx.effects.setPlayerOperate(pid);
        }
        ctx.effects.spawnCheckedCells(event.data.cells, event.data.x, event.data.y);
        return true;
      },
    },
    {
      eventType: 'DRINK',
      handle(event: Extract<GameEvent, { type: 'DRINK' }>, ctx: GameEventContext) {
        const pid = event.data.player;
        const isLocal = pid === ctx.myPlayerId;
        if (isLocal) addGameLog(`You drink ${event.data.type}`, 'highlight');
        const drinker = ctx.entities.getPlayer(pid);
        if (isLocal || (drinker && ctx.world.isVisible(drinker.pos.x, drinker.pos.y))) {
          ctx.audio.play('DRINK');
        }
        if (drinker) {
          ctx.effects.setPlayerOperate(pid);
        }
        return true;
      },
    },
    {
      eventType: 'EAT',
      handle(event: Extract<GameEvent, { type: 'EAT' }>, ctx: GameEventContext) {
        const pid = event.data.player;
        if (ctx.entities.getPlayer(pid)) {
          ctx.effects.setPlayerOperate(pid);
        }
        return true;
      },
    },
    {
      eventType: 'ENERGY_BURST',
      handle(event: Extract<GameEvent, { type: 'ENERGY_BURST' }>, ctx: GameEventContext) {
        const pid = event.data.player;
        const p = ctx.entities.getPlayer(pid);
        const isLocal = pid === ctx.myPlayerId;
        if (ctx.effects.particlesRef && p && (isLocal || ctx.world.isVisible(p.pos.x, p.pos.y))) {
          const cx = p.pos.x * TILE_SIZE + TILE_SIZE / 2;
          const cy = p.pos.y * TILE_SIZE + TILE_SIZE / 2;
          spawnEnergy(ctx.effects.particlesRef, cx, cy);
        }
        return true;
      },
    },
    {
      eventType: 'UNLOCK',
      handle(event: Extract<GameEvent, { type: 'UNLOCK' }>, ctx: GameEventContext) {
        const pid = event.data.player;
        if (ctx.entities.getPlayer(pid)) {
          ctx.effects.setPlayerOperate(pid);
        }
        return true;
      },
    },
    {
      eventType: 'READ',
      handle(event: Extract<GameEvent, { type: 'READ' }>, ctx: GameEventContext) {
        const pid = event.data.player;
        const reader = ctx.entities.getPlayer(pid);
        const isLocal = pid === ctx.myPlayerId;
        const readerVisible = isLocal || (reader && ctx.world.isVisible(reader.pos.x, reader.pos.y));
        if (readerVisible) ctx.audio.play(event.data.sound ?? 'READ');
        if (reader) {
          ctx.effects.setPlayerRead(pid);
        }
        if (readerVisible && ctx.effects.particlesRef && reader) {
          const cx = reader.pos.x * TILE_SIZE + TILE_SIZE / 2;
          const cy = reader.pos.y * TILE_SIZE + TILE_SIZE / 2;
          const visual = event.data.visual;
          const particlesRef = ctx.effects.particlesRef;
          switch (visual) {
            case 'IDENTIFY': spawnIdentify(particlesRef, cx, cy); break;
            case 'UP':
              spawnUp(particlesRef, cx, cy);
              if (event.data.shadow_particles) spawnShadowUp(particlesRef, cx, cy, 5);
              break;
            case 'CURSE':
              spawnCurse(particlesRef, cx, cy);
              spawnShadowUp(particlesRef, cx, cy, 10);
              ctx.effects.spawnFlare(cx, cy, 6, 64, '#ffffff', 800);
              break;
            case 'SCREAM': {
              spawnScream(particlesRef, cx, cy);
              const beckonedIds = event.data.beckoned_ids ?? [];
              for (const id of beckonedIds) forceAlertMob(id);
              break;
            }
            case 'ENERGY':
              spawnEnergy(particlesRef, cx, cy);
              ctx.effects.spawnFloatingText(cx, cy - TILE_SIZE, 'CHARGED!', '#44ccff');
              ctx.effects.spawnSpellSprite(cx, cy, SPELL_CHARGE);
              break;
            case 'NOTE': {
              spawnNote(particlesRef, cx, cy);
              const mobs = event.data.affected_mobs ?? [];
              for (const m of mobs) {
                if (ctx.world.isVisible(m.x, m.y)) {
                  spawnNote(particlesRef, m.x * TILE_SIZE + TILE_SIZE / 2, m.y * TILE_SIZE + TILE_SIZE / 2);
                }
              }
              break;
            }
            case 'TERROR':
              spawnTerror(particlesRef, cx, cy);
              ctx.effects.spawnFlare(cx, cy, 5, 64, '#ff0000', 800);
              break;
            case 'CHANGE': {
              spawnChange(particlesRef, cx, cy);
              const oldKind = event.data.old_kind;
              const newKind = event.data.new_kind;
              if (oldKind && newKind) {
                ctx.effects.addTransmuteEffect({
                  x: cx, y: cy,
                  oldCoords: coordsForKind(oldKind),
                  newCoords: coordsForKind(newKind),
                  startTime: performance.now(),
                });
              }
              break;
            }
            case 'MAP': {
              ctx.effects.spawnFloatingText(cx, cy - TILE_SIZE, 'MAPPED!', '#ffdd44');
              ctx.effects.spawnSpellSprite(cx, cy, SPELL_MAP);
              const discoverPos = event.data.discover_positions ?? [];
              for (const pos of discoverPos) {
                if (ctx.world.isVisible(pos.x, pos.y)) {
                  spawnDiscover(particlesRef, pos.x * TILE_SIZE + TILE_SIZE / 2, pos.y * TILE_SIZE + TILE_SIZE / 2);
                }
              }
              break;
            }
            case 'FLASH':
              ctx.effects.flashScreen(350);
              break;
          }
        }
        return true;
      },
    },
    {
      eventType: 'TELEPORT',
      handle(event: Extract<GameEvent, { type: 'TELEPORT' }>, ctx: GameEventContext) {
        const pid = event.data.player;
        const isLocal = pid === ctx.myPlayerId;
        const fromVisible = ctx.world.isVisible(event.data.from_x, event.data.from_y);
        const toVisible = ctx.world.isVisible(event.data.x, event.data.y);
        if (isLocal || fromVisible) {
          ctx.audio.play('TELEPORT');
          if (ctx.effects.particlesRef) {
            spawnLight(ctx.effects.particlesRef, event.data.from_x * TILE_SIZE + TILE_SIZE / 2, event.data.from_y * TILE_SIZE + TILE_SIZE / 2);
          }
        }
        if ((isLocal || toVisible) && ctx.effects.particlesRef) {
          spawnLight(ctx.effects.particlesRef, event.data.x * TILE_SIZE + TILE_SIZE / 2, event.data.y * TILE_SIZE + TILE_SIZE / 2);
        }
        return true;
      },
    },
    {
      eventType: 'CHAINS_PULL',
      handle(event: Extract<GameEvent, { type: 'CHAINS_PULL' }>, ctx: GameEventContext) {
        const isLocal = event.data.player === ctx.myPlayerId;
        const fromVisible = ctx.world.isVisible(event.data.from_x, event.data.from_y);
        const toVisible = ctx.world.isVisible(event.data.to_x, event.data.to_y);
        if (isLocal || fromVisible || toVisible) {
          playChainPull(ctx.effects.lightningRef, event.data.from_x, event.data.from_y, event.data.to_x, event.data.to_y, ctx.audio);
        }
        return true;
      },
    },
    {
      eventType: 'MIRROR_IMAGE',
      handle(event: Extract<GameEvent, { type: 'MIRROR_IMAGE' }>, ctx: GameEventContext) {
        const pid = event.data.player;
        const isLocal = pid === ctx.myPlayerId;
        const clones = event.data.clones || [];
        for (const clone of clones) {
          if (isLocal || ctx.world.isVisible(clone.x, clone.y)) {
            if (ctx.effects.particlesRef) {
              spawnLight(ctx.effects.particlesRef, clone.x * TILE_SIZE + TILE_SIZE / 2, clone.y * TILE_SIZE + TILE_SIZE / 2);
            }
            ctx.audio.play('TELEPORT');
          }
        }
        return true;
      },
    },
    {
      eventType: 'HEAL',
      handle(event: Extract<GameEvent, { type: 'HEAL' }>, ctx: GameEventContext) {
        const cx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
        const cy = event.data.y * TILE_SIZE;
        ctx.effects.spawnFloatingText(cx, cy, `+${event.data.amount}`, '#2ecc71');
        if (ctx.effects.particlesRef) {
          spawnHeal(ctx.effects.particlesRef, cx, cy + TILE_SIZE / 2, 4);
        }
        if (event.data.target === ctx.myPlayerId) {
          addGameLog(`You heal for ${event.data.amount}`, 'positive');
        }
        return true;
      },
    },
    {
      eventType: 'PLANT_TRIGGERED',
      handle(event: Extract<GameEvent, { type: 'PLANT_TRIGGERED' }>, ctx: GameEventContext) {
        const { plant, x, y, player } = event.data;
        const plants = ctx.entities.getPlants();
        const nextPlants = plants.filter(p => !(p.x === x && p.y === y));
        if (nextPlants.length !== plants.length) {
          ctx.entities.setPlants(nextPlants);
        }

        const cx = x * TILE_SIZE + TILE_SIZE / 2;
        const cy = y * TILE_SIZE + TILE_SIZE / 2;
        const plantKey = (plant || 'sungrass').toLowerCase();

        if (ctx.world.isVisible(x, y)) {
          if (ctx.effects.particlesRef) {
            spawnLeaf(ctx.effects.particlesRef, cx, cy, 6);

            if (plantKey === 'sungrass') {
              spawnShaft(ctx.effects.particlesRef, cx, cy, 3);
            } else if (plantKey === 'starflower') {
              ctx.effects.spawnFlare(cx, cy, 6, 32, '#ffff00', 2000);
            } else if (plantKey === 'earthroot') {
              spawnEarthBurst(ctx.effects.particlesRef, cx, cy, 8);
              ctx.effects.shakeScreen(1, 400);
            } else if (plantKey === 'firebloom') {
              spawnFlameBurst(ctx.effects.particlesRef, cx, cy, 5);
            } else if (plantKey === 'blindweed') {
              spawnLight(ctx.effects.particlesRef, cx, cy, 4);
            } else if (plantKey === 'fadeleaf') {
              spawnLight(ctx.effects.particlesRef, cx, cy, 3);
            }
          }
        }

        const isLocal = player === ctx.myPlayerId;
        if (isLocal) {
          if (plantKey === 'mageroyal' || plantKey === 'dreamfoil') {
            addGameLog(i18n.t('log.refreshed', { defaultValue: 'You feel refreshed.' }), 'positive');
          } else if (plantKey === 'fadeleaf') {
            addGameLog(i18n.t('log.teleported', { defaultValue: 'In a blink of an eye you were teleported to another location of the level.' }), 'neutral');
          } else {
            const plantName = i18n.t(`plant.${plantKey}`, { defaultValue: plantKey.replace('_', ' ') });
            addGameLog(i18n.t('log.trample_plant', { plant: plantName, defaultValue: `You trample the ${plantName}` }), 'positive');
          }

          const announcement = PLANT_ANNOUNCEMENTS[plantKey];
          if (announcement) {
            ctx.effects.spawnFloatingText(cx, cy - TILE_SIZE / 2, announcement.text, announcement.color);
          }
        }
        return true;
      },
    },
    {
      eventType: 'TRAP_TRIGGERED',
      handle(event: Extract<GameEvent, { type: 'TRAP_TRIGGERED' }>, ctx: GameEventContext) {
        const entity = ctx.entities.getEntity(event.data.player);
        const isElectric = event.data.trap === 'shocking_trap' || event.data.trap === 'storm_trap';
        if (event.data.x != null && event.data.y != null) {
          const traps = ctx.entities.getTraps();
          const existing = traps.find(t => t.x === event.data.x && t.y === event.data.y);
          if (existing) {
            existing.trap_type = event.data.trap;
          } else {
            traps.push({
              x: event.data.x,
              y: event.data.y,
              trap_type: event.data.trap,
              renderPos: { x: event.data.x, y: event.data.y },
              revealStartTime: null,
            });
            ctx.entities.setTraps(traps);
          }
        }
        if (event.data.player === ctx.myPlayerId) {
          addGameLog(`You trigger a ${event.data.trap} trap${event.data.damage ? ` for ${event.data.damage} damage` : ''}`, 'negative');
        }
        if (entity) {
          const cx = entity.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
          const cy = entity.renderPos.y * TILE_SIZE;
          if (isElectric) {
            ctx.audio.play('LIGHTNING');
            if (event.data.x != null && event.data.y != null) {
              const tx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
              const ty = event.data.y * TILE_SIZE + TILE_SIZE / 2;
              ctx.effects.spawnLightning(tx, ty, cx, cy, '#66ccff');
            }
            if (ctx.effects.particlesRef) spawnSparkMoving(ctx.effects.particlesRef, cx, cy + TILE_SIZE / 2, 6);
            ctx.effects.spawnFloatingText(cx, cy, 'ZAP!', '#66ccff');
          } else {
            const isExplosive = event.data.trap === 'explosive_trap';
            const isFire = event.data.trap === 'burning_trap' || event.data.trap === 'blazing_trap';
            if (isFire) {
              ctx.audio.play('BURNING', 1.0, 250);
              if (ctx.effects.particlesRef) spawnFlameBurst(ctx.effects.particlesRef, cx, cy + TILE_SIZE / 2, 10);
            } else if (!isExplosive) {
              ctx.audio.play('TRAP');
            }
            if (event.data.damage > 0) {
              ctx.effects.spawnFloatingText(cx, cy, `-${event.data.damage}`, '#e74c3c');
            }
            if (ctx.effects.particlesRef && !isExplosive) {
              const trap = event.data.trap;
              const particlesRef = ctx.effects.particlesRef;
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
      },
    },
    {
      eventType: 'MOVE',
      handle(event: Extract<GameEvent, { type: 'MOVE' }>, ctx: GameEventContext) {
        const tileX = event.data.x;
        const tileY = event.data.y;
        const tileType = ctx.world.getTile(tileX, tileY);
        const isDoor = tileType === 3;
        const isMe = event.data.entity === ctx.myPlayerId;
        if (isMe) {
          if (isDoor) ctx.audio.play('DOOR_OPEN');
          else if (tileType && ctx.audio.playStep) ctx.audio.playStep(tileType);
          else ctx.audio.play('MOVE');
        } else {
          if (ctx.world.isVisible(tileX, tileY)) {
            if (isDoor) ctx.audio.play('DOOR_OPEN');
            else ctx.audio.play(event.type);
          }
        }
        if (isWaterTile(tileType)) {
          const entityVisible = isMe || ctx.world.isVisible(tileX, tileY);
          if (entityVisible) {
            const entityId = event.data.entity;
            const playerEnt = ctx.entities.getPlayer(entityId);
            const mobEnt = ctx.entities.getMob(entityId);
            const flying = playerEnt
              ? (playerEnt.active_effects || []).some((e) => e.key === 'levitation')
              : !!mobEnt?.flying;
            if (!flying) {
              spawnWaterRipple(tileX * TILE_SIZE + TILE_SIZE / 2, tileY * TILE_SIZE + TILE_SIZE / 2);
            }
          }
        }
        return true;
      },
    },
    {
      eventType: 'MOVE_RESULT',
      handle(event: Extract<GameEvent, { type: 'MOVE_RESULT' }>, ctx: GameEventContext) {
        if (event.data.entity === ctx.myPlayerId) {
          movementPredictor.onMoveResult(event.data, ctx.entities.getPlayer(event.data.entity) ?? null);
        }
        return true;
      },
    },
    {
      eventType: 'DROP',
      handle(event: Extract<GameEvent, { type: 'DROP' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          addGameLog(`You drop the ${event.data.item_name}`, 'neutral');
          const me = ctx.entities.getPlayer(event.data.player);
          if (me) {
            ctx.effects.spawnFloatingText(me.renderPos.x * TILE_SIZE + TILE_SIZE / 2, me.renderPos.y * TILE_SIZE, `${event.data.item_name}`, '#ffffff', 18);
          }
        }
        return true;
      },
    },
    {
      eventType: 'PICKUP',
      handle(event: Extract<GameEvent, { type: 'PICKUP' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.audio.play('PICKUP');
          addGameLog(`You picked up ${event.data.item}`, 'positive');
          ctx.effects.spawnFlyingItem(event.data.item, event.data.item_type, event.data.x, event.data.y);
        }
        return true;
      },
    },
    {
      eventType: 'PICKUP_GOLD',
      handle(event: Extract<GameEvent, { type: 'PICKUP_GOLD' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.audio.play('GOLD');
          addGameLog(`You picked up ${event.data.amount} gold`, 'positive');
        }
        return true;
      },
    },
    {
      eventType: 'PICKUP_KEY',
      handle(event: Extract<GameEvent, { type: 'PICKUP_KEY' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.audio.play('PICKUP');
          addGameLog(`You picked up ${event.data.name}`, 'positive');
          const me = ctx.entities.getPlayer(ctx.myPlayerId);
          if (me) {
            ctx.effects.spawnFloatingText(me.renderPos.x * TILE_SIZE + TILE_SIZE / 2, me.renderPos.y * TILE_SIZE, `${event.data.name}`, '#ffffff', 18);
          }
        }
        return true;
      },
    },
    {
      eventType: 'STAIRS_DOWN',
      handle(event: Extract<GameEvent, { type: 'STAIRS_DOWN' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId && event.data.first_visit) {
          ctx.audio.play('STAIRS_DOWN');
        }
        return true;
      },
    },
    {
      eventType: 'EQUIP_CURSED',
      handle(event: Extract<GameEvent, { type: 'EQUIP_CURSED' }>, ctx: GameEventContext) {
        const pid = event.data.player_id;
        if (pid === ctx.myPlayerId) {
          ctx.audio.play('CURSED');
          addGameLog('You feel a sinister energy from the cursed item!', 'negative');
        }
        if (ctx.effects.particlesRef) {
          const cx = event.data.x * TILE_SIZE + TILE_SIZE / 2;
          const cy = event.data.y * TILE_SIZE + TILE_SIZE / 2;
          spawnShadowUp(ctx.effects.particlesRef, cx, cy, 10);
        }
        return true;
      },
    },
  ];
}
