import { useCallback } from 'react';
import { defaultToolbarClickDispatcher, TARGETED_ACTIONS } from './toolbar/ToolbarClickDispatcher';

export function useItemActions({ send, equippedItems, targetingMode, setTargetingMode, setShowInventory, quickslot, onOpenClericCastBar, belongings, myStats }) {
  const equipItem = useCallback((itemId) => send({ type: 'EQUIP_ITEM', item_id: itemId }), [send]);

  const executeItemAction = useCallback((itemId, action, opts = {}) => {
    const { tx, ty, fromQuickbar } = opts;
    if (action === 'CAST') {
      const isTome = belongings?.artifact?.id === itemId && belongings?.artifact?.kind === 'holy_tome'
        || belongings?.misc?.id === itemId && belongings?.misc?.kind === 'holy_tome'
        || (belongings?.backpack?.items || []).some(it => it.id === itemId && it.kind === 'holy_tome');
      if (isTome) {
        onOpenClericCastBar?.();
        return;
      }
    }
    if (TARGETED_ACTIONS.includes(action) && tx === undefined) {
      setTargetingMode({ itemId, action, fromQuickbar: !!fromQuickbar });
      setShowInventory(false);
      return;
    }
    send({ type: 'EXECUTE_ITEM_ACTION', item_id: itemId, action, target_x: tx, target_y: ty });
  }, [send, setTargetingMode, setShowInventory, belongings, onOpenClericCastBar]);

  const assignQuickslot = useCallback((itemId) => {
    const slots = quickslot?.slots || [];
    let idx = slots.findIndex(s => !s.item_id);
    if (idx < 0) idx = 0;
    send({ type: 'SET_QUICKSLOT', index: idx, item_id: itemId });
  }, [quickslot, send]);

  const handleToolbarClick = useCallback((item) => {
    defaultToolbarClickDispatcher.dispatch(item, {
      send,
      equippedItems,
      belongings,
      myStats,
      targetingMode,
      setTargetingMode,
      equipItem,
      executeItemAction,
      onOpenClericCastBar,
    });
  }, [send, equippedItems, belongings, myStats, targetingMode, setTargetingMode, equipItem, executeItemAction, onOpenClericCastBar]);

  return { equipItem, executeItemAction, assignQuickslot, handleToolbarClick };
}
