import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import SettingsPanel from '../menu/SettingsPanel';
import WndJournal from './WndJournal';
import FeedbackModal from './FeedbackModal';
import WndOverlay from './WndOverlay';
import { WindowLevel } from '../game/window/WindowTypes';

export default function GameMenu({ depth, guidePages, onClose, onLeaveGame, onReplayTutorial }) {
  const { t } = useTranslation();
  const [showSettings, setShowSettings] = useState(false);
  const [showJournal, setShowJournal] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);

  if (showFeedback) {
    return <FeedbackModal onClose={() => setShowFeedback(false)} defaultContext={`InGame (Floor ${depth || 1})`} />;
  }

  if (showJournal) {
    return <WndJournal depth={depth} guidePages={guidePages} onClose={() => setShowJournal(false)} />;
  }

  if (showSettings) {
    return <SettingsPanel onClose={() => setShowSettings(false)} />;
  }

  return (
    <WndOverlay id="game-menu" level={WindowLevel.BASE} onClose={onClose} className="game-menu-overlay">
      <div className="game-menu" onClick={(e) => e.stopPropagation()}>
        <h2 className="game-menu-title">{t('game.menu')}</h2>
        <button className="game-menu-btn" onClick={() => setShowJournal(true)}>
          {t('journal.title')}
        </button>
        <button className="game-menu-btn" onClick={() => setShowSettings(true)}>
          {t('game.settings')}
        </button>
        <button className="game-menu-btn" onClick={() => setShowFeedback(true)}>
          {t('menu.feedback', 'Feedback')}
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
    </WndOverlay>
  );
}
