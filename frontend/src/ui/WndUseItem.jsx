import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';
import ItemActionButtons from './ItemActionButtons';
import useDismissOnOutsidePointer from './useDismissOnOutsidePointer';
import useRegisterWindow from '../game/window/useRegisterWindow';
import { WindowLevel } from '../game/window/WindowTypes';
import { titleColor } from './itemActions';
import { statLines } from './itemStatLines';
import { comparisonLines } from './itemComparison';
import useEntityName from './useEntityName';

// Left-click item dialog: a compact, non-blocking panel anchored at
// bottom-center. Registered with modal:false and rendered as a bare fixed
// element (no full-screen overlay), so player movement and world clicks keep
// working underneath it; Escape or an outside click dismisses it.
export default function WndUseItem({ item, onAction, onAssignQuickslot, onClose, onOpenJournal, belongings }) {
  const { t } = useTranslation();

  useRegisterWindow({
    id: 'wnd-use-item',
    level: WindowLevel.FLOATING,
    onClose,
    closeOnEscape: true,
    modal: false,
  });

  // Dismiss on outside pointerdown. The panel swallows its own pointerdown
  // so clicking an action button doesn't pre-close it.
  useDismissOnOutsidePointer(onClose);

  const itemName = useEntityName(item);
  if (!item) return null;

  const level = item.level_known && item.level ? `${item.level > 0 ? '+' : ''}${item.level}` : null;
  const stats = statLines(item, t);

  const compare = findComparison(item, belongings, t);

  return (
    <div
      className="wnd-use-item-popup"
      role="dialog"
      aria-label={itemName}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <div className="wnd-item">
        <div className="wnd-item-title">
          <ItemIcon item={item} size={32} />
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
          <ItemActionButtons
            item={item}
            onAction={onAction}
            onAssignQuickslot={onAssignQuickslot}
            onClose={onClose}
          />
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
