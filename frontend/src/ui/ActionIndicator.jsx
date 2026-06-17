export default function ActionIndicator({ myStats, onAction }) {
  const actions = myStats?.belongings?.weapon?.actions || [];
  const isZap = actions.includes('ZAP');
  const isThrow = actions.includes('THROW');
  if (!isZap && !isThrow) return null;
  const color = isZap ? '#8855cc' : '#cc7722';
  const label = isZap ? '⚡' : '🏹';
  return (
    <div
      className="side-tag side-tag--action"
      style={{ borderColor: color }}
      onClick={() => onAction(isZap ? 'ZAP' : 'THROW')}
      title={isZap ? 'Zap' : 'Throw'}
    >
      <span style={{ fontSize: 16 }}>{label}</span>
    </div>
  );
}
