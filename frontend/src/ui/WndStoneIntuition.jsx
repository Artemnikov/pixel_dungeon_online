import { useTranslation } from 'react-i18next';
import WndBag from './WndBag';

export default function WndStoneIntuition({
  belongings, candidates, pickMode, possibleKinds,
  gold, energy, strength,
  onPickItem, onGuess, onClose,
}) {
  const { t } = useTranslation();

  if (pickMode === 'guess') {
    return (
      <div className="window stone-guess-window">
        <div className="window-title">{t('ui.whatIsThisItem')}</div>
        <div className="window-content">
          {possibleKinds.map((kind) => (
            <button
              key={kind}
              className="stone-guess-btn"
              onClick={() => onGuess(kind)}
            >
              {kind}
            </button>
          ))}
          <button className="stone-guess-cancel" onClick={onClose}>
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
      title={t('ui.chooseUnidentifiedItem')}
      onSelectItem={(item) => onPickItem(item.id)}
      onClose={onClose}
    />
  );
}
