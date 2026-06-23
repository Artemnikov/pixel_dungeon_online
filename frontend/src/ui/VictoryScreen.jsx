// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// VictoryScreen — shown when the player escapes with the Amulet of Yendor
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import WndScoreBreakdown from './WndScoreBreakdown';

export default function VictoryScreen({ scoreBreakdown, onNewGame, onMenu }) {
  const { t } = useTranslation();
  const [shown, setShown] = useState(false);
  const [showScoreBreakdown, setShowScoreBreakdown] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(true));
    return () => cancelAnimationFrame(id);
  }, []);

  return (
    <div className={`victory-screen${shown ? ' victory-screen--shown' : ''}`}>
      <div className="victory-screen__title">{t('game.victory', 'You Win!')}</div>
      <div className="victory-screen__subtitle">{t('game.victoryDesc', 'You escaped the dungeon with the Amulet of Yendor!')}</div>
      {scoreBreakdown && (
        <div className="game-over-score">
          <div className="game-over-score__row">
            <span>{t('game.score.kills', 'Enemies slain')}</span>
            <span>{scoreBreakdown.kills}</span>
          </div>
          <div className="game-over-score__row">
            <span>{t('game.score.floors', 'Floors explored')}</span>
            <span>{scoreBreakdown.floors}</span>
          </div>
          <div className="game-over-score__row">
            <span>{t('game.score.gold', 'Gold collected')}</span>
            <span>{scoreBreakdown.gold}</span>
          </div>
          {scoreBreakdown.total_score != null && (
            <button
              className="wnd-close-btn"
              style={{ marginTop: '8px', width: '100%' }}
              onClick={() => setShowScoreBreakdown(true)}
            >
              {t('score.title')}
            </button>
          )}
        </div>
      )}
      <div className="game-over-actions">
        <button className="game-over-btn" onClick={onNewGame}>{t('game.newGame', 'New Game')}</button>
        <button className="game-over-btn" onClick={onMenu}>{t('game.menu', 'Main Menu')}</button>
      </div>
      {showScoreBreakdown && (
        <WndScoreBreakdown
          scoreBreakdown={scoreBreakdown}
          onClose={() => setShowScoreBreakdown(false)}
        />
      )}
    </div>
  );
}
