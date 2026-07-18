// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// WndChasmJump — confirm dialog shown when a player steps onto a chasm tile
// (mirrors SPD's Chasm.heroJump() WndOptions, adapted to this engine's
// click-to-confirm pattern instead of Java's click-again-to-commit one).
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

export default function WndChasmJump({ onConfirm, onDecline }) {
  const { t } = useTranslation();

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onDecline();
      else if (e.key === 'Enter') onConfirm();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onConfirm, onDecline]);

  return (
    <div className="wnd-chasm-jump-overlay">
      <div className="wnd-chasm-jump">
        <div className="wnd-chasm-jump__title">{t('game.chasm.title', 'Chasm')}</div>
        <div className="wnd-chasm-jump__desc">{t('game.chasm.desc', 'Do you really want to jump into the chasm? A fall that far will be painful.')}</div>
        <div className="wnd-chasm-jump__actions">
          <button className="wnd-chasm-jump__btn wnd-chasm-jump__btn--yes" onClick={onConfirm}>
            {t('game.chasm.yes', 'Yes, I know what I\'m doing')}
          </button>
          <button className="wnd-chasm-jump__btn wnd-chasm-jump__btn--no" onClick={onDecline}>
            {t('game.chasm.no', 'No, I changed my mind')}
          </button>
        </div>
      </div>
    </div>
  );
}
