import { useEffect } from 'react';
import { TILE_SIZE, MOVE_DURATION, CAMERA_LERP } from '../constants';
import { DEST_TILE_SIZE } from './sewers/constants';
import { buildWaterClipPath, drawWaterBackground, getWaterTextureForDepth } from './sewers/draw';
import { drawGrid, drawGridCaps } from './draw/grid';
import { drawCustomTiles } from './draw/customTiles';
import { drawTerrainFeatures } from './draw/terrainFeatures';
import { drawItems } from './draw/items';
import { drawMobs } from './draw/mobs';
import { drawPlayers } from './draw/players';
import { advanceAndDrawProjectiles } from './draw/projectiles';
import { advanceAndDrawMagicMissiles } from './draw/magicMissile';
import { advanceAndDrawParticles } from './draw/particles';
import { advanceAndDrawCheckedCells } from './draw/searchEffects';
import { drawWarnedTiles } from './draw/warnedTiles';
import { advanceAndDrawFloatingText } from './draw/floatingText';
import { drawTransmuting } from './draw/transmuting';
import { advanceAndDrawFlares } from './draw/flare';
import { advanceAndDrawSpellSprites } from './draw/spellSprite';
import { advanceAndDrawLightning } from './draw/lightning';
import { advanceAndDrawShieldHalos } from './draw/shieldHalo';
import { advanceAndDrawStateEffects } from './draw/states';
import { advanceAndDrawSurprises } from './draw/surprise';
import { advanceAndDrawScreenShake } from './draw/screenShake';
import { advanceAndDrawBeams } from './draw/beam';
import { advanceAndDrawBlobAreas } from './draw/blobArea';
import { drawCharHealth } from './draw/charHealth';
import { drawTargetHealthIndicator } from './draw/targetHealthIndicator';
import { drawTargetedCell } from './draw/targetedCell';

export default function useGameRenderer({
  canvasRef,
  grid,
  myPlayerId,
  depth,
  assetImages,
  entitiesRef,
  visionRef,
  openDoorsRef,
  projectilesRef,
  trapsRef,
  customTilesRef,
  mobAnimRef,
  dyingMobsRef,
  playerAnimRef,
  particlesRef,
  searchEffectsRef,
  floatingTextRef,
  screenFlashRef,
  warnedTilesRef,
  myPlayerIdRef,
  panOffsetRef,
  cameraLerpRef,
  zoomRef,
  isRefocusingRef,
  isDraggingRef,
  setCamera,
  transmuteEffectsRef,
  flareEffectsRef,
  spellSpriteEffectsRef,
  lightningRef,
  shieldHaloRef,
  stateEffectsRef,
  magicMissileRef,
  surpriseRef,
  selectedEnemyIdRef,
  hoveredCellRef,
  screenShakeRef,
  beamRef,
  blobAreasRef,
}) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    const waterClipPath = buildWaterClipPath(grid);
    const waterTex = getWaterTextureForDepth(depth, assetImages.waterFrames);
    const gridBounds = {
      x: 0,
      y: 0,
      w: (grid[0]?.length ?? 0) * DEST_TILE_SIZE,
      h: grid.length * DEST_TILE_SIZE,
    };

    const updateAnimations = () => {
      const now = performance.now();
      const allEntities = [
        ...Object.values(entitiesRef.current.players),
        ...Object.values(entitiesRef.current.mobs),
      ];
      allEntities.forEach(entity => {
        if (entity.targetPos && entity.animStartTime != null && entity.animStartPos) {
          // Linear (constant-velocity) interpolation so multi-tile travel glides without the
          // per-tile deceleration micro-stop that easeOut produced at each boundary.
          const t = Math.min((now - entity.animStartTime) / MOVE_DURATION, 1.0);
          entity.renderPos.x = entity.animStartPos.x + (entity.targetPos.x - entity.animStartPos.x) * t;
          entity.renderPos.y = entity.animStartPos.y + (entity.targetPos.y - entity.animStartPos.y) * t;
        }
      });
    };

    const render = () => {
      if (grid.length === 0) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.imageSmoothingEnabled = false;
      updateAnimations();

      const rect = canvas.getBoundingClientRect();
      const lw = rect.width, lh = rect.height;

      if (isRefocusingRef.current) {
        panOffsetRef.current.x += (0 - panOffsetRef.current.x) * CAMERA_LERP;
        panOffsetRef.current.y += (0 - panOffsetRef.current.y) * CAMERA_LERP;
        if (Math.abs(panOffsetRef.current.x) < 0.5 && Math.abs(panOffsetRef.current.y) < 0.5) {
          panOffsetRef.current = { x: 0, y: 0 };
          isRefocusingRef.current = false;
        }
      }

      let cameraX = 0;
      let cameraY = 0;
      const myPlayer = entitiesRef.current.players[myPlayerIdRef.current];

      if (myPlayer) {
        cameraX = myPlayer.renderPos.x * TILE_SIZE - lw / 2 + TILE_SIZE / 2 + panOffsetRef.current.x;
        cameraY = myPlayer.renderPos.y * TILE_SIZE - lh / 2 + TILE_SIZE / 2 + panOffsetRef.current.y;

        const gridCols = grid[0]?.length ?? 0;
        const gridRows = grid.length;
        const z = zoomRef.current;
        const PAN_BORDER = 3;
        const halfW = (PAN_BORDER * (lw / 2 - TILE_SIZE / 2)) / z;
        const halfH = (PAN_BORDER * (lh / 2 - TILE_SIZE / 2)) / z;
        cameraX = Math.max(-halfW, Math.min(cameraX, gridCols * TILE_SIZE - lw / z + halfW));
        cameraY = Math.max(-halfH, Math.min(cameraY, gridRows * TILE_SIZE - lh / z + halfH));

        panOffsetRef.current.x = cameraX - (myPlayer.renderPos.x * TILE_SIZE - lw / 2 + TILE_SIZE / 2);
        panOffsetRef.current.y = cameraY - (myPlayer.renderPos.y * TILE_SIZE - lh / 2 + TILE_SIZE / 2);

        if (isDraggingRef.current) {
          cameraLerpRef.current.x = cameraX;
          cameraLerpRef.current.y = cameraY;
        } else {
          cameraLerpRef.current.x += (cameraX - cameraLerpRef.current.x) * CAMERA_LERP;
          cameraLerpRef.current.y += (cameraY - cameraLerpRef.current.y) * CAMERA_LERP;
        }
      }

      setCamera({ x: cameraLerpRef.current.x, y: cameraLerpRef.current.y });

      ctx.save();
      ctx.scale(canvas.width / lw, canvas.height / lh);
      const z = zoomRef.current;
      ctx.translate(lw / 2, lh / 2);
      ctx.scale(z, z);
      ctx.translate(-lw / 2, -lh / 2);
      ctx.translate(-cameraLerpRef.current.x, -cameraLerpRef.current.y);
      advanceAndDrawScreenShake(ctx, { shakeRef: screenShakeRef });

      drawWaterBackground(ctx, waterTex, waterClipPath, gridBounds, performance.now());
      drawGrid(ctx, { grid, depth, assetImages, visionRef, openDoorsRef });
      drawCustomTiles(ctx, { customTiles: customTilesRef.current, assetImages, visionRef });
      drawTerrainFeatures(ctx, assetImages.terrainFeatures, trapsRef.current, grid, visionRef);
      advanceAndDrawBlobAreas(ctx, { blobAreasRef, visionRef });
      if (warnedTilesRef) drawWarnedTiles(ctx, { ref: warnedTilesRef });
      drawItems(ctx, { entitiesRef, visionRef, assetImages });
      drawMobs(ctx, { entitiesRef, visionRef, assetImages, mobAnimRef, dyingMobsRef });
      drawCharHealth(ctx, { entitiesRef, visionRef });
      drawTargetHealthIndicator(ctx, { entitiesRef, visionRef, selectedEnemyIdRef });
      drawPlayers(ctx, { entitiesRef, visionRef, assetImages, playerAnimRef, myPlayerId });
      drawGridCaps(ctx, { grid, depth, assetImages, visionRef });
      drawTargetedCell(ctx, { hoveredCellRef, assetImages });
      advanceAndDrawCheckedCells(ctx, { ref: searchEffectsRef });
      advanceAndDrawParticles(ctx, { particlesRef });
      advanceAndDrawFlares(ctx, { flareRef: flareEffectsRef });
      advanceAndDrawSpellSprites(ctx, { spellSpriteRef: spellSpriteEffectsRef, assetImages });
      advanceAndDrawFloatingText(ctx, { floatingTextRef });
      advanceAndDrawSurprises(ctx, { surpriseRef });
      advanceAndDrawShieldHalos(ctx, { haloRef: shieldHaloRef });
      advanceAndDrawStateEffects(ctx, { stateEffectsRef });
      drawTransmuting(ctx, { transmuteEffectsRef, assetImages });
      advanceAndDrawProjectiles(ctx, { projectilesRef, assetImages });
      advanceAndDrawMagicMissiles(ctx, magicMissileRef);
      advanceAndDrawBeams(ctx, { beamRef, assetImages });
      advanceAndDrawLightning(ctx, { lightningRef });

      ctx.restore();

      // Retribution screen flash: full-screen white overlay that fades in screen space.
      if (screenFlashRef?.current?.until > performance.now()) {
        const remaining = screenFlashRef.current.until - performance.now();
        const alpha = Math.min(remaining / 100, 1) * 0.5;
        ctx.fillStyle = `rgba(255,255,255,${alpha})`;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }

      // Vision loss: when the local player is dead, dim the screen but keep the
      // world visible so they can still spectate (alpha ramps 0 -> 0.55 over 2s).
      const me = entitiesRef.current.players[myPlayerIdRef.current];
      if (me && me.is_downed) {
        const elapsed = performance.now() - (me.deathStart || performance.now());
        const alpha = Math.min(elapsed / 2000, 1) * 0.55;
        ctx.fillStyle = `rgba(0, 0, 0, ${alpha})`;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationFrameId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grid, myPlayerId, assetImages, depth]);
}
