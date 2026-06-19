export default function ActionIndicator({ myStats, onAction }) {
  const actions = myStats?.belongings?.weapon?.actions || [];
  const isZap = actions.includes('ZAP');
  const isThrow = actions.includes('THROW');
  const isImbue = !isZap && !isThrow && actions.includes('IMBUE');
  if (!isZap && !isThrow && !isImbue) return null;
  const action = isZap ? 'ZAP' : isThrow ? 'THROW' : 'IMBUE';
  const color = isZap ? '#8855cc' : isThrow ? '#cc7722' : '#55ccff';
  const label = isZap ? '⚡' : isThrow ? '🏹' : '🪄';
  const title = isZap ? 'Zap' : isThrow ? 'Throw' : 'Imbue';
  return (
    <div
      className="side-tag side-tag--action"
      style={{ borderColor: color }}
      onClick={() => onAction(action)}
      title={title}
    >
      <span style={{ fontSize: 16 }}>{label}</span>
    </div>
  );
}
