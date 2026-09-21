import { TILE_SIZE, ENTITY_LIFT } from '../../constants';
import { defaultPlayerRenderPipeline } from '../animation/PlayerRenderPipeline';
import { getCharacterDescriptor } from '../characterDescriptors';

export function drawPlayers(ctx, { entitiesRef, visionRef, assetImages, playerAnimRef, myPlayerId, shieldFxRef }) {
  const players = entitiesRef?.current?.players;
  if (!players) return;

  const now = performance.now();
  const visibleTiles = visionRef?.current?.visible;

  Object.values(players).forEach(player => {
    const rx = Math.round(player.renderPos.x);
    const ry = Math.round(player.renderPos.y);
    const isPlayerVisible = (visibleTiles && visibleTiles.has(`${rx},${ry}`)) || player.id === myPlayerId;
    if (!isPlayerVisible) return;

    const x = player.renderPos.x * TILE_SIZE;
    const y = player.renderPos.y * TILE_SIZE - ENTITY_LIFT;
    const deathElapsed = now - (player.deathStart || now);
    const anim = (playerAnimRef && playerAnimRef.current[player.id]) || {};
    const charDesc = getCharacterDescriptor(player.class_type);
    const playerSprite = (assetImages && assetImages[charDesc.assetKey]) || assetImages?.warrior || null;

    defaultPlayerRenderPipeline.render(ctx, {
      player,
      anim,
      now,
      deathElapsed,
      x,
      y,
      myPlayerId,
      playerSprite,
      shieldFxRef,
    });
  });
}
