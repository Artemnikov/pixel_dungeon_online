// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// WndResurrect — resurrection dialog. Two modes:
// 1. Ankh mode (hasAnkh=true): player picks 2 items to keep, rest goes to LostBackpack
// 2. Standard mode (hasAnkh=false): simple "Respawn" / "Give up" dialog
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

export default function WndResurrect({
  onConfirm, onDecline, onAnkhChoice,
  hasAnkh = false, inventory = [], keptItems = [], onToggleItem,
}) {
  const { t } = useTranslation();

  if (hasAnkh) {
    return (
      <AnkhItemPicker
        inventory={inventory}
        keptItems={keptItems}
        onToggleItem={onToggleItem}
        onConfirm={onConfirm}
        onDecline={onDecline}
        onAnkhChoice={onAnkhChoice}
      />
    );
  }

  return (
    <div className="wnd-resurrect-overlay">
      <div className="wnd-resurrect">
        <div className="wnd-resurrect__title">{t('game.resurrect.title', 'Rise from the dead?')}</div>
        <div className="wnd-resurrect__desc">
          {t('game.resurrect.descLost', 'You are reborn on this floor, but your gear was scattered where you fell. Half HP, debuffs cleared.')}
        </div>
        <div className="wnd-resurrect__actions">
          <button className="wnd-resurrect__btn wnd-resurrect__btn--yes" onClick={onConfirm}>
            {t('game.resurrect.yes', 'Respawn')}
          </button>
          <button className="wnd-resurrect__btn wnd-resurrect__btn--no" onClick={onDecline}>
            {t('game.resurrect.no', 'Give up')}
          </button>
        </div>
      </div>
    </div>
  );
}

function AnkhItemPicker({ inventory, keptItems, onToggleItem, onDecline, onAnkhChoice }) {
  const { t } = useTranslation();
  const maxKept = 2;

  const selectableItems = useMemo(() =>
    inventory.filter(item => item.kind !== 'ankh' && item.kind !== 'lost_backpack' && !item.is_bag),
    [inventory],
  );

  const handleConfirm = () => {
    if (keptItems.length === 2) {
      onAnkhChoice(keptItems);
    } else if (keptItems.length === 0) {
      // Default to first 2 equippable items or first 2 items
      const defaults = selectableItems.slice(0, 2).map(i => i.id);
      onAnkhChoice(defaults);
    }
  };

  return (
    <div className="wnd-resurrect-overlay">
      <div className="wnd-resurrect wnd-resurrect--ankh">
        <div className="wnd-resurrect__title">
          {t('game.resurrect.ankhTitle', 'Ankh of Resurrection')}
        </div>
        <div className="wnd-resurrect__desc">
          {t('game.resurrect.ankhDesc', 'Choose 2 items to keep. The rest will be placed in a Lost Backpack on the ground.')}
        </div>
        <div className="wnd-resurrect__item-grid">
          {selectableItems.map(item => {
            const isSelected = keptItems.includes(item.id);
            const disabled = !isSelected && keptItems.length >= maxKept;
            return (
              <button
                key={item.id}
                className={`wnd-resurrect__item ${isSelected ? 'wnd-resurrect__item--selected' : ''} ${disabled ? 'wnd-resurrect__item--disabled' : ''}`}
                onClick={() => !disabled && onToggleItem(item.id)}
                disabled={disabled}
                title={item.name}
              >
                <span className="wnd-resurrect__item-name">{item.name}</span>
                {item.level > 0 && <span className="wnd-resurrect__item-level">+{item.level}</span>}
              </button>
            );
          })}
        </div>
        <div className="wnd-resurrect__selected-count">
          {t('game.resurrect.selectedCount', { count: keptItems.length, max: maxKept, defaultValue: '{{count}}/{{max}} items selected' })}
        </div>
        <div className="wnd-resurrect__actions">
          <button
            className="wnd-resurrect__btn wnd-resurrect__btn--yes"
            onClick={handleConfirm}
            disabled={keptItems.length === 0}
          >
            {t('game.resurrect.ankhConfirm', 'Resurrect')}
          </button>
          <button className="wnd-resurrect__btn wnd-resurrect__btn--no" onClick={onDecline}>
            {t('game.resurrect.no', 'Give up')}
          </button>
        </div>
      </div>
    </div>
  );
}
