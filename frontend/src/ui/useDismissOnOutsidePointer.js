import { useEffect, useRef } from 'react';

/**
 * Dismiss a floating popup when the player clicks/taps anywhere outside it.
 * The popup's own container must stopPropagation on pointerdown so interactive
 * children (action buttons, etc.) don't dismiss it before their click handler
 * runs.
 *
 * The listener is attached on the next tick so the very gesture that opened the
 * popup doesn't immediately dismiss it, and `onClose` is kept in a ref so the
 * listener survives re-renders without churn.
 */
export default function useDismissOnOutsidePointer(onClose) {
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    const close = () => onCloseRef.current?.();
    const id = setTimeout(() => {
      window.addEventListener('pointerdown', close);
    }, 0);
    return () => {
      clearTimeout(id);
      window.removeEventListener('pointerdown', close);
    };
    // The listener holds no stale closure state: onClose is read through a ref,
    // so attach only once.
  }, []);
}