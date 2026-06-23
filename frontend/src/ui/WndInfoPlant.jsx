import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import IconTitle from './IconTitle';

// SPD WndInfoPlant.java port: name + description. Plants aren't yet a first-
// class entity in the backend, so this window is presented as a generic
// "tile-with-flavour" card — caller passes a name and description directly.
export default function WndInfoPlant({ name, description, onClose }) {
  const { t } = useTranslation();
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="wnd-overlay" onClick={onClose}>
      <div className="wnd-info-card" onClick={(e) => e.stopPropagation()}>
        <IconTitle
          icon={<div style={{ width: 16, height: 16, background: '#3a7a3a', border: '1px solid #444' }} />}
          title={name || t('tile.grass')}
        />
        {description && <div className="wnd-info-desc">{description}</div>}
      </div>
    </div>
  );
}
