import { TILE_SIZE, TILE_SCALE, ENTITY_LIFT, PLAYER_ATTACK_DURATION, PLAYER_OPERATE_DURATION, PLAYER_READ_DURATION } from '../../constants';
import { drawWhiteSilhouette } from './flash';
import { drawShieldHalo } from './shieldHalo';

function pixelRound(value, pixelWidth) {
  return Math.ceil(value * pixelWidth) / pixelWidth;
}

export function drawPlayers(ctx, { entitiesRef, visionRef, assetImages, playerAnimRef, myPlayerId }) {
  Object.values(entitiesRef.current.players).forEach(player => {
    const isPlayerVisible = visionRef.current.visible.has(`${Math.round(player.renderPos.x)},${Math.round(player.renderPos.y)}`) || player.id === myPlayerId;
    if (!isPlayerVisible) return;

    const x = player.renderPos.x * TILE_SIZE;
    const y = player.renderPos.y * TILE_SIZE - ENTITY_LIFT;

    // Map class -> sheet key directly. assetImages[key] is null until that sheet
    // loads, and the `if (playerSprite)` guard below skips drawing until then, so
    // a known class never flashes as the warrior fallback during load.
    const CLASS_KEYS = { warrior: 'warrior', mage: 'mage', rogue: 'rogue', huntress: 'huntress' };
    const playerSprite = assetImages[CLASS_KEYS[player.class_type] || 'warrior'];

    if (playerSprite) {
      // Note: Currently all armors share row 11 in the sprite sheet. If specific
      // per-armor rows are added to items.png later, map player.armor_type here.

      ctx.save();

      if (player.fadeAlpha != null && player.fadeAlpha < 1) {
        ctx.globalAlpha = player.fadeAlpha;
      }

      const RUN_FRAMES    = [2, 3, 4, 5, 6, 7];
      const IDLE_FRAMES   = [0, 0, 0, 1, 0, 0, 1, 1];
      const ATTACK_FRAMES = [13, 14, 15, 0];
      const DIE_FRAMES    = [8, 9, 10, 11, 12, 11];
      const OPERATE_FRAMES = [16, 17, 16, 17];
      const READ_FRAMES = [19, 20, 20, 20, 20, 20, 20, 20, 20, 19];

      const now = performance.now();
      const anim = (playerAnimRef && playerAnimRef.current[player.id]) || {};
      const isAttacking = !player.is_downed && anim.attackUntil && now < anim.attackUntil;
      const isOperating = !player.is_downed && !isAttacking && anim.operateUntil && now < anim.operateUntil;
      const isReading = !player.is_downed && !isAttacking && !isOperating && anim.readUntil && now < anim.readUntil;
      const isFlashing = anim.flashUntil && now < anim.flashUntil;

      const isMoving = !player.is_downed && !isAttacking && !isOperating && !isReading && player.targetPos && (
        Math.abs(player.targetPos.x - player.renderPos.x) > 0.05 ||
        Math.abs(player.targetPos.y - player.renderPos.y) > 0.05
      );

      let frameIndex;
      if (player.is_downed) {
        const elapsed = now - (player.deathStart || now);
        const fi = Math.min(Math.floor(elapsed / 50), DIE_FRAMES.length - 1);
        frameIndex = DIE_FRAMES[fi];
      } else if (isAttacking) {
        const elapsed = now - (anim.attackUntil - PLAYER_ATTACK_DURATION);
        const fi = Math.min(Math.floor(elapsed / (PLAYER_ATTACK_DURATION / ATTACK_FRAMES.length)), ATTACK_FRAMES.length - 1);
        frameIndex = ATTACK_FRAMES[fi];
      } else if (isOperating) {
        const elapsed = now - (anim.operateUntil - PLAYER_OPERATE_DURATION);
        const fi = Math.min(Math.floor(elapsed / (PLAYER_OPERATE_DURATION / OPERATE_FRAMES.length)), OPERATE_FRAMES.length - 1);
        frameIndex = OPERATE_FRAMES[fi];
      } else if (isReading) {
        const elapsed = now - (anim.readUntil - PLAYER_READ_DURATION);
        const fi = Math.min(Math.floor(elapsed / (PLAYER_READ_DURATION / READ_FRAMES.length)), READ_FRAMES.length - 1);
        frameIndex = READ_FRAMES[fi];
      } else if (isMoving) {
        frameIndex = RUN_FRAMES[Math.floor(now / 50) % RUN_FRAMES.length];
      } else {
        frameIndex = IDLE_FRAMES[Math.floor(now / 1000) % IDLE_FRAMES.length];
      }

      const sx = frameIndex * 12;
      const sWidth = 12;
      const dWidth = sWidth * TILE_SCALE;
      const xOffset = (TILE_SIZE - dWidth) / 2;
      const FRAME_H = TILE_SIZE / TILE_SCALE;

      if (player.flipX) {
        ctx.translate(x + TILE_SIZE - xOffset, y);
        ctx.scale(-1, 1);
        ctx.drawImage(playerSprite, sx, 0, sWidth, FRAME_H, 0, 0, dWidth, TILE_SIZE);
        if (isFlashing) drawWhiteSilhouette(ctx, playerSprite, sx, 0, sWidth, FRAME_H, 0, 0, dWidth, TILE_SIZE);
      } else {
        ctx.drawImage(playerSprite, sx, 0, sWidth, FRAME_H, x + xOffset, y, dWidth, TILE_SIZE);
        if (isFlashing) drawWhiteSilhouette(ctx, playerSprite, sx, 0, sWidth, FRAME_H, x + xOffset, y, dWidth, TILE_SIZE);
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
    if (totalShield > 0) {
      drawShieldHalo(ctx, x + TILE_SIZE / 2, y, totalShield, player.fadeAlpha ?? 1);
    }
  });
}
