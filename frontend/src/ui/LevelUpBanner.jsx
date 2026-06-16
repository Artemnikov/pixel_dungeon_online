import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';

export default function LevelUpBanner({
  level,
  tierUnlocked,
  talentPoints,
  canChooseSubclass,
  canChooseArmorAbility,
  onOpenTalents,
  onDismiss,
}) {
  const { t } = useTranslation();
  const timerRef = useRef(null);
  const onDismissRef = useRef(onDismiss);
  useEffect(() => { onDismissRef.current = onDismiss; });

  useEffect(() => {
    timerRef.current = setTimeout(() => onDismissRef.current?.(), 3000);
    return () => clearTimeout(timerRef.current);
  }, [level]);

  const handleClick = () => {
    clearTimeout(timerRef.current);
    const hasMilestone = tierUnlocked || canChooseSubclass || canChooseArmorAbility;
    if (hasMilestone) onOpenTalents?.();
    onDismiss?.();
  };

  const totalPts = Object.values(talentPoints || {}).reduce((a, b) => a + b, 0);
  const milestone = canChooseSubclass ? t('ui.newSubclass')
    : canChooseArmorAbility ? t('ui.newAbility')
    : tierUnlocked ? t('ui.tierUnlocked', { tier: tierUnlocked })
    : null;

  return (
    <div className="levelup-banner" onClick={handleClick}>
      <div className="levelup-banner-content">
        <span className="levelup-text">{t('ui.levelUp', { level })}</span>
        {milestone && <span className="levelup-milestone">{milestone}</span>}
        {totalPts > 0 && (
          <span className="levelup-pts">{t('ui.talentPoints', { count: totalPts })}</span>
        )}
        <span className="levelup-hint">{t('ui.tapToView')}</span>
      </div>
    </div>
  );
}
