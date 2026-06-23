import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import IconTitle from './IconTitle';
import HeroIcon from './HeroIcon';
import WndInfoBuff from './WndInfoBuff';
import buffsImg from '../assets/pixel-dungeon/interfaces/buffs.png';

const BUFF_SIZE = 7;
const BUFF_COLS = 18;

const CLASS_ICON_INDEX = { warrior: 0, mage: 1, rogue: 2, huntress: 3 };

// SPD WndHero.java port: tabbed hero info window with Stats / Talents / Buffs
// tabs. Opens from the StatusPane avatar click (which currently opens the
// talent pane) or a dedicated hero-info key.
function BuffRow({ buff, onClick }) {
  const idx = buff.icon ?? 0;
  const col = idx % BUFF_COLS;
  const row = Math.floor(idx / BUFF_COLS);
  const px = BUFF_SIZE * 2;
  const remaining = buff.remaining != null && buff.duration
    ? ` (${Math.ceil(buff.remaining)}s)`
    : '';
  return (
    <div className="wnd-hero-buff" onClick={() => onClick(buff)}>
      <div style={{
        width: px, height: px,
        backgroundImage: `url(${buffsImg})`,
        backgroundPosition: `-${col * px}px -${row * px}px`,
        backgroundSize: `${BUFF_COLS * px}px ${px * 8}`,
        imageRendering: 'pixelated',
        flexShrink: 0,
      }} />
      <span>{buff.name}{remaining}</span>
    </div>
  );
}

function StatsTab({ myStats, depth, gold }) {
  const { t } = useTranslation();
  const classIcon = CLASS_ICON_INDEX[myStats?.classType] ?? 0;
  const className = t(`class.${myStats?.classType || 'warrior'}`, {
    defaultValue: myStats?.classType || 'Warrior',
  });
  const title = myStats?.name
    ? `${myStats.name}\n${t('ui.lv', { level: myStats.level })} ${className}`
    : `${t('ui.lv', { level: myStats.level })} ${className}`;

  const rows = [
    { label: t('ui.str', { defaultValue: 'STR' }), value: myStats?.strength ?? '?' },
    {
      label: t('ui.hpStat'),
      value: myStats?.shield > 0
        ? `${myStats.hp}+${myStats.shield}/${myStats.maxHp}`
        : `${myStats.hp}/${myStats.maxHp}`,
    },
    { label: t('ui.expStat', { defaultValue: 'EXP' }), value: `${myStats?.exp ?? 0}/${myStats?.maxExp ?? 10}` },
    { label: t('rankings.gold'), value: gold ?? 0 },
    { label: t('rankings.depth'), value: depth ?? 1 },
  ];

  return (
    <div className="wnd-hero-tab">
      <IconTitle icon={<HeroIcon index={classIcon} size={16} />} title={title} />
      <div className="wnd-hero-stats">
        {rows.map((r, i) => (
          <div key={i} className="wnd-hero-stat-row">
            <span className="wnd-hero-stat-label">{r.label}</span>
            <span className="wnd-hero-stat-value">{r.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function BuffsTab({ effects, onBuffClick }) {
  const { t } = useTranslation();
  if (!effects || effects.length === 0) {
    return <div className="wnd-hero-tab"><div className="wnd-info-desc">{t('ui.noBuffs', { defaultValue: 'No active buffs.' })}</div></div>;
  }
  return (
    <div className="wnd-hero-tab">
      {effects.map((buff, i) => (
        <BuffRow key={i} buff={buff} onClick={onBuffClick} />
      ))}
    </div>
  );
}

export default function WndHero({ myStats, depth, gold, onOpenTalents, onClose }) {
  const { t } = useTranslation();
  const [tab, setTab] = useState(0);
  const [buffPopup, setBuffPopup] = useState(null);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const tabs = [
    { label: t('ui.stats'), icon: '★' },
    { label: t('ui.talents'), icon: '✦' },
    { label: t('ui.buffs'), icon: '✧' },
  ];

  const handleTabClick = (i) => {
    if (i === 1 && onOpenTalents) {
      // Talents tab opens the full TalentPane (which has upgrade controls).
      onClose?.();
      onOpenTalents();
      return;
    }
    setTab(i);
  };

  return (
    <>
      <div className="wnd-overlay" onClick={onClose}>
        <div className="wnd-hero" onClick={(e) => e.stopPropagation()}>
          <div className="wnd-hero-tabs">
            {tabs.map((tb, i) => (
              <button
                key={i}
                className={`wnd-hero-tab-btn${tab === i ? ' active' : ''}`}
                onClick={() => handleTabClick(i)}
              >
                <span className="wnd-hero-tab-icon">{tb.icon}</span>
                <span className="wnd-hero-tab-label">{tb.label}</span>
              </button>
            ))}
          </div>
          <div className="wnd-hero-content">
            {tab === 0 && <StatsTab myStats={myStats} depth={depth} gold={gold} />}
            {tab === 1 && (
              <div className="wnd-hero-tab">
                <div className="wnd-info-desc">{t('ui.tapToView')}</div>
              </div>
            )}
            {tab === 2 && <BuffsTab effects={myStats?.effects} onBuffClick={setBuffPopup} />}
          </div>
          <button className="wnd-close-btn" onClick={onClose}>{t('ui.close')}</button>
        </div>
      </div>
      {buffPopup && (
        <WndInfoBuff buff={buffPopup} onClose={() => setBuffPopup(null)} />
      )}
    </>
  );
}
