// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// WndChasmJump — confirm dialog shown when a player steps onto a chasm tile
// (mirrors SPD's Chasm.heroJump() WndOptions, adapted to this engine's
// click-to-confirm pattern instead of Java's click-again-to-commit one).
import { useTranslation } from 'react-i18next';

export default function WndChasmJump({ onConfirm, onDecline }) {
  const { t } = useTranslation();

  return (
    <div className="wnd-chasm-jump-overlay">
      <div className="wnd-chasm-jump">
        <div className="wnd-chasm-jump__title">{t('game.chasm.title', 'Jump into the chasm?')}</div>
        <div className="wnd-chasm-jump__desc">{t('game.chasm.desc', "You'll fall to the floor below and take damage.")}</div>
        <div className="wnd-chasm-jump__actions">
          <button className="wnd-chasm-jump__btn wnd-chasm-jump__btn--yes" onClick={onConfirm}>
            {t('game.chasm.yes', 'Yes')}
          </button>
          <button className="wnd-chasm-jump__btn wnd-chasm-jump__btn--no" onClick={onDecline}>
            {t('game.chasm.no', 'No')}
          </button>
        </div>
      </div>
    </div>
  );
}
