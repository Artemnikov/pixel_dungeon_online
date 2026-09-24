import { useLayoutEffect, useRef } from 'react';
import ItemActionButtons from './ItemActionButtons';
import useDismissOnOutsidePointer from './useDismissOnOutsidePointer';
import useRegisterWindow from '../game/window/useRegisterWindow';
import { WindowLevel } from '../game/window/WindowTypes';
import useEntityName from './useEntityName';

export default function RightClickMenu({ item, x, y, onAction, onAssignQuickslot, onClose }) {
  const ref = useRef(null);

  useRegisterWindow({
    id: 'right-click-menu',
    level: WindowLevel.FLOATING,
    onClose,
  });

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const nx = x + width > window.innerWidth ? Math.max(0, window.innerWidth - width - 4) : x;
    const ny = y + height > window.innerHeight ? Math.max(0, window.innerHeight - height - 4) : y;
    el.style.left = `${nx}px`;
    el.style.top = `${ny}px`;
  }, [x, y]);

  // Dismiss on outside pointerdown; the menu swallows its own pointerdown so
  // clicking an action button doesn't pre-close it.
  useDismissOnOutsidePointer(onClose);

  const itemName = useEntityName(item);
  if (!item) return null;

  return (
    <div
      ref={ref}
      className="rc-menu"
      style={{ left: x, top: y }}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <div className="rc-menu-title">{itemName}</div>
      <ItemActionButtons
        item={item}
        onAction={onAction}
        onAssignQuickslot={onAssignQuickslot}
        onClose={onClose}
      />
    </div>
  );
}
