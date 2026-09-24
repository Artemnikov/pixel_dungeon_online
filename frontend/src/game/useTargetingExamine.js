import { useCallback, useState, useRef, useEffect } from 'react';
import { describeCell } from '../input/describeCell';
import { playLocalPlayerSearch } from '../rendering/draw/searchEffects';
import { WeaponSkillRegistry } from '../data/weaponSkills';
import { defaultTargetingTapDispatcher } from './targeting/TargetingTapDispatcher';

const TARGETED_ABILITIES = [
  'heroic_leap',
  'smoke_bomb',
  'death_mark',
  'challenge',
  'elemental_strike',
  'power_of_many',
];

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
    defaultTargetingTapDispatcher.dispatch(targetingModeRef.current, tileX, tileY, {
      send,
      equippedItems,
      entitiesRef,
      selectedEnemyIdRef,
      setTargetingMode,
    });
  }, [send, equippedItems, entitiesRef, selectedEnemyIdRef, setTargetingMode]);

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
  const sendDuelistFinisher = () => {
    const weapon = equippedItems?.weapon;
    const skill = WeaponSkillRegistry.getSkillForWeapon(weapon);
    if (skill && !skill.requiresTarget) {
      send({ type: 'DUELIST_FINISHER' });
      setTargetingMode(false);
      return;
    }
    if (targetingModeRef.current && typeof targetingModeRef.current === 'object' && targetingModeRef.current.duelistFinisher) {
      setTargetingMode(false);
      return;
    }
    setTargetingMode({ duelistFinisher: true, itemId: weapon?.id });
  };
  const sendCastSpell = (spell) => send({ type: 'CAST_CLERIC_SPELL', spell });
  const sendSetClericQuickSpell = (spell) => send({ type: 'SET_CLERIC_QUICK_SPELL', spell });

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
    sendDuelistFinisher,
    sendCastSpell,
    sendSetClericQuickSpell,
  };
}
