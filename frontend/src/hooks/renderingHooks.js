import { useEffect, useMemo, useRef } from 'react';
import useGameRenderer from '../rendering/useGameRenderer';
import { inspectScreenPos } from '../rendering/inspectScreenPos';

export default function useRenderingHooks({
  canvasRef, inspectPopupRef, inspectSubRef,
  grid, myPlayerId, depth,
  floorFadeRef, assetImages,
  entitiesRef, visionRef, openDoorsRef, projectilesRef,
  customTilesRef, customWallsRef, torchesRef,
  mobAnimRef, dyingMobsRef, playerAnimRef, particlesRef, searchEffectsRef,
  floatingTextRef, screenFlashRef, screenShakeRef, myPlayerIdRef,
  warnedTilesRef, transmuteEffectsRef, flareEffectsRef, spellSpriteEffectsRef,
  lightningRef, shieldHaloRef, stateEffectsRef, magicMissileRef,
  staffAmbientRef, surpriseRef, flyingItemsRef, selectedEnemyIdRef,
  hoveredCellRef, beamRef, blobAreasRef,
  panOffsetRef, cameraLerpRef, zoomRef,
  isRefocusingRef, isDraggingRef, isCameraDetachedRef, detachedCameraRef,
  setCamera,
  targeting,
  quickslot, itemsById,
}) {
  useGameRenderer({
    canvasRef, grid, myPlayerId, depth, assetImages, floorFadeRef,
    entitiesRef, visionRef, openDoorsRef, projectilesRef,
    customTilesRef, customWallsRef, torchesRef,
    mobAnimRef, dyingMobsRef, playerAnimRef, particlesRef, searchEffectsRef,
    floatingTextRef, screenFlashRef, screenShakeRef, myPlayerIdRef, warnedTilesRef,
    transmuteEffectsRef, flareEffectsRef, spellSpriteEffectsRef, lightningRef,
    shieldHaloRef, stateEffectsRef, magicMissileRef, staffAmbientRef,
    surpriseRef, flyingItemsRef, selectedEnemyIdRef,
    targetingModeRef: targeting.targetingModeRef, hoveredCellRef, beamRef, blobAreasRef,
    panOffsetRef, cameraLerpRef, zoomRef,
    isRefocusingRef, isDraggingRef,
    isCameraDetachedRef, detachedCameraRef,
    setCamera,
  });

  // Destructure targeting values used in JSX
  const {
    examineMode, inspectInfo,
    handleExamineOrReveal,
    sendUseAbility, sendUseComboMove, sendPrepStrike,
    sendDuelistFinisher, sendCastSpell, sendSetClericQuickSpell,
  } = targeting;

  // Drive the inspect popup every frame
  const clearInspectRef = useRef(null);
  useEffect(() => { clearInspectRef.current = targeting.clearInspect; });
  useEffect(() => {
    if (!inspectInfo) return;
    const anchor = inspectInfo.anchor;
    const DISMISS_MS = 3000;
    let raf;
    let lastSub;
    let lastActive = 0;
    let ticked = false;
    const tick = () => {
      const now = performance.now();
      if (!ticked) { lastActive = now; ticked = true; }
      let sub = inspectInfo.sub;
      if (anchor.type === 'mob') {
        const mob = entitiesRef.current.mobs[anchor.id];
        if (!mob) { clearInspectRef.current(); return; }
        sub = mob.hp != null && mob.max_hp != null ? `HP ${mob.hp}/${mob.max_hp}` : null;
      }
      if (sub !== lastSub) { lastSub = sub; lastActive = now; }
      if (now - lastActive > DISMISS_MS) { clearInspectRef.current(); return; }

      const el = inspectPopupRef.current;
      if (el) {
        const pos = inspectScreenPos(
          canvasRef.current, cameraLerpRef.current, zoomRef.current,
          anchor, entitiesRef.current.mobs, visionRef.current.visible,
        );
        if (pos) {
          el.style.display = '';
          el.style.left = `${pos.left}px`;
          el.style.top = `${pos.top}px`;
          el.style.transform = pos.below ? 'translate(-50%, 0)' : 'translate(-50%, -100%)';
          const subEl = inspectSubRef.current;
          if (subEl) {
            subEl.textContent = sub || '';
            subEl.style.display = sub ? '' : 'none';
          }
        } else {
          el.style.display = 'none';
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inspectInfo]);

  const toolbarItems = useMemo(() => Array.from({ length: 6 }).map((_, i) => {
    const slot = quickslot?.slots?.[i];
    if (!slot) return null;
    if (slot.item_id) return itemsById[slot.item_id] || null;
    if (slot.is_placeholder && slot.placeholder_kind) {
      return { id: null, kind: slot.placeholder_kind, name: '', type: null, is_placeholder: true };
    }
    return null;
  }), [quickslot, itemsById]);

  return {
    examineMode, inspectInfo,
    handleExamineOrReveal,
    sendUseAbility, sendUseComboMove, sendPrepStrike,
    sendDuelistFinisher, sendCastSpell, sendSetClericQuickSpell,
    toolbarItems,
  };
}
