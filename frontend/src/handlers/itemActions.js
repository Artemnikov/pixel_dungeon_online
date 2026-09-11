import { useCallback } from 'react';

const TARGETED_ACTIONS = ['THROW', 'ZAP', 'DIRECT', 'SHOOT', 'CAST', 'STEAL', 'PLANT_SEED', 'UNLOCK', 'KEY_REVEAL'];

export function useItemActions({ send, equippedItems, targetingMode, setTargetingMode, setShowInventory, quickslot }) {
  const equipItem = useCallback((itemId) => send({ type: 'EQUIP_ITEM', item_id: itemId }), [send]);

  const executeItemAction = useCallback((itemId, action, tx, ty) => {
    if (TARGETED_ACTIONS.includes(action) && tx === undefined) {
      setTargetingMode({ itemId, action });
      setShowInventory(false);
      return;
    }
    send({ type: 'EXECUTE_ITEM_ACTION', item_id: itemId, action, target_x: tx, target_y: ty });
  }, [send, setTargetingMode, setShowInventory]);

  const assignQuickslot = useCallback((itemId) => {
    const slots = quickslot?.slots || [];
    let idx = slots.findIndex(s => !s.item_id);
    if (idx < 0) idx = 0;
    send({ type: 'SET_QUICKSLOT', index: idx, item_id: itemId });
  }, [quickslot, send]);

  const handleToolbarClick = useCallback((item) => {
    if (!item) return;
    if (item.type === 'potion') {
      send({ type: 'USE_ITEM', item_id: item.id });
      return;
    }
    if (item.type === 'weapon') {
      if (item.kind === 'staff') {
        if (targetingMode && typeof targetingMode === 'object' && targetingMode.itemId === item.id) {
          setTargetingMode(false);
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
          setTargetingMode(item.id);
        } else {
          setTargetingMode(false);
        }
      } else if (item.range && item.range > 1) {
        setTargetingMode(prev => !prev);
      }
    } else if (item.type === 'wearable') {
      equipItem(item.id);
    } else if (item.throw_behavior === 'missile' || item.type === 'throwable' || item.throw_behavior === 'seed' || item.type === 'seed' || item.default_action === 'THROW') {
      if (targetingMode && typeof targetingMode === 'object' && targetingMode.itemId === item.id) {
        setTargetingMode(false);
      } else {
        setTargetingMode({ itemId: item.id, action: 'THROW' });
      }
    } else if (item.type === 'wand') {
      if (targetingMode && typeof targetingMode === 'object' && targetingMode.itemId === item.id) {
        setTargetingMode(false);
      } else {
        executeItemAction(item.id, 'ZAP');
      }
    } else if (item.default_action) {
      executeItemAction(item.id, item.default_action);
    }
  }, [send, executeItemAction, equipItem, equippedItems, targetingMode, setTargetingMode]);

  return { equipItem, executeItemAction, assignQuickslot, handleToolbarClick };
}
