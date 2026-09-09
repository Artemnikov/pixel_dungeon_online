import { useEffect, useRef } from 'react';
import { getWsBaseUrl } from '../config/urls';
import { sendMessage } from './send';
import { startFloorFade } from '../rendering/floorTransition';
import { TILE_SIZE, FLOOR_FADE_OUT_MS } from '../constants';
import AudioManager from '../audio/AudioManager';
import * as movementPredictor from './movementPredictor';
import type { ServerMessage, InitMessage, StateUpdateMessage } from '../types/contract';
import type { HookProps } from './types';
import { WorldManager } from './services/WorldManager';
import { EntityManager } from './services/EntityManager';
import { VisualEffectsManager } from './services/VisualEffectsManager';
import { HeroStateSync } from './services/HeroStateSync';
import { GameCallbacks } from './services/GameCallbacks';
import { defaultStateSynchronizer } from './sync/StateSynchronizer';
import type { StateSyncContext } from './sync/IStateSynchronizer';
import { defaultEventDispatcher } from './events/defaultDispatcher';
import type { GameEventContext } from './events/IGameEventHandler';

const HEARTBEAT_INTERVAL_MS = 15000;
const WATCHDOG_TIMEOUT_MS = 30000;
const RECONNECT_BASE_MS = 500;
const RECONNECT_MAX_MS = 10000;

// Room-join rejection close codes (backend/app/main.py's game_websocket):
// 4001 wrong password, 4002 room full. Never worth retrying.
const ROOM_REJECT_CODES = new Set([4001, 4002]);

// Stairs/chasm events that should fade-and-snap the camera on floor change.
// CHASM_FALL is the fall transition (SPD Chasm.heroFall -> InterlevelScene.Mode.FALL).
const FLOOR_CHANGE_EVENT_TYPES = new Set(['STAIRS_DOWN', 'STAIRS_UP', 'CHASM_FALL']);

export default function useGameSocket({
  enabled,
  gameId,
  roomPassword,
  sessionId,
  selectedClass,
  difficulty,
  challenges,
  playerName,
  setConnectionStatus,
  onRoomRejected,
  socketRef,
  gridRef,
  myPlayerIdRef,
  entitiesRef,
  visionRef,
  openDoorsRef,
  projectilesRef,
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
  flyingItemsRef,
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
  onWandmakerDialogue,
  onGhostQuestGiven,
  onGhostQuestProcessed,
  onGhostQuestComplete,
  onScrollSelectTarget,
  onStoneSelectTarget,
  onStoneIntuitionPickItem,
  onStoneIntuitionGuessKind,
  onStoneAugmentSelect,
  onStoneAugmentPickItem,
  onGhostGearOpen,
  onBossSlain,
  onPlayerDeath,
  onAlchemyPreviewResult,
  onAlchemyBrewed,
  onAlchemyEnergized,
  onTrinketChoice,
  onToolkitEnergizePrompt,
  onOpenAlchemy,
  onLoreNeeded,
}: HookProps) {
  const depthRef = useRef(1);

  // The effects manager owns all gameplay/UI effects (projectiles, particles,
  // talent upgrade bursts, ...). It must be created once and be stable for the
  // hook lifetime: the socket handler closure and the UI components (which
  // register talent button DOM nodes) must all share the exact same instance.
  const effectsRef = useRef<VisualEffectsManager | null>(null);
  if (effectsRef.current === null) {
    effectsRef.current = new VisualEffectsManager({
      projectilesRef,
      mobAnimRef,
      playerAnimRef,
      particlesRef,
      searchEffectsRef,
      floatingTextRef,
      warnedTilesRef,
      screenFlashRef,
      transmuteEffectsRef,
      flareEffectsRef,
      spellSpriteEffectsRef,
      lightningRef,
      shieldHaloRef,
      stateEffectsRef,
      screenShakeRef,
      magicMissileRef,
      beamRef,
      surpriseRef,
      flyingItemsRef,
    });
  }
  const effects = effectsRef.current;

  useEffect(() => {
    if (!enabled) return;

    const world = new WorldManager({
      gridRef,
      setGrid,
      visionRef,
      openDoorsRef,
      depthRef,
      setDepth,
      blobAreasRef,
      customTilesRef,
      customWallsRef,
      torchesRef,
      setExitPos,
    });

    const entities = new EntityManager({
      entitiesRef,
      dyingMobsRef,
      myPlayerIdRef,
      setMyPlayerId,
      wasDownedRef,
      selectedEnemyIdRef,
    });

    const heroState = new HeroStateSync({
      setMyStats,
      setInventory,
      setEquippedItems,
      setBelongings,
      setQuickslot,
      setGold,
      setEnergy,
      setHasAmulet,
      setBossInfo,
      setBossLurking,
      setDifficulty,
    });

    const ui = new GameCallbacks({
      onLevelUp,
      onSubclassChoiceAvailable,
      onArmorAbilityChoiceAvailable,
      onImbueWandChoiceAvailable,
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
      onWandmakerDialogue,
      onGhostQuestGiven,
      onGhostQuestProcessed,
      onGhostQuestComplete,
      onScrollSelectTarget,
      onStoneSelectTarget,
      onStoneIntuitionPickItem,
      onStoneIntuitionGuessKind,
      onStoneAugmentSelect,
      onStoneAugmentPickItem,
      onGhostGearOpen,
      onBossSlain,
      onPlayerDeath,
      onAlchemyPreviewResult,
      onAlchemyBrewed,
      onAlchemyEnergized,
      onTrinketChoice,
      onToolkitEnergizePrompt,
      onOpenAlchemy,
      onLoreNeeded,
    });

    const syncContext: StateSyncContext = {
      world,
      entities,
      heroState,
    };

    const eventContext: GameEventContext = {
      myPlayerId: myPlayerIdRef.current,
      world,
      entities,
      effects,
      ui,
      audio: AudioManager,
    };

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
      const roomPasswordParam = roomPassword ? `&room_password=${encodeURIComponent(roomPassword)}` : '';
      const ws = new WebSocket(`${wsBaseUrl}/ws/game/${gameId}?class_type=${selectedClass}&difficulty=${difficulty}${challengesParam}${nameParam}${adminParam}${sessionParam}${roomPasswordParam}`);
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
      ws.onclose = (event) => {
        clearTimers();
        if (ROOM_REJECT_CODES.has(event.code)) {
          intentionalClose = true;
          onRoomRejected?.(event.reason || 'rejected');
          return;
        }
        scheduleReconnect();
      };

      let pendingInit: InitMessage | null = null;
      let deferredApplyPending = false;

      let initApplyIsFloorChange = false;

      const applyInit = (data: InitMessage) => {
        // Clear stale entities and visual effects from the previous floor.
        effects.clearFloorEffects();

        world.initFloor({
          grid: data.grid,
          depth: data.depth,
          customTiles: data.custom_tiles,
          customWalls: data.custom_walls,
          torches: data.torches,
          exitPos: (data as unknown as { exit_pos?: [number, number] | null }).exit_pos,
        });

        if (data.difficulty) heroState.setDifficulty(data.difficulty);
        if (data.player_id) entities.setMyPlayerId(data.player_id);

        entities.setTraps((data.traps || []).map(t => ({
          ...t,
          renderPos: { x: t.x, y: t.y },
          revealStartTime: null,
        })));
        entities.setItems([]);
        const mobs = entities.getMobs();
        Object.keys(mobs).forEach(id => delete mobs[id]);
        if (entities.dyingMobsRef) entities.dyingMobsRef.current = {};

        // On floor transitions, snap the local player entity immediately to the
        // new entrance tile so it doesn't glide across map coordinates from the
        // previous floor. This must happen before sync runs so that the
        // existing entity's renderPos/targetPos/animStartPos are all aligned.
        if (initApplyIsFloorChange) {
          const myId = entities.getMyPlayerId();
          const p = myId ? entities.getPlayer(myId) : undefined;
          if (p) {
            const sp = data.self_player as { pos?: { x: number; y: number } } | undefined;
            p.renderPos = { x: sp?.pos?.x ?? 0, y: sp?.pos?.y ?? 0 };
            p.targetPos = { x: sp?.pos?.x ?? 0, y: sp?.pos?.y ?? 0 };
            p.animStartPos = { x: sp?.pos?.x ?? 0, y: sp?.pos?.y ?? 0 };
            p.animStartTime = null;
          }
        }

        if (data.self_player) {
          defaultStateSynchronizer.sync({
            type: 'STATE_UPDATE',
            players: [],
            mobs: [],
            visible_tiles: [],
            events: [],
            self_player: data.self_player,
          }, syncContext);
        }
      };

      const applyStateUpdate = (data: StateUpdateMessage) => {
        defaultStateSynchronizer.sync(data, syncContext);

        if (data.events) {
          eventContext.myPlayerId = entities.getMyPlayerId();
          data.events.forEach(ev => defaultEventDispatcher.dispatch(ev, eventContext));
        }
      };

      const snapCameraForFloorChange = (direction: 'down' | 'up', newPos: { x: number; y: number }) => {
        if (isCameraDetachedRef) isCameraDetachedRef.current = false;
        if (!cameraLerpRef?.current) return;
        const myId = entities.getMyPlayerId() ?? '';
        const me = entities.getPlayer(myId);
        const oldPos = me?.renderPos ?? newPos;
        const dx = (newPos.x - oldPos.x) * TILE_SIZE;
        const dy = (newPos.y - oldPos.y) * TILE_SIZE;
        const snapTileOffset = direction === 'down' ? -TILE_SIZE : TILE_SIZE;
        cameraLerpRef.current.x += dx;
        cameraLerpRef.current.y += dy + snapTileOffset;
      };

      ws.onmessage = (event) => {
        lastMsgAt = Date.now();
        let data: ServerMessage;
        try {
          data = JSON.parse(event.data) as ServerMessage;
        } catch (e) {
          console.error('Failed to parse incoming WebSocket message:', e);
          return;
        }
        if (data.type === 'PONG') return;

        if (data.type === 'INIT') {
          pendingInit = data;
          return;
        }

        if (data.type === 'MOVE_RESULT') {
          // MOVE_RESULT fast lane: step confirmations are sent by the server as
          // compact top-level messages ahead of the bulk STATE_UPDATE frame, so
          // they arrive at RTT speed instead of riding inside the 40Hz frame
          // payload. Reuse the frame event path -- the MOVE_RESULT handler in
          // events/player.ts confirms the step to the movement predictor.
          eventContext.myPlayerId = entities.getMyPlayerId();
          defaultEventDispatcher.dispatch(data, eventContext);
          return;
        }

        if (data.type !== 'STATE_UPDATE') return;

        // A fade triggered by an earlier tick is still mid-flight (screen is fading to
        // black / held black); drop intermediate ticks rather than risk them being
        // applied mid-fade or racing the deferred apply below.
        if (deferredApplyPending) return;

        const myId = entities.getMyPlayerId();
        const floorChangeEvent = data.events?.find(
          ev => FLOOR_CHANGE_EVENT_TYPES.has(ev.type) && (ev as { data: { player: string } }).data.player === myId,
        );

        if (floorChangeEvent) movementPredictor.clearInFlight();

        if (!floorChangeEvent) {
          if (pendingInit) {
            const isNewPlayer = pendingInit.is_new === true;
            const initDepth = pendingInit.depth;
            if (isCameraDetachedRef) isCameraDetachedRef.current = false;
            applyInit(pendingInit);
            pendingInit = null;
            if (isNewPlayer && initDepth === 1 && onLoreNeeded) {
              onLoreNeeded(1, () => {});
            }
          }
          applyStateUpdate(data);
          return;
        }

        const isChasmFall = floorChangeEvent.type === 'CHASM_FALL';
        const direction = floorChangeEvent.type === 'STAIRS_UP' ? 'up' : 'down';
        const initToApply = pendingInit;
        pendingInit = null;
        const newPos = data.players.find(p => p.id === myId)?.pos;
        deferredApplyPending = true;

        if (isChasmFall) {
          AudioManager.play('FALLING');
        }

        const finishTransition = () => {
          if (floorFadeRef) startFloorFade(floorFadeRef, direction, isChasmFall);
          setTimeout(() => {
            deferredApplyPending = false;
            initApplyIsFloorChange = true;
            if (initToApply) applyInit(initToApply);
            initApplyIsFloorChange = false;
            applyStateUpdate(data);
            if (newPos) snapCameraForFloorChange(direction, newPos);
          }, FLOOR_FADE_OUT_MS);
        };

        const currentDepth = initToApply?.depth ?? data.depth ?? depthRef.current;
        const needsLore = floorChangeEvent.type === 'STAIRS_DOWN'
          && floorChangeEvent.data.first_visit
          && [1, 6, 11, 16, 21].includes(currentDepth);

        if (needsLore && onLoreNeeded) {
          onLoreNeeded(currentDepth, finishTransition);
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

  const sendStoneTarget = (stoneId: string, itemId: string) => {
    const ws = socketRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      sendMessage(ws, { type: 'SELECT_STONE_TARGET', stone_id: stoneId, item_id: itemId });
    }
  };

  return { sendSelectScrollTarget, sendStoneTarget, effects };
}
