import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import IconTitle from './IconTitle';

// SPD WndChallenges.java port: shows challenge toggles with descriptions.
// In the online version, challenges are set at character selection time,
// so this window is informational (shows which challenges are active and
// their effects). The only currently supported challenge is "stronger_bosses".
const CHALLENGES = [
  {
    id: 'stronger_bosses',
    nameKey: 'challenges.stronger_bosses',
    descKey: 'challenges.stronger_bosses_desc',
  },
];

export default function WndChallenges({ activeChallenges, onClose }) {
  const { t } = useTranslation();
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const active = new Set(
    Array.isArray(activeChallenges)
      ? activeChallenges
      : (activeChallenges || '').split(',').filter(Boolean)
  );

  return (
    <div className="wnd-overlay" onClick={onClose}>
      <div className="wnd-info-card" onClick={(e) => e.stopPropagation()}>
        <IconTitle
          icon={<div style={{ width: 16, height: 16, background: '#8a3a3a' }} />}
          title={t('challenges.title')}
        />
        <div className="wnd-info-desc">
          {t('challenges.intro', 'Challenges make the game harder. They are set at character selection and cannot be changed mid-run.')}
        </div>
        {CHALLENGES.map(ch => {
          const isActive = active.has(ch.id);
          return (
            <div key={ch.id} className={`wnd-challenge${isActive ? ' active' : ''}`}>
              <div className="wnd-challenge-header">
                <span className="wnd-challenge-name">{t(ch.nameKey)}</span>
                <span className={`wnd-challenge-status${isActive ? ' on' : ''}`}>
                  {isActive ? t('settings.on') : t('settings.off')}
                </span>
              </div>
              <div className="wnd-challenge-desc">{t(ch.descKey)}</div>
            </div>
          );
        })}
        <button className="wnd-close-btn" onClick={onClose}>{t('ui.close')}</button>
      </div>
    </div>
  );
}
