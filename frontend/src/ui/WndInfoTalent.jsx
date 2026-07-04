import { useMemo, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import TalentIcon from './TalentIcon';

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
  const overlayRef = useRef(null);
  const desc = useMemo(() => {
    if (descProp) return descProp;
    const key = `talent.descriptions.${talentId}`;
    return t(key, { defaultValue: '' });
  }, [descProp, talentId, t]);
  const atMax = currentLevel >= maxPoints;

  useEffect(() => {
    overlayRef.current?.focus();
  }, []);

  return (
    <div
      className="wnd-overlay"
      tabIndex={-1}
      ref={overlayRef}
      onClick={onClose}
      onKeyDown={(e) => {
        if (e.key === 'Escape') {
          e.stopPropagation();
          onClose();
        }
      }}
    >
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
              <TalentIcon talentId={talentId} className="wnd-upgrade-icon" />
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
    </div>
  );
}
