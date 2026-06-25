import { useEffect, useRef } from 'react';
import { getWsBaseUrl } from '../config/urls';
import { sendMessage } from './send';
import { syncState } from './syncState';
import { handleEvent } from './handleEvent';
import { startFloorFade } from '../rendering/floorTransition';
import { TILE_SIZE, FLOOR_FADE_OUT_MS } from '../constants';
import type { ServerMessage, InitMessage, StateUpdateMessage } from '../types/contract';
import type { HookProps, HandlerCtx } from './types';

const HEARTBEAT_INTERVAL_MS = 15000;
const WATCHDOG_TIMEOUT_MS = 30000;
const RECONNECT_BASE_MS = 500;
const RECONNECT_MAX_MS = 10000;

// Stairs/chasm events that should fade-and-snap the camera on floor change. A future
// CHASM_FALL_START call site adds itself here once the chasm-fall mechanic lands.
const FLOOR_CHANGE_EVENT_TYPES = new Set(['STAIRS_DOWN', 'STAIRS_UP']);

export default function useGameSocket({
  enabled,
  gameId,
  sessionId,
  selectedClass,
  difficulty,
  challenges,
  playerName,
  setConnectionStatus,
  socketRef,
  gridRef,
  myPlayerIdRef,
  entitiesRef,
  visionRef,
  openDoorsRef,
  projectilesRef,
  trapsRef,
  customTilesRef,
  customWallsRef,
  torchesRef,
  mobAnimRef,
  dyingMobsRef,
  playerAnimRef,
  particlesRef,
  searchEffectsRef,
  floatingTextRef,
  screenFlashRef,
  transmuteEffectsRef,
  flareEffectsRef,
  spellSpriteEffectsRef,
  lightningRef,
  shieldHaloRef,
  stateEffectsRef,
  magicMissileRef,
  screenShakeRef,
  beamRef,
  blobAreasRef,
  surpriseRef,
  selectedEnemyIdRef,
  warnedTilesRef,
  wasDownedRef,
  floorFadeRef,
  cameraLerpRef,
  isCameraDetachedRef,
  setGrid,
  setDepth,
  setMyPlayerId,
  setInventory,
  setEquippedItems,
  setMyStats,
  setDifficulty,
  setBossInfo,
  setGold,
  setEnergy,
  setHasAmulet,
  setBossLurking,
  setExitPos,
  setBelongings,
  setQuickslot,
  onLevelUp,
  onSubclassChoiceAvailable,
  onArmorAbilityChoiceAvailable,
  onImbueWandChoiceAvailable,
  onTalentUpgraded,
  onMetamorphOpen,
  onMetamorphOptions,
  onGooFightStarted,
  onTenguFightStarted,
  onChasmPrompt,
  onDM300FightStarted,
  onDwarfKingFightStarted,
  onDwarfKingPhase2,
  onYogFightStarted,
  onYogFinalPhase,
  onShopOpen,
  onImpDialogue,
  onGhostDialogue,
  onGhostQuestGiven,
  onGhostQuestComplete,
  onScrollSelectTarget,
  onGhostGearOpen,
  onBossSlain,
  onPlayerDeath,
  onLoreNeeded,
}: HookProps) {
  const depthRef = useRef(1);

  useEffect(() => {
    if (!enabled) return;

    let attempt = 0;
    let intentionalClose = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
    let watchdogTimer: ReturnType<typeof setInterval> | null = null;
    let lastMsgAt = Date.now();
    const status = (s: string) => { if (setConnectionStatus) setConnectionStatus(s); };

    const clearTimers = () => {
      if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null; }
      if (watchdogTimer) { clearInterval(watchdogTimer); watchdogTimer = null; }
    };

    const scheduleReconnect = () => {
      if (intentionalClose || !enabled) return;
      status('reconnecting');
      const delay = Math.min(RECONNECT_BASE_MS * 2 ** attempt, RECONNECT_MAX_MS);
      const jittered = delay / 2 + Math.random() * (delay / 2);
      attempt += 1;
      reconnectTimer = setTimeout(connect, jittered);
    };

    function connect() {
      reconnectTimer = null;
      const wsBaseUrl = getWsBaseUrl();
      const nameParam = playerName ? `&name=${encodeURIComponent(playerName)}` : '';
      const sessionParam = sessionId ? `&session=${encodeURIComponent(sessionId)}` : '';
      const urlParams = new URLSearchParams(window.location.search);
      const adminSecret = urlParams.get('admin_secret') || '';
      const adminParam = adminSecret ? `&admin_secret=${encodeURIComponent(adminSecret)}` : '';
      const challengesParam = challenges ? `&challenges=${encodeURIComponent(challenges)}` : '';
      const ws = new WebSocket(`${wsBaseUrl}/ws/game/${gameId}?class_type=${selectedClass}&difficulty=${difficulty}${challengesParam}${nameParam}${adminParam}${sessionParam}`);
      socketRef.current = ws;

      ws.onopen = () => {
        attempt = 0;
        lastMsgAt = Date.now();
        status('connected');
        clearTimers();
        heartbeatTimer = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) sendMessage(ws, { type: 'PING' });
        }, HEARTBEAT_INTERVAL_MS);
        watchdogTimer = setInterval(() => {
          if (Date.now() - lastMsgAt > WATCHDOG_TIMEOUT_MS) {
            try { ws.close(); } catch { /* falls through to onclose */ }
          }
        }, WATCHDOG_TIMEOUT_MS / 2);
      };
      ws.onerror = () => {
        if (attempt === 0) console.warn('Failed to connect to channel');
      };
      ws.onclose = () => {
        clearTimers();
        scheduleReconnect();
      };

      // INIT only arrives on floor change (or first connect) — see main.py's
      // last_sent_floor check. We don't yet know at INIT-receipt time whether this
      // floor change came from stairs (fade) or an admin/debug warp (no fade), so the
      // grid swap is always stashed here and only actually applied from
      // applyStateUpdate below, once we've seen the paired STATE_UPDATE's events.
      let pendingInit: InitMessage | null = null;
      // While true, the fade-out is mid-flight: any STATE_UPDATE/INIT arriving before
      // the deferred apply fires gets folded into the pending payload instead of being
      // applied (and instead of triggering a second, overlapping fade).
      let deferredApplyPending = false;

      const applyInit = (data: InitMessage) => {
        setGrid(data.grid);
        gridRef.current = data.grid;
        visionRef.current.discovered = new Set();
        trapsRef.current = data.traps || [];
        customTilesRef.current = data.custom_tiles || [];
        customWallsRef.current = data.custom_walls || [];
        torchesRef.current = data.torches || [];
        if (typeof data.depth === 'number') { setDepth(data.depth); depthRef.current = data.depth; }
        if (data.player_id) {
          setMyPlayerId(data.player_id);
          myPlayerIdRef.current = data.player_id;
        }
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if (setExitPos) setExitPos((data as any).exit_pos || null);
      };

      const applyStateUpdate = (data: StateUpdateMessage) => {
        if (typeof data.depth === 'number') { setDepth(data.depth); depthRef.current = data.depth; }
        if (data.difficulty) setDifficulty(data.difficulty);
        if (typeof data.gold === 'number' && setGold) setGold(data.gold);
        if (typeof data.energy === 'number' && setEnergy) setEnergy(data.energy);
        if (typeof data.has_amulet === 'boolean' && setHasAmulet) setHasAmulet(data.has_amulet);
        if (typeof data.boss_lurking === 'boolean' && setBossLurking) setBossLurking(data.boss_lurking);

        syncState(data, {
          myPlayerIdRef, gridRef, entitiesRef, visionRef, openDoorsRef, trapsRef,
          dyingMobsRef, wasDownedRef,
          setInventory, setEquippedItems, setMyStats, setBossInfo, setBelongings, setQuickslot,
        });

        const handlerCtx: HandlerCtx = {
          myPlayerIdRef, gridRef, setGrid, entitiesRef, visionRef,
          projectilesRef, mobAnimRef, dyingMobsRef, playerAnimRef, particlesRef,
          searchEffectsRef, floatingTextRef, screenFlashRef, screenShakeRef,
          transmuteEffectsRef, warnedTilesRef, flareEffectsRef, spellSpriteEffectsRef,
          lightningRef, shieldHaloRef, stateEffectsRef, magicMissileRef,
          surpriseRef, selectedEnemyIdRef, beamRef, blobAreasRef,
          onLevelUp, onSubclassChoiceAvailable, onArmorAbilityChoiceAvailable,
          onImbueWandChoiceAvailable, onTalentUpgraded,
          onMetamorphOpen, onMetamorphOptions, onGooFightStarted, onTenguFightStarted, onChasmPrompt,
          onDM300FightStarted, onDwarfKingFightStarted, onDwarfKingPhase2, onYogFightStarted, onYogFinalPhase,
          onShopOpen, onImpDialogue, onGhostDialogue, onGhostQuestGiven, onGhostQuestComplete, onScrollSelectTarget, onGhostGearOpen, onBossSlain, onPlayerDeath,
          depth: depthRef.current,
        };

        if (data.events) {
          data.events.forEach(ev => handleEvent(ev, handlerCtx));
        }
      };

      // Camera snap-then-pan (SPD GameScene.java): force-offset cameraLerpRef one tile
      // in the direction the player just dropped from/rose to, on top of the player's
      // raw movement delta (which keeps any existing pan/zoom offset intact); the
      // existing CAMERA_LERP exponential settle in useGameRenderer pulls it back onto
      // the player next frame, reading as "drop down" / "rise up" into view.
      const snapCameraForFloorChange = (direction: 'down' | 'up', newPos: { x: number; y: number }) => {
        if (isCameraDetachedRef) isCameraDetachedRef.current = false;
        if (!cameraLerpRef?.current) return;
        const me = entitiesRef.current.players[myPlayerIdRef.current ?? ''];
        const oldPos = me?.renderPos ?? newPos;
        const dx = (newPos.x - oldPos.x) * TILE_SIZE;
        const dy = (newPos.y - oldPos.y) * TILE_SIZE;
        const snapTileOffset = direction === 'down' ? -TILE_SIZE : TILE_SIZE;
        cameraLerpRef.current.x += dx;
        cameraLerpRef.current.y += dy + snapTileOffset;
      };

      ws.onmessage = (event) => {
        lastMsgAt = Date.now();
        const data = JSON.parse(event.data) as ServerMessage;
        if (data.type === 'PONG') return;

        if (data.type === 'INIT') {
          pendingInit = data;
          return;
        }

        if (data.type !== 'STATE_UPDATE') return;

        console.log('[WS] STATE_UPDATE', data.players.length, 'players, my level:', data.players.find(p => p.id === myPlayerIdRef.current)?.level);

        // A fade triggered by an earlier tick is still mid-flight (screen is fading to
        // black / held black); drop intermediate ticks rather than risk them being
        // applied mid-fade or racing the deferred apply below.
        if (deferredApplyPending) return;

        const floorChangeEvent = data.events?.find(
          ev => FLOOR_CHANGE_EVENT_TYPES.has(ev.type) && (ev as { data: { player: string } }).data.player === myPlayerIdRef.current,
        );

        if (!floorChangeEvent) {
          // Steady state (most ticks), or a non-stairs depth change (admin teleport,
          // resurrect, etc.) — apply any stashed INIT immediately, no fade.
          if (pendingInit) {
            const isFirstConnect = !!pendingInit.player_id;
            const initDepth = pendingInit.depth;
            if (isCameraDetachedRef) isCameraDetachedRef.current = false;
            applyInit(pendingInit);
            pendingInit = null;
            // First connection to depth 1 = new game. Show lore chain over the
            // rendered world (Dungeon intro → Sewers intro → game is revealed).
            if (isFirstConnect && initDepth === 1 && onLoreNeeded) {
              onLoreNeeded(1, () => {});
            }
          }
          applyStateUpdate(data);
          return;
        }

        // Stairs/chasm floor change: fade out, then swap grid+position+camera while
        // the screen is fully black, then let the fade play back in. Input is gated
        // client-side for the whole fade window via isFloorFadeActive(floorFadeRef).
        // If this is first descent into a new region, show lore text before the fade.
        const direction = floorChangeEvent.type === 'STAIRS_UP' ? 'up' : 'down';
        const initToApply = pendingInit;
        pendingInit = null;
        const newPos = data.players.find(p => p.id === myPlayerIdRef.current)?.pos;
        deferredApplyPending = true;

        const finishTransition = () => {
          if (floorFadeRef) startFloorFade(floorFadeRef, direction);
          setTimeout(() => {
            deferredApplyPending = false;
            if (initToApply) applyInit(initToApply);
            applyStateUpdate(data);
            if (newPos) snapCameraForFloorChange(direction, newPos);
          }, FLOOR_FADE_OUT_MS);
        };

        const needsLore = floorChangeEvent.type === 'STAIRS_DOWN'
          && floorChangeEvent.data.first_visit
          && [1, 6, 11, 16, 21].includes(data.depth);

        if (needsLore && onLoreNeeded) {
          onLoreNeeded(data.depth, finishTransition);
        } else {
          finishTransition();
        }
      };
    }

    connect();

    return () => {
      intentionalClose = true;
      clearTimers();
      if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
      const ws = socketRef.current;
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, gameId, sessionId]);

  const sendSelectScrollTarget = (scrollId: string, itemId: string) => {
    const ws = socketRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      sendMessage(ws, { type: 'SELECT_SCROLL_TARGET', scroll_id: scrollId, item_id: itemId });
    }
  };

  return { sendSelectScrollTarget };
}
