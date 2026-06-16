import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import SettingsPanel from '../menu/SettingsPanel';

export default function GameMenu({ onClose, onLeaveGame }) {
  const { t } = useTranslation();
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape') {
        if (showSettings) {
          setShowSettings(false);
        } else {
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [showSettings, onClose]);

  if (showSettings) {
    return <SettingsPanel onClose={() => setShowSettings(false)} />;
  }

  return (
    <div className="game-menu-overlay" onClick={onClose}>
      <div className="game-menu" onClick={(e) => e.stopPropagation()}>
        <h2 className="game-menu-title">{t('game.menu')}</h2>
        <button className="game-menu-btn" onClick={() => setShowSettings(true)}>
          {t('game.settings')}
        </button>
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
