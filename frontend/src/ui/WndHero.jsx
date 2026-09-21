import { useState, memo } from 'react';
import { useTranslation } from 'react-i18next';
import IconTitle from './IconTitle';
import HeroIcon from './HeroIcon';
import WndInfoBuff from './WndInfoBuff';
import TalentPane from './TalentPane';
import WndOverlay from './WndOverlay';
import { WindowLevel } from '../game/window/WindowTypes';
import buffsImg from '../assets/pixel-dungeon/interfaces/buffs.png';

const BUFF_SIZE = 7;
const BUFF_COLS = 18;

const CLASS_ICON_INDEX = { warrior: 0, mage: 1, rogue: 2, huntress: 3, duelist: 4, cleric: 5 };

// SPD WndHero.java port: tabbed hero window with Stats / Talents / Buffs tabs.
// The Talents tab embeds the full TalentPane (with upgrade controls). Opened
// via the `t` key (talents tab), avatar click (stats tab), or level-up banner.
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
  const className = t(`hero.classes.${myStats?.classType}.name`, {
    defaultValue: t(`class.${myStats?.classType || 'warrior'}`, {
      defaultValue: myStats?.classType || 'Warrior',
    }),
  });
  const levelVal = myStats?.level ?? 1;
  const hpVal = myStats?.hp ?? 0;
  const maxHpVal = myStats?.maxHp ?? 10;
  const shieldVal = myStats?.shield ?? 0;
  const title = myStats?.name
    ? `${myStats.name}\n${t('ui.lv', { level: levelVal })} ${className}`
    : `${t('ui.lv', { level: levelVal })} ${className}`;

  const rows = [
    { label: t('ui.str', { defaultValue: 'STR' }), value: myStats?.strength ?? '?' },
    {
      label: t('ui.hpStat'),
      value: shieldVal > 0
        ? `${hpVal}+${shieldVal}/${maxHpVal}`
        : `${hpVal}/${maxHpVal}`,
    },
    { label: t('ui.expStat', { defaultValue: 'EXP' }), value: `${myStats?.exp ?? 0}/${myStats?.maxExp ?? 10}` },
    { label: t('rankings.gold'), value: gold ?? 0 },
    { label: t('rankings.depth'), value: depth ?? 1 },
  ];

  return (
    <div className="wnd-hero-tab">
      <IconTitle icon={<HeroIcon index={classIcon} classType={myStats?.classType} size={16} />} title={title} />
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

function WndHero({ myStats, depth, gold, heroTab, onTabChange, onClose, talentPaneProps }) {
  const { t } = useTranslation();
  const [buffPopup, setBuffPopup] = useState(null);

  const tabs = [
    { label: t('ui.stats'), icon: '★' },
    { label: t('ui.talents'), icon: '✦' },
    { label: t('ui.buffs'), icon: '✧' },
  ];

  return (
    <>
      <WndOverlay id="wnd-hero" level={WindowLevel.BASE} onClose={onClose}>
        <div className="wnd-hero wnd-hero--wide" onClick={(e) => e.stopPropagation()}>
          <div className="wnd-hero-tabs">
            {tabs.map((tb, i) => (
              <button
                key={i}
                className={`wnd-hero-tab-btn${heroTab === i ? ' active' : ''}`}
                onClick={() => onTabChange(i)}
              >
                <span className="wnd-hero-tab-icon">{tb.icon}</span>
                <span className="wnd-hero-tab-label">{tb.label}</span>
              </button>
            ))}
          </div>
          <div className="wnd-hero-content">
            {heroTab === 0 && <StatsTab myStats={myStats} depth={depth} gold={gold} />}
            {heroTab === 1 && (
              <div className="wnd-hero-tab wnd-hero-tab--talents">
                <TalentPane embedded {...talentPaneProps} onClose={onClose} />
              </div>
            )}
            {heroTab === 2 && <BuffsTab effects={myStats?.effects} onBuffClick={setBuffPopup} />}
          </div>
          <button className="wnd-close-btn" onClick={onClose}>{t('ui.close')}</button>
        </div>
      </WndOverlay>
      {buffPopup && (
        <WndInfoBuff buff={buffPopup} onClose={() => setBuffPopup(null)} />
      )}
    </>
  );
}

export default memo(WndHero);
