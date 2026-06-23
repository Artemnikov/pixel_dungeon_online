import { useEffect, useLayoutEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import IconTitle from './IconTitle';
import WndInfoMob from './WndInfoMob';
import WndInfoItem from './WndInfoItem';
import WndInfoTrap from './WndInfoTrap';

export default function WndInfoCell({ cellInfo, style, onClose }) {
  const { t } = useTranslation();
  const ref = useRef(null);
  const positionedRef = useRef(false);

  useEffect(() => {
    if (!onClose) return;
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  useEffect(() => {
    if (!onClose) return;
    const close = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    window.addEventListener('pointerdown', close);
    return () => window.removeEventListener('pointerdown', close);
  }, [onClose]);

  // Reposition on mount: place popup above the anchor tile, centered
  // horizontally. Flip below if it would overflow the viewport.
  // Runs only once — skipped on re-renders so the card doesn't jump.
  useLayoutEffect(() => {
    if (positionedRef.current) return;
    positionedRef.current = true;
    const el = ref.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const anchorX = parseFloat(el.style.left);
    const anchorY = parseFloat(el.style.top);
    if (isNaN(anchorX) || isNaN(anchorY)) return;

    let x = anchorX - width / 2;       // centered on anchor
    let y = anchorY - height - 8;      // above anchor

    // Flip below if above viewport
    if (y < 4) y = anchorY + 8;
    // Keep within horizontal bounds
    if (x < 4) x = 4;
    else if (x + width > window.innerWidth - 4) x = window.innerWidth - width - 4;

    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
  });

  if (!cellInfo) return null;

  let content;
  switch (cellInfo.kind) {
    case 'mob':
      content = <WndInfoMob mob={cellInfo.mob} />;
      break;
    case 'item':
      content = <WndInfoItem item={cellInfo.item} />;
      break;
    case 'trap':
      content = <WndInfoTrap trapType={cellInfo.trapType} />;
      break;
    case 'darkness':
      content = (
        <div className="wnd-info-card">
          <IconTitle
            icon={<div style={{ width: 16, height: 16, background: '#111' }} />}
            title={cellInfo.name || t('tile.darkness')}
          />
          <div className="wnd-info-desc">{t('tile.darkness')}</div>
        </div>
      );
      break;
    case 'player': {
      const p = cellInfo.player;
      const stats = p ? [
        `${t('ui.hpStat')}: ${p.hp}/${p.max_hp}`,
        `${t('ui.attackStat')}: ${p.attack_skill ?? '?'}`,
        `${t('ui.defenseStat')}: ${p.defense_skill ?? '?'}`,
        `${t('ui.lv', { level: p.level ?? '?' })}`,
      ] : [];
      content = (
        <div className="wnd-info-card">
          <IconTitle
            icon={<div style={{ width: 16, height: 16, background: '#4a6a9a' }} />}
            title={cellInfo.name}
          />
          {stats.length > 0 && (
            <div className="wnd-info-stats">
              {stats.map((s, i) => <div key={i} className="wnd-info-stat-row">{s}</div>)}
            </div>
          )}
        </div>
      );
      break;
    }
    case 'tile':
    default:
      content = (
        <div className="wnd-info-card">
          <IconTitle
            icon={<div style={{ width: 16, height: 16, background: '#5a5a5a' }} />}
            title={cellInfo.name}
          />
          {cellInfo.description && (
            <div className="wnd-info-desc">{cellInfo.description}</div>
          )}
        </div>
      );
      break;
  }

  return (
    <div ref={ref} className="inspect-popup" style={style}>
      {content}
    </div>
  );
}
