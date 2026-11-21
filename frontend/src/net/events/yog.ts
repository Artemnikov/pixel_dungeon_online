import { TILE_SIZE } from '../../constants';
import i18n from '../../i18n';
import { spawnLeaf, spawnShadowUp } from '../../rendering/draw/particles';
import { spawnPurpleBurst } from '../../rendering/draw/purpleParticle';
import { spawnSmoke } from '../../rendering/draw/smokeParticle';
import {
  addTargetedCells, startCellEmitter, startMobJump, startMobPush,
} from '../../rendering/yogEffects';
import { FIST_ZAP_MS } from '../../rendering/mobs';
import type { GameEvent } from '../../types/contract';
import type { CustomTileLayer } from '../types';
import type { GameEventContext, IGameEventHandler } from './IGameEventHandler';

const centre = (v: number) => v * TILE_SIZE + TILE_SIZE / 2;

// CharSprite status colours (CharSprite.POSITIVE / WARNING / NEGATIVE / NEUTRAL).
const STATUS_COLORS: Record<string, string> = {
  positive: '#00ff00',
  warning: '#ff8800',
  negative: '#ff0000',
  neutral: '#ffff00',
};

const STATUS_DEFAULTS: Record<string, string> = {
  'statusText.invulnerable': 'invulnerable',
  'statusText.bleeding': 'Bleeding {{value}}',
  'statusText.deferred': 'deferred {{value}}',
};

function pushOut(ctx: GameEventContext, mobId: string, from: { x: number; y: number } | null, to: { x: number; y: number }) {
  if (!from) return;
  const mob = ctx.entities.getMob(mobId);
  if (!mob) return;
  mob.renderPos = { x: from.x, y: from.y };
  startMobPush(mobId, from, to);
}

export function createYogEventHandlers(): IGameEventHandler[] {
  return [
    {
      eventType: 'YOG_JOIN_PROMPT',
      handle(event: Extract<GameEvent, { type: 'YOG_JOIN_PROMPT' }>, ctx: GameEventContext) {
        ctx.ui.yogJoinPrompt(event.data);
        return true;
      },
    },
    {
      eventType: 'YOG_PARTY_STATUS',
      handle(event: Extract<GameEvent, { type: 'YOG_PARTY_STATUS' }>, ctx: GameEventContext) {
        ctx.ui.yogPartyStatus(event.data);
        return true;
      },
    },
    {
      eventType: 'YOG_PROMPT_CLOSE',
      handle(_event: Extract<GameEvent, { type: 'YOG_PROMPT_CLOSE' }>, ctx: GameEventContext) {
        ctx.ui.yogPromptClose();
        return true;
      },
    },
    {
      eventType: 'YOG_PHASE_CHANGE',
      handle(event: Extract<GameEvent, { type: 'YOG_PHASE_CHANGE' }>, ctx: GameEventContext) {
        ctx.ui.yogPhaseChange(event.data);
        return true;
      },
    },
    {
      // HallsBossLevel.seal: CellEmitter.get(entrance).start(FlameParticle.FACTORY, 0.1f, 10).
      eventType: 'YOG_ARENA_SEALED',
      handle(event: Extract<GameEvent, { type: 'YOG_ARENA_SEALED' }>) {
        startCellEmitter(event.data.x, event.data.y, 'flame', 0.1, 10);
        return true;
      },
    },
    {
      eventType: 'YOG_ARENA_UNSEALED',
      handle(event: Extract<GameEvent, { type: 'YOG_ARENA_UNSEALED' }>, ctx: GameEventContext) {
        ctx.world.setCustomLayers(
          event.data.custom_tiles as CustomTileLayer[],
          event.data.custom_walls as CustomTileLayer[],
        );
        return true;
      },
    },
    {
      eventType: 'YOG_VIEW_DISTANCE',
      handle() {
        return true;
      },
    },
    {
      // CellEmitter.get(cell).burst(ShadowParticle.UP, n) at exit-1 / exit / exit+1.
      eventType: 'YOG_SHADOW_BURST',
      handle(event: Extract<GameEvent, { type: 'YOG_SHADOW_BURST' }>, ctx: GameEventContext) {
        const ref = ctx.effects.particlesRef;
        if (!ref) return true;
        for (const [x, y, n] of event.data.cells) {
          if (!ctx.world.isVisible(x, y)) continue;
          for (let i = 0; i < n; i++) {
            spawnShadowUp(ref, x * TILE_SIZE + Math.random() * TILE_SIZE, y * TILE_SIZE + Math.random() * TILE_SIZE, 1);
          }
        }
        return true;
      },
    },
    {
      // YogDzewa.addFist: Actor.add(new Pushing(fist, exit, fist.pos)).
      eventType: 'YOG_FIST_SPAWN',
      handle(event: Extract<GameEvent, { type: 'YOG_FIST_SPAWN' }>, ctx: GameEventContext) {
        pushOut(ctx, event.data.fist, { x: event.data.from_x, y: event.data.from_y }, { x: event.data.x, y: event.data.y });
        return true;
      },
    },
    {
      // Summons are pushed out from their summoner (Pushing).
      eventType: 'MOB_SPAWN',
      handle(event: Extract<GameEvent, { type: 'MOB_SPAWN' }>, ctx: GameEventContext) {
        const { from_x: fx, from_y: fy } = event.data;
        pushOut(ctx, event.data.mob, fx != null && fy != null ? { x: fx, y: fy } : null, { x: event.data.x, y: event.data.y });
        return true;
      },
    },
    {
      // YogDzewa.act: sprite.parent.add(new TargetedCell(p, 0xFF0000)) per path cell.
      eventType: 'YOG_TARGETED_CELLS',
      handle(event: Extract<GameEvent, { type: 'YOG_TARGETED_CELLS' }>) {
        addTargetedCells(event.data.cells, event.data.color, event.data.duration_ms);
        return true;
      },
    },
    {
      // Beam.DeathRay from Yog's centre to each beam's collision cell, and
      // CellEmitter.center(yog).burst(PurpleParticle.BURST, 1..2) per hit.
      eventType: 'YOG_DEATH_RAY',
      handle(event: Extract<GameEvent, { type: 'YOG_DEATH_RAY' }>, ctx: GameEventContext) {
        const sx = centre(event.data.sx);
        const sy = centre(event.data.sy);
        for (const [ex, ey] of event.data.ends) {
          ctx.effects.spawnBeam(sx, sy, centre(ex), centre(ey), 'death_ray');
        }
        const ref = ctx.effects.particlesRef;
        if (ref && ctx.world.isVisible(event.data.sx, event.data.sy)) {
          for (let i = 0; i < event.data.hits.length; i++) {
            spawnPurpleBurst(ref, sx, sy, 1 + Math.floor(Math.random() * 2));
          }
        }
        return true;
      },
    },
    {
      // FistSprite.zap: MagicMissile.boltFromChar(boltType); BrightFist adds a
      // Beam.LightRay instead of a bolt.
      eventType: 'FIST_ZAP',
      handle(event: Extract<GameEvent, { type: 'FIST_ZAP' }>, ctx: GameEventContext) {
        ctx.effects.setMobAnimUntil(event.data.mob, 'zapUntil', FIST_ZAP_MS);
        const mob = ctx.entities.getMob(event.data.mob);
        if (mob) {
          const dx = event.data.target_x - event.data.x;
          if (dx > 0) { mob.facing = 'RIGHT'; mob.flipX = false; } else if (dx < 0) { mob.facing = 'LEFT'; mob.flipX = true; }
        }
        const sx = centre(event.data.x);
        const sy = centre(event.data.y);
        const tx = centre(event.data.target_x);
        const ty = centre(event.data.target_y);
        if (event.data.bolt === 'light_ray') {
          ctx.effects.spawnBeam(sx, sy, tx, ty, 'light_ray');
        } else {
          ctx.effects.spawnMagicMissile(sx, sy, tx, ty, event.data.bolt);
        }
        return true;
      },
    },
    {
      // CharSprite.showStatus.
      eventType: 'STATUS_TEXT',
      handle(event: Extract<GameEvent, { type: 'STATUS_TEXT' }>, ctx: GameEventContext) {
        if (!ctx.world.isVisible(event.data.x, event.data.y)) return true;
        const text = i18n.t(event.data.key, {
          value: event.data.value ?? '',
          defaultValue: STATUS_DEFAULTS[event.data.key] ?? event.data.key,
        });
        ctx.effects.spawnFloatingText(centre(event.data.x), event.data.y * TILE_SIZE, text,
          STATUS_COLORS[event.data.kind] ?? STATUS_COLORS.neutral);
        return true;
      },
    },
    {
      // Speck.STEAM bursts (evaporated water) and LeafParticle.GENERAL (grass growth).
      eventType: 'TERRAIN_BURST',
      handle(event: Extract<GameEvent, { type: 'TERRAIN_BURST' }>, ctx: GameEventContext) {
        const ref = ctx.effects.particlesRef;
        if (!ref) return true;
        for (const [x, y, n] of event.data.cells) {
          if (!ctx.world.isVisible(x, y)) continue;
          if (event.data.kind === 'leaf') spawnLeaf(ref, centre(x), centre(y), n);
          else spawnSmoke(ref, centre(x), centre(y), Math.ceil(n / 2));
        }
        return true;
      },
    },
    {
      // RipperDemon prep: TargetedCell(leapPos, 0xFF0000) + RipperSprite.leapPrep.
      eventType: 'RIPPER_LEAP_PREP',
      handle(event: Extract<GameEvent, { type: 'RIPPER_LEAP_PREP' }>, ctx: GameEventContext) {
        addTargetedCells([[event.data.x, event.data.y]], event.data.color, event.data.duration_ms);
        ctx.effects.setMobAnimUntil(event.data.mob, 'prepUntil', 3000);
        const mob = ctx.entities.getMob(event.data.mob);
        if (mob) {
          const dx = event.data.x - mob.renderPos.x;
          if (dx > 0) { mob.facing = 'RIGHT'; mob.flipX = false; } else if (dx < 0) { mob.facing = 'LEFT'; mob.flipX = true; }
        }
        return true;
      },
    },
    {
      // RipperDemon leap: sprite.jump(pos, leapPos), then Pushing to the bounce cell.
      eventType: 'RIPPER_LEAP',
      handle(event: Extract<GameEvent, { type: 'RIPPER_LEAP' }>, ctx: GameEventContext) {
        ctx.effects.setMobAnimUntil(event.data.mob, 'prepUntil', 0);
        const mob = ctx.entities.getMob(event.data.mob);
        if (!mob) return true;
        const from = { x: event.data.from_x, y: event.data.from_y };
        const land = { x: event.data.x, y: event.data.y };
        const end = { x: event.data.end_x, y: event.data.end_y };
        mob.renderPos = { ...from };
        startMobJump(event.data.mob, from, land);
        if (end.x !== land.x || end.y !== land.y) {
          const jumpMs = Math.max(1, Math.hypot(land.x - from.x, land.y - from.y)) * 100;
          setTimeout(() => startMobPush(event.data.mob, land, end), jumpMs);
        }
        return true;
      },
    },
    {
      eventType: 'EYE_CHARGE_END',
      handle(event: Extract<GameEvent, { type: 'EYE_CHARGE_END' }>, ctx: GameEventContext) {
        ctx.effects.setMobCharge(event.data.mob, 0);
        return true;
      },
    },
  ];
}
