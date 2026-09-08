import { useCallback, useState, useRef, useEffect } from 'react';
import { describeCell } from '../input/describeCell';
import { playLocalPlayerSearch } from '../rendering/draw/searchEffects';
import { isAttackReady, consumeAttackCooldown } from '../net/events/combat';

const TARGETED_ABILITIES = ['heroic_leap', 'smoke_bomb', 'death_mark'];

export default function useTargetingExamine({
  entitiesRef, visionRef, myPlayerIdRef, gridRef,
  equippedItems, send, selectedEnemyIdRef,
  playerAnimRef, searchEffectsRef,
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

  const clearInspect = useCallback(() => setInspectInfo(null), []);

  const resolveTargetingTap = useCallback((tileX, tileY) => {
    const tm = targetingModeRef.current;
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
      const isCombatAction = tm.action === 'THROW' || tm.action === 'ZAP';
      if (isCombatAction && !isAttackReady()) return;
      if (isCombatAction) consumeAttackCooldown();
      send({ type: 'EXECUTE_ITEM_ACTION', item_id: tm.itemId, action: tm.action, target_x: tileX, target_y: tileY });
      setTargetingMode(false);
      return;
    }
    const weaponId = typeof tm === 'string' ? tm : equippedItems.weapon?.id;
    if (weaponId) {
      if (!isAttackReady()) return;
      consumeAttackCooldown((equippedItems.weapon?.attack_cooldown ?? 1.0) * 1000);
      // If the tapped cell is the locked target's cell, let the server auto-aim
      // (angle around corners) via target_entity_id; SPD QuickSlotButton.autoAim.
      const lockId = selectedEnemyIdRef?.current || null;
      const lock = lockId ? entitiesRef.current.mobs[lockId] : null;
      const onLock = lock && Math.round(lock.renderPos.x) === tileX && Math.round(lock.renderPos.y) === tileY;
      send({ type: 'RANGED_ATTACK', item_id: weaponId, target_x: tileX, target_y: tileY,
             target_entity_id: onLock ? lockId : null });
      setTargetingMode(typeof tm === 'string' ? false : true);
    }
  }, [send, equippedItems, setTargetingMode, entitiesRef, selectedEnemyIdRef]);

  const resolveExamineTap = useCallback((tileX, tileY) => {
    const info = describeCell({
      tileX, tileY, gridRef, entitiesRef, visionRef,
      myPlayerId: myPlayerIdRef.current,
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
  }, [clearInspect, setExamineMode, setInspectInfo, entitiesRef, gridRef, myPlayerIdRef, visionRef]);

  const handleExamineOrReveal = useCallback(() => {
    clearInspect();
    if (examineModeRef.current) {
      setExamineMode(false);
      send({ type: 'SEARCH' });
      playLocalPlayerSearch({
        player: entitiesRef.current.players[myPlayerIdRef.current],
        grid: gridRef.current,
        searchEffectsRef,
        playerAnimRef,
        playerId: myPlayerIdRef.current,
      });
    } else {
      setTargetingMode(false);
      setExamineMode(true);
    }
  }, [clearInspect, send, setExamineMode, setTargetingMode, entitiesRef, myPlayerIdRef, gridRef, playerAnimRef, searchEffectsRef]);

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
