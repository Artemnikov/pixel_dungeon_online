import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import { actionLabel, orderedActions } from './itemActions';

// Shared action-buttons row for item popups (WndUseItem, RightClickMenu).
// Renders the item's ordered action buttons plus an optional
// quickslot-assign button; callers wrap it in their own layout container
// (e.g. .wnd-item-actions) and provide the close/action wiring.
export default function ItemActionButtons({ item, onAction, onAssignQuickslot, onClose }) {
  const { t } = useTranslation();

  if (!item) return null;

  const def = item.default_action;
  const run = (action) => {
    AudioManager.play('CLICK');
    onClose();
    onAction(item.id, action);
  };

  return (
    <>
      {orderedActions(item).map(action => (
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
    </>
  );
}