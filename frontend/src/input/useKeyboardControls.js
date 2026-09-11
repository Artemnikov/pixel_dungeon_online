import { useEffect, useRef } from 'react';
import { DIRECTION_KEYS, getVector } from './directionUtils';
import { KeyboardMovementController } from './controller/KeyboardMovementController';

export { DIRECTION_KEYS, getVector };

export default function useKeyboardControls(props) {
  const propsRef = useRef(props);
  useEffect(() => {
    propsRef.current = props;
  });

  useEffect(() => {
    const getContext = () => {
      const p = propsRef.current || {};
      const myId = p.myPlayerIdRef?.current || '';
      const me = myId && p.entitiesRef?.current?.players ? p.entitiesRef.current.players[myId] : null;

      return {
        myPlayerId: myId,
        myPlayer: me,
        grid: p.gridRef?.current || [],
        entities: p.entitiesRef?.current || { players: {}, mobs: {}, items: [], traps: [], plants: [] },
        socket: p.socketRef?.current,
        playerAnimRef: p.playerAnimRef,
        floorFadeRef: p.floorFadeRef,
        showItemBrowserRef: p.showItemBrowserRef,
        gameMenuOpenRef: p.gameMenuOpenRef,
        isRefocusingRef: p.isRefocusingRef,
        isDraggingRef: p.isDraggingRef,
        onCloseItemBrowser: p.onCloseItemBrowser,
        onOpenItemBrowser: p.onOpenItemBrowser,
        setShowInventory: p.setShowInventory,
        onExamineOrReveal: p.onExamineOrReveal,
        onCancelModes: p.onCancelModes,
        emergencyDrinkItem: p.emergencyDrinkItem,
        onEmergencyDrink: p.onEmergencyDrink,
        triggerWait: p.triggerWait,
        onOpenTalents: p.onOpenTalents,
        onOpenAlchemyRef: p.onOpenAlchemyRef,
        quickslot: p.quickslot,
        itemsById: p.itemsById,
        handleToolbarDoubleClick: p.handleToolbarDoubleClick,
        handleToolbarClick: p.handleToolbarClick,
      };
    };

    const controller = new KeyboardMovementController(getContext);
    controller.attach(window);

    return () => {
      controller.detach(window);
    };
  }, []);
}
