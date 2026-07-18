// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// WndResurrect — in-place respawn dialog (shown when a player dies with
// respawns remaining, on Easy or Medium difficulty). Replaces the former
// ankh-only stub.
import { useTranslation } from 'react-i18next';

export default function WndResurrect({ onConfirm, onDecline, respawnsUsed = 0, maxRespawns = 3, lootDropped = false }) {
  const { t } = useTranslation();
  const remaining = Math.max(0, maxRespawns - respawnsUsed);
  const descKey = lootDropped ? 'game.resurrect.descLost' : 'game.resurrect.desc';
  const descDefault = lootDropped
    ? 'You are reborn on this floor, but your gear was scattered where you fell. Half HP, debuffs cleared.'
    : 'You are reborn on this floor with your gear intact. Half HP, debuffs cleared.';

  return (
    <div className="wnd-resurrect-overlay">
      <div className="wnd-resurrect">
        <div className="wnd-resurrect__title">{t('game.resurrect.title', 'Rise from the dead?')}</div>
        <div className="wnd-resurrect__desc">{t(descKey, descDefault)}</div>
        <div className="wnd-resurrect__remaining">
          {t('game.resurrect.remaining', { count: remaining, defaultValue: 'Respawns remaining: {{count}}' })}
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
