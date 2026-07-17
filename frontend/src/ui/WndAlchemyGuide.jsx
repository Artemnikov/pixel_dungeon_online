// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// Alchemy guide window (SPD WndJournal.AlchemyTab). Opened from the guide
// button inside the alchemy station. Shows the 9 alchemy-guide pages from
// `journal.document.alchemy_guide.*` (Document.ALCHEMY_GUIDE): a row of
// category icon buttons selects the page, then the page title + body text
// is shown, with Prev/Next + Close controls.
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';

// Page keys + icon coords, in SPD AlchemyTab order (sprites[] in WndJournal).
// Icons are representative items.png cells for each category holder sprite.
const PAGES = [
  { key: 'potions',        coords: [3, 24] },  // SEED_HOLDER
  { key: 'stones',         coords: [0, 21] },  // STONE_HOLDER
  { key: 'energy_food',    coords: [3, 1] },   // FOOD_HOLDER / energy crystal
  { key: 'exotic_potions', coords: [0, 22] },  // POTION_HOLDER
  { key: 'exotic_scrolls', coords: [0, 19] },  // SCROLL_HOLDER
  { key: 'bombs',          coords: [0, 5] },   // BOMB_HOLDER
  { key: 'weapons',        coords: [3, 9] },   // MISSILE_HOLDER
  { key: 'brews_elixirs',  coords: [0, 22] },  // ELIXIR_HOLDER
  { key: 'spells',         coords: [3, 17] },  // SPELL_HOLDER
];

export default function WndAlchemyGuide({ onClose }) {
  const { t } = useTranslation();
  const [page, setPage] = useState(0);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose?.();
      else if (e.key === 'ArrowLeft') setPage(p => Math.max(0, p - 1));
      else if (e.key === 'ArrowRight') setPage(p => Math.min(PAGES.length - 1, p + 1));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const select = (i) => { AudioManager.play('CLICK'); setPage(i); };
  const current = PAGES[page];

  return (
    <div className="wnd-overlay" onClick={onClose}>
      <div className="wnd-alchemy-guide" onClick={(e) => e.stopPropagation()}>
        <h2 className="wnd-alchemy-guide-title">{t('alchemy.guide.title')}</h2>

        <div className="wnd-alchemy-guide-pages">
          {PAGES.map((p, i) => (
            <button
              key={p.key}
              className={`wnd-alchemy-guide-page-btn${i === page ? ' active' : ''}`}
              title={t(`alchemy.guide.${p.key}.title`)}
              onClick={() => select(i)}
            >
              <ItemIcon item={{}} coords={p.coords} size={24} />
            </button>
          ))}
        </div>

        <div className="wnd-alchemy-guide-body">
          <h3 className="wnd-alchemy-guide-page-title">
            {t(`alchemy.guide.${current.key}.title`)}
          </h3>
          <p className="wnd-alchemy-guide-page-text">
            {t(`alchemy.guide.${current.key}.body`)}
          </p>
        </div>

        <div className="wnd-alchemy-guide-controls">
          <button
            className="wnd-alchemy-guide-nav"
            disabled={page === 0}
            onClick={() => select(page - 1)}
          >{t('alchemy.guide.prev')}</button>
          <span className="wnd-alchemy-guide-counter">{page + 1}/{PAGES.length}</span>
          <button
            className="wnd-alchemy-guide-nav"
            disabled={page === PAGES.length - 1}
            onClick={() => select(page + 1)}
          >{t('alchemy.guide.next')}</button>
          <button className="wnd-close-btn" onClick={onClose}>
            {t('alchemy.guide.close')}
          </button>
        </div>
      </div>
    </div>
  );
}
