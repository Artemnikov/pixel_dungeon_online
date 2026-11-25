import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getHeroIconIndex } from '../data/heroIcons';
import HeroIcon from './HeroIcon';
import WndOverlay from './WndOverlay';
import WndInfoArmorAbility from './WndInfoArmorAbility';
import { WindowLevel, WindowBackdrop } from '../game/window/WindowTypes';

function talentIdToAbility(tid) {
  return tid.replace(/_(talent|ability)$/, '');
}

export default function ArmorAbilityChoice({ options, onChoose, onSkip, abilitySelectors }) {
  const { t } = useTranslation();
  const [confirm, setConfirm] = useState(null);
  const [info, setInfo] = useState(null);

  if (!options || options.length === 0) return null;

  const confirmAbility = abilitySelectors?.[confirm] || talentIdToAbility(confirm || '');

  if (confirm) {
    return (
      <WndOverlay
        id="wnd-armor-ability-confirm"
        level={WindowLevel.DIALOG}
        backdrop={WindowBackdrop.DARK}
        onClose={() => setConfirm(null)}
        className="choice-overlay"
      >
        <div className="wnd-options" onClick={(e) => e.stopPropagation()}>
          <div className="wnd-options-icon">
            <HeroIcon index={getHeroIconIndex('ability', confirmAbility)} size={32} />
          </div>
          <div className="wnd-options-title">
            {t(`ability.${confirmAbility}.name`, { defaultValue: confirmAbility.replace(/_/g, ' ') })}
          </div>
          <div className="wnd-options-msg">{t('ability.confirm')}</div>
          <div className="wnd-options-buttons">
            <button className="wnd-opt-btn yes" onClick={() => { onChoose(confirm); setConfirm(null); }}>
              {t('subclass.yes')}
            </button>
            <button className="wnd-opt-btn no" onClick={() => setConfirm(null)}>
              {t('subclass.no')}
            </button>
          </div>
        </div>
      </WndOverlay>
    );
  }

  if (info) {
    const infoAbility = abilitySelectors?.[info] || talentIdToAbility(info || '');
    return <WndInfoArmorAbility ability={infoAbility} onClose={() => setInfo(null)} />;
  }

  return (
    <WndOverlay
      id="wnd-armor-ability-choice"
      level={WindowLevel.BASE}
      backdrop={WindowBackdrop.DARK}
      onClose={onSkip}
      className="choice-overlay"
    >
      <div className="choice-modal wnd-choose-armor-ability" onClick={(e) => e.stopPropagation()}>
        <div className="choice-header">
          <span className="choice-header-icon">🛡</span>
          <span className="choice-header-title">{t('ability.title')}</span>
        </div>
        <p className="choice-subtitle">{t('ability.subtitle')}</p>
        <div className="choice-list">
          {options.map(tid => {
            const ability = abilitySelectors?.[tid] || talentIdToAbility(tid);
            return (
              <div key={tid} className="choice-list-item">
                <button
                  className="choice-list-btn"
                  onClick={() => setConfirm(tid)}
                >
                  <span className="choice-list-name">{t(`ability.${ability}.name`, { defaultValue: ability.replace(/_/g, ' ') })}</span>
                  <span className="choice-list-desc">{t(`ability.${ability}.desc`)}</span>
                </button>
                <button
                  className="choice-info-btn"
                  title={t('subclass.info')}
                  onClick={() => setInfo(tid)}
                >
                  ?
                </button>
              </div>
            );
          })}
        </div>
        <button className="choice-skip" onClick={onSkip}>
          {t('ability.skip')}
        </button>
      </div>
    </WndOverlay>
  );
}
