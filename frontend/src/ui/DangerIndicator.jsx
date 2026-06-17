// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// DangerIndicator — SPD's skull + enemy count tag on the right side.
// Shows number of visible hostile mobs. Click to cycle focus through them.
import { useEffect, useState } from 'react';

export default function DangerIndicator({ visionRef, entitiesRef, myPlayerIdRef, onCycleEnemy }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let raf;
    const tick = () => {
      const v = visionRef?.current?.visible;
      if (v) {
        const mobs = entitiesRef?.current?.mobs || {};
        let c = 0;
        for (const m of Object.values(mobs)) {
          if (m.faction === 'enemy' && v.has(`${Math.round(m.renderPos.x)},${Math.round(m.renderPos.y)}`)) {
            c++;
          }
        }
        setCount(c);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [visionRef, entitiesRef, myPlayerIdRef]);

  if (count === 0) return null;

  return (
    <div className="danger-indicator" onClick={onCycleEnemy} title={`${count} visible enemy${count !== 1 ? 'ies' : 'y'}`}>
      <svg viewBox="0 0 16 16" width="16" height="16" fill="#c03838">
        <path d="M8 1L1 15h14L8 1z" />
      </svg>
      <span className="danger-indicator__count">{count}</span>
    </div>
  );
}
