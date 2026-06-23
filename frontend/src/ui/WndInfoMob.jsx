import { useTranslation } from 'react-i18next';
import IconTitle from './IconTitle';
import buffsImg from '../assets/pixel-dungeon/interfaces/buffs.png';

const BUFF_SIZE = 7;
const BUFF_COLS = 18;

function MobSprite({ mob, size = 16 }) {
  const color = mob.faction === 'dungeon' ? '#a83a3a' : '#88a83a';
  return (
    <div style={{
      width: size, height: size, background: color,
      border: '1px solid #444', imageRendering: 'pixelated',
    }} />
  );
}

function BuffIcons({ effects, scale = 2 }) {
  if (!effects || effects.length === 0) return null;
  const px = BUFF_SIZE * scale;
  return (
    <div className="wnd-info-buffs">
      {effects.slice(0, 12).map((eff, i) => {
        const idx = eff.icon ?? 0;
        const col = idx % BUFF_COLS;
        const row = Math.floor(idx / BUFF_COLS);
        return (
          <div
            key={i}
            className="wnd-info-buff"
            title={`${eff.name}${eff.remaining != null && eff.duration ? ` (${Math.ceil(eff.remaining)}s)` : ''}`}
            style={{
              width: px, height: px,
              backgroundImage: `url(${buffsImg})`,
              backgroundPosition: `-${col * px}px -${row * px}px`,
              backgroundSize: `${BUFF_COLS * px}px ${px * 8}`,
              imageRendering: 'pixelated',
            }}
          />
        );
      })}
    </div>
  );
}

export default function WndInfoMob({ mob }) {
  const { t } = useTranslation();
  if (!mob) return null;

  const name = mob.locale_key ? t(mob.locale_key, { defaultValue: mob.name }) : mob.name;
  const hpPct = mob.max_hp > 0 ? Math.max(0, Math.min(1, mob.hp / mob.max_hp)) : 0;

  const descKey = mob.locale_key
    ? `${mob.locale_key.replace(/^mob\./, 'mob.desc.')}`
    : null;
  const description = (descKey && t(descKey, { defaultValue: '' })) || mob.description || '';

  const stats = [
    `${t('ui.hpStat')}: ${mob.hp}/${mob.max_hp}`,
    `${t('ui.attackStat')}: ${mob.attack_skill}`,
    `${t('ui.defenseStat')}: ${mob.defense_skill}`,
    `${t('ui.damageStat')}: ${mob.damage_min}-${mob.damage_max}`,
    `${t('ui.drStat')}: ${mob.dr_min}-${mob.dr_max}`,
    `${t('ui.expStat')}: ${mob.exp}`,
  ];

  return (
    <div className="wnd-info-card">
      <IconTitle icon={<MobSprite mob={mob} />} title={name} />
      <div className="wnd-info-hpbar">
        <div className="wnd-info-hpbar-fill" style={{ width: `${hpPct * 100}%` }} />
        <span className="wnd-info-hpbar-label">{mob.hp}/{mob.max_hp}</span>
      </div>
      {mob.buffs && mob.buffs.length > 0 && <BuffIcons effects={mob.buffs} />}
      <div className="wnd-info-stats">
        {stats.map((s, i) => <div key={i} className="wnd-info-stat-row">{s}</div>)}
      </div>
      {description && <div className="wnd-info-desc">{description}</div>}
    </div>
  );
}
