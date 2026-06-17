import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import RankingsPane from './RankingsPane';

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
  onNewGame,
  onMenu,
}) {
  const { t } = useTranslation();
  const [shown, setShown] = useState(false);
  const [showRankings, setShowRankings] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(true));
    return () => cancelAnimationFrame(id);
  }, []);

  useEffect(() => {
    if (shown) {
      const id = setTimeout(() => setShowRankings(true), 1500);
      return () => clearTimeout(id);
    }
  }, [shown]);

  return (
    <>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '20px',
          zIndex: 50,
          pointerEvents: 'none',
          opacity: shown ? 1 : 0,
          transition: 'opacity 2s ease-in',
        }}
      >
        <div
          style={{
            fontFamily: 'monospace',
            fontSize: '48px',
            fontWeight: 'bold',
            color: '#e74c3c',
            textShadow: '0 2px 6px #000',
            letterSpacing: '2px',
          }}
        >
          {t('game.youDied')}
        </div>
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
          </div>
        )}
      </div>

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
        />
      )}
    </>
  );
}
