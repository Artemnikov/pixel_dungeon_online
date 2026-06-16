import { useTranslation } from 'react-i18next';

const PREP_TIERS = [
  { min: 1.0, labelKey: 'Tier 0', dmg: '+10%' },
  { min: 3.0, labelKey: 'Tier 1', dmg: '+20%' },
  { min: 5.0, labelKey: 'Tier 2', dmg: '+35%' },
  { min: 9.0, labelKey: 'Tier 3', dmg: '+50%' },
];

export default function PrepStrikeButton({
  subclass,
  invisible,
  prepSeconds,
  onPrepStrike,
}) {
  const { t } = useTranslation();
  if (subclass !== 'assassin' || !invisible || !prepSeconds || prepSeconds < 1.0) {
    return null;
  }

  let tier = -1;
  for (let i = PREP_TIERS.length - 1; i >= 0; i--) {
    if (prepSeconds >= PREP_TIERS[i].min) { tier = i; break; }
  }

  const info = tier >= 0 ? PREP_TIERS[tier] : null;

  return (
    <div className="prep-btn-container">
      <button
        type="button"
        className="prep-btn"
        onClick={() => onPrepStrike?.()}
        title={t('combat.prepTooltip', { tier: info?.labelKey || '?', dmg: info?.dmg || '?', secs: Math.round(prepSeconds) })}
      >
        <div className="prep-btn-label">
          {t('combat.prepStrike')}
          {info && <span className="prep-btn-tier"> {info.labelKey}</span>}
        </div>
        <div className="prep-btn-bar">
          <div className="prep-btn-fill" style={{
            width: `${Math.min(100, (prepSeconds / 9) * 100)}%`
          }} />
        </div>
      </button>
    </div>
  );
}
