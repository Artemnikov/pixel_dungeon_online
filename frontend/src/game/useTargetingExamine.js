import { useState, useRef, useEffect } from 'react';
import { describeCell } from '../input/describeCell';

const TARGETED_ABILITIES = ['heroic_leap', 'smoke_bomb', 'death_mark'];

export default function useTargetingExamine({
  entitiesRef, visionRef, myPlayerIdRef, gridRef,
  equippedItems, send, trapsRef,
}) {
  const [targetingMode, setTargetingMode] = useState(false);
  const [examineMode, setExamineMode] = useState(false);
  const [inspectInfo, setInspectInfo] = useState(null);

  const targetingModeRef = useRef(false);
  const examineModeRef = useRef(false);
  const onTargetTapRef = useRef(null);
  const onExamineTapRef = useRef(null);

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
      trapsRef,
    });
    setExamineMode(false);
    if (!info) { clearInspect(); return; }
    // Keep the legacy name/sub for the inline popup fallback, plus the full
    // structured payload so WndInfoCell can dispatch to the right info window.
    setInspectInfo({
      name: info.name,
      sub: info.sub,
      anchor: info.anchor,
      cellInfo: info,
    });
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

  // Auto-dismiss the inspect modal if its anchor mob dies or leaves vision.
  useEffect(() => {
    if (!inspectInfo || inspectInfo.anchor?.type !== 'mob') return;
    const id = inspectInfo.anchor.id;
    const check = () => {
      const mob = entitiesRef.current.mobs[id];
      if (!mob) { setInspectInfo(null); return; }
      const mx = Math.round(mob.renderPos.x), my = Math.round(mob.renderPos.y);
      if (!visionRef.current.visible.has(`${mx},${my}`)) setInspectInfo(null);
    };
    const iv = setInterval(check, 200);
    return () => clearInterval(iv);
  }, [inspectInfo]); // eslint-disable-line react-hooks/exhaustive-deps

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
    clearInspect,
    resolveTargetingTap,
    resolveExamineTap,
    handleExamineOrReveal,
    sendUseAbility,
    sendUseComboMove,
    sendPrepStrike,
  };
}
