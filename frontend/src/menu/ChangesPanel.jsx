import { useTranslation } from 'react-i18next';
import Panel from './Panel';

export default function ChangesPanel({ onClose }) {
  const { t } = useTranslation();

  const entries = [
    { version: t('changelog.title'), title: t('changelog.titleName'), changes: [t('changelog.changes0'), t('changelog.changes1'), t('changelog.changes2'), t('changelog.changes3'), t('changelog.changes4')] },
    { version: t('changelog.v082'), title: t('changelog.v082Name'), changes: [t('changelog.v0820'), t('changelog.v0821'), t('changelog.v0822'), t('changelog.v0823')] },
    { version: t('changelog.v081'), title: t('changelog.v081Name'), changes: [t('changelog.v0810'), t('changelog.v0811'), t('changelog.v0812'), t('changelog.v0813'), t('changelog.v0814'), t('changelog.v0815'), t('changelog.v0816'), t('changelog.v0817'), t('changelog.v0818'), t('changelog.v0819'), t('changelog.v08110')] },
    { version: t('changelog.v062'), title: t('changelog.v062Name'), changes: [t('changelog.v0620'), t('changelog.v0621'), t('changelog.v0622'), t('changelog.v0623'), t('changelog.v0624'), t('changelog.v0625'), t('changelog.v0626')] },
    { version: t('changelog.v061'), title: t('changelog.v061Name'), changes: [t('changelog.v0610'), t('changelog.v0611'), t('changelog.v0612')] },
    { version: t('changelog.v060'), title: t('changelog.v060Name'), changes: [t('changelog.v0600'), t('changelog.v0601'), t('changelog.v0602'), t('changelog.v0603'), t('changelog.v0604')] },
    { version: t('changelog.v050'), title: t('changelog.v050Name'), changes: [t('changelog.v0500'), t('changelog.v0501'), t('changelog.v0502'), t('changelog.v0503')] },
    { version: t('changelog.v0411'), title: t('changelog.v0411Name'), changes: [t('changelog.v04110'), t('changelog.v04111'), t('changelog.v04112'), t('changelog.v04113'), t('changelog.v04114'), t('changelog.v04115'), t('changelog.v04116')] },
    { version: t('changelog.v046'), title: t('changelog.v046Name'), changes: [t('changelog.v0460'), t('changelog.v0461'), t('changelog.v0462'), t('changelog.v0463'), t('changelog.v0464'), t('changelog.v0465'), t('changelog.v0466'), t('changelog.v0467')] },
    { version: t('changelog.v045'), title: t('changelog.v045Name'), changes: [t('changelog.v0450')] },
    { version: t('changelog.v044'), title: t('changelog.v044Name'), changes: [t('changelog.v0440'), t('changelog.v0441'), t('changelog.v0442'), t('changelog.v0443'), t('changelog.v0444'), t('changelog.v0445'), t('changelog.v0446'), t('changelog.v0447'), t('changelog.v0448'), t('changelog.v0449')] },
    { version: t('changelog.v042'), title: t('changelog.v042Name'), changes: [t('changelog.v0420'), t('changelog.v0421'), t('changelog.v0422')] },
    { version: t('changelog.v041'), title: t('changelog.v041Name'), changes: [t('changelog.v0410'), t('changelog.v0411'), t('changelog.v0412')] },
    { version: t('changelog.v040'), title: t('changelog.v040Name'), changes: [t('changelog.v0400'), t('changelog.v0401'), t('changelog.v0402'), t('changelog.v0403'), t('changelog.v0404')] },
    { version: t('changelog.v031'), title: t('changelog.v031Name'), changes: [t('changelog.v0310'), t('changelog.v0311'), t('changelog.v0312'), t('changelog.v0313'), t('changelog.v0314')] },
    { version: t('changelog.v030'), title: t('changelog.v030Name'), changes: [t('changelog.v0300'), t('changelog.v0301'), t('changelog.v0302'), t('changelog.v0303'), t('changelog.v0304'), t('changelog.v0305')] },
    { version: t('changelog.v020'), title: t('changelog.v020Name'), changes: [t('changelog.v0200'), t('changelog.v0201'), t('changelog.v0202'), t('changelog.v0203'), t('changelog.v0204'), t('changelog.v0205'), t('changelog.v0206'), t('changelog.v0207'), t('changelog.v0208'), t('changelog.v0209'), t('changelog.v0210')] },
    { version: t('changelog.v010'), title: t('changelog.v010Name'), changes: [t('changelog.v0100'), t('changelog.v0101'), t('changelog.v0102'), t('changelog.v0103')] },
    { version: t('changelog.v00x'), title: t('changelog.v00xName'), changes: [t('changelog.v00x0'), t('changelog.v00x1'), t('changelog.v00x2'), t('changelog.v00x3')] },
  ];

  return (
    <Panel title={t('panel.changes')} icon="CHANGES" onClose={onClose} wide>
      {entries.map((entry) => (
        <div key={entry.version} className="opd-changelog-entry">
          <h3 className="opd-section-title">
            {entry.version} <span className="opd-changelog-name">{entry.title}</span>
          </h3>
          <ul>
            {entry.changes.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      ))}
    </Panel>
  );
}
