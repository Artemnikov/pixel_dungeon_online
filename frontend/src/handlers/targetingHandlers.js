import { useCallback } from 'react';
import { defaultToolbarDoubleClickDispatcher } from './toolbar/ToolbarDoubleClickDispatcher';

export function useTargetingHandlers({
  send,
  entitiesRef,
  myPlayerIdRef,
  visionRef,
  selectedEnemyIdRef,
  myStats,
  equippedItems,
  belongings,
  setTargetingMode,
}) {
  const handleToolbarDoubleClick = useCallback((item) => {
    defaultToolbarDoubleClickDispatcher.dispatch(item, {
      send,
      entitiesRef,
      myPlayerIdRef,
      visionRef,
      selectedEnemyIdRef,
      myStats,
      equippedItems,
      belongings,
      setTargetingMode,
    });
  }, [send, entitiesRef, myPlayerIdRef, visionRef, selectedEnemyIdRef, myStats, equippedItems, belongings, setTargetingMode]);

  return { handleToolbarDoubleClick };
}
