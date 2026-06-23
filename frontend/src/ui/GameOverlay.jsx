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
  return (
    <>
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
