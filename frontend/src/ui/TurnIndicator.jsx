import { memo, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

/** How often the countdown re-renders. Frames arrive far slower than this. */
const TICK_MS = 200;

function formatSeconds(total) {
  const safe = Math.max(0, Math.ceil(total));
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, '0')}`;
}

/**
 * Whose turn it is, and how long until the room auto-Waits.
 *
 * The server only sends `timer` to the player it is waiting on, and a
 * turn-based room is deliberately quiet while nothing happens, so each new
 * `timer` value is treated as a fresh reading: `anchor` is when it arrived and
 * the countdown runs down from there locally.
 */
function TurnIndicator({ turn }) {
  const { t } = useTranslation();
  const timer = turn?.timer ?? null;

  // `forTimer` tags the reading the countdown belongs to, so a new server
  // value renders immediately (derived here) while the running count ticks
  // down from the last interval instead of being recomputed during render.
  const [shown, setShown] = useState(() => ({ forTimer: timer, left: timer }));

  useEffect(() => {
    if (timer == null) return undefined;
    let remaining = timer;
    const id = setInterval(() => {
      remaining = Math.max(0, remaining - TICK_MS / 1000);
      setShown({ forTimer: timer, left: remaining });
    }, TICK_MS);
    return () => clearInterval(id);
  }, [timer]);

  if (!turn) return null;

  const mine = turn.is_my_turn === true;
  const left = shown.forTimer === timer ? shown.left : timer;
  const next = (turn.order || []).slice(0, 4);

  return (
    <div
      className={`side-tag side-tag--turn ${mine ? 'is-mine' : 'is-waiting'}`}
      title={mine ? t('turn.yourTurn') : t('turn.waitingForOthers')}
    >
      <span className="side-tag__label">{t('turn.turn')} {turn.turn ?? 0}</span>
      {left != null && left <= 0.25 && (
        <span className="side-tag-cd is-urgent">{formatSeconds(0)}</span>
      )}
      {left != null && left > 0.25 && (
        <span className="side-tag-cd">{formatSeconds(left)}</span>
      )}
      {next.length > 1 && (
        <span className="side-tag__label">
          {next.map((a) => (a.kind === 'mob' ? '☠' : '☺')).join('')}
        </span>
      )}
    </div>
  );
}

export default memo(TurnIndicator);
