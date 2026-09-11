import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { TILE_SIZE, TILE_SCALE, MIN_ZOOM, MAX_DPR } from '../constants';
import useAudioUnlock from '../audio/useAudioUnlock';
import useMusicByDepth from '../audio/useMusicByDepth';
import useAssetImages from '../rendering/useAssetImages';
import useGameSocket from '../net/useGameSocket';
import useDebugApi from '../dev/useDebugApi';
import { createShieldFxRef } from '../rendering/draw/shieldHalo';
import { getLoreForDepth } from '../game/loreTexts';
import useModalState from '../game/useModalState';
import useTalents from '../game/talents/useTalents';
import useTargetingExamine from '../game/useTargetingExamine';
import AudioManager from '../audio/AudioManager';
import { useItemActions } from '../handlers/itemActions';
import { useTargetingHandlers } from '../handlers/targetingHandlers';
import { useGameLifecycle } from './useGameLifecycle';
import { windowManager } from '../game/window/WindowManager';
import { RESUME_SESSION_KEY } from '../game/useResumeBundle';

export default function useGameHooks(state) {
  const {
    canvasRef,
    gameState, setGameState, selectedClass,
    difficulty, setDifficulty,
    challenges, gameId,
    playerName, roomPassword, sessionId,
    setConnectionStatus, setShowTutorial,
    setGrid, setMyPlayerId,
    viewport, setViewport,
    setInventory, equippedItems, setEquippedItems,
    belongings, setBelongings, quickslot, setQuickslot,
    myStats, setMyStats, bossInfo, setBossInfo,
    bossFightActive, setBossFightActive, bossBleeding, setBossBleeding,
    depth, setDepth,
    hasAmulet, setHasAmulet,
    bossLurking, setBossLurking,
    setGold, setEnergy, setExitPos,
    ghostQuestGiven, setGhostQuestGiven,
    setShowBossSlainBanner, setBossSlainData,
    setScoreBreakdown, setCanResurrect, setHasAnkh,
    setKeptItems, setIsVictory, setRespawnsUsed, setMaxRespawns,
    setLootDropped, setDeathCause,
    setLoreOverlay,
    setRoomJoinError,
  } = state;

  const bossBleedingEffective = bossBleeding
    || (bossInfo?.name === 'Tengu' && bossInfo.hp * 2 <= bossInfo.maxHp);

  // --- shared refs ---
  const socketRef = useRef(null);
  const gridRef = useRef([]);
  const entitiesRef = useRef({ players: {}, mobs: {}, items: [], traps: [], plants: [] });
  const myPlayerIdRef = useRef(null);
  const projectilesRef = useRef([]);
  const visionRef = useRef({ visible: new Set(), discovered: new Set() });
  const openDoorsRef = useRef(new Set());
  const panOffsetRef = useRef({ x: 0, y: 0 });
  const cameraLerpRef = useRef({ x: 0, y: 0 });
  const TILE_SCREEN = TILE_SIZE * TILE_SCALE;
  const zoomRef = useRef(
    window.innerWidth < TILE_SCREEN * 10
      ? Math.max(MIN_ZOOM, window.innerWidth / (TILE_SCREEN * 10))
      : 1.0
  );
  const isDraggingRef = useRef(false);
  const isRefocusingRef = useRef(false);
  const isPinchingRef = useRef(false);
  const isCameraDetachedRef = useRef(false);
  const detachedCameraRef = useRef({ x: 0, y: 0 });
  const wasDownedRef = useRef(false);
  const mobAnimRef = useRef({});
  const dyingMobsRef = useRef({});
  const playerAnimRef = useRef({});
  const particlesRef = useRef([]);
  const searchEffectsRef = useRef([]);
  const warnedTilesRef = useRef(null);
  const floatingTextRef = useRef([]);
  const transmuteEffectsRef = useRef([]);
  const flareEffectsRef = useRef([]);
  const spellSpriteEffectsRef = useRef([]);
  const magicMissileRef = useRef([]);
  const staffAmbientRef = useRef([]);
  const screenFlashRef = useRef(null);
  const screenShakeRef = useRef(null);
  const beamRef = useRef([]);
  const blobAreasRef = useRef({});
  const lightningRef = useRef([]);
  const shieldHaloRef = createShieldFxRef();
  const stateEffectsRef = useRef([]);
  const surpriseRef = useRef([]);
  const flyingItemsRef = useRef([]);
  const selectedEnemyIdRef = useRef(null);
  const hoveredCellRef = useRef(null);
  const customTilesRef = useRef([]);
  const customWallsRef = useRef([]);
  const torchesRef = useRef([]);
  const depthRef = useRef(1);
  const floorFadeRef = useRef(null);
  const onOpenAlchemyRef = useRef(null);

  useEffect(() => { depthRef.current = depth; }, [depth]);

  // Callback ref for canvas-wrapper resize observer
  const resizeObserverRef = useRef(null);
  const wrapperRef = useCallback((node) => {
    if (resizeObserverRef.current) {
      resizeObserverRef.current.disconnect();
      resizeObserverRef.current = null;
    }
    if (!node) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setViewport({
          width: Math.round(width),
          height: Math.round(height),
          dpr: Math.min(window.devicePixelRatio || 1, MAX_DPR),
        });
      }
    });
    observer.observe(node);
    resizeObserverRef.current = observer;
  }, [setViewport]);

  const canFitFullUI = Math.min(viewport.width / 360, viewport.height / 200) >= 2;
  const interfaceSize = (viewport.width > viewport.height && canFitFullUI) ? 2 : 0;
  const isDesktop = interfaceSize > 0;

  // send
  const send = useCallback((msg) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(msg));
    }
  }, []);

  // --- lore ---
  const loreFinishRef = useRef(null);
  const handleLoreNeeded = useCallback((depth, finishTransition) => {
    const lore = getLoreForDepth(depth);
    loreFinishRef.current = () => {
      setLoreOverlay(null);
      finishTransition();
    };
    setLoreOverlay({ depth, body: lore.body });
  }, [setLoreOverlay]);

  const handleLoreDismiss = useCallback(() => {
    loreFinishRef.current?.();
    if (!localStorage.getItem('opd-tutorial-completed')) {
      setShowTutorial(true);
    }
  }, [setShowTutorial]);

  const handleReplayTutorial = useCallback(() => {
    localStorage.removeItem('opd-tutorial-completed');
    setShowTutorial(true);
  }, [setShowTutorial]);

  // --- domain hooks ---
  const modals = useModalState();
  useEffect(() => { onOpenAlchemyRef.current = modals.onOpenAlchemy; });
  const talent = useTalents({ gameState, selectedClass, myStats, send });
  const targeting = useTargetingExamine({
    entitiesRef, visionRef, myPlayerIdRef, gridRef,
    equippedItems, send, selectedEnemyIdRef,
    playerAnimRef, searchEffectsRef,
  });

  // --- infra hooks ---
  useDebugApi({
    gridRef, entitiesRef, visionRef, openDoorsRef,
    myPlayerIdRef, panOffsetRef, cameraLerpRef, zoomRef, depthRef,
  });
  useAudioUnlock();
  const assetImages = useAssetImages();
  useMusicByDepth({ enabled: true, menu: gameState !== 'PLAYING', depth, bossFightActive: bossFightActive && !!bossInfo, bossBleeding: bossBleedingEffective, bossLurking, tense: ghostQuestGiven && depth <= 5, amuletObtained: hasAmulet });

  const { sendSelectScrollTarget, sendStoneTarget, effects } = useGameSocket({
    enabled: gameState === 'PLAYING',
    gameId, roomPassword, sessionId, selectedClass, difficulty, challenges, playerName,
    setConnectionStatus,
    onRoomRejected: (reason) => {
      setRoomJoinError(reason || 'Could not join room');
      setGameState('ROOMS');
    },
    socketRef, gridRef, myPlayerIdRef, entitiesRef,
    visionRef, openDoorsRef, projectilesRef,
    customTilesRef, customWallsRef, torchesRef,
    mobAnimRef, dyingMobsRef, playerAnimRef, particlesRef, searchEffectsRef, floatingTextRef, screenFlashRef, screenShakeRef, wasDownedRef, warnedTilesRef, transmuteEffectsRef, flareEffectsRef, spellSpriteEffectsRef, lightningRef, shieldHaloRef, stateEffectsRef, magicMissileRef, staffAmbientRef, surpriseRef, flyingItemsRef, selectedEnemyIdRef, beamRef, blobAreasRef,
    cameraLerpRef, isCameraDetachedRef, floorFadeRef,
    setGrid, setDepth, setMyPlayerId, setInventory,
    setEquippedItems, setMyStats, setDifficulty, setBossInfo,
    setGold, setEnergy, setHasAmulet, setBossLurking, setExitPos, setBelongings, setQuickslot,
    onLoreNeeded: handleLoreNeeded,
    onLevelUp: talent.onLevelUp,
    onSubclassChoiceAvailable: talent.onSubclassChoiceAvailable,
    onArmorAbilityChoiceAvailable: talent.onArmorAbilityChoiceAvailable,
    onGooFightStarted: () => setBossFightActive(true),
    onTenguFightStarted: () => setBossFightActive(true),
    onDM300FightStarted: () => setBossFightActive(true),
    onDwarfKingFightStarted: () => setBossFightActive(true),
    onDwarfKingPhase2: () => setBossBleeding(true),
    onYogFightStarted: () => setBossFightActive(true),
    onYogFinalPhase: () => setBossBleeding(true),
    onMetamorphOpen: talent.onMetamorphOpen,
    onMetamorphOptions: talent.onMetamorphOptions,
    onShopOpen: modals.onShopOpen,
    onImpDialogue: modals.onImpDialogue,
    onGhostDialogue: modals.onGhostDialogue,
    onWandmakerDialogue: modals.onWandmakerDialogue,
    onChasmPrompt: modals.onChasmPrompt,
    onGhostQuestGiven: () => setGhostQuestGiven(true),
    onGhostQuestProcessed: () => setGhostQuestGiven(false),
    onGhostQuestComplete: () => setGhostQuestGiven(false),
    onImbueWandChoiceAvailable: modals.onImbueWand,
    onScrollSelectTarget: modals.onScrollSelectTarget,
    onStoneSelectTarget: modals.onStoneSelectTarget,
    onStoneIntuitionPickItem: modals.onStoneIntuitionPickItem,
    onStoneIntuitionGuessKind: modals.onStoneIntuitionGuessKind,
    onStoneAugmentSelect: modals.onStoneAugmentSelect,
    onStoneAugmentPickItem: modals.onStoneAugmentPickItem,
    onEnchantChoiceAvailable: modals.onEnchantChoiceAvailable,
    onGhostGearOpen: modals.onGhostGearOpen,
    onAlchemyPreviewResult: modals.onAlchemyPreviewResult,
    onAlchemyBrewed: modals.onAlchemyBrewed,
    onTrinketChoice: modals.onTrinketChoice,
    onToolkitEnergizePrompt: modals.onToolkitEnergizePrompt,
    onOpenAlchemy: modals.onOpenAlchemy,
    onBossSlain: (data) => {
      setBossSlainData(data);
      setShowBossSlainBanner(true);
      setBossFightActive(false);
      setBossBleeding(false);
    },
    onPlayerDeath: (data) => {
      setScoreBreakdown(data.score_breakdown || null);
      setCanResurrect(!!data.can_resurrect);
      setHasAnkh(!!data.has_ankh);
      setKeptItems([]);
      setIsVictory(!!data.victory);
      setRespawnsUsed(data.respawns_used ?? 0);
      setMaxRespawns(data.max_respawns ?? 3);
      setLootDropped(!!data.loot_dropped);
      setDeathCause(data.death_cause ?? null);
    },
  });

  // --- busy state ---
  const [isBusy, setIsBusy] = useState(false);
  useEffect(() => {
    const id = setInterval(() => {
      const me = entitiesRef.current?.players?.[myPlayerIdRef.current];
      const anim = playerAnimRef.current?.[myPlayerIdRef.current];
      setIsBusy(!!me && !!anim && (
        (anim.attackUntil || 0) > performance.now()
        || (anim.operateUntil || 0) > performance.now()
        || (anim.readUntil || 0) > performance.now()
      ));
    }, 50);
    return () => clearInterval(id);
  }, []);

  // --- handler hooks ---
  const { equipItem, executeItemAction, assignQuickslot, handleToolbarClick } = useItemActions({
    send, equippedItems, targetingMode: targeting.targetingMode,
    setTargetingMode: targeting.setTargetingMode, setShowInventory: modals.setShowInventory, quickslot,
  });

  const { handleToolbarDoubleClick } = useTargetingHandlers({
    send, entitiesRef, myPlayerIdRef, visionRef, selectedEnemyIdRef,
  });

  const { resetForRestart, handleLeaveGame } = useGameLifecycle({
    socketRef, entitiesRef, visionRef, myPlayerIdRef, wasDownedRef,
    setMyPlayerId, setGrid, setMyStats, setBossInfo, setBossFightActive,
    setBossBleeding, setBossLurking, setShowBossSlainBanner, setBossSlainData,
    setInventory, setConnectionStatus, setScoreBreakdown, setCanResurrect,
    setIsVictory, setRespawnsUsed, setMaxRespawns, setLootDropped,
    resetMetamorph: talent.resetMetamorph, setGameState,
    setGameMenuOpen: modals.setGameMenuOpen,
  });

  useEffect(() => {
    return windowManager.setFallbackHandler(() => {
      if (targeting.examineModeRef.current || targeting.targetingModeRef.current) {
        targeting.setExamineMode(false);
        targeting.setTargetingMode(false);
        targeting.clearInspect();
        return true;
      }
      if (!modals.gameMenuOpenRef.current && gameState === 'PLAYING') {
        modals.setGameMenuOpen(true);
        return true;
      }
      return false;
    });
  }, [targeting, modals, gameState]);

  const handleEscape = useCallback(() => {
    windowManager.handleEscape();
  }, []);

  // --- computed items ---
  const itemsById = useMemo(() => {
    const map = {};
    if (!belongings) return map;
    ['weapon', 'armor', 'artifact', 'misc', 'ring'].forEach(k => {
      if (belongings[k]) map[belongings[k].id] = belongings[k];
    });
    const walk = (bag) => {
      (bag?.items || []).forEach(it => {
        map[it.id] = it;
        if (it.items) walk(it);
      });
    };
    walk(belongings.backpack);
    return map;
  }, [belongings]);

  // Emergency heal prompt
  const emergencyHealItem = useMemo(() => {
    if (myStats.isDowned || myStats.isRegen) return null;
    const maxHp = myStats.maxHp || 1;
    if ((myStats.hp ?? 0) / maxHp > 0.2) return null;
    const items = Object.values(itemsById || {});
    return items.find(it => it?.kind === 'health_potion')
      || items.find(it => it?.type === 'waterskin' && (it.volume || 0) > 0)
      || null;
  }, [myStats, itemsById]);

  const promptWarnedRef = useRef(false);
  useEffect(() => {
    if (emergencyHealItem) {
      if (!promptWarnedRef.current) {
        promptWarnedRef.current = true;
        AudioManager.play('HEALTH_WARN');
      }
    } else {
      promptWarnedRef.current = false;
    }
  }, [emergencyHealItem]);

  const drinkEmergencyHeal = useCallback((item) => {
    if (!item?.id) return;
    send({ type: 'USE_ITEM', item_id: item.id });
  }, [send]);

  const cycleEnemyCamera = useCallback((hostile) => {
    if (!hostile || hostile.length === 0) return;
    const pos = (hostile[0].targetPos || hostile[0].renderPos);
    const lw = canvasRef.current?.getBoundingClientRect()?.width || window.innerWidth;
    const lh = canvasRef.current?.getBoundingClientRect()?.height || window.innerHeight;
    const z = zoomRef.current;
    cameraLerpRef.current = {
      x: Math.round(pos.x) * TILE_SIZE + TILE_SIZE / 2 - lw / 2 / z,
      y: Math.round(pos.y) * TILE_SIZE + TILE_SIZE / 2 - lh / 2 / z,
    };
    panOffsetRef.current = { x: 0, y: 0 };
    isRefocusingRef.current = false;
    isCameraDetachedRef.current = false;
  }, []);

  return {
    // refs
    canvasRef, socketRef, gridRef, entitiesRef, myPlayerIdRef,
    projectilesRef, visionRef, openDoorsRef, panOffsetRef, cameraLerpRef,
    zoomRef, isDraggingRef, isRefocusingRef, isPinchingRef,
    isCameraDetachedRef, detachedCameraRef, wasDownedRef,
    mobAnimRef, dyingMobsRef, playerAnimRef, particlesRef, searchEffectsRef,
    warnedTilesRef, floatingTextRef, transmuteEffectsRef, flareEffectsRef,
    spellSpriteEffectsRef, magicMissileRef, staffAmbientRef,
    screenFlashRef, screenShakeRef, beamRef, blobAreasRef, lightningRef,
    shieldHaloRef, stateEffectsRef, surpriseRef, flyingItemsRef,
    selectedEnemyIdRef, hoveredCellRef, customTilesRef,
    customWallsRef, torchesRef, depthRef, floorFadeRef, onOpenAlchemyRef,
    wrapperRef,
    // computed
    depth, bossBleedingEffective, interfaceSize, isDesktop, TILE_SCREEN,
    // callbacks
    send, handleLoreNeeded, handleLoreDismiss, handleReplayTutorial,
    // domain hooks
    modals, talent, targeting,
    // infra
    assetImages,
    // game socket
    sendSelectScrollTarget, sendStoneTarget,
    // animation manager
    effects,
    // busy
    isBusy,
    // handlers
    equipItem, executeItemAction, assignQuickslot,
    handleToolbarClick, handleToolbarDoubleClick,
    handleEscape, resetForRestart, handleLeaveGame,
    // computed items
    itemsById, emergencyHealItem, drinkEmergencyHeal,
    cycleEnemyCamera,
  };
}
