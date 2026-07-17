import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';

const itemLabel = (item) => {
  if (!item) return '';
  const lvl = item.level_known && item.level > 0 ? ` +${item.level}` : '';
  return `${item.name}${lvl}`;
};

// Port of WndWandmaker.java: picking one of the two offered wands opens an
// item-info preview with confirm/cancel first, same pattern as WndSadGhost's
// reward choice, so a misclick doesn't forfeit the other wand.
export default function WndWandmaker({ npcId, text, canClaim, wand1, wand2, onChoose, onClose }) {
  const { t } = useTranslation();
  const [pending, setPending] = useState(null); // 'wand1' | 'wand2' | null

  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== 'Escape') return;
      if (pending) setPending(null);
      else onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [pending, onClose]);

  const pendingItem = pending === 'wand1' ? wand1 : pending === 'wand2' ? wand2 : null;

  if (pendingItem) {
    return (
      <div className="wnd-overlay" onClick={() => setPending(null)}>
        <div className="wnd-item" onClick={(e) => e.stopPropagation()}>
          <div className="wnd-item-title">
            <ItemIcon item={pendingItem} size={16} />
            <span>{itemLabel(pendingItem)}</span>
          </div>
          {pendingItem.description && (
            <div className="wnd-item-desc">{pendingItem.description}</div>
          )}
          <div className="wnd-item-actions">
            <button
              className="default"
              onClick={() => { AudioManager.play('CLICK'); onChoose(npcId, pending); }}
            >
              {t('wandmaker.confirm')}
            </button>
            <button onClick={() => { AudioManager.play('CLICK'); setPending(null); }}>
              {t('wandmaker.cancel')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="wnd-overlay" onClick={onClose}>
      <div className="wnd-item" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-item-title">{t('wandmaker.title')}</div>
        <div className="wnd-item-desc">{text}</div>
        <div className="wnd-item-actions">
          {canClaim && wand1 && (
            <button
              className="default"
              onClick={() => { AudioManager.play('CLICK'); setPending('wand1'); }}
            >
              {t('wandmaker.takeWand1')}: {itemLabel(wand1)}
            </button>
          )}
          {canClaim && wand2 && (
            <button
              className="default"
              onClick={() => { AudioManager.play('CLICK'); setPending('wand2'); }}
            >
              {t('wandmaker.takeWand2')}: {itemLabel(wand2)}
            </button>
          )}
          <button onClick={() => { AudioManager.play('CLICK'); onClose(); }}>{t('wandmaker.close')}</button>
        </div>
      </div>
    </div>
  );
}
