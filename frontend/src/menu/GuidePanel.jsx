import { useTranslation } from 'react-i18next';
import Panel from './Panel';

export default function GuidePanel({ onClose }) {
  const { t } = useTranslation();

  const sections = [
    { title: t('guide.title'), body: [t('guide.body1'), t('guide.body2'), t('guide.body3')] },
    { title: t('guide.combatTitle'), body: [t('guide.combat1'), t('guide.combat2'), t('guide.combat3')] },
    { title: t('guide.classesTitle'), body: [t('guide.classes1'), t('guide.classes2'), t('guide.classes3'), t('guide.classes4')] },
    { title: t('guide.multiplayerTitle'), body: [t('guide.multiplayer1'), t('guide.multiplayer2')] },
  ];

  return (
    <Panel title={t('panel.guide')} icon="JOURNAL" onClose={onClose} wide>
      {sections.map((section) => (
        <div key={section.title} className="opd-guide-section">
          <h3 className="opd-section-title">{section.title}</h3>
          {section.body.map((p, i) => <p key={i}>{p}</p>)}
        </div>
      ))}
    </Panel>
  );
}
