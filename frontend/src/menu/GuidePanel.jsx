import { useTranslation } from 'react-i18next';
import Panel from './Panel';

const GUIDE_PAGES = [
  'Intro', 'Examining', 'Surprise_Attacks', 'Identifying',
  'Food', 'Alchemy', 'Dieing', 'Searching', 'Strength',
  'Upgrades', 'Looting', 'Levelling', 'Positioning', 'Magic',
];

export default function GuidePanel({ onClose }) {
  const { t } = useTranslation();

  return (
    <Panel title={t('guide.title')} icon="JOURNAL" onClose={onClose} wide>
      {GUIDE_PAGES.map((pageId) => (
        <div key={pageId} className="opd-guide-section">
          <h3 className="opd-section-title">{t(`guide.pages.${pageId}.title`)}</h3>
          {t(`guide.pages.${pageId}.body`).split('\n\n').map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
      ))}
    </Panel>
  );
}
