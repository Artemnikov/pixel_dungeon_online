const COMBO_MOVES = {
  clobber: { count: 2, tint: '#00ff00', label: 'Clobber' },
  slam: { count: 4, tint: '#ccff00', label: 'Slam' },
  parry: { count: 6, tint: '#ffff00', label: 'Parry' },
  crush: { count: 8, tint: '#ffcc00', label: 'Crush' },
  fury: { count: 10, tint: '#ff0000', label: 'Fury' },
};

export default function ComboDisplay({
  subclass,
  comboCount,
  onUseComboMove,
}) {
  if (subclass !== 'gladiator' || !comboCount) return null;

  const unlockedMoves = Object.entries(COMBO_MOVES)
    .filter(([, move]) => comboCount >= move.count);

  return (
    <div className="combo-container">
      <div className="combo-label">
        Combo <span className="combo-count">{comboCount}</span>
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
              {move.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
