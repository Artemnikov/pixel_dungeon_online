import { useEffect, useRef } from 'react';
import { windowManager } from './WindowManager';
import { WindowLevel, WindowBackdrop } from './WindowTypes';

export function useRegisterWindow(options = {}) {
  const {
    id,
    level = WindowLevel.BASE,
    enabled = true,
  } = options || {};

  const optionsRef = useRef(options);
  useEffect(() => {
    optionsRef.current = options;
  });

  useEffect(() => {
    if (!enabled || !id) return undefined;

    windowManager.register({
      id,
      level,
      get onClose() {
        return optionsRef.current?.onClose;
      },
      get closeOnEscape() {
        return optionsRef.current?.closeOnEscape ?? true;
      },
      get closeOnBackdrop() {
        return optionsRef.current?.closeOnBackdrop ?? true;
      },
      get backdrop() {
        return optionsRef.current?.backdrop ?? WindowBackdrop.DIM;
      },
      get modal() {
        return optionsRef.current?.modal ?? true;
      },
      get digitActions() {
        return optionsRef.current?.digitActions;
      },
      onKeyDown: (code, e, ctx) => optionsRef.current?.onKeyDown?.(code, e, ctx),
      onKeyUp: (code, e, ctx) => optionsRef.current?.onKeyUp?.(code, e, ctx),
    });

    return () => {
      windowManager.unregister(id);
    };
  }, [id, level, enabled]);
}

export default useRegisterWindow;
