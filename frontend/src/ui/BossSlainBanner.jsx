import { useEffect, useRef, memo } from 'react';

const BANNER_W = 127;
const BANNER_H = 68;
const BADGE_SIZE = 16;
const BADGE_COLS = 8;
const SCALE = 2;

function BossSlainBanner({ badgeImage, onDismiss }) {
  const timerRef = useRef(null);
  const onDismissRef = useRef(onDismiss);
  useEffect(() => { onDismissRef.current = onDismiss; });

  useEffect(() => {
    timerRef.current = setTimeout(() => onDismissRef.current?.(), 3000);
    return () => clearTimeout(timerRef.current);
  }, []);

  const col = badgeImage % BADGE_COLS;
  const row = Math.floor(badgeImage / BADGE_COLS);

  return (
    <div className="boss-slain-root">
      <div className="boss-slain-badge"
           style={{
             width: BADGE_SIZE * SCALE,
             height: BADGE_SIZE * SCALE,
             backgroundPosition: `${-(col * BADGE_SIZE * SCALE)}px ${-(row * BADGE_SIZE * SCALE)}px`,
             backgroundSize: `${BADGE_SIZE * BADGE_COLS * SCALE}px ${BADGE_SIZE * (256 / BADGE_SIZE) * SCALE}px`,
           }} />
      <div className="boss-slain-banner"
           style={{
             width: BANNER_W * SCALE,
             height: BANNER_H * SCALE,
             backgroundPosition: `0 ${-(157 * SCALE)}px`,
             backgroundSize: `${512 * SCALE}px ${256 * SCALE}px`,
           }} />
    </div>
  );
}

export default memo(BossSlainBanner);
