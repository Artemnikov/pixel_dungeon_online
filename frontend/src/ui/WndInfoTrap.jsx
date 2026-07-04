import { useTranslation } from 'react-i18next';
import IconTitle from './IconTitle';

function TrapIcon({ trapType }) {
  const colors = {
    worn_dart: '#888', tengu_dart: '#c33',
    burning_trap: '#e80', blazing_trap: '#f60',
  };
  return (
    <div style={{
      width: 16, height: 16, background: colors[trapType] || '#888',
      border: '1px solid #444', imageRendering: 'pixelated',
    }} />
  );
}

export default function WndInfoTrap({ trapType, active = true }) {
  const { t } = useTranslation();
  const nameKey = `trap.${trapType}`;
  const descKey = `trap.desc.${trapType}`;
  const name = t(nameKey, { defaultValue: trapType });
  const desc = (active ? '' : `${t('trap.inactive')}\n\n`) + t(descKey, { defaultValue: '' });

  return (
    <div className="wnd-info-card">
      <IconTitle icon={<TrapIcon trapType={trapType} />} title={name} />
      {desc && <div className="wnd-info-desc">{desc}</div>}
    </div>
  );
}
