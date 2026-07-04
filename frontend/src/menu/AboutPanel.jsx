import { useTranslation, Trans } from 'react-i18next';
import Panel from './Panel';
import { APP_VERSION } from './content/changelog';

export default function AboutPanel({ onClose }) {
  const { t } = useTranslation();
  return (
    <Panel title={t('panel.about')} icon="SHPX" onClose={onClose}>
      <div className="opd-about">
        <p className="opd-about-title">{t('about.heading')}</p>
        <p className="opd-about-version">v{APP_VERSION}</p>
        <p>
          <Trans i18nKey="about.p1" components={{ 1: <strong />, 5: <strong /> }} />
        </p>
        <p>{t('about.p2')}</p>
        <p className="opd-about-links">
          <a href="https://shatteredpixel.com" target="_blank" rel="noreferrer">{t('about.linkShattered')}</a>
          {' · '}
          <a href="https://patreon.com/ShatteredPixel" target="_blank" rel="noreferrer">{t('about.linkPatreon')}</a>
          {' · '}
          <a href="https://github.com/00-Evan/shattered-pixel-dungeon" target="_blank" rel="noreferrer">{t('about.linkSource')}</a>
        </p>
        <p className="opd-about-copy">
          <Trans i18nKey="about.copyright" components={{ 1: <a href="https://github.com/Artemnikov/shattered_pixel_dungeon_online" target="_blank" rel="noreferrer" /> }} />
        </p>
      </div>
    </Panel>
  );
}
