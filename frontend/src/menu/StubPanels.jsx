import { useTranslation } from 'react-i18next';
import Panel from './Panel';

export function RankingsPanel({ onClose }) {
  const { t } = useTranslation();
  return (
    <Panel title={t('panel.rankings')} icon="RANKINGS" onClose={onClose}>
      <div className="opd-empty">
        <p>{t('rankings.emptyTitle')}</p>
        <p className="opd-empty-sub">{t('rankings.emptySub')}</p>
      </div>
    </Panel>
  );
}

export function NewsPanel({ onClose }) {
  const { t } = useTranslation();
  return (
    <Panel title={t('panel.news')} icon="NEWS" onClose={onClose}>
      <div className="opd-empty">
        <p>{t('rankings.newsEmptyTitle')}</p>
        <p className="opd-empty-sub">{t('rankings.newsEmptySub')}</p>
      </div>
    </Panel>
  );
}
