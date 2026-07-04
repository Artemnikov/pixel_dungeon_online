import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';

const itemLabel = (item) => {
  if (!item) return '';
  const lvl = item.level_known && item.level > 0 ? ` +${item.level}` : '';
  return `${item.name}${lvl}`;
};

// Port of WndSadGhost + its RewardWindow (WndSadGhost.java:84-159): picking
// weapon/armor opens an item-info preview with confirm/cancel before the
// choice is actually committed, so a misclick doesn't forfeit the other reward.
export default function WndSadGhost({ npcId, text, canClaim, weapon, armor, onChoose, onClose }) {
  const { t } = useTranslation();
  const [pending, setPending] = useState(null); // 'weapon' | 'armor' | null

  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== 'Escape') return;
      if (pending) setPending(null);
      else onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [pending, onClose]);

  const pendingItem = pending === 'weapon' ? weapon : pending === 'armor' ? armor : null;

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
              {t('ghost.confirm')}
            </button>
            <button onClick={() => { AudioManager.play('CLICK'); setPending(null); }}>
              {t('ghost.cancel')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="wnd-overlay" onClick={onClose}>
      <div className="wnd-item" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-item-title">{t('ghost.title')}</div>
        <div className="wnd-item-desc">{text}</div>
        <div className="wnd-item-actions">
          {canClaim && weapon && (
            <button
              className="default"
              onClick={() => { AudioManager.play('CLICK'); setPending('weapon'); }}
            >
              {t('ghost.takeWeapon')}: {itemLabel(weapon)}
            </button>
          )}
          {canClaim && armor && (
            <button
              className="default"
              onClick={() => { AudioManager.play('CLICK'); setPending('armor'); }}
            >
              {t('ghost.takeArmor')}: {itemLabel(armor)}
            </button>
          )}
          <button onClick={() => { AudioManager.play('CLICK'); onClose(); }}>{t('ghost.close')}</button>
        </div>
      </div>
    </div>
  );
}
