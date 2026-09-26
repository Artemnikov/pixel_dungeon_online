import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import './menu.css';
import './roomSelection.css';
import AudioManager from '../audio/AudioManager';
import Icon from './Icon';
import MenuButton from './MenuButton';
import { getApiBaseUrl } from '../config/urls';
import sewersSplash from '../assets/pixel-dungeon/splashes/sewers.jpg';

const POLL_MS = 5000;

const REASON_KEYS = {
  'wrong password': 'rooms.reasonWrongPassword',
  'room full': 'rooms.reasonRoomFull',
  'dungeon faction disabled': 'rooms.reasonDungeonDisabled',
};

export default function RoomSelection({ onJoin, onBack, joinError, onDismissError }) {
  const { t } = useTranslation();
  const [rooms, setRooms] = useState({ public: { room_id: 'public', player_count: 0 }, groups: [] });
  const [loading, setLoading] = useState(true);
  const [passwordPrompt, setPasswordPrompt] = useState(null);
  const [passwordInput, setPasswordInput] = useState('');
  const [createName, setCreateName] = useState('');
  const [createPassword, setCreatePassword] = useState('');
  const [createAllowDungeon, setCreateAllowDungeon] = useState(true);
  const [createGameMode, setCreateGameMode] = useState('realtime');
  const [createTurnTimer, setCreateTurnTimer] = useState('60');
  const [creating, setCreating] = useState(false);

  const fetchRooms = useCallback(async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/rooms`);
      if (!res.ok) return;
      const data = await res.json();
      setRooms(data);
    } catch {
      // network hiccup -- keep showing the last known list
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRooms();
    const id = setInterval(fetchRooms, POLL_MS);
    return () => clearInterval(id);
  }, [fetchRooms]);

  const joinPublic = () => {
    onDismissError?.();
    onJoin('public', '', true);
  };

  const joinGroup = (room) => {
    onDismissError?.();
    if (room.has_password) {
      setPasswordPrompt(room.room_id);
      setPasswordInput('');
      return;
    }
    onJoin(room.room_id, '', room.allow_dungeon !== false);
  };

  const confirmPassword = () => {
    if (!passwordPrompt) return;
    const room = rooms.groups.find(r => r.room_id === passwordPrompt);
    onJoin(passwordPrompt, passwordInput, room?.allow_dungeon !== false);
  };

  const createGroup = async () => {
    const name = createName.trim();
    if (!name || creating) return;
    setCreating(true);
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/rooms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          password: createPassword || null,
          allow_dungeon: createAllowDungeon,
          game_mode: createGameMode,
          // Only meaningful for a turn room; the server defaults it otherwise.
          turn_timer_seconds: createGameMode === 'turnbased'
            ? Math.max(5, Number(createTurnTimer) || 60)
            : null,
        }),
      });
      const data = await res.json();
      if (data.room_id) {
        onDismissError?.();
        onJoin(data.room_id, createPassword, createAllowDungeon);
      }
    } catch {
      // swallow -- user can retry
    } finally {
      setCreating(false);
    }
  };

  const reasonText = joinError ? t(REASON_KEYS[joinError] || joinError) : '';

  return (
    <div className="opd-rooms">
      <img className="opd-rooms-splash" src={sewersSplash} alt="" />
      <div className="opd-rooms-scrim" />

      <div className="opd-rooms-ui">
        <h1 className="opd-rooms-title">{t('rooms.title')}</h1>

        {joinError && (
          <div className="opd-rooms-error">{t('rooms.rejected', { reason: reasonText })}</div>
        )}

        <MenuButton
          icon="ENTER"
          accent
          className="opd-rooms-public-btn"
          onClick={joinPublic}
          label={(
            <>
              <span>{t('rooms.joinPublic')}</span>
              <span className="opd-rooms-count">{rooms.public?.player_count ?? 0} {t('rooms.online')}</span>
            </>
          )}
        />

        <div className="opd-rooms-card">
          <h2 className="opd-section-title">{t('rooms.groupsTitle')}</h2>
          {loading && <p className="opd-empty-sub">{t('rooms.loading')}</p>}
          {!loading && rooms.groups.length === 0 && (
            <p className="opd-empty-sub">{t('rooms.noGroups')}</p>
          )}
          {rooms.groups.map((room) => (
            <div key={room.room_id} className="opd-room-row">
              <span className="opd-room-name">
                {room.has_password && (
                  <span className="opd-room-lock" aria-label={t('rooms.locked')}>&#128274;</span>
                )}
                {room.name}
                {room.game_mode === 'turnbased' && (
                  <span className="opd-room-mode" title={t('rooms.turnBased')}>&#9878;</span>
                )}
              </span>
              <span className="opd-room-count">{room.player_count}/{room.max_players}</span>
              <MenuButton className="opd-room-join-btn" onClick={() => joinGroup(room)} label={t('rooms.join')} />
            </div>
          ))}

          {passwordPrompt && (
            <div className="opd-rooms-password-prompt">
              <input
                autoFocus
                type="password"
                placeholder={t('rooms.passwordPlaceholder')}
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') confirmPassword(); }}
              />
              <MenuButton className="opd-rooms-compact-btn" onClick={confirmPassword} label={t('rooms.join')} />
              <MenuButton className="opd-rooms-compact-btn" onClick={() => setPasswordPrompt(null)} label={t('rooms.cancel')} />
            </div>
          )}
        </div>

        <div className="opd-rooms-card">
          <h2 className="opd-section-title">{t('rooms.createTitle')}</h2>
          <input
            className="opd-rooms-create-name"
            type="text"
            maxLength={30}
            placeholder={t('rooms.namePlaceholder')}
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
          />
          <input
            className="opd-rooms-create-password"
            type="password"
            maxLength={30}
            placeholder={t('rooms.passwordOptionalPlaceholder')}
            value={createPassword}
            onChange={(e) => setCreatePassword(e.target.value)}
          />
          <label className="hero-challenge-toggle" style={{ margin: '8px 0', color: '#ccc', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={createAllowDungeon}
              onChange={(e) => { AudioManager.play('CLICK'); setCreateAllowDungeon(e.target.checked); }}
            />
            {t('rooms.allowDungeon')}
          </label>
          <label
            className="hero-challenge-toggle"
            style={{ margin: '0 0 8px', color: '#ccc', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
          >
            <input
              type="checkbox"
              checked={createGameMode === 'turnbased'}
              onChange={(e) => {
                AudioManager.play('CLICK');
                setCreateGameMode(e.target.checked ? 'turnbased' : 'realtime');
              }}
            />
            {t('rooms.turnBased')}
          </label>
          {createGameMode === 'turnbased' && (
            <label
              className="opd-rooms-create-turn-timer"
              style={{ margin: '0 0 8px', color: '#ccc', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              {t('rooms.turnTimer')}
              <input
                type="number"
                min={5}
                max={300}
                step={5}
                value={createTurnTimer}
                onChange={(e) => setCreateTurnTimer(e.target.value)}
                style={{ width: '64px' }}
              />
            </label>
          )}
          <MenuButton
            accent
            className="opd-rooms-create-btn"
            onClick={createGroup}
            label={t('rooms.create')}
            disabled={!createName.trim() || creating}
          />
        </div>

        <button className="opd-rooms-back-btn" onClick={() => { AudioManager.play('CLICK'); onBack(); }}>
          <Icon name="CHEVRON" scale={2} />
          <span>{t('rooms.back')}</span>
        </button>
      </div>
    </div>
  );
}
