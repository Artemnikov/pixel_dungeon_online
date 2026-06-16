import { useState, useRef, useEffect } from 'react';
import { TILE_SIZE } from '../constants';
import { describeCell } from '../input/describeCell';

const TARGETED_ABILITIES = ['heroic_leap', 'smoke_bomb', 'death_mark'];

// Live viewport position of an inspect-popup anchor (a world tile, or a mob we follow
// by its renderPos). Returns { left, top, below } or null when the popup should hide
// (mob gone/out of view, or the anchor panned off the visible canvas). Pure so it can
// be called from the per-frame rAF loop without reading refs during render.
function inspectScreenPos(canvas, cam, zoom, anchor, mobs, visible) {
  if (!canvas || !anchor) return null;
  let wx, wyTop, wyBottom;
  if (anchor.type === 'mob') {
    const mob = mobs[anchor.id];
    if (!mob) return null;
    const mx = Math.round(mob.renderPos.x), my = Math.round(mob.renderPos.y);
    if (!visible.has(`${mx},${my}`)) return null;
    wx = (mob.renderPos.x + 0.5) * TILE_SIZE;
    wyTop = mob.renderPos.y * TILE_SIZE;
    wyBottom = (mob.renderPos.y + 1) * TILE_SIZE;
  } else {
    wx = (anchor.x + 0.5) * TILE_SIZE;
    wyTop = anchor.y * TILE_SIZE;
    wyBottom = (anchor.y + 1) * TILE_SIZE;
  }
  const rect = canvas.getBoundingClientRect();
  const cw = rect.width, ch = rect.height;
  const left = rect.left + (wx - cam.x - cw / 2) * zoom + cw / 2;
  const topY = rect.top + (wyTop - cam.y - ch / 2) * zoom + ch / 2;
  const bottomY = rect.top + (wyBottom - cam.y - ch / 2) * zoom + ch / 2;
  if (left < rect.left || left > rect.right || bottomY < rect.top || topY > rect.bottom) return null;
  const below = topY < rect.top + 70;
  return { left, top: below ? bottomY + 6 : topY - 6, below };
}

export default function useTargetingExamine({
  canvasRef, cameraLerpRef, zoomRef,
  entitiesRef, visionRef, myPlayerIdRef, gridRef,
  equippedItems, send,
}) {
  const [targetingMode, setTargetingMode] = useState(false);
  const [examineMode, setExamineMode] = useState(false);
  const [inspectInfo, setInspectInfo] = useState(null);

  const targetingModeRef = useRef(false);
  const examineModeRef = useRef(false);
  const onTargetTapRef = useRef(null);
  const onExamineTapRef = useRef(null);
  const inspectPopupRef = useRef(null);
  const inspectSubRef = useRef(null);

  useEffect(() => { targetingModeRef.current = targetingMode; }, [targetingMode]);
  useEffect(() => { examineModeRef.current = examineMode; }, [examineMode]);

  const clearInspect = () => setInspectInfo(null);

  const resolveTargetingTap = (tileX, tileY) => {
    const tm = targetingModeRef.current;
    console.log('resolveTargetingTap', { tm, tileX, tileY });
    if (tm && typeof tm === 'object' && tm.ability) {
      send({ type: 'USE_ARMOR_ABILITY', ability: tm.ability, target_x: tileX, target_y: tileY });
      setTargetingMode(false);
      return;
    }
    if (tm && typeof tm === 'object' && tm.comboMove) {
      send({ type: 'USE_COMBO_MOVE', move: tm.comboMove, target_x: tileX, target_y: tileY });
      setTargetingMode(false);
      return;
    }
    if (tm && typeof tm === 'object' && tm.prepStrike) {
      send({ type: 'PREPARATION_STRIKE', target_x: tileX, target_y: tileY });
      setTargetingMode(false);
      return;
    }
    if (tm && typeof tm === 'object' && tm.action) {
      console.log('Sending EXECUTE_ITEM_ACTION', { item_id: tm.itemId, action: tm.action, target_x: tileX, target_y: tileY });
      send({ type: 'EXECUTE_ITEM_ACTION', item_id: tm.itemId, action: tm.action, target_x: tileX, target_y: tileY });
      setTargetingMode(false);
      return;
    }
    const weaponId = typeof tm === 'string' ? tm : equippedItems.weapon?.id;
    if (weaponId) {
      send({ type: 'RANGED_ATTACK', item_id: weaponId, target_x: tileX, target_y: tileY });
      setTargetingMode(typeof tm === 'string' ? false : true);
    }
  };

  const resolveExamineTap = (tileX, tileY) => {
    const info = describeCell({
      tileX, tileY, gridRef, entitiesRef, visionRef,
      myPlayerId: myPlayerIdRef.current,
    });
    setExamineMode(false);
    if (!info) { clearInspect(); return; }
    setInspectInfo({ name: info.name, sub: info.sub, anchor: info.anchor });
  };

  const handleExamineOrReveal = () => {
    clearInspect();
    if (examineModeRef.current) {
      setExamineMode(false);
      send({ type: 'SEARCH' });
    } else {
      setTargetingMode(false);
      setExamineMode(true);
    }
  };

  useEffect(() => { onTargetTapRef.current = resolveTargetingTap; });
  useEffect(() => { onExamineTapRef.current = resolveExamineTap; });

  // While a popup is open, drive it every frame: reposition from the live camera + anchor
  // (so it sticks to its tile/mob), refresh a mob's HP, and handle auto-dismiss.
  useEffect(() => {
    if (!inspectInfo) return;
    const anchor = inspectInfo.anchor;
    const DISMISS_MS = 3000;
    let raf;
    let lastSub;
    let lastActive = null;
    const tick = () => {
      const now = performance.now();
      if (lastActive == null) lastActive = now;

      let sub = inspectInfo.sub;
      if (anchor.type === 'mob') {
        const mob = entitiesRef.current.mobs[anchor.id];
        if (!mob) { setInspectInfo(null); return; }
        sub = mob.hp != null && mob.max_hp != null ? `HP ${mob.hp}/${mob.max_hp}` : null;
      }
      if (sub !== lastSub) { lastSub = sub; lastActive = now; }
      if (now - lastActive > DISMISS_MS) { setInspectInfo(null); return; }

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
  }, [inspectInfo]); // eslint-disable-line react-hooks/exhaustive-deps -- canvasRef/cameraLerpRef/zoomRef/entitiesRef/visionRef are stable React refs

  const sendUseAbility = (ability) => {
    if (TARGETED_ABILITIES.includes(ability)) {
      setTargetingMode({ ability });
      return;
    }
    send({ type: 'USE_ARMOR_ABILITY', ability });
  };

  const sendUseComboMove = (move) => {
    if (move === 'parry') {
      send({ type: 'USE_COMBO_MOVE', move });
      return;
    }
    setTargetingMode({ comboMove: move });
  };

  const sendPrepStrike = () => setTargetingMode({ prepStrike: true });

  return {
    targetingMode, setTargetingMode,
    examineMode, setExamineMode,
    inspectInfo,
    targetingModeRef,
    examineModeRef,
    onTargetTapRef,
    onExamineTapRef,
    inspectPopupRef,
    inspectSubRef,
    clearInspect,
    resolveTargetingTap,
    resolveExamineTap,
    handleExamineOrReveal,
    sendUseAbility,
    sendUseComboMove,
    sendPrepStrike,
  };
}
