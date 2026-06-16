import GameMenu from './GameMenu';
import GameOverScreen from './GameOverScreen';

export default function GameOverlay({
  gameMenuOpen, onCloseMenu, onLeaveGame,
  isDowned, playerName, classType, level, depth, gold,
  subclass, armorAbility, talentLevels, talentDefs, inventory,
  selectedClass, onNewGame, onMenu,
}) {
  return (
    <>
      {gameMenuOpen && (
        <GameMenu
          onClose={onCloseMenu}
          onLeaveGame={onLeaveGame}
        />
      )}
      {!!isDowned && (
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
          onNewGame={onNewGame}
          onMenu={onMenu}
        />
      )}
    </>
  );
}
