import { useEffect, useLayoutEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import { actionLabel, orderedActions } from './itemActions';
import useEntityName from './useEntityName';

export default function RightClickMenu({ item, x, y, onAction, onAssignQuickslot, onClose }) {
  const { t } = useTranslation();
  const ref = useRef(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const nx = x + width > window.innerWidth ? Math.max(0, window.innerWidth - width - 4) : x;
    const ny = y + height > window.innerHeight ? Math.max(0, window.innerHeight - height - 4) : y;
    el.style.left = `${nx}px`;
    el.style.top = `${ny}px`;
  }, [x, y]);

  useEffect(() => {
    const close = () => onClose();
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    const id = setTimeout(() => {
      window.addEventListener('pointerdown', close);
      window.addEventListener('keydown', onKey);
    }, 0);
    return () => {
      clearTimeout(id);
      window.removeEventListener('pointerdown', close);
      window.removeEventListener('keydown', onKey);
    };
  }, [onClose]);

  const itemName = useEntityName(item);
  if (!item) return null;

  const def = item.default_action;
  const run = (action) => {
    AudioManager.play('CLICK');
    onClose();
    onAction(item.id, action);
  };

  return (
    <div
      ref={ref}
      className="rc-menu"
      style={{ left: x, top: y }}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <div className="rc-menu-title">{itemName}</div>
      {orderedActions(item).map(action => (
        <button key={action} className={action === def ? 'default' : ''} onClick={() => run(action)}>
          {actionLabel(action, t)}
        </button>
      ))}
      {def && (
        <button
          className="qs-assign"
          onClick={() => { AudioManager.play('CLICK'); onAssignQuickslot(item.id); onClose(); }}
        >
          {t('ui.quickslot')}
        </button>
      )}
    </div>
  );
}
