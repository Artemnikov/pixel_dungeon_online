import { useTranslation } from 'react-i18next';

const COMBO_MOVES = {
  clobber: { count: 2, tint: '#00ff00', labelKey: 'combat.clobber' },
  slam: { count: 4, tint: '#ccff00', labelKey: 'combat.slam' },
  parry: { count: 6, tint: '#ffff00', labelKey: 'combat.parry' },
  crush: { count: 8, tint: '#ffcc00', labelKey: 'combat.crush' },
  fury: { count: 10, tint: '#ff0000', labelKey: 'combat.fury' },
};

export default function ComboDisplay({
  subclass,
  comboCount,
  onUseComboMove,
}) {
  const { t } = useTranslation();
  if (subclass !== 'gladiator' || !comboCount) return null;

  const unlockedMoves = Object.entries(COMBO_MOVES)
    .filter(([, move]) => comboCount >= move.count);

  return (
    <div className="combo-container">
      <div className="combo-label">
        {t('combat.combo')} <span className="combo-count">{t('combat.comboCount', { count: comboCount })}</span>
      </div>
      {unlockedMoves.length > 0 && (
        <div className="combo-moves">
          {unlockedMoves.map(([id, move]) => (
            <button
              key={id}
              className="combo-move-btn"
              style={{ color: move.tint, borderColor: move.tint }}
              onClick={() => onUseComboMove?.(id)}
            >
              {t(move.labelKey)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
