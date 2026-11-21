import { TILE_SIZE } from '../../constants';
import { spawnFlameBurst, spawnSacrificeFlame } from '../../rendering/draw/flameParticle';
import { spawnElmo } from '../../rendering/draw/elmoParticle';
import {
  spawnWhiteSplash,
  spawnSewerBarrelBurst,
  spawnLeafForRegion,
  spawnEnergy,
  spawnBoneRattle,
  spawnCoin,
  spawnBombBlast,
  spawnDust,
  spawnCritSparkle,
  spawnRockSpecks,
} from '../../rendering/draw/particles';
import { regionForDepth } from '../../rendering/regions';
import type { GameEvent } from '../../types/contract';
import type { GameEventContext, IGameEventHandler } from './IGameEventHandler';

const BOMB_BLAST_TINT: Record<string, [string, string]> = {
  frost_bomb: ['#AEE6FF', '#2C79B8'],
  smoke_bomb: ['#CFCFCF', '#5A5A5A'],
  holy_bomb: ['#FFF3B0', '#C99A00'],
  flashbang_bomb: ['#FFFFFF', '#7FA8FF'],
  arcane_bomb: ['#E4B4FF', '#6A22AA'],
  regrowth_bomb: ['#BFF7A0', '#2E7D32'],
  woolly_bomb: ['#FFFFFF', '#BFBFBF'],
};

export function createWorldEventHandlers(): IGameEventHandler[] {
  return [
    {
      eventType: 'CHASM_PROMPT',
      handle(event: Extract<GameEvent, { type: 'CHASM_PROMPT' }>, ctx: GameEventContext) {
        ctx.ui.chasmPrompt(event.data);
        return true;
      },
    },
    {
      eventType: 'CHASM_FALL',
      handle(event: Extract<GameEvent, { type: 'CHASM_FALL' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId && event.data.feather) {
          const me = ctx.entities.getPlayer(event.data.player);
          if (me && ctx.effects.particlesRef) {
            const px = me.renderPos.x * TILE_SIZE + TILE_SIZE / 2;
            const py = me.renderPos.y * TILE_SIZE + TILE_SIZE / 2;
            spawnEnergy(ctx.effects.particlesRef, px, py, 20);
            spawnWhiteSplash(ctx.effects.particlesRef, px, py, 10);
          }
        }
        return true;
      },
    },
    {
      eventType: 'SCREEN_SHAKE',
      handle(event: Extract<GameEvent, { type: 'SCREEN_SHAKE' }>, ctx: GameEventContext) {
        ctx.effects.shakeScreen(event.data.intensity, event.data.duration_ms);
        return true;
      },
    },
    {
      eventType: 'MOB_CHASM_FALL',
      handle(event: Extract<GameEvent, { type: 'MOB_CHASM_FALL' }>, ctx: GameEventContext) {
        const { x, y } = event.data;
        if (ctx.world.isVisible(x, y)) {
          const cx = x * TILE_SIZE + TILE_SIZE / 2;
          const cy = y * TILE_SIZE + TILE_SIZE / 2;
          if (ctx.effects.particlesRef) {
            spawnDust(ctx.effects.particlesRef, cx, cy, 8, '#8a8a8a');
            spawnWhiteSplash(ctx.effects.particlesRef, cx, cy, 6);
          }
          ctx.audio.play('FALLING');
        }
        return true;
      },
    },
    {
      eventType: 'BLOB_UPDATE',
      handle(event: Extract<GameEvent, { type: 'BLOB_UPDATE' }>, ctx: GameEventContext) {
        const { id, type, cells } = event.data;
        ctx.world.updateBlob(id, type, cells);
        return true;
      },
    },
    {
      eventType: 'BLOB_DEPLETED',
      handle(event: Extract<GameEvent, { type: 'BLOB_DEPLETED' }>, ctx: GameEventContext) {
        ctx.world.removeBlob(event.data.id);
        return true;
      },
    },
    {
      eventType: 'STATE_EFFECT',
      handle(event: Extract<GameEvent, { type: 'STATE_EFFECT' }>, ctx: GameEventContext) {
        const { effect, x, y } = event.data;
        if (ctx.world.isVisible(x, y)) {
          ctx.effects.spawnStateParticles(x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, effect);
        }
        return true;
      },
    },
    {
      eventType: 'SPELL_SPRITE',
      handle(event: Extract<GameEvent, { type: 'SPELL_SPRITE' }>, ctx: GameEventContext) {
        const { x, y, index } = event.data;
        if (ctx.world.isVisible(x, y)) {
          ctx.effects.spawnSpellSprite(x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, index);
        }
        return true;
      },
    },
    {
      eventType: 'FIRE_IMBUE_ACTIVATED',
      handle(event: Extract<GameEvent, { type: 'FIRE_IMBUE_ACTIVATED' }>, ctx: GameEventContext) {
        const { x, y } = event.data;
        if (ctx.world.isVisible(x, y)) {
          if (ctx.effects.particlesRef) {
            spawnFlameBurst(ctx.effects.particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 16);
          }
          ctx.audio.play('BURNING', 1.0, 250);
        }
        return true;
      },
    },
    {
      eventType: 'FLAME_BURST',
      handle(event: Extract<GameEvent, { type: 'FLAME_BURST' }>, ctx: GameEventContext) {
        const { x, y } = event.data;
        if (ctx.world.isVisible(x, y)) {
          if (ctx.effects.particlesRef) {
            spawnFlameBurst(ctx.effects.particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 8);
          }
          ctx.audio.play('BURNING', 1.0, 250);
        }
        return true;
      },
    },
    {
      eventType: 'INFERNO_ACTIVATED',
      handle(event: Extract<GameEvent, { type: 'INFERNO_ACTIVATED' }>, ctx: GameEventContext) {
        const { x, y } = event.data;
        if (ctx.world.isVisible(x, y) && ctx.effects.particlesRef) {
          spawnElmo(ctx.effects.particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 12);
        }
        return true;
      },
    },
    {
      eventType: 'SACRIFICIAL_FIRE',
      handle(event: Extract<GameEvent, { type: 'SACRIFICIAL_FIRE' }>, ctx: GameEventContext) {
        const { x, y } = event.data;
        if (ctx.world.isVisible(x, y)) {
          if (ctx.effects.particlesRef) {
            spawnElmo(ctx.effects.particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 8);
          }
          ctx.audio.play('BURNING', 1.0, 250);
        }
        return true;
      },
    },
    {
      eventType: 'SACRIFICE_FEED',
      handle(event: Extract<GameEvent, { type: 'SACRIFICE_FEED' }>, ctx: GameEventContext) {
        const { x, y } = event.data;
        if (ctx.world.isVisible(x, y)) {
          if (ctx.effects.particlesRef) {
            spawnSacrificeFlame(ctx.effects.particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 20);
          }
          ctx.audio.play('BURNING', 1.0, 250);
        }
        return true;
      },
    },
    {
      eventType: 'SACRIFICE_REWARD',
      handle(event: Extract<GameEvent, { type: 'SACRIFICE_REWARD' }>, ctx: GameEventContext) {
        const { x, y } = event.data;
        if (ctx.world.isVisible(x, y)) {
          if (ctx.effects.particlesRef) {
            for (let dx = -1; dx <= 1; dx++) {
              for (let dy = -1; dy <= 1; dy++) {
                spawnSacrificeFlame(ctx.effects.particlesRef, (x + dx) * TILE_SIZE + TILE_SIZE / 2, (y + dy) * TILE_SIZE + TILE_SIZE / 2, 20);
              }
            }
          }
          ctx.audio.play('BURNING', 1.0, 250);
        }
        return true;
      },
    },
    {
      eventType: 'SACRIFICE_UNWORTHY',
      handle() {
        return true;
      },
    },
    {
      eventType: 'MAP_PATCH',
      handle(event: Extract<GameEvent, { type: 'MAP_PATCH' }>, ctx: GameEventContext) {
        if (event.data?.custom_tiles) {
          ctx.world.patchCustomTiles(event.data.custom_tiles);
        }
        if (event.data?.tiles) {
          ctx.world.patchGrid(event.data.tiles, (x, y) => {
            if (ctx.effects.particlesRef) {
              spawnSewerBarrelBurst(ctx.effects.particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2);
            }
          });
          if (ctx.effects.particlesRef) {
            for (const t of event.data.tiles) {
              if (!t.fx || !ctx.world.isVisible(t.x, t.y)) continue;
              const cx = t.x * TILE_SIZE + TILE_SIZE / 2;
              const cy = t.y * TILE_SIZE + TILE_SIZE / 2;
              if (t.fx === 'rock') {
                spawnRockSpecks(ctx.effects.particlesRef, cx, cy, 10);
              } else if (t.fx === 'blast') {
                spawnBombBlast(ctx.effects.particlesRef, cx, cy, 10);
              }
            }
          }
        }
        return true;
      },
    },
    {
      eventType: 'WOOL_BURST',
      handle(event: Extract<GameEvent, { type: 'WOOL_BURST' }>, ctx: GameEventContext) {
        const { x, y } = event.data;
        if (ctx.world.isVisible(x, y) && ctx.effects.particlesRef) {
          spawnWhiteSplash(ctx.effects.particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 4);
        }
        return true;
      },
    },
    {
      eventType: 'FLOCK',
      handle(event: Extract<GameEvent, { type: 'FLOCK' }>, ctx: GameEventContext) {
        const sheep = event.data.sheep || [];
        if (ctx.effects.particlesRef) {
          for (const s of sheep) {
            if (ctx.world.isVisible(s.x, s.y)) {
              spawnWhiteSplash(ctx.effects.particlesRef, s.x * TILE_SIZE + TILE_SIZE / 2, s.y * TILE_SIZE + TILE_SIZE / 2, 4);
            }
          }
        }
        return true;
      },
    },
    {
      eventType: 'BOMB_LIT',
      handle(event: Extract<GameEvent, { type: 'BOMB_LIT' }>, ctx: GameEventContext) {
        const { x, y } = event.data;
        if (ctx.world.isVisible(x, y) && ctx.effects.particlesRef) {
          spawnCritSparkle(ctx.effects.particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 5, '#FF5522');
        }
        return true;
      },
    },
    {
      eventType: 'BOMB_BLAST',
      handle(event: Extract<GameEvent, { type: 'BOMB_BLAST' }>, ctx: GameEventContext) {
        const { x, y, kind, cells } = event.data;
        const [core, edge] = BOMB_BLAST_TINT[kind] ?? ['#FFDD66', '#992200'];
        if (ctx.effects.particlesRef) {
          if (ctx.world.isVisible(x, y)) {
            spawnBombBlast(ctx.effects.particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 26, core, edge);
            ctx.effects.shakeScreen(1, 220);
            if (kind === 'firebomb') ctx.audio.play('BURNING', 1.0, 250);
          }
          for (const cell of cells ?? []) {
            const [cxx, cyy] = cell;
            if (ctx.world.isVisible(cxx, cyy)) {
              spawnDust(ctx.effects.particlesRef, cxx * TILE_SIZE + TILE_SIZE / 2, cyy * TILE_SIZE + TILE_SIZE / 2, 3, '#8a8a8a');
            }
          }
        }
        return true;
      },
    },
    {
      eventType: 'LOCKED',
      handle(event: Extract<GameEvent, { type: 'LOCKED' }>, ctx: GameEventContext) {
        ctx.audio.play('LOCKED');
        const { x, y } = event.data;
        if (x != null && y != null && ctx.world.isVisible(x, y)) {
          const cx = x * TILE_SIZE + TILE_SIZE / 2;
          const cy = y * TILE_SIZE + TILE_SIZE * 0.2;
          ctx.effects.spawnFloatingText(cx, cy, 'Locked', '#ffaa44', -1, undefined, { fontSize: 13, lineWidth: 3 });
        }
        return true;
      },
    },
    {
      eventType: 'OPEN_CHEST',
      handle(event: Extract<GameEvent, { type: 'OPEN_CHEST' }>, ctx: GameEventContext) {
        const { x, y, chest_type } = event.data;
        if (ctx.world.isVisible(x, y) && ctx.effects.particlesRef) {
          const cx = x * TILE_SIZE + TILE_SIZE / 2;
          const cy = y * TILE_SIZE + TILE_SIZE / 2;
          if (chest_type === 'TOMB') {
            ctx.effects.shakeScreen(1, 500);
            spawnWhiteSplash(ctx.effects.particlesRef, cx, cy, 6);
          } else if (chest_type === 'SKELETON' || chest_type === 'REMAINS') {
            spawnBoneRattle(ctx.effects.particlesRef, cx, cy);
            spawnWhiteSplash(ctx.effects.particlesRef, cx, cy, 4);
          } else {
            spawnWhiteSplash(ctx.effects.particlesRef, cx, cy, 4);
          }
        }
        return true;
      },
    },
    {
      eventType: 'LEAF_BURST',
      handle(event: Extract<GameEvent, { type: 'LEAF_BURST' }>, ctx: GameEventContext) {
        const { x, y } = event.data;
        if (ctx.world.isVisible(x, y) && ctx.effects.particlesRef) {
          const region = regionForDepth(ctx.world.depth || 1);
          spawnLeafForRegion(ctx.effects.particlesRef, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2, 4, region);
        }
        return true;
      },
    },
    {
      eventType: 'GOLD_DROP',
      handle(event: Extract<GameEvent, { type: 'GOLD_DROP' }>, ctx: GameEventContext) {
        const { x, y } = event.data;
        if (ctx.world.isVisible(x, y)) {
          const cx = x * TILE_SIZE + TILE_SIZE / 2;
          const cy = y * TILE_SIZE + TILE_SIZE / 2;
          if (ctx.effects.particlesRef) {
            spawnCoin(ctx.effects.particlesRef, cx, cy);
          }
          ctx.audio.play('GOLD');
        }
        return true;
      },
    },
    {
      eventType: 'CRYSTAL_CHEST_SHATTER',
      handle(event: Extract<GameEvent, { type: 'CRYSTAL_CHEST_SHATTER' }>, ctx: GameEventContext) {
        const { x, y } = event.data;
        if (ctx.world.isVisible(x, y) && ctx.effects.particlesRef) {
          const cx = x * TILE_SIZE + TILE_SIZE / 2;
          const cy = y * TILE_SIZE + TILE_SIZE / 2;
          spawnWhiteSplash(ctx.effects.particlesRef, cx, cy, 6);
          spawnEnergy(ctx.effects.particlesRef, cx, cy, 10);
        }
        return true;
      },
    },
  ];
}
