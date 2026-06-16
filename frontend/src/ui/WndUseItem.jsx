import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';
import { actionLabel, orderedActions, titleColor } from './itemActions';
import useEntityName from './useEntityName';

export default function WndUseItem({ item, onAction, onAssignQuickslot, onClose }) {
  const { t } = useTranslation();
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const itemName = useEntityName(item);
  if (!item) return null;

  const def = item.default_action;
  const actions = orderedActions(item);
  const level = item.level_known && item.level ? `${item.level > 0 ? '+' : ''}${item.level}` : null;

  const run = (action) => {
    AudioManager.play('CLICK');
    onClose();
    onAction(item.id, action);
  };

  return (
    <div className="wnd-overlay" onClick={onClose}>
      <div className="wnd-item" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-item-title">
          <ItemIcon item={item} size={16} />
          <span style={{ color: titleColor(item) }}>
            {itemName}{level ? ` ${level}` : ''}
          </span>
        </div>

        {item.description && (
          <div className="wnd-item-desc">{item.description}</div>
        )}

        <div className="wnd-item-actions">
          {actions.map(action => (
            <button
              key={action}
              className={action === def ? 'default' : ''}
              onClick={() => run(action)}
            >
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
      </div>
    </div>
  );
}
