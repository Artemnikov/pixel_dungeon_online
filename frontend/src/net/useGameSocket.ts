import { useEffect } from 'react';
import { getWsBaseUrl } from '../config/urls';
import { sendMessage } from './send';
import { syncState } from './syncState';
import { handleEvent } from './handleEvent';
import type { ServerMessage } from '../types/contract';
import type { HookProps, HandlerCtx } from './types';

const HEARTBEAT_INTERVAL_MS = 15000;
const WATCHDOG_TIMEOUT_MS = 30000;
const RECONNECT_BASE_MS = 500;
const RECONNECT_MAX_MS = 10000;

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
  onDM300FightStarted,
  onDwarfKingFightStarted,
  onDwarfKingPhase2,
  onYogFightStarted,
  onYogFinalPhase,
  onShopOpen,
  onImpDialogue,
  onScrollSelectTarget,
  onBossSlain,
  onPlayerDeath,
}: HookProps) {
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

      ws.onmessage = (event) => {
        lastMsgAt = Date.now();
        const data = JSON.parse(event.data) as ServerMessage;
        if (data.type === 'PONG') return;

        if (data.type === 'INIT') {
          setGrid(data.grid);
          gridRef.current = data.grid;
          visionRef.current.discovered = new Set();
          trapsRef.current = data.traps || [];
          customTilesRef.current = data.custom_tiles || [];
          if (typeof data.depth === 'number') setDepth(data.depth);
          if (data.player_id) {
            setMyPlayerId(data.player_id);
            myPlayerIdRef.current = data.player_id;
          }
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          if (setExitPos) setExitPos((data as any).exit_pos || null);
          return;
        }

        if (data.type !== 'STATE_UPDATE') return;

        console.log('[WS] STATE_UPDATE', data.players.length, 'players, my level:', data.players.find(p => p.id === myPlayerIdRef.current)?.level);

        if (typeof data.depth === 'number') setDepth(data.depth);
        if (data.difficulty) setDifficulty(data.difficulty);
        if (typeof data.gold === 'number' && setGold) setGold(data.gold);
        if (typeof data.energy === 'number' && setEnergy) setEnergy(data.energy);

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
          onMetamorphOpen, onMetamorphOptions, onGooFightStarted, onTenguFightStarted,
          onDM300FightStarted, onDwarfKingFightStarted, onDwarfKingPhase2, onYogFightStarted, onYogFinalPhase,
          onShopOpen, onImpDialogue, onScrollSelectTarget, onBossSlain, onPlayerDeath,
        };

        if (data.events) {
          data.events.forEach(ev => handleEvent(ev, handlerCtx));
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
