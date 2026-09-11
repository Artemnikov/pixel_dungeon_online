import { useTranslation } from 'react-i18next';
import IconTitle from './IconTitle';
import WndOverlay from './WndOverlay';
import { WindowLevel } from '../game/window/WindowTypes';

export default function WndInfoPlant({ name, description, plantType, onClose }) {
  const { t } = useTranslation();

  const card = (
    <div className="wnd-info-card" onClick={(e) => e.stopPropagation()}>
      <IconTitle
        icon={<div style={{ width: 16, height: 16, background: '#3a7a3a', border: '1px solid #444', borderRadius: '2px' }} />}
        title={name || t('tile.grass')}
      />
      {description && <div className="wnd-info-desc">{description}</div>}
    </div>
  );

  if (onClose) {
    return (
      <WndOverlay id="wnd-info-plant" level={WindowLevel.SECONDARY} onClose={onClose}>
        {card}
      </WndOverlay>
    );
  }

  return card;
}
