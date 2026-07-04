import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

// SPD WndJournal.java port (simplified): tabbed journal with Guide, Catalog,
// and Story tabs. The Guide tab reuses the existing GuidePanel content. The
// Catalog tab shows discovered items (not yet tracked server-side — shows a
// placeholder). The Story tab shows lore texts for visited depths.
// Opens from the GameMenu or a journal button.

function GuideTab() {
  const { t } = useTranslation();
  return (
    <div className="wnd-journal-tab">
      <div className="wnd-info-desc">
        {t('journal.guideText', 'The dungeon is divided into 5 regions, each with a boss. Defeat bosses to progress deeper. Find the Amulet of Yendor on floor 26 and return to the surface to win.')}
      </div>
      <div className="wnd-journal-depths">
        <div className="wnd-journal-depth-row"><span>Sewers</span><span>1-5</span></div>
        <div className="wnd-journal-depth-row"><span>Prison</span><span>6-10</span></div>
        <div className="wnd-journal-depth-row"><span>Caves</span><span>11-15</span></div>
        <div className="wnd-journal-depth-row"><span>Dwarven City</span><span>16-20</span></div>
        <div className="wnd-journal-depth-row"><span>Demon Halls</span><span>21-26</span></div>
      </div>
    </div>
  );
}

function CatalogTab() {
  const { t } = useTranslation();
  return (
    <div className="wnd-journal-tab">
      <div className="wnd-info-desc">
        {t('journal.catalogEmpty', 'Item catalog tracking is not yet available in the online version.')}
      </div>
    </div>
  );
}

function StoryTab({ depth }) {
  const { t } = useTranslation();
  const regions = [
    { name: t('journal.sewers', 'Sewers'), desc: t('journal.sewersStory', 'The sewers beneath the city are infested with rats, gnolls, and slimes. Goo, a conglomerate of vile substances, guards the way down.') },
    { name: t('journal.prison', 'Prison'), desc: t('journal.prisonStory', 'The abandoned prison is home to skeletons, thieves, and guards. Tengu, the enigmatic assassin, awaits in the depths.') },
    { name: t('journal.caves', 'Caves'), desc: t('journal.cavesStory', 'The caves are filled with bats, gnoll brutes, and shamans. DM-300, an ancient dwarven defense machine, guards the passage.') },
    { name: t('journal.city', 'Dwarven City'), desc: t('journal.cityStory', 'The dwarven city is ruled by the undead King of Dwarves. Monks, golems, and warlocks patrol the halls.') },
    { name: t('journal.halls', 'Demon Halls'), desc: t('journal.hallsStory', 'The demon halls are the domain of Yog-Dzewa. Evil Eyes, scorpios, and ripper demons stalk the darkness.') },
  ];
  const currentRegion = Math.min(4, Math.floor((depth - 1) / 5));

  return (
    <div className="wnd-journal-tab">
      {regions.map((r, i) => (
        <div
          key={i}
          className={`wnd-journal-story-region${i <= currentRegion ? ' visited' : ''}`}
        >
          <div className="wnd-journal-story-name">{r.name}</div>
          <div className="wnd-journal-story-desc">{i <= currentRegion ? r.desc : '???'}</div>
        </div>
      ))}
    </div>
  );
}

export default function WndJournal({ depth, onClose }) {
  const { t } = useTranslation();
  const [tab, setTab] = useState(0);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const tabs = [
    { label: t('journal.guide', 'Guide'), icon: '?' },
    { label: t('journal.catalog', 'Catalog'), icon: '◇' },
    { label: t('journal.story', 'Story'), icon: '✦' },
  ];

  return (
    <div className="wnd-overlay" onClick={onClose}>
      <div className="wnd-hero" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-hero-tabs">
          {tabs.map((tb, i) => (
            <button
              key={i}
              className={`wnd-hero-tab-btn${tab === i ? ' active' : ''}`}
              onClick={() => setTab(i)}
            >
              <span className="wnd-hero-tab-icon">{tb.icon}</span>
              <span className="wnd-hero-tab-label">{tb.label}</span>
            </button>
          ))}
        </div>
        <div className="wnd-hero-content">
          {tab === 0 && <GuideTab />}
          {tab === 1 && <CatalogTab />}
          {tab === 2 && <StoryTab depth={depth} />}
        </div>
        <button className="wnd-close-btn" onClick={onClose}>{t('ui.close')}</button>
      </div>
    </div>
  );
}
