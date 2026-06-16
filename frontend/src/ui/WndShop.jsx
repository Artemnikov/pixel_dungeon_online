import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';
import { entityDisplayName } from './useEntityName';

export default function WndShop({ npcId, stock, gold, backpackItems, onBuy, onSell, onClose }) {
  const { t } = useTranslation();
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const sellable = (backpackItems || []).filter(i => (i.value || 0) > 0 && i.kind !== 'gold');

  return (
    <div className="wnd-overlay wnd-shop-overlay" onClick={onClose}>
      <div className="wnd-shop" onClick={(e) => e.stopPropagation()}>
        <button
          className="wnd-bag-close"
          onClick={() => { AudioManager.play('CLICK'); onClose(); }}
          aria-label={t('menu.closeShop')}
        >
          ✕
        </button>
        <div className="wnd-shop-header">
          <span className="wnd-shop-title">{t('shop.title')}</span>
          <span className="inv-gold">{gold ?? 0}<i className="inv-gold-icon" /></span>
        </div>
        <div className="wnd-shop-columns">
          <div className="wnd-shop-col">
            <div className="wnd-shop-col-title">{t('shop.buy')}</div>
            <div className="wnd-shop-list">
              {stock.length === 0 && <div className="wnd-shop-empty">{t('shop.nothingForSale')}</div>}
              {stock.map(item => (
                <button
                  key={item.id}
                  className="wnd-shop-row"
                  disabled={(gold ?? 0) < (item.value || 0)}
                  onClick={() => { AudioManager.play('CLICK'); onBuy(npcId, item.id); }}
                >
                  <ItemIcon item={item} size={28} />
                  <span className="wnd-shop-name">{entityDisplayName(item, t)}</span>
                  <span className="wnd-shop-price">{item.value}<i className="inv-gold-icon" /></span>
                </button>
              ))}
            </div>
          </div>
          <div className="wnd-shop-col">
            <div className="wnd-shop-col-title">{t('shop.sell')}</div>
            <div className="wnd-shop-list">
              {sellable.length === 0 && <div className="wnd-shop-empty">{t('shop.nothingToSell')}</div>}
              {sellable.map(item => (
                <button
                  key={item.id}
                  className="wnd-shop-row"
                  onClick={() => { AudioManager.play('CLICK'); onSell(item.id); }}
                >
                  <ItemIcon item={item} size={28} />
                  <span className="wnd-shop-name">{entityDisplayName(item, t)}</span>
                  <span className="wnd-shop-price">{item.value}<i className="inv-gold-icon" /></span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
