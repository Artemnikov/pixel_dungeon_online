import { useEffect, useState } from 'react';
import SettingsPanel from '../menu/SettingsPanel';

export default function GameMenu({ onClose, onLeaveGame }) {
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
        <h2 className="game-menu-title">Menu</h2>
        <button className="game-menu-btn" onClick={() => setShowSettings(true)}>
          Settings
        </button>
        <button className="game-menu-btn danger" onClick={onLeaveGame}>
          Leave Game
        </button>
        <button className="game-menu-btn accent" onClick={onClose}>
          Resume
        </button>
      </div>
    </div>
  );
}
