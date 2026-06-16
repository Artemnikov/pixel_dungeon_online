import { useEffect, useState } from 'react';

export default function LootIndicator({ entitiesRef, myPlayerIdRef, onPickup }) {
  const [item, setItem] = useState(null);

  useEffect(() => {
    let raf;
    const tick = () => {
      const players = entitiesRef?.current?.players || {};
      const myId = myPlayerIdRef?.current;
      const hero = myId ? players[myId] : null;
      if (hero?.targetPos) {
        const { x, y } = hero.targetPos;
        const items = entitiesRef?.current?.items || [];
        const found = items.find(i => i.pos && i.pos.x === Math.round(x) && i.pos.y === Math.round(y));
        setItem(found || null);
      } else {
        setItem(null);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [entitiesRef, myPlayerIdRef]);

  if (!item) return null;
  return (
    <div className="side-tag side-tag--loot" onClick={onPickup} title={`Pick up ${item.name}`}>
      <svg viewBox="0 0 16 16" width="16" height="16" fill="#1858a8">
        <path d="M8 2l6 6H2L8 2zm-2 6h4v6H6V8z"/>
      </svg>
      <span className="side-tag__label">{item.name}</span>
    </div>
  );
}
