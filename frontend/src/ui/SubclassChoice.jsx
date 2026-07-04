import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getHeroIconIndex } from '../data/heroIcons';
import HeroIcon from './HeroIcon';

const SUBCLASS_IDS = ['berserker', 'gladiator', 'assassin', 'freerunner', 'battlemage', 'warlock', 'sniper', 'warden'];

function displayName(id) {
  return id.charAt(0).toUpperCase() + id.slice(1);
}

export default function SubclassChoice({ options, onChoose, onSkip }) {
  const { t } = useTranslation();
  const [confirm, setConfirm] = useState(null);
  const [info, setInfo] = useState(null);

  if (!options || options.length === 0) return null;

  if (confirm) {
    return (
      <div className="choice-overlay" onClick={() => setConfirm(null)}>
        <div className="wnd-options" onClick={(e) => e.stopPropagation()}>
          <div className="wnd-options-icon">
            <HeroIcon index={getHeroIconIndex('subclass', confirm)} size={32} />
          </div>
          <div className="wnd-options-title">
            {displayName(confirm)}
          </div>
          <div className="wnd-options-msg">{t('subclass.confirm')}</div>
          <div className="wnd-options-buttons">
            <button className="wnd-opt-btn yes" onClick={() => { onChoose(confirm); setConfirm(null); }}>
              {t('subclass.yes')}
            </button>
            <button className="wnd-opt-btn no" onClick={() => setConfirm(null)}>
              {t('subclass.no')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (info) {
    return (
      <div className="choice-overlay" onClick={() => setInfo(null)}>
        <div className="wnd-info-subclass" onClick={(e) => e.stopPropagation()}>
          <div className="wnd-info-title">
            <HeroIcon index={getHeroIconIndex('subclass', info)} size={32} />
            <span className="wnd-info-name">{displayName(info)}</span>
          </div>
          <div className="wnd-info-desc">{t(`subclass.${info}.full`)}</div>
          <button className="wnd-close-btn" onClick={() => setInfo(null)}>{t('subclass.close')}</button>
        </div>
      </div>
    );
  }

  return (
    <div className="choice-overlay" onClick={onSkip}>
      <div className="choice-modal wnd-choose-subclass" onClick={(e) => e.stopPropagation()}>
        <div className="choice-header">
          <span className="choice-header-icon">⚔</span>
          <span className="choice-header-title">{t('subclass.title')}</span>
        </div>
        <p className="choice-subtitle">{t('subclass.subtitle')}</p>
        <div className="choice-list">
          {options.map(sc => (
            <div key={sc} className="choice-list-item">
              <button
                className="choice-list-btn"
                onClick={() => setConfirm(sc)}
              >
                <span className="choice-list-name">{displayName(sc)}</span>
                <span className="choice-list-desc">{t(`subclass.${sc}.short`)}</span>
              </button>
              <button
                className="choice-info-btn"
                title={t('subclass.info')}
                onClick={() => setInfo(sc)}
              >
                ?
              </button>
            </div>
          ))}
        </div>
        <button className="choice-skip" onClick={onSkip}>
          {t('subclass.skip')}
        </button>
      </div>
    </div>
  );
}
