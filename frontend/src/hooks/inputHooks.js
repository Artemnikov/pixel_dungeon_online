import { useCallback } from 'react';
import { TILE_SIZE } from '../constants';
import useKeyboardControls from '../input/useKeyboardControls';
import useCanvasControls from '../input/useCanvasControls';
import useScaledCursor from '../input/useScaledCursor';
import { resolveTapAction } from '../input/resolveTap';
import * as movementPredictor from '../net/movementPredictor';
import { defaultMoveResultDispatcher } from '../net/movement/MoveResultDispatcher';
import { startLocalPlayerMeleeAnim } from '../net/events/combat';
import { isFloorFadeActive } from '../rendering/floorTransition';
import AudioManager from '../audio/AudioManager';

export default function useInputHooks({
  gameState, showTutorial, loreOverlay, myStats,
  gridRef, entitiesRef, myPlayerIdRef,
    socketRef, canvasRef, zoomRef, cameraLerpRef,
  isDraggingRef, isRefocusingRef, isPinchingRef,
  isCameraDetachedRef, detachedCameraRef, floorFadeRef,
  panOffsetRef, onOpenAlchemyRef, hoveredCellRef,
  playerAnimRef,
  targeting, modals, talent,
  handleToolbarClick, handleToolbarDoubleClick,
  handleEscape, quickslot, itemsById,
  send, emergencyHealItem, drinkEmergencyHeal,
  viewport,
}) {
  const { hasDraggedRef } = useCanvasControls({
    enabled: gameState === 'PLAYING',
    canvasRef, socketRef,
    panOffsetRef, zoomRef, cameraLerpRef,
    isDraggingRef, isRefocusingRef, isPinchingRef,
    isCameraDetachedRef, detachedCameraRef,
    targetingModeRef: targeting.targetingModeRef,
    onTargetTapRef: targeting.onTargetTapRef,
    examineModeRef: targeting.examineModeRef,
    onExamineTapRef: targeting.onExamineTapRef,
    entitiesRef, myPlayerIdRef,
    hoveredCellRef,
    floorFadeRef,
    gridRef, onOpenAlchemyRef,
    playerAnimRef,
  });

  useKeyboardControls({
    socketRef, inventory: [], setShowInventory: modals.setShowInventory,
    handleToolbarClick, handleToolbarDoubleClick,
    onExamineOrReveal: targeting.handleExamineOrReveal, onCancelModes: handleEscape,
    triggerWait: () => send({ type: 'WAIT' }),
    isRefocusingRef, isDraggingRef, floorFadeRef,
    quickslot, itemsById,
    gameMenuOpenRef: modals.gameMenuOpenRef,
    showItemBrowserRef: modals.showItemBrowserRef,
    onOpenTalents: () => {
      if (gameState !== 'PLAYING' || showTutorial || loreOverlay) return;
      if (talent.showHeroWindow) {
        talent.closeHero();
      } else {
        talent.openHero(1);
      }
    },
    onOpenItemBrowser: () => {
      if (!myStats.isAdmin) return;
      if (!modals.showItemBrowser) modals.setShowItemBrowser(true);
    },
    onCloseItemBrowser: () => {
      modals.setShowItemBrowser(false);
    },
    gridRef, entitiesRef, myPlayerIdRef,
    onOpenAlchemy: modals.onOpenAlchemy,
    onOpenAlchemyRef,
    playerAnimRef,
    emergencyDrinkItem: emergencyHealItem,
    onEmergencyDrink: drinkEmergencyHeal,
  });

  const resolveTapAtScreen = useCallback((clientX, clientY) => {
    if (!canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = clientX - rect.left;
    const clickY = clientY - rect.top;

    const cw = rect.width, ch = rect.height;
    const z = zoomRef.current;
    const worldX = (clickX - cw / 2) / z + cameraLerpRef.current.x + cw / 2;
    const worldY = (clickY - ch / 2) / z + cameraLerpRef.current.y + ch / 2;

    const tileX = Math.floor(worldX / TILE_SIZE);
    const tileY = Math.floor(worldY / TILE_SIZE);

    if (targeting.examineModeRef.current) {
      targeting.resolveExamineTap(tileX, tileY);
      return;
    }

    targeting.clearInspect();

    if (targeting.targetingModeRef.current) {
      targeting.resolveTargetingTap(tileX, tileY);
      return;
    }

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      const myPlayer = entitiesRef.current.players[myPlayerIdRef.current];
      const playerTile = myPlayer ? (myPlayer.targetPos || myPlayer.renderPos) : null;
      const action = resolveTapAction({ tileX, tileY, playerTile, mobs: entitiesRef.current.mobs, grid: gridRef.current, playerFaction: myPlayer?.faction });
      if (action.type === 'OPEN_ALCHEMY') {
        onOpenAlchemyRef.current();
        return;
      }
      if (action.type === 'MOVE' || action.type === 'PATH_STEPS') isRefocusingRef.current = true;
      // One-shot actions (WAIT, NPC_INTERACT) and far-tap PATH_STEPS go out as
      // the plain message. Adjacent-tap MOVE is NOT sent raw: it goes through
      // the same paced, seq-acked MOVE_STEP machinery as the keyboard, so the
      // server can't race ahead of the client animation (which caused the
      // position to snap/teleport back).
      if (!myPlayer || action.type === 'WAIT' || action.type === 'NPC_INTERACT' || action.type === 'PATH_STEPS') {
        socketRef.current.send(JSON.stringify(action));
      }
      if (myPlayer && action.type === 'MOVE') {
        const dirMap = { UP: [0,-1], DOWN: [0,1], LEFT: [-1,0], RIGHT: [1,0], UP_LEFT: [-1,-1], UP_RIGHT: [1,-1], DOWN_LEFT: [-1,1], DOWN_RIGHT: [1,1] };
        const d = dirMap[action.direction];
        if (!d) return;
        const res = movementPredictor.predictMove(myPlayer, d[0], d[1], myPlayerIdRef.current, gridRef.current, entitiesRef.current);
        defaultMoveResultDispatcher.dispatch(res, {
          myPlayer,
          playerAnimRef,
          onOpenAlchemyRef,
          onMeleeAttack: () => startLocalPlayerMeleeAnim(myPlayer, playerAnimRef, AudioManager),
          socket: socketRef.current,
          dx: d[0],
          dy: d[1],
        });
      } else if (myPlayer && action.type === 'PATH_STEPS' && action.steps.length > 0) {
        // Server-paced auto-walk: preview the first step for animation only.
        // No seq'd MOVE_STEP is dispatched (there's no client-side path pump),
        // so no stray zero-delta steps reach the server.
        const preview = movementPredictor.startPath(myPlayer, action.steps.map(s => ({ dx: s[0], dy: s[1] })), myPlayerIdRef.current, gridRef.current, entitiesRef.current);
        // Keep the immediate melee feedback when the path's first step bumps a
        // mob: the server bump-attacks once the paced walk arrives, but the
        // local swing should start now (mirrors the moved-tap bump outcome).
        if (preview?.kind === 'bumped') {
          const primary = movementPredictor.primaryBlocker(preview.blockers);
          if (primary?.action === 'melee-attack') startLocalPlayerMeleeAnim(myPlayer, playerAnimRef, AudioManager);
        }
      }
    }
  }, [targeting, onOpenAlchemyRef, isRefocusingRef, canvasRef, socketRef, zoomRef, cameraLerpRef, entitiesRef, myPlayerIdRef, gridRef, playerAnimRef]);

  const handleCanvasClick = useCallback((e) => {
    if (isFloorFadeActive(floorFadeRef)) return;
    if (hasDraggedRef.current) return;
    resolveTapAtScreen(e.clientX, e.clientY);
  }, [hasDraggedRef, floorFadeRef, resolveTapAtScreen]);

  const isMac = /Macintosh|MacIntel|MacPPC|Mac68K/.test(navigator.userAgent);
  const { mouseCursorVal, controllerCursorVal } = useScaledCursor(viewport.width, viewport.height, viewport.dpr, isMac);

  return { hasDraggedRef, handleCanvasClick, isMac, mouseCursorVal, controllerCursorVal };
}
