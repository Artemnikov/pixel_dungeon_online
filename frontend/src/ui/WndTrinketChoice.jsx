// SPD TrinketCatalyst.WndTrinket: pick one of four rolled trinkets.
import { useTranslation } from 'react-i18next';
import ItemIcon from './ItemIcon';
import { coordsForKind } from '../rendering/sprites';

export default function WndTrinketChoice({ kinds, onChoose, onClose }) {
  const { t } = useTranslation();
  return (
    <div className="choice-modal-backdrop">
      <div className="choice-modal alchemy-trinket-choice">
        <h3>{t('alchemy.chooseTrinket')}</h3>
        <div className="alchemy-trinket-row">
          {kinds.map((kind) => (
            <button key={kind} className="alchemy-trinket-btn" onClick={() => onChoose(kind)}>
              <ItemIcon item={{ kind }} coords={coordsForKind(kind)} size={40} />
            </button>
          ))}
        </div>
        <button onClick={onClose}>{t('alchemy.later')}</button>
      </div>
    </div>
  );
}
