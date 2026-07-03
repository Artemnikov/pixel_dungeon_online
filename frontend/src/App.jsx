import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import './styles/index.css';

import CharacterSelection from './CharacterSelection';
import MainMenu from './menu/MainMenu';
import cursorMouseUrl from './assets/cursors/cursor_mouse.png';
import cursorMouse2xUrl from './assets/cursors/cursor_mouse@2x.png';
import cursorControllerUrl from './assets/cursors/cursor_controller.png';
import cursorController2xUrl from './assets/cursors/cursor_controller@2x.png';

import { TILE_SIZE, TILE_SCALE, MIN_ZOOM, MAX_DPR } from './constants';
import useAudioUnlock from './audio/useAudioUnlock';
import useMusicByDepth from './audio/useMusicByDepth';
import useAssetImages from './rendering/useAssetImages';
import useGameRenderer from './rendering/useGameRenderer';
import useGameSocket from './net/useGameSocket';
import useKeyboardControls from './input/useKeyboardControls';
import useCanvasControls from './input/useCanvasControls';
import { resolveTapAction } from './input/resolveTap';
import { isFloorFadeActive } from './rendering/floorTransition';
import LoreOverlay from './ui/LoreOverlay';
import { getLoreForDepth } from './game/loreTexts';
import useDebugApi from './dev/useDebugApi';

import useModalState from './game/useModalState';
import useTalentFlow from './game/useTalentFlow';
import useTargetingExamine from './game/useTargetingExamine';

import StatusPane from './ui/StatusPane';
import BossHealthBar from './ui/BossHealthBar';
import KeyDisplay from './ui/KeyDisplay';
import DangerIndicator from './ui/DangerIndicator';
import SideTags from './ui/SideTags';
import AttackIndicator from './ui/AttackIndicator';
import LootIndicator from './ui/LootIndicator';
import ResumeIndicator from './ui/ResumeIndicator';
import ActionIndicator from './ui/ActionIndicator';
import GameLog from './ui/GameLog';
import ToastOverlay from './ui/ToastOverlay';
import LoadingOverlay from './ui/LoadingOverlay';
import GameHud from './ui/GameHud';
import GameModals from './ui/GameModals';
import TalentLayer from './ui/TalentLayer';
import GameOverlay from './ui/GameOverlay';
import BossSlainBanner from './ui/BossSlainBanner';
import WndInfoBuff from './ui/WndInfoBuff';

// Live viewport position of an inspect-popup anchor (a world tile, or a mob we follow
// by its renderPos). Returns { left, top, below } or null when the popup should hide
// (mob gone/out of view, or the anchor panned off the visible canvas).
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

function App() {
  const { t } = useTranslation();
  // --- screen flow / session state ---
  const [gameState, setGameState] = useState('WELCOME');
  const [selectedClass, setSelectedClass] = useState('warrior');
  const [playerName, setPlayerName] = useState('');
  const [difficulty, setDifficulty] = useState('normal');
  const [challenges, setChallenges] = useState('');
  const [gameId] = useState('default-lobby');
  const [sessionId, setSessionId] = useState(
    () => sessionStorage.getItem('opd_session') || ''
  );
  const [connectionStatus, setConnectionStatus] = useState(null);

  // --- game state ---
  const [grid, setGrid] = useState([]);
  const [myPlayerId, setMyPlayerId] = useState(null);
  const [viewport, setViewport] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
    dpr: Math.min(window.devicePixelRatio || 1, MAX_DPR),
  });
  const [inventory, setInventory] = useState([]);
  const [equippedItems, setEquippedItems] = useState({ weapon: null, wearable: null });
  const [belongings, setBelongings] = useState(null);
  const [quickslot, setQuickslot] = useState(null);
  const [myStats, setMyStats] = useState({ hp: 0, maxHp: 10, name: '' });
  const [bossInfo, setBossInfo] = useState(null);
  const [bossFightActive, setBossFightActive] = useState(false);
  const [bossBleeding, setBossBleeding] = useState(false);
  const [depth, setDepth] = useState(1);
  const [, setCamera] = useState({ x: 0, y: 0 });
  const [gold, setGold] = useState(0);
  const [energy, setEnergy] = useState(0);
  const [hasAmulet, setHasAmulet] = useState(false);
  const [bossLurking, setBossLurking] = useState(false);
  const [exitPos, setExitPos] = useState(null);
  const [scoreBreakdown, setScoreBreakdown] = useState(null);
  const [canResurrect, setCanResurrect] = useState(false);
  const [isVictory, setIsVictory] = useState(false);
  const [ghostQuestGiven, setGhostQuestGiven] = useState(false);
  const [showBossSlainBanner, setShowBossSlainBanner] = useState(false);
  const [bossSlainData, setBossSlainData] = useState(null);
  const [loreOverlay, setLoreOverlay] = useState(null);
  const [inspectBuff, setInspectBuff] = useState(null);
  const loreFinishRef = useRef(null);

  const handleLoreNeeded = useCallback((depth, finishTransition) => {
    const lore = getLoreForDepth(depth);
    loreFinishRef.current = () => {
      setLoreOverlay(null);
      finishTransition();
    };
    setLoreOverlay({ depth, body: lore.body });
  }, []);

  const handleLoreDismiss = useCallback(() => {
    loreFinishRef.current?.();
  }, []);

  // --- shared refs ---
  const canvasRef = useRef(null);
  const socketRef = useRef(null);
  const gridRef = useRef([]);
  const entitiesRef = useRef({ players: {}, mobs: {} });
  const myPlayerIdRef = useRef(null);
  const projectilesRef = useRef([]);
  const visionRef = useRef({ visible: new Set(), discovered: new Set() });
  const openDoorsRef = useRef(new Set());
  const musicRef = useRef(null);
  const panOffsetRef = useRef({ x: 0, y: 0 });
  const cameraLerpRef = useRef({ x: 0, y: 0 });
  const TILE_SCREEN = TILE_SIZE * TILE_SCALE; // 64px per tile at zoom=1
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
  const shieldHaloRef = useRef([]);
  const stateEffectsRef = useRef([]);
  const surpriseRef = useRef([]);
  const selectedEnemyIdRef = useRef(null);
  const hoveredCellRef = useRef(null);
  const trapsRef = useRef([]);
  const customTilesRef = useRef([]);
  const customWallsRef = useRef([]);
  const torchesRef = useRef([]);
  const depthRef = useRef(1);
  const floorFadeRef = useRef(null);
  const inspectPopupRef = useRef(null);
  const inspectSubRef = useRef(null);
  const onOpenAlchemyRef = useRef(null);

  useEffect(() => { depthRef.current = depth; }, [depth]);

  const wrapperRef = useRef(null);

  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;
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
    observer.observe(wrapper);
    return () => observer.disconnect();
  }, []);

  const canFitFullUI = Math.min(viewport.width / 360, viewport.height / 200) >= 2;
  const interfaceSize = (viewport.width > viewport.height && canFitFullUI) ? 2 : 0;

  // Define send early — domain hooks below need it; safe because it only reads socketRef (a ref)
  const send = useCallback((msg) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(msg));
    }
  }, []);

  // --- domain hooks ---
  const modals = useModalState();
  useEffect(() => { onOpenAlchemyRef.current = modals.onOpenAlchemy; });
  const talent = useTalentFlow({ gameState, selectedClass, myStats, send });
  const targeting = useTargetingExamine({
    entitiesRef, visionRef, myPlayerIdRef, gridRef,
    equippedItems, send, trapsRef,
  });

  // --- infra hooks ---
  useDebugApi({
    gridRef, entitiesRef, visionRef, openDoorsRef,
    myPlayerIdRef, panOffsetRef, cameraLerpRef, zoomRef, depthRef,
  });
  useAudioUnlock();
  const assetImages = useAssetImages();
  useMusicByDepth({ enabled: true, menu: gameState !== 'PLAYING', depth, bossFightActive: bossFightActive && !!bossInfo, bossBleeding, bossLurking, tense: ghostQuestGiven && depth <= 5, amuletObtained: hasAmulet, musicRef });

  const { sendSelectScrollTarget, sendStoneTarget } = useGameSocket({
    enabled: gameState === 'PLAYING',
    gameId, sessionId, selectedClass, difficulty, challenges, playerName,
    setConnectionStatus,
    socketRef, gridRef, myPlayerIdRef, entitiesRef,
    visionRef, openDoorsRef, projectilesRef,
    trapsRef, customTilesRef, customWallsRef, torchesRef,
    mobAnimRef, dyingMobsRef, playerAnimRef, particlesRef, searchEffectsRef, floatingTextRef, screenFlashRef, screenShakeRef, wasDownedRef, warnedTilesRef, transmuteEffectsRef, flareEffectsRef, spellSpriteEffectsRef, lightningRef, shieldHaloRef, stateEffectsRef, magicMissileRef, staffAmbientRef, surpriseRef, selectedEnemyIdRef, beamRef, blobAreasRef,
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
    onChasmPrompt: modals.onChasmPrompt,
    onGhostQuestGiven: () => setGhostQuestGiven(true),
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
    onTalentUpgraded: talent.onTalentUpgraded,
    onBossSlain: (data) => {
      setBossSlainData(data);
      setShowBossSlainBanner(true);
      setBossFightActive(false);
      setBossBleeding(false);
    },
    onPlayerDeath: (data) => {
      setScoreBreakdown(data.score_breakdown || null);
      setCanResurrect(!!data.can_resurrect);
      setIsVictory(!!data.victory);
    },
  });

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
  });

  useGameRenderer({
    canvasRef, grid, myPlayerId, depth, assetImages, floorFadeRef,
    entitiesRef, visionRef, openDoorsRef, projectilesRef,
    trapsRef, customTilesRef, customWallsRef, torchesRef,
    mobAnimRef, dyingMobsRef, playerAnimRef, particlesRef, searchEffectsRef, floatingTextRef, screenFlashRef, screenShakeRef, myPlayerIdRef, warnedTilesRef, transmuteEffectsRef, flareEffectsRef, spellSpriteEffectsRef, lightningRef, shieldHaloRef, stateEffectsRef, magicMissileRef, staffAmbientRef, surpriseRef, selectedEnemyIdRef, hoveredCellRef, beamRef, blobAreasRef,
    panOffsetRef, cameraLerpRef, zoomRef,
    isRefocusingRef, isDraggingRef,
    isCameraDetachedRef, detachedCameraRef,
    setCamera,
  });

  // --- item action dispatch ---
  const TARGETED_ACTIONS = ['THROW', 'ZAP', 'DIRECT', 'SHOOT'];

  const equipItem = useCallback((itemId) => send({ type: 'EQUIP_ITEM', item_id: itemId }), [send]);

  const executeItemAction = useCallback((itemId, action, tx, ty) => {
    if (TARGETED_ACTIONS.includes(action) && tx === undefined) {
      targeting.setTargetingMode({ itemId, action });
      modals.setShowInventory(false);
      return;
    }
    send({ type: 'EXECUTE_ITEM_ACTION', item_id: itemId, action, target_x: tx, target_y: ty });
  }, [send]); // targeting.setTargetingMode and modals.setShowInventory are stable setters

  const assignQuickslot = useCallback((itemId) => {
    const slots = quickslot?.slots || [];
    let idx = slots.findIndex(s => !s.item_id);
    if (idx < 0) idx = 0;
    send({ type: 'SET_QUICKSLOT', index: idx, item_id: itemId });
  }, [quickslot, send]);

  // --- toolbar handlers ---
  const handleToolbarClick = useCallback((item) => {
    if (!item) return;
    if (item.type === 'potion') {
      send({ type: 'USE_ITEM', item_id: item.id });
      return;
    }
    if (item.type === 'weapon') {
      if (item.kind === 'staff') {
        if (targeting.targetingMode && typeof targeting.targetingMode === 'object' && targeting.targetingMode.itemId === item.id) {
          targeting.setTargetingMode(false);
        } else if (item.default_action) {
          executeItemAction(item.id, item.default_action);
        }
        return;
      }
      if (item.default_action && TARGETED_ACTIONS.includes(item.default_action)) {
        executeItemAction(item.id, item.default_action);
        return;
      }
      const isEquipped = equippedItems.weapon && equippedItems.weapon.id === item.id;
      if (!isEquipped) {
        equipItem(item.id);
        if (item.range && item.range > 1) {
          targeting.setTargetingMode(item.id);
        } else {
          targeting.setTargetingMode(false);
        }
      } else if (item.range && item.range > 1) {
        targeting.setTargetingMode(prev => !prev);
      }
    } else if (item.type === 'wearable') {
      equipItem(item.id);
    } else if (item.type === 'throwable') {
      if (targeting.targetingMode && typeof targeting.targetingMode === 'object' && targeting.targetingMode.itemId === item.id) {
        targeting.setTargetingMode(false);
      } else {
        targeting.setTargetingMode({ itemId: item.id, action: 'THROW' });
      }
    } else if (item.type === 'wand') {
      if (targeting.targetingMode && typeof targeting.targetingMode === 'object' && targeting.targetingMode.itemId === item.id) {
        targeting.setTargetingMode(false);
      } else {
        executeItemAction(item.id, 'ZAP');
      }
    } else if (item.default_action) {
      executeItemAction(item.id, item.default_action);
    }
  }, [send, executeItemAction, equipItem, equippedItems, targeting.targetingMode, targeting.setTargetingMode]);

  const handleToolbarDoubleClick = useCallback((item) => {
    if (!item) return;
    const isTargeted = item.type === 'wand'
      || item.type === 'throwable'
      || (item.type === 'weapon' && item.range && item.range > 1)
      || item.kind === 'staff';
    if (!isTargeted) return;

    const myPlayer = entitiesRef.current.players[myPlayerIdRef.current];
    if (!myPlayer) return;

    let nearestMob = null;
    let minDist = item.range + 1;

    Object.values(entitiesRef.current.mobs).forEach(mob => {
      if (!visionRef.current.visible.has(`${Math.round(mob.renderPos.x)},${Math.round(mob.renderPos.y)}`)) return;
      const dx = mob.renderPos.x - myPlayer.renderPos.x;
      const dy = mob.renderPos.y - myPlayer.renderPos.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist <= item.range && dist < minDist) {
        minDist = dist;
        nearestMob = mob;
      }
    });

    if (nearestMob) {
      const tx = Math.round(nearestMob.renderPos.x);
      const ty = Math.round(nearestMob.renderPos.y);
      if (item.default_action && TARGETED_ACTIONS.includes(item.default_action)) {
        send({ type: 'EXECUTE_ITEM_ACTION', item_id: item.id, action: item.default_action, target_x: tx, target_y: ty });
      } else {
        send({ type: 'RANGED_ATTACK', item_id: item.id, target_x: tx, target_y: ty });
      }
    }
  }, [send]);

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

  const handleEscape = useCallback(() => {
    if (targeting.examineModeRef.current || targeting.targetingModeRef.current) {
      targeting.setExamineMode(false);
      targeting.setTargetingMode(false);
      targeting.clearInspect();
    } else if (talent.showSubclassChoice) {
      talent.setShowSubclassChoice(false);
    } else if (talent.showArmorAbilityChoice) {
      talent.setShowArmorAbilityChoice(false);
    } else if (talent.showTalentPane) {
      talent.setShowTalentPane(false);
      talent.setUpgradedTalentId(null);
    } else if (!modals.gameMenuOpenRef.current) {
      modals.setGameMenuOpen(true);
    }
  }, [talent.showSubclassChoice, talent.showArmorAbilityChoice, talent.showTalentPane]);

  const resetForRestart = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.close();
    }
    entitiesRef.current = { players: {}, mobs: {} };
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
    talent.resetMetamorph();
  }, [talent.resetMetamorph]);

  const handleLeaveGame = useCallback(() => {
    resetForRestart();
    modals.setGameMenuOpen(false);
    setGameState('WELCOME');
  }, [resetForRestart]);

  useKeyboardControls({
    socketRef, inventory, setShowInventory: modals.setShowInventory,
    handleToolbarClick, handleToolbarDoubleClick,
    onExamineOrReveal: targeting.handleExamineOrReveal, onCancelModes: handleEscape,
    triggerWait: () => send({ type: 'WAIT' }),
    isRefocusingRef, isDraggingRef, floorFadeRef,
    quickslot, itemsById,
    onRadialSelect: modals.handleRadialSelect,
    gameMenuOpenRef: modals.gameMenuOpenRef,
    showItemBrowserRef: modals.showItemBrowserRef,
    onOpenTalents: () => talent.setShowTalentPane(v => !v),
    onOpenItemBrowser: () => {
      if (!myStats.isAdmin) return;
      modals.setShowItemBrowser(v => !v);
    },
  });

  const handleCanvasClick = useCallback((e) => {
    if (isFloorFadeActive(floorFadeRef)) return;
    if (hasDraggedRef.current) return;
    if (!canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

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
      const action = resolveTapAction({ tileX, tileY, playerTile, mobs: entitiesRef.current.mobs, grid: gridRef.current });
      if (action.type === 'OPEN_ALCHEMY') {
        modals.onOpenAlchemy();
        return;
      }
      if (action.type === 'MOVE_TO' || action.type === 'MOVE') isRefocusingRef.current = true;
      socketRef.current.send(JSON.stringify(action));
    }
  }, []);

  const isDesktop = interfaceSize > 0;
  const isMac = /Macintosh|MacIntel|MacPPC|Mac68K/.test(navigator.userAgent);
  const mouseCursorVal = isMac
    ? `url(${cursorMouse2xUrl}) 2 2, pointer`
    : `image-set(url(${cursorMouseUrl}) 1x, url(${cursorMouse2xUrl}) 2x) 1 1, pointer`;
  const controllerCursorVal = isMac
    ? `url(${cursorController2xUrl}) 16 16, crosshair`
    : `image-set(url(${cursorControllerUrl}) 1x, url(${cursorController2xUrl}) 2x) 8 8, crosshair`;

  // Destructure targeting values used in JSX so the linter doesn't flag object-property
  // accesses on a hook return that contains refs.
  const {
    targetingMode, examineMode, inspectInfo,
    handleExamineOrReveal,
    sendUseAbility, sendUseComboMove, sendPrepStrike,
  } = targeting;

  // Drive the inspect popup every frame: reposition from live camera, update mob HP,
  // hide off-screen, auto-dismiss after 3s of no activity.
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

  // --- screen flow ---
  if (gameState === 'WELCOME') {
    return (
      <>
        <title>{t('app.titleWelcome')}</title>
        <meta name="description" content={t('app.descWelcome')} />
        <div className={isDesktop ? 'desktop-mode' : ''}
             style={isDesktop ? { '--cursor-mouse': mouseCursorVal } : {}}>
          <MainMenu onStart={() => setGameState('SELECT')} />
        </div>
      </>
    );
  }

  if (gameState === 'SELECT') {
    return (
      <>
        <title>{t('app.titleSelect')}</title>
        <meta name="description" content={t('app.descSelect')} />
        <div className={isDesktop ? 'desktop-mode' : ''}
             style={isDesktop ? { '--cursor-mouse': mouseCursorVal } : {}}>
          <CharacterSelection onSelect={(c, d, n, strongerBosses) => {
            setSelectedClass(c);
            setDifficulty(d);
            setChallenges(strongerBosses ? 'stronger_bosses' : '');
            setPlayerName(n);
            const newSession = crypto.randomUUID();
            sessionStorage.setItem('opd_session', newSession);
            setSessionId(newSession);
            setGameState('PLAYING');
          }} />
        </div>
      </>
    );
  }

  const cursorStyle = (targetingMode || examineMode)
    ? isDesktop ? controllerCursorVal : 'crosshair'
    : isDesktop ? mouseCursorVal.replace(', pointer', ', auto') : 'default';

  return (
    <>
      <title>{t('app.titlePlaying', { depth })}</title>
      <meta name="description" content={t('app.descPlaying', { depth })} />
      <div className={`game-container ${isDesktop ? 'desktop-mode' : ''}`}
           style={isDesktop ? { '--cursor-mouse': mouseCursorVal } : {}}>

        <LoadingOverlay visible={grid.length === 0} />

        {connectionStatus === 'reconnecting' && (
          <div className="reconnect-banner" role="status">
            {t('app.reconnecting')}
          </div>
        )}

        <BossHealthBar boss={bossInfo} bleeding={bossBleeding} interfaceSize={interfaceSize} assetImages={assetImages} />
        <KeyDisplay keys={myStats.keys} depth={depth} />

        <SideTags>
          <AttackIndicator
            myStats={myStats}
            onAttack={(targetId) => send({ type: 'ATTACK', target_id: targetId })}
          />
          <ActionIndicator
            myStats={myStats}
            onAction={(action) => {
              const weapon = myStats?.belongings?.weapon;
              if (weapon) executeItemAction(weapon.id, action);
            }}
          />
          <LootIndicator
            entitiesRef={entitiesRef}
            myPlayerIdRef={myPlayerIdRef}
            onPickup={() => send({ type: 'PICKUP_FLOOR' })}
          />
          <ResumeIndicator
            myStats={myStats}
            onResume={() => send({ type: 'RESUME' })}
          />
          <DangerIndicator
            visionRef={visionRef}
            entitiesRef={entitiesRef}
            myPlayerIdRef={myPlayerIdRef}
            onCycleEnemy={() => {
              const visible = visionRef.current.visible;
              if (!visible) return;
              const hostile = Object.values(entitiesRef.current.mobs).filter(m =>
                m.faction === 'enemy' && visible.has(`${Math.round(m.renderPos.x)},${Math.round(m.renderPos.y)}`)
              );
              if (hostile.length === 0) return;
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
            }}
          />
        </SideTags>

        <StatusPane
          myStats={myStats}
          interfaceSize={interfaceSize}
          depth={depth}
          exitPos={exitPos}
          isAdmin={myStats.isAdmin}
          onSearch={handleExamineOrReveal}
          hasTalentPoints={Object.values(talent.talentPoints || {}).some(p => p > 0)}
          gold={gold}
          onOpenTalentPane={() => talent.setShowTalentPane(true)}
          onTeleport={(floor) => send({ type: 'ADMIN_TELEPORT', target_floor: floor })}
          isBusy={isBusy}
          onBuffClick={(buff) => setInspectBuff(buff)}
          assetImages={assetImages}
        />

        <div className="canvas-wrapper" ref={wrapperRef}>
          <canvas
            ref={canvasRef}
            width={Math.round(viewport.width * viewport.dpr)}
            height={Math.round(viewport.height * viewport.dpr)}
            className="game-canvas"
            style={{ cursor: cursorStyle }}
            onClick={handleCanvasClick}
          />
        </div>

        {inspectInfo && (
          <div
            ref={inspectPopupRef}
            className="inspect-popup"
            style={{ display: 'none' }}
          >
            <span className="inspect-popup-name">{inspectInfo.name}</span>
            <span className="inspect-popup-sub" ref={inspectSubRef} style={{ display: 'none' }} />
          </div>
        )}

        {inspectBuff && (
          <WndInfoBuff
            buff={inspectBuff}
            onClose={() => setInspectBuff(null)}
          />
        )}

        <GameHud
          interfaceSize={interfaceSize}
          isDesktop={isDesktop}
          canvasWidth={viewport.width}
          assetImages={assetImages}
          toolbarItems={toolbarItems}
          equippedItems={equippedItems}
          targetingMode={targetingMode}
          swappedQuickslots={modals.swappedQuickslots}
          showInventory={modals.showInventory}
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={myStats.strength}
          myStats={myStats}
          onWait={() => send({ type: 'WAIT' })}
          onSearch={handleExamineOrReveal}
          onInventory={() => modals.setShowInventory(v => !v)}
          onQuickBag={modals.handleQuickBag}
          onSwap={modals.handleSwap}
          onSlotClick={(item, idx) => {
            if (!item || item.is_placeholder || item.default_action == null) {
              modals.openQuickslotPicker(idx);
            } else {
              handleToolbarClick(item);
            }
          }}
          onSlotDoubleClick={handleToolbarDoubleClick}
          onSlotLongPress={(item, idx) => modals.openQuickslotPicker(idx)}
          onSlotContextMenu={(item, idx) => modals.openQuickslotPicker(idx)}
          onUseAbility={sendUseAbility}
          onTriggerBerserk={() => send({ type: 'TRIGGER_BERSERK' })}
          onPrepStrike={sendPrepStrike}
          onUseComboMove={sendUseComboMove}
          onOpenItem={modals.setUseItemTarget}
          onContextMenu={(item, x, y) => modals.setCtxMenu({ item, x, y })}
          onDefaultAction={(item) => executeItemAction(item.id, item.default_action)}
          onCloseInventory={() => modals.setShowInventory(false)}
        />

        <GameLog />
        <ToastOverlay />

        {showBossSlainBanner && bossSlainData && (
          <BossSlainBanner
            badgeImage={bossSlainData.badge_image}
            onDismiss={() => setShowBossSlainBanner(false)}
          />
        )}

        <GameModals
          modals={modals}
          itemsById={itemsById}
          toolbarItems={toolbarItems}
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={myStats.strength}
          isDesktop={isDesktop}
          executeItemAction={executeItemAction}
          assignQuickslot={assignQuickslot}
          sendSelectScrollTarget={sendSelectScrollTarget}
          sendStoneTarget={sendStoneTarget}
          send={send}
          handleToolbarClick={handleToolbarClick}
        />

        <TalentLayer
          talent={talent}
          myStats={myStats}
          gameState={gameState}
          showItemBrowser={modals.showItemBrowser}
          setShowItemBrowser={modals.setShowItemBrowser}
          itemCatalog={modals.itemCatalog}
          send={send}
        />

        {loreOverlay && (
          <LoreOverlay key={loreOverlay.depth} depth={loreOverlay.depth} body={loreOverlay.body} onContinue={handleLoreDismiss} />
        )}

        <GameOverlay
          gameMenuOpen={modals.gameMenuOpen}
          onCloseMenu={() => modals.setGameMenuOpen(false)}
          onLeaveGame={handleLeaveGame}
          isDowned={myStats.isDowned}
          playerName={myStats.name}
          classType={myStats.classType}
          level={myStats.level}
          depth={depth}
          gold={gold}
          subclass={myStats.subclass}
          armorAbility={myStats.armorAbility}
          talentLevels={myStats.talentLevels}
          talentDefs={talent.talentDefs}
          inventory={inventory}
          selectedClass={selectedClass}
          scoreBreakdown={scoreBreakdown}
          canResurrect={canResurrect}
          isVictory={isVictory}
          onResurrect={() => send({ type: 'RESURRECT' })}
          onNewGame={() => { resetForRestart(); setGameState('SELECT'); }}
          onMenu={() => { resetForRestart(); setGameState('WELCOME'); }}
          challenges={challenges}
        />
      </div>
    </>
  );
}

export default App;
