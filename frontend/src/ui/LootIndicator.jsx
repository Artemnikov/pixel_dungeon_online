import { useEffect, useState, memo } from 'react';
import ItemIcon from './ItemIcon';

function LootIndicator({ entitiesRef, myPlayerIdRef, onPickup, position }) {
  const [item, setItem] = useState(null);
  const [flash, setFlash] = useState(false);

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
        if (found && (!item || found.id !== item.id || found.quantity !== item.quantity)) {
          setFlash(true);
          setTimeout(() => setFlash(false), 400);
        }
        setItem(found || null);
      } else {
        setItem(null);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [entitiesRef, myPlayerIdRef, item]);

  if (!item || !position) return null;

  return (
    <div
      className={`loot-indicator${flash ? ' loot-indicator--flash' : ''}`}
      style={{
        position: 'fixed',
        left: position.x,
        top: position.y - 24,
        width: position.w,
        height: 24,
      }}
      onClick={onPickup}
      title={`Pick up ${item.name}`}
    >
      <ItemIcon item={item} size={16} />
      <span className="loot-indicator__label">{item.name}</span>
    </div>
  );
}

export default memo(LootIndicator);
