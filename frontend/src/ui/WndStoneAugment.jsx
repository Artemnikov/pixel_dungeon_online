import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import WndBag from './WndBag';

export default function WndStoneAugment({
  belongings, candidates,
  gold, energy, strength,
  onChoose, onClose,
}) {
  const { t } = useTranslation();
  const [selectedItemId, setSelectedItemId] = useState(null);

  if (selectedItemId) {
    const selectedItem = Object.values(belongings?.items || {}).find(i => i.id === selectedItemId);
    const isWeapon = selectedItem?.type === 'weapon';
    const options = isWeapon
      ? [{ key: 'speed', label: t('ui.augmentSpeed') }, { key: 'damage', label: t('ui.augmentDamage') }]
      : [{ key: 'evasion', label: t('ui.augmentEvasion') }, { key: 'defense', label: t('ui.augmentDefense') }];

    return (
      <div className="window stone-augment-window">
        <div className="window-title">{t('ui.chooseAugment')}</div>
        <div className="window-content">
          {options.map((opt) => (
            <button
              key={opt.key}
              className="stone-augment-btn"
              onClick={() => onChoose(selectedItemId, opt.key)}
            >
              {opt.label}
            </button>
          ))}
          <button className="stone-augment-back" onClick={() => setSelectedItemId(null)}>
            {t('ui.goBack')}
          </button>
          <button className="stone-augment-cancel" onClick={onClose}>
            {t('ui.cancel')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <WndBag
      belongings={belongings}
      gold={gold}
      energy={energy}
      strength={strength}
      selectMode
      itemFilter={(item) => candidates.includes(item.id)}
      title={t('ui.chooseItemToAugment')}
      onSelectItem={(item) => setSelectedItemId(item.id)}
      onClose={onClose}
    />
  );
}
