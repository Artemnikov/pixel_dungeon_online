import { useEffect, useRef } from 'react';
import { isFloorFadeActive } from '../rendering/floorTransition';
import { BACKEND_TILE } from '../rendering/sewers/constants';

const DIRECTION_KEYS = new Set(['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'KeyW', 'KeyA', 'KeyS', 'KeyD']);

function isUp(code) { return code === 'ArrowUp' || code === 'KeyW'; }
function isDown(code) { return code === 'ArrowDown' || code === 'KeyS'; }
function isLeft(code) { return code === 'ArrowLeft' || code === 'KeyA'; }
function isRight(code) { return code === 'ArrowRight' || code === 'KeyD'; }

// Net movement vector from the set of currently held direction keys. Opposite keys
// cancel out (e.g. holding left+right yields dx=0). Diagonals are just dx,dy = ±1 each.
function getVector(pressed) {
  let dx = 0, dy = 0;
  for (const code of pressed) {
    if (isUp(code)) dy = -1;
    if (isDown(code)) dy = 1;
    if (isLeft(code)) dx = -1;
    if (isRight(code)) dx = 1;
  }
  return { dx, dy };
}

export default function useKeyboardControls({
  socketRef,
  inventory,
  setShowInventory,
  handleToolbarClick,
  handleToolbarDoubleClick,
  onExamineOrReveal,
  onCancelModes,
  triggerWait,
  isRefocusingRef,
  isDraggingRef,
  quickslot,
  itemsById,
  gameMenuOpenRef,
  showItemBrowserRef,
  onOpenTalents,
  onOpenItemBrowser,
  floorFadeRef,
  gridRef,
  entitiesRef,
  myPlayerIdRef,
  onOpenAlchemy,
}) {
  const lastKeyRef = useRef({ key: null, time: 0 });
  const pressedKeysRef = useRef(new Set());
  const lastSentVectorRef = useRef({ dx: 0, dy: 0 });

  useEffect(() => {
    // Send the current held-direction intent to the server, which paces the actual
    // stepping. Only sends on change so key auto-repeat is irrelevant. dx,dy = 0 stops.
    const syncMoveIntent = () => {
      if (socketRef.current?.readyState !== WebSocket.OPEN) return;
      const { dx, dy } = getVector(pressedKeysRef.current);
      const last = lastSentVectorRef.current;
      if (dx === last.dx && dy === last.dy) return;
      lastSentVectorRef.current = { dx, dy };
      if (dx === 0 && dy === 0) {
        socketRef.current.send(JSON.stringify({ type: 'MOVE_STOP' }));
      } else {
        isRefocusingRef.current = true;
        isDraggingRef.current = false;
        socketRef.current.send(JSON.stringify({ type: 'MOVE_INTENT', dx, dy }));
      }
    };

    const handleKeyDown = (e) => {
      if (isFloorFadeActive(floorFadeRef)) return;
      if (showItemBrowserRef?.current) {
        if (e.code === 'KeyU' || e.code === 'Escape') {
          e.preventDefault();
          if (onOpenItemBrowser) onOpenItemBrowser();
        }
        return;
      }

      pressedKeysRef.current.add(e.code);

      if (e.code === 'KeyF') {
        setShowInventory(prev => !prev);
        return;
      }
      if (e.code === 'KeyE') {
        if (onExamineOrReveal) onExamineOrReveal();
        return;
      }
      if (e.code === 'Escape') {
        if (gameMenuOpenRef?.current) return;
        if (onCancelModes) onCancelModes();
        return;
      }
      if (e.code === 'Space') {
        e.preventDefault();
        if (triggerWait) triggerWait();
        return;
      }
      if (e.code === 'KeyT') {
        if (onOpenTalents) onOpenTalents();
        return;
      }
      if (e.code === 'KeyU') {
        e.preventDefault();
        if (onOpenItemBrowser) onOpenItemBrowser();
        return;
      }

      if (['Digit1', 'Digit2', 'Digit3', 'Digit4', 'Digit5', 'Digit6'].includes(e.code)) {
        const index = parseInt(e.code.slice(-1)) - 1;
        const slot = quickslot?.slots?.[index];
        const item = slot?.item_id ? (itemsById?.[slot.item_id] || null) : null;
        if (item) {
          const now = Date.now();
          const isDoubleTap = lastKeyRef.current.key === e.code && (now - lastKeyRef.current.time) < 300;

          if (isDoubleTap) {
            handleToolbarDoubleClick(item);
            lastKeyRef.current = { key: null, time: 0 };
          } else {
            handleToolbarClick(item);
            lastKeyRef.current = { key: e.code, time: now };
          }
        }
      }

      if (DIRECTION_KEYS.has(e.code)) {
        // Check if the tile in the pressed direction is an alchemy pot.
        // If so, open the alchemy overlay instead of moving into it.
        const dx = isRight(e.code) ? 1 : isLeft(e.code) ? -1 : 0;
        const dy = isDown(e.code) ? 1 : isUp(e.code) ? -1 : 0;
        const me = entitiesRef?.current?.players[myPlayerIdRef?.current];
        if (me && dx + dy !== 0) {
          const pos = me.targetPos || me.renderPos;
          const tx = Math.round(pos.x) + dx;
          const ty = Math.round(pos.y) + dy;
          const g = gridRef?.current;
          if (g?.[ty]?.[tx] === BACKEND_TILE.ALCHEMY.id) {
            if (onOpenAlchemy) onOpenAlchemy();
            return;
          }
        }
        // Auto-repeat keydowns don't change the held set, so syncMoveIntent no-ops on
        // them; the server paces repeated stepping while the key stays down.
        syncMoveIntent();
      }
    };

    const handleKeyUp = (e) => {
      pressedKeysRef.current.delete(e.code);
      if (DIRECTION_KEYS.has(e.code) && !showItemBrowserRef?.current) {
        syncMoveIntent();
      }
    };

    const handleBlur = () => {
      pressedKeysRef.current.clear();
      syncMoveIntent();
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    window.addEventListener('blur', handleBlur);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      window.removeEventListener('blur', handleBlur);
    };
  }, [inventory, handleToolbarClick, handleToolbarDoubleClick, socketRef, setShowInventory, onExamineOrReveal, onCancelModes, triggerWait, isRefocusingRef, isDraggingRef, quickslot, itemsById, gameMenuOpenRef, showItemBrowserRef, onOpenTalents, onOpenItemBrowser, floorFadeRef, gridRef, entitiesRef, myPlayerIdRef, onOpenAlchemy]);
}
