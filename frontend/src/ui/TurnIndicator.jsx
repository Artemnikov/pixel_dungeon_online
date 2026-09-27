import { memo, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

/** How often the countdown re-renders. Frames arrive far slower than this. */
const TICK_MS = 200;

const CLASS_ICONS = {
  warrior: '⚔',
  mage: '🔮',
  rogue: '🗡',
  huntress: '🏹',
  cleric: '☀️',
  duelist: '🤺',
};

function formatSeconds(total) {
  const safe = Math.max(0, Math.ceil(total));
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, '0')}`;
}

/**
 * Whose turn it is, who is waiting to move, and how long until the room auto-Waits.
 */
function TurnIndicator({ turn, myPlayerId }) {
  const { t } = useTranslation();
  const timer = turn?.timer ?? null;

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

  const playerEntries = (turn.order || []).filter((a) => a.kind === 'player');
  const hasMobs = (turn.order || []).some((a) => a.kind === 'mob');
  const waitingPlayers = playerEntries.filter((p) => p.needs_input !== false);

  const titleTooltip = mine
    ? t('turn.yourTurn')
    : waitingPlayers.length > 0
    ? `${t('turn.waitingFor')}: ${waitingPlayers.map((p) => (p.id === myPlayerId ? t('turn.you') : p.name || t('turn.hero'))).join(', ')}`
    : t('turn.waitingForOthers');

  return (
    <div
      className={`side-tag side-tag--turn ${mine ? 'is-mine' : 'is-waiting'}`}
      title={titleTooltip}
    >
      <div className="turn-header">
        <span className="side-tag__label">{t('turn.turn')} {turn.turn ?? 0}</span>
        {left != null && left <= 0.25 && (
          <span className="side-tag-cd is-urgent">{formatSeconds(0)}</span>
        )}
        {left != null && left > 0.25 && (
          <span className="side-tag-cd">{formatSeconds(left)}</span>
        )}
      </div>

      {playerEntries.length > 0 && (
        <div className="turn-badges">
          {playerEntries.map((p) => {
            const isMe = Boolean(myPlayerId && p.id === myPlayerId);
            const isWaiting = p.needs_input !== false;
            const classKey = (p.class_type || '').toLowerCase();
            const icon = CLASS_ICONS[classKey] || '☺';
            const rawName = p.name || t('turn.hero');
            const displayName = isMe ? `${rawName} (${t('turn.you')})` : rawName;
            const statusText = isWaiting ? t('turn.acting') : t('turn.ready');

            return (
              <div
                key={p.id}
                className={`turn-badge ${isWaiting ? 'turn-badge--waiting' : 'turn-badge--ready'} ${isMe ? 'turn-badge--me' : ''}`}
                title={`${displayName} — ${statusText}`}
              >
                <span className="turn-badge__icon">{icon}</span>
                <span className="turn-badge__name">{displayName}</span>
                <span className="turn-badge__status">{isWaiting ? '⏳' : '✓'}</span>
              </div>
            );
          })}
          {hasMobs && (
            <div className="turn-badge turn-badge--dungeon" title={t('turn.dungeon')}>
              <span className="turn-badge__icon">☠</span>
              <span className="turn-badge__name">{t('turn.dungeon')}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default memo(TurnIndicator);
