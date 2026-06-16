export default function AttackIndicator({ myStats, onAttack }) {
  const target = myStats?.attack_target;
  if (!target) return null;
  return (
    <div className="side-tag side-tag--attack" onClick={() => onAttack(target.id)} title={`Attack ${target.name}`}>
      <svg viewBox="0 0 16 16" width="16" height="16" fill="#c03838">
        {/* sword/attack icon: simple cross */}
        <line x1="2" y1="2" x2="14" y2="14" stroke="#c03838" strokeWidth="2"/>
        <line x1="14" y1="2" x2="2" y2="14" stroke="#c03838" strokeWidth="2"/>
      </svg>
      <span className="side-tag__label">{target.name}</span>
    </div>
  );
}
