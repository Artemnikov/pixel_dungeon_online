import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import SettingsPanel from '../menu/SettingsPanel';
import WndJournal from './WndJournal';
import WndChallenges from './WndChallenges';

export default function GameMenu({ depth, guidePages, challenges, onClose, onLeaveGame, onReplayTutorial }) {
  const { t } = useTranslation();
  const [showSettings, setShowSettings] = useState(false);
  const [showJournal, setShowJournal] = useState(false);
  const [showChallenges, setShowChallenges] = useState(false);

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape') {
        if (showChallenges) setShowChallenges(false);
        else if (showJournal) setShowJournal(false);
        else if (showSettings) setShowSettings(false);
        else onClose();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [showSettings, showJournal, showChallenges, onClose]);

  if (showChallenges) {
    return <WndChallenges activeChallenges={challenges} onClose={() => setShowChallenges(false)} />;
  }

  if (showJournal) {
    return <WndJournal depth={depth} guidePages={guidePages} onClose={() => setShowJournal(false)} />;
  }

  if (showSettings) {
    return <SettingsPanel onClose={() => setShowSettings(false)} />;
  }

  return (
    <div className="game-menu-overlay" onClick={onClose}>
      <div className="game-menu" onClick={(e) => e.stopPropagation()}>
        <h2 className="game-menu-title">{t('game.menu')}</h2>
        <button className="game-menu-btn" onClick={() => setShowJournal(true)}>
          {t('journal.title')}
        </button>
        <button className="game-menu-btn" onClick={() => setShowChallenges(true)}>
          {t('challenges.title')}
        </button>
        <button className="game-menu-btn" onClick={() => setShowSettings(true)}>
          {t('game.settings')}
        </button>
        {onReplayTutorial && (
          <button className="game-menu-btn" onClick={() => { onClose(); onReplayTutorial(); }}>
            {t('tutorial.replay')}
          </button>
        )}
        <button className="game-menu-btn danger" onClick={onLeaveGame}>
          {t('game.leaveGame')}
        </button>
        <button className="game-menu-btn accent" onClick={onClose}>
          {t('game.resume')}
        </button>
      </div>
    </div>
  );
}
