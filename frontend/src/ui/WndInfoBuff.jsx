import { useEffect, memo } from 'react';
import { useTranslation } from 'react-i18next';
import IconTitle from './IconTitle';
import buffsImg from '../assets/pixel-dungeon/interfaces/buffs.png';

const BUFF_SIZE = 7;
const BUFF_COLS = 18;

// SPD WndInfoBuff.java port: icon + name + description for a single buff.
// Called from StatusPane/BossHealthBar when a buff icon is clicked.
function WndInfoBuff({ buff, onClose }) {
  const { t } = useTranslation();
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!buff) return null;
  const idx = buff.icon ?? 0;
  const col = idx % BUFF_COLS;
  const row = Math.floor(idx / BUFF_COLS);
  const px = BUFF_SIZE * 3;

  const remaining = buff.remaining != null && buff.duration
    ? ` (${Math.ceil(buff.remaining)}s / ${Math.ceil(buff.duration)}s)`
    : '';

  // Look up description by buff key in the locale (buff.desc.<key>).
  const descKey = `buff.desc.${buff.key}`;
  const description = t(descKey, { defaultValue: buff.description || '' });

  return (
    <div className="wnd-overlay" onClick={onClose}>
      <div className="wnd-info-card" onClick={(e) => e.stopPropagation()}>
        <IconTitle
          icon={
            <div style={{
              width: px, height: px,
              backgroundImage: `url(${buffsImg})`,
              backgroundPosition: `-${col * px}px -${row * px}px`,
              backgroundSize: `${BUFF_COLS * px}px ${px * 8}`,
              imageRendering: 'pixelated',
            }} />
          }
          title={buff.name}
          sub={remaining}
        />
        {description && <div className="wnd-info-desc">{description}</div>}
      </div>
    </div>
  );
}

export default memo(WndInfoBuff);
