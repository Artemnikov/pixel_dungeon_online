import { TILE_SIZE, TILE_SCALE, ENTITY_LIFT, DEATH_ANIMATION_DURATION, DEATH_FADE_START_MS } from '../../constants';
import { drawWhiteSilhouette } from './flash';
import { drawShieldFx } from './shieldHalo';
import { defaultHeroAnimationPipeline } from '../animation/HeroAnimationPipeline';

function pixelRound(value, pixelWidth) {
  return Math.ceil(value * pixelWidth) / pixelWidth;
}

export function drawPlayers(ctx, { entitiesRef, visionRef, assetImages, playerAnimRef, myPlayerId, shieldFxRef }) {
  Object.values(entitiesRef.current.players).forEach(player => {
    const isPlayerVisible = visionRef.current.visible.has(`${Math.round(player.renderPos.x)},${Math.round(player.renderPos.y)}`) || player.id === myPlayerId;
    if (!isPlayerVisible) return;

    const x = player.renderPos.x * TILE_SIZE;
    const y = player.renderPos.y * TILE_SIZE - ENTITY_LIFT;

    const now = performance.now();
    const deathElapsed = now - (player.deathStart || now);
    // Unified death window: the corpse is hidden once the anim + fade completes.
    if (player.is_downed && deathElapsed >= DEATH_ANIMATION_DURATION) return;

    // Map class -> sheet key directly. assetImages[key] is null until that sheet
    // loads, and the `if (playerSprite)` guard below skips drawing until then, so
    // a known class never flashes as the warrior fallback during load.
    const CLASS_KEYS = {
      warrior: 'warrior',
      mage: 'mage',
      rogue: 'rogue',
      huntress: 'huntress',
      duelist: 'duelist',
      cleric: 'cleric',
    };
    const playerSprite = assetImages[CLASS_KEYS[player.class_type] || 'warrior'];

    if (playerSprite) {

      ctx.save();

      if (player.fadeAlpha != null && player.fadeAlpha < 1) {
        ctx.globalAlpha = player.fadeAlpha;
      }
      if (player.is_downed) {
        const deathFade = deathElapsed <= DEATH_FADE_START_MS ? 1 : Math.max(0, 1 - (deathElapsed - DEATH_FADE_START_MS) / (DEATH_ANIMATION_DURATION - DEATH_FADE_START_MS));
        ctx.globalAlpha *= deathFade;
      }

      const anim = (playerAnimRef && playerAnimRef.current[player.id]) || {};
      const isFlashing = anim.flashUntil && now < anim.flashUntil;

      const frameIndex = defaultHeroAnimationPipeline.getFrameIndex({
        player,
        anim,
        now,
        deathElapsed,
      });

      const sx = frameIndex * 12;
      const sWidth = 12;
      const dWidth = sWidth * TILE_SCALE;
      const xOffset = (TILE_SIZE - dWidth) / 2;
      const SRC_FRAME_H = 15;
      const armorTier = player.equipped_wearable?.tier ?? 0;
      const sy = Math.max(0, Math.min(armorTier, 6)) * SRC_FRAME_H;

      if (player.flipX) {
        ctx.translate(x + TILE_SIZE - xOffset, y);
        ctx.scale(-1, 1);
        ctx.drawImage(playerSprite, sx, sy, sWidth, SRC_FRAME_H, 0, 0, dWidth, TILE_SIZE);
        if (isFlashing) drawWhiteSilhouette(ctx, playerSprite, sx, sy, sWidth, SRC_FRAME_H, 0, 0, dWidth, TILE_SIZE);
      } else {
        ctx.drawImage(playerSprite, sx, sy, sWidth, SRC_FRAME_H, x + xOffset, y, dWidth, TILE_SIZE);
        if (isFlashing) drawWhiteSilhouette(ctx, playerSprite, sx, sy, sWidth, SRC_FRAME_H, x + xOffset, y, dWidth, TILE_SIZE);
      }
      ctx.restore();
    }

    // SPD-style CharHealthIndicator for other players (1px bar, 4/6 width, centered above sprite)
    if (player.id !== myPlayerId && !player.is_downed) {
      const hp = player.hp || 0;
      const maxHp = player.max_hp || 1;
      const shield = (player.shields || []).reduce((sum, s) => sum + (s.amount || 0), 0);

      {
        const max = Math.max(hp + shield, maxHp);
        let healthPct = hp / max;
        let shieldPct = (hp + shield) / max;

        const barW = TILE_SIZE * (4 / 6);
        const barX = x + (TILE_SIZE - barW) / 2;
        const barY = y - 8;

        const pxW = barW;

        ctx.fillStyle = '#cc0000';
        ctx.fillRect(barX, barY, barW, 2);

        const shldW = barW * pixelRound(shieldPct, pxW);
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(barX, barY, shldW, 2);

        const hpW = barW * pixelRound(healthPct, pxW);
        ctx.fillStyle = '#00ee00';
        ctx.fillRect(barX, barY, hpW, 2);
      }
    }

    if (player.id !== myPlayerId && !player.is_downed) {
      ctx.fillStyle = 'white';
      ctx.font = '10px Arial';
      ctx.textAlign = 'center';
      ctx.fillText(player.name, x + TILE_SIZE / 2, y - 15);

      if (player.is_afk) {
        ctx.font = 'bold 10px Arial';
        ctx.fillStyle = '#ffdd55';
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 3;
        ctx.strokeText('(AFK)', x + TILE_SIZE / 2, y - 26);
        ctx.fillText('(AFK)', x + TILE_SIZE / 2, y - 26);
      }
    }

    const totalShield = (player.shields || []).reduce((sum, s) => sum + (s.amount || 0), 0);
    if (shieldFxRef) {
      drawShieldFx(ctx, shieldFxRef, player.id, x + TILE_SIZE / 2, y, totalShield, player.fadeAlpha ?? 1);
    }
  });
}
