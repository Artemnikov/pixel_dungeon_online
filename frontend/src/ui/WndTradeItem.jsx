import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import WndInfoItem from './WndInfoItem';

export default function WndTradeItem({ item, mode, onConfirm, onCancel, price }) {
  const { t } = useTranslation();
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onCancel(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel]);

  if (!item) return null;
  const isSell = mode === 'sell';
  const label = isSell
    ? t('shop.sellConfirm', { price })
    : t('shop.buyConfirm', { price });

  return (
    <div className="wnd-overlay" onClick={onCancel}>
      <div className="wnd-info-card wnd-trade" onClick={(e) => e.stopPropagation()}>
        <WndInfoItem item={item} />
        <div className="wnd-trade-actions">
          <button className="wnd-trade-btn" onClick={() => { AudioManager.play('CLICK'); onConfirm(); }}>
            {label}
          </button>
          <button className="wnd-trade-btn cancel" onClick={() => { AudioManager.play('CLICK'); onCancel(); }}>
            {t('ui.cancel')}
          </button>
        </div>
      </div>
    </div>
  );
}
