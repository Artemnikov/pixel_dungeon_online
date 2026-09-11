import { useCallback } from 'react';
import { clearResumeBundle } from '../game/useResumeBundle';

export function useGameLifecycle({
  socketRef, entitiesRef, visionRef, myPlayerIdRef, wasDownedRef,
  setMyPlayerId, setGrid, setMyStats, setBossInfo, setBossFightActive,
  setBossBleeding, setBossLurking, setShowBossSlainBanner, setBossSlainData,
  setInventory, setConnectionStatus, setScoreBreakdown, setCanResurrect,
  setIsVictory, setRespawnsUsed, setMaxRespawns, setLootDropped,
  resetMetamorph, setGameState, setGameMenuOpen,
}) {
  const resetForRestart = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.close();
    }
    entitiesRef.current = { players: {}, mobs: {}, items: [], traps: [], plants: [] };
    visionRef.current = { visible: new Set(), discovered: new Set() };
    myPlayerIdRef.current = null;
    wasDownedRef.current = false;
    setMyPlayerId(null);
    setGrid([]);
    setMyStats({ hp: 0, maxHp: 10, name: '' });
    setBossInfo(null);
    setBossFightActive(false);
    setBossBleeding(false);
    setBossLurking(false);
    setShowBossSlainBanner(false);
    setBossSlainData(null);
    setInventory([]);
    setConnectionStatus(null);
    setScoreBreakdown(null);
    setCanResurrect(false);
    setIsVictory(false);
    setRespawnsUsed(0);
    setMaxRespawns(3);
    setLootDropped(false);
    if (resetMetamorph) resetMetamorph();
  }, [resetMetamorph, socketRef, entitiesRef, visionRef, myPlayerIdRef, wasDownedRef, setMyPlayerId, setGrid, setMyStats, setBossInfo, setBossFightActive, setBossBleeding, setBossLurking, setShowBossSlainBanner, setBossSlainData, setInventory, setConnectionStatus, setScoreBreakdown, setCanResurrect, setIsVictory, setRespawnsUsed, setMaxRespawns, setLootDropped]);

  const handleLeaveGame = useCallback(() => {
    clearResumeBundle();
    resetForRestart();
    if (setGameMenuOpen) setGameMenuOpen(false);
    if (setGameState) setGameState('WELCOME');
  }, [resetForRestart, setGameMenuOpen, setGameState]);

  return { resetForRestart, handleLeaveGame };
}

export default useGameLifecycle;
