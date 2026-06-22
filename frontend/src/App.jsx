import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import './styles/index.css';

import CharacterSelection from './CharacterSelection';
import MainMenu from './menu/MainMenu';
import cursorMouseUrl from './assets/cursors/cursor_mouse.png';
import cursorControllerUrl from './assets/cursors/cursor_controller.png';

import { TILE_SIZE, MAX_DPR } from './constants';
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
  const loreFinishRef = useRef(null);

  const handleLoreNeeded = useCallback((depth, finishTransition) => {
    loreFinishRef.current = finishTransition;
    setLoreOverlay(getLoreForDepth(depth));
  }, []);

  const handleLoreDismiss = () => {
    loreFinishRef.current?.();
    loreFinishRef.current = null;
    setLoreOverlay(null);
  };

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
  const zoomRef = useRef(1.0);
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

  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  // Define send early — domain hooks below need it; safe because it only reads socketRef (a ref)
  const send = (msg) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(msg));
    }
  };

  // --- domain hooks ---
  const modals = useModalState();
  const talent = useTalentFlow({ gameState, selectedClass, myStats, send });
  const targeting = useTargetingExamine({
    canvasRef, cameraLerpRef, zoomRef,
    entitiesRef, visionRef, myPlayerIdRef, gridRef,
    equippedItems, send,
  });

  // --- infra hooks ---
  useDebugApi({
    gridRef, entitiesRef, visionRef, openDoorsRef,
    myPlayerIdRef, panOffsetRef, cameraLerpRef, zoomRef, depthRef,
  });
  useAudioUnlock();
  const assetImages = useAssetImages();
  useMusicByDepth({ enabled: true, menu: gameState !== 'PLAYING', depth, bossFightActive: bossFightActive && !!bossInfo, bossBleeding, bossLurking, tense: ghostQuestGiven && depth <= 5, amuletObtained: hasAmulet, musicRef });

  const { sendSelectScrollTarget } = useGameSocket({
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
    onGhostGearOpen: modals.onGhostGearOpen,
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

  const isBusy = useMemo(() => {
    const me = entitiesRef.current?.players?.[myPlayerIdRef.current];
    if (!me) return false;
    const anim = playerAnimRef.current?.[myPlayerIdRef.current];
    if (!anim) return false;
    const now = performance.now();
    return (anim.attackUntil || 0) > now
      || (anim.operateUntil || 0) > now
      || (anim.readUntil || 0) > now;
  }, [myStats]); // re-derive when myStats changes (every frame)

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
  const TARGETED_ACTIONS = ['THROW', 'ZAP', 'DIRECT'];

  const equipItem = (itemId) => send({ type: 'EQUIP_ITEM', item_id: itemId });

  const executeItemAction = (itemId, action, tx, ty) => {
    if (TARGETED_ACTIONS.includes(action) && tx === undefined) {
      targeting.setTargetingMode({ itemId, action });
      modals.setShowInventory(false);
      return;
    }
    send({ type: 'EXECUTE_ITEM_ACTION', item_id: itemId, action, target_x: tx, target_y: ty });
  };

  const assignQuickslot = (itemId) => {
    const slots = quickslot?.slots || [];
    let idx = slots.findIndex(s => !s.item_id);
    if (idx < 0) idx = 0;
    send({ type: 'SET_QUICKSLOT', index: idx, item_id: itemId });
  };

  // --- toolbar handlers ---
  const handleToolbarClick = (item) => {
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
  };

  const handleToolbarDoubleClick = (item) => {
    const isRangedWeapon = item && item.type === 'weapon' && item.range && item.range > 1;
    const isThrowable = item && item.type === 'throwable';
    if (!isRangedWeapon && !isThrowable) return;

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
      if (isThrowable) {
        send({ type: 'EXECUTE_ITEM_ACTION', item_id: item.id, action: 'THROW', target_x: tx, target_y: ty });
      } else {
        send({ type: 'RANGED_ATTACK', item_id: item.id, target_x: tx, target_y: ty });
      }
    }
  };

  // Flatten belongings into an id->item map for quickslot resolution.
  const itemsById = {};
  if (belongings) {
    ['weapon', 'armor', 'artifact', 'misc', 'ring'].forEach(k => {
      if (belongings[k]) itemsById[belongings[k].id] = belongings[k];
    });
    const walk = (bag) => {
      (bag?.items || []).forEach(it => {
        itemsById[it.id] = it;
        if (it.items) walk(it);
      });
    };
    walk(belongings.backpack);
  }

  const handleEscape = () => {
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
  };

  const resetForRestart = () => {
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
  };

  const handleLeaveGame = () => {
    resetForRestart();
    modals.setGameMenuOpen(false);
    setGameState('WELCOME');
  };

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

  const handleCanvasClick = (e) => {
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
      const action = resolveTapAction({ tileX, tileY, playerTile, mobs: entitiesRef.current.mobs });
      if (action.type === 'MOVE_TO' || action.type === 'MOVE') isRefocusingRef.current = true;
      socketRef.current.send(JSON.stringify(action));
    }
  };

  const isDesktop = interfaceSize > 0;

  // Destructure targeting values used in JSX so the linter doesn't flag object-property
  // accesses on a hook return that contains refs.
  const {
    targetingMode, examineMode, inspectInfo,
    inspectPopupRef, inspectSubRef,
    handleExamineOrReveal,
    sendUseAbility, sendUseComboMove, sendPrepStrike,
  } = targeting;

  // --- screen flow ---
  if (gameState === 'WELCOME') {
    return (
      <>
        <title>{t('app.titleWelcome')}</title>
        <meta name="description" content={t('app.descWelcome')} />
        <div className={isDesktop ? 'desktop-mode' : ''}
             style={isDesktop ? { '--cursor-mouse': `url(${cursorMouseUrl}) 1 1, pointer` } : {}}>
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
             style={isDesktop ? { '--cursor-mouse': `url(${cursorMouseUrl}) 1 1, pointer` } : {}}>
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
    ? isDesktop
      ? `url(${cursorControllerUrl}) 8 8, crosshair`
      : 'crosshair'
    : isDesktop
      ? `url(${cursorMouseUrl}) 1 1, auto`
      : 'default';

  // Toolbar quickslots mirror the real quickslot state, resolving each slot's item id
  // against the flattened belongings.
  const toolbarItems = Array.from({ length: 6 }).map((_, i) => {
    const slot = quickslot?.slots?.[i];
    if (!slot) return null;
    if (slot.item_id) return itemsById[slot.item_id] || null;
    if (slot.is_placeholder && slot.placeholder_kind) {
      return { id: null, kind: slot.placeholder_kind, name: '', type: null, is_placeholder: true };
    }
    return null;
  });

  return (
    <>
      <title>{t('app.titlePlaying', { depth })}</title>
      <meta name="description" content={t('app.descPlaying', { depth })} />
      <div className={`game-container ${isDesktop ? 'desktop-mode' : ''}`}
           style={isDesktop ? { '--cursor-mouse': `url(${cursorMouseUrl}) 1 1, pointer` } : {}}>

        <LoadingOverlay visible={grid.length === 0} />

        {connectionStatus === 'reconnecting' && (
          <div className="reconnect-banner" role="status">
            {t('app.reconnecting')}
          </div>
        )}

        <BossHealthBar boss={bossInfo} />
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
          depth={depth}
          exitPos={exitPos}
          isAdmin={myStats.isAdmin}
          onSearch={handleExamineOrReveal}
          hasTalentPoints={Object.values(talent.talentPoints || {}).some(p => p > 0)}
          onOpenTalents={() => talent.setShowTalentPane(v => !v)}
          onTeleport={(floor) => send({ type: 'ADMIN_TELEPORT', target_floor: floor })}
          isBusy={isBusy}
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
            style={{
              position: 'fixed',
              left: 0,
              top: 0,
              display: 'none',
              transform: 'translate(-50%, -100%)',
              background: 'rgba(0, 0, 0, 0.85)',
              border: '1px solid #6a6a6a',
              borderRadius: 3,
              padding: '3px 7px',
              color: '#ffffff',
              font: '11px monospace',
              lineHeight: 1.25,
              whiteSpace: 'nowrap',
              textAlign: 'center',
              pointerEvents: 'none',
              zIndex: 60,
            }}
          >
            <div style={{ fontWeight: 'bold' }}>{inspectInfo.name}</div>
            {/* Uncontrolled (no React child) so the rAF loop can update the live HP text
                without React clobbering it on the next per-frame re-render. */}
            <div ref={inspectSubRef} style={{ color: '#bdbdbd', display: 'none' }} />
          </div>
        )}

        <GameHud
          interfaceSize={interfaceSize}
          isDesktop={isDesktop}
          canvasWidth={viewport.width}
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

        <button className="fullscreen-btn" onClick={toggleFullscreen} title={isFullscreen ? t('app.exitFullscreen') : t('app.fullscreen')}>
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {isFullscreen ? (
              <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
            ) : (
              <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
            )}
          </svg>
        </button>

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
          <LoreOverlay title={loreOverlay.title} body={loreOverlay.body} onContinue={handleLoreDismiss} />
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
        />
      </div>
    </>
  );
}

export default App;
