import { useTranslation } from 'react-i18next';

export default function WndChooseEnchant({
  options, isWeapon,
  onChoose, onClose,
}) {
  const { t } = useTranslation();

  return (
    <div className="window choose-enchant-window">
      <div className="window-title">
        {isWeapon ? t('ui.chooseEnchantment') : t('ui.chooseGlyph')}
      </div>
      <div className="window-content">
        <p className="choose-enchant-desc">
          {t('ui.chooseEnchantDesc')}
        </p>
        {options.map((opt, i) => (
          <button
            key={opt}
            className="choose-enchant-btn"
            onClick={() => onChoose(i)}
          >
            {t(`enchant.${opt}`, opt.replace(/_/g, ' '))}
          </button>
        ))}
        <button className="choose-enchant-cancel" onClick={onClose}>
          {t('ui.cancel')}
        </button>
      </div>
    </div>
  );
}
