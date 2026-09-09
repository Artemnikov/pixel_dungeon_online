import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import TalentIcon from './TalentIcon';
import Icon from '../menu/Icon';
import WndOverlay from './WndOverlay';
import { WindowLevel } from '../game/window/WindowTypes';

export default function WndInfoTalent({
  talentId,
  name,
  desc: descProp,
  currentLevel,
  maxPoints,
  canUpgrade,
  onUpgrade,
  onClose,
}) {
  const { t } = useTranslation();
  const desc = useMemo(() => {
    if (descProp) return descProp;
    const key = `talent.descriptions.${talentId}`;
    return t(key, { defaultValue: '' });
  }, [descProp, talentId, t]);
  const atMax = currentLevel >= maxPoints;

  return (
    <WndOverlay id="wnd-info-talent" level={WindowLevel.SECONDARY} onClose={onClose}>
      <div className="wnd-info-talent" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-info-title">
          <TalentIcon talentId={talentId} />
          <span className="wnd-info-name">{name || talentId}</span>
          {currentLevel > 0 && <span className="wnd-info-level">+{currentLevel}</span>}
        </div>
        <div className="wnd-info-desc">{desc}</div>
        <div className="wnd-info-points">
          {t('ui.points', { current: currentLevel, max: maxPoints })}
        </div>
        <div className="wnd-info-actions">
          {canUpgrade ? (
            <button className="wnd-upgrade-btn" onClick={() => { onUpgrade?.(talentId); onClose?.(); }}>
              <Icon name="TALENT" scale={1} className="wnd-upgrade-icon" />
              {t('ui.upgrade')}
            </button>
          ) : (
            <button className="wnd-upgrade-btn disabled" disabled>
              {atMax ? t('ui.maxed') : t('ui.locked')}
            </button>
          )}
          <button className="wnd-close-btn" onClick={onClose}>{t('ui.close')}</button>
        </div>
      </div>
    </WndOverlay>
  );
}
