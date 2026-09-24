import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { isTargetSelection, canAutoAimFromQuickbar } from '../game/targetingModeInfo';

// In-game "Select target" pill, styled like EmergencyHealPrompt. Shown while a
// target-selection action is armed (throwables, wands, staffs, ranged weapons,
// aimed abilities, cleric spells, ...). Clicking it cancels targeting (Escape).
function TargetingPrompt({ targetingMode, itemsById, onCancel }) {
  const { t } = useTranslation();
  if (!isTargetSelection(targetingMode)) return null;
  const quickbarHint = canAutoAimFromQuickbar(targetingMode, itemsById);
  const label = quickbarHint
    ? t('ui.selectTargetQuickbar')
    : t('ui.selectTarget');
  return (
    <button
      type="button"
      className="targeting-prompt prompt-pill"
      onClick={(e) => { e.stopPropagation(); onCancel?.(false); }}
      title={label}
    >
      <span className="targeting-prompt__icon">+</span>
      <span className="targeting-prompt__label">{label}</span>
      <span className="prompt-pill__hint">[ESC]</span>
    </button>
  );
}

export default memo(TargetingPrompt);