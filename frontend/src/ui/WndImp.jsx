import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';

export default function WndImp({ npcId, text, canClaim, onClaim, onClose }) {
  const { t } = useTranslation();
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="wnd-overlay" onClick={onClose}>
      <div className="wnd-item" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-item-title">{t('imp.title')}</div>
        <div className="wnd-item-desc">{text}</div>
        <div className="wnd-item-actions">
          {canClaim && (
            <button
              className="default"
              onClick={() => { AudioManager.play('CLICK'); onClaim(npcId); }}
            >
              {t('imp.claimReward')}
            </button>
          )}
          <button onClick={() => { AudioManager.play('CLICK'); onClose(); }}>{t('imp.close')}</button>
        </div>
      </div>
    </div>
  );
}
