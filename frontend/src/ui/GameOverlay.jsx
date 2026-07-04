import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import GameMenu from './GameMenu';
import GameOverScreen from './GameOverScreen';
import VictoryScreen from './VictoryScreen';
import WndResurrect from './WndResurrect';

export default function GameOverlay({
  gameMenuOpen, onCloseMenu, onLeaveGame,
  isDowned, playerName, classType, level, depth, gold,
  subclass, armorAbility, talentLevels, talentDefs, inventory,
  selectedClass, scoreBreakdown, canResurrect, isVictory, onResurrect,
  onNewGame, onMenu, challenges,
}) {
  const { t } = useTranslation();
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  return (
    <>
      <button className="fullscreen-btn" onClick={toggleFullscreen} title={isFullscreen ? t('app.exitFullscreen') : t('app.fullscreen')}>
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          {isFullscreen ? (
            <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
          ) : (
            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
          )}
        </svg>
      </button>

      {gameMenuOpen && (
        <GameMenu
          depth={depth}
          challenges={challenges}
          onClose={onCloseMenu}
          onLeaveGame={onLeaveGame}
        />
      )}
      {!!isDowned && canResurrect && (
        <WndResurrect
          onConfirm={onResurrect}
          onDecline={onMenu}
        />
      )}
      {!!isDowned && isVictory && (
        <VictoryScreen
          scoreBreakdown={scoreBreakdown}
          onNewGame={onNewGame}
          onMenu={onMenu}
        />
      )}
      {!!isDowned && !canResurrect && !isVictory && (
        <GameOverScreen
          playerName={playerName}
          classType={classType || selectedClass}
          level={level || 1}
          depth={depth}
          gold={gold ?? 0}
          subclass={subclass}
          armorAbility={armorAbility}
          talentLevels={talentLevels}
          talentDefs={talentDefs}
          inventory={inventory}
          scoreBreakdown={scoreBreakdown}
          onNewGame={onNewGame}
          onMenu={onMenu}
        />
      )}
    </>
  );
}
