// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// WndResurrect — ankh resurrection dialog (shown when player dies with ankh in inventory)
import { useTranslation } from 'react-i18next';

export default function WndResurrect({ onConfirm, onDecline }) {
  const { t } = useTranslation();

  return (
    <div className="wnd-resurrect-overlay">
      <div className="wnd-resurrect">
        <div className="wnd-resurrect__title">{t('game.resurrect.title', 'Rise from the dead?')}</div>
        <div className="wnd-resurrect__desc">{t('game.resurrect.desc', 'Your ankh shatters and you are reborn on this floor.')}</div>
        <div className="wnd-resurrect__actions">
          <button className="wnd-resurrect__btn wnd-resurrect__btn--yes" onClick={onConfirm}>
            {t('game.resurrect.yes', 'Yes')}
          </button>
          <button className="wnd-resurrect__btn wnd-resurrect__btn--no" onClick={onDecline}>
            {t('game.resurrect.no', 'No')}
          </button>
        </div>
      </div>
    </div>
  );
}
