import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import RankingsPane from './RankingsPane';
import WndScoreBreakdown from './WndScoreBreakdown';

export default function GameOverScreen({
  playerName,
  classType,
  level,
  depth,
  gold,
  subclass,
  armorAbility,
  talentLevels,
  talentDefs,
  inventory,
  scoreBreakdown,
  deathCause,
  onNewGame,
  onMenu,
}) {
  const { t } = useTranslation();
  const [shown, setShown] = useState(false);
  const [showRankings, setShowRankings] = useState(false);
  const [showScoreBreakdown, setShowScoreBreakdown] = useState(false);

  useEffect(() => {
    const id = setTimeout(() => setShown(true), 3000);
    return () => clearTimeout(id);
  }, []);

  return (
    <>
      <div
        className={`wnd-death-dialog ${shown ? 'wnd-death-dialog--visible' : ''}`}
        role="dialog"
        aria-label={t('game.youDied')}
        onPointerDown={(e) => e.stopPropagation()}
        onMouseDown={(e) => e.stopPropagation()}
        onTouchStart={(e) => e.stopPropagation()}
      >
        <div className="wnd-death-title">
          {deathCause === 'fall' ? t('game.youDiedFell', 'You fell to death...') : t('game.youDied')}
        </div>

        <div className="wnd-death-stats">
          <div className="wnd-death-stat-row">
            <span className="wnd-death-stat-label">{t('rankings.class')}</span>
            <span className="wnd-death-stat-value">{classType} {subclass || ''} (Lvl {level})</span>
          </div>
          <div className="wnd-death-stat-row">
            <span className="wnd-death-stat-label">{t('rankings.depth')}</span>
            <span className="wnd-death-stat-value">{depth}</span>
          </div>
          {scoreBreakdown && (
            <>
              <div className="wnd-death-stat-row">
                <span className="wnd-death-stat-label">{t('game.score.kills', 'Enemies slain')}</span>
                <span className="wnd-death-stat-value">{scoreBreakdown.kills}</span>
              </div>
              <div className="wnd-death-stat-row">
                <span className="wnd-death-stat-label">{t('game.score.gold', 'Gold collected')}</span>
                <span className="wnd-death-stat-value">{scoreBreakdown.gold}</span>
              </div>
            </>
          )}
        </div>

        <div className="wnd-death-actions">
          <button className="wnd-death-btn wnd-death-btn--primary" onClick={onNewGame}>
            {t('game.newGame', 'New Game')}
          </button>
          <button className="wnd-death-btn" onClick={onMenu}>
            {t('game.menuBtn', 'Menu')}
          </button>
          <button className="wnd-death-btn wnd-death-btn--secondary" onClick={() => setShowRankings(true)}>
            {t('rankings.title', 'Rankings')}
          </button>
          {scoreBreakdown?.total_score != null && (
            <button className="wnd-death-btn wnd-death-btn--secondary" onClick={() => setShowScoreBreakdown(true)}>
              {t('score.title', 'Score')}
            </button>
          )}
        </div>
      </div>

      {showScoreBreakdown && (
        <WndScoreBreakdown
          scoreBreakdown={scoreBreakdown}
          onClose={() => setShowScoreBreakdown(false)}
        />
      )}

      {showRankings && (
        <RankingsPane
          playerName={playerName}
          classType={classType}
          level={level}
          depth={depth}
          gold={gold}
          subclass={subclass}
          armorAbility={armorAbility}
          talentLevels={talentLevels}
          talentDefs={talentDefs}
          inventory={inventory}
          onNewGame={onNewGame}
          onMenu={onMenu}
          onClose={() => setShowRankings(false)}
        />
      )}
    </>
  );
}
