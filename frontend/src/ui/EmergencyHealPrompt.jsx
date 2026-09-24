import { memo } from 'react';
import { useTranslation } from 'react-i18next';

function EmergencyHealPrompt({ item, onDrink }) {
  const { t } = useTranslation();
  const isWaterskin = item?.type === 'waterskin';
  const label = isWaterskin
    ? t('ui.lowHpWaterskin', { volume: item.volume || 0, max: 20 })
    : t('ui.lowHpDrink');
  return (
    <button
      type="button"
      className="emergency-heal-prompt prompt-pill"
      onClick={(e) => { e.stopPropagation(); onDrink(); }}
      title={label}
    >
      <span className="emergency-heal-prompt__icon">+</span>
      <span className="emergency-heal-prompt__label">{label}</span>
      <span className="prompt-pill__hint">[SPACE]</span>
    </button>
  );
}

export default memo(EmergencyHealPrompt);
