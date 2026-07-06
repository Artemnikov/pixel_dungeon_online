import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';
import { actionLabel, orderedActions, titleColor } from './itemActions';
import { statLines } from './itemStatLines';
import { comparisonLines } from './itemComparison';
import useEntityName from './useEntityName';

export default function WndUseItem({ item, onAction, onAssignQuickslot, onClose, onOpenJournal, belongings }) {
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
  const stats = statLines(item, t);

  const compare = findComparison(item, belongings, t);

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
          {onOpenJournal && (
            <button
              className="wnd-item-journal"
              aria-label={t('journal.guide', 'Guide')}
              onClick={() => { AudioManager.play('CLICK'); onOpenJournal(); }}
            >
              i
            </button>
          )}
        </div>

        {item.description && (
          <div className="wnd-item-desc">{item.description}</div>
        )}

        {stats.length > 0 && (
          <div className="wnd-info-stats">
            {stats.map((l, i) => <div key={i} className="wnd-info-stat-row">{l}</div>)}
          </div>
        )}

        {compare && (
          <div className="wnd-info-compare">
            <div className="wnd-info-compare-header">{t('ui.comparedToEquipped')}</div>
            {compare.map((row, i) => (
              <div key={i} className="wnd-info-compare-row">
                <span className="wnd-info-compare-label">{row.label}</span>
                <span className="wnd-info-compare-val wnd-info-compare-eq">{row.eqVal}</span>
                <span className="wnd-info-compare-arrow">&rarr;</span>
                <span className="wnd-info-compare-val wnd-info-compare-item">{row.itemVal}</span>
              </div>
            ))}
          </div>
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

function findComparison(item, belongings, t) {
  if (!belongings || !item) return null;

  const wTypes = ['weapon', 'melee_weapon', 'staff', 'missile_weapon'];
  const isWeapon = wTypes.includes(item.type) || wTypes.includes(item.kind);
  const isArmor = item.type === 'wearable' || item.kind === 'armor';
  const isRing = item.kind === 'ring' || item.type === 'ring';

  if (isWeapon && belongings.weapon && belongings.weapon.id !== item.id) {
    return comparisonLines(item, belongings.weapon, t);
  }
  if (isArmor && belongings.armor && belongings.armor.id !== item.id) {
    return comparisonLines(item, belongings.armor, t);
  }
  if (isRing && belongings.ring && belongings.ring.id !== item.id) {
    return comparisonLines(item, belongings.ring, t);
  }

  return null;
}
