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
};

export default function RoomSelection({ onJoin, onBack, joinError, onDismissError }) {
  const { t } = useTranslation();
  const [rooms, setRooms] = useState({ public: { room_id: 'public', player_count: 0 }, groups: [] });
  const [loading, setLoading] = useState(true);
  const [passwordPrompt, setPasswordPrompt] = useState(null);
  const [passwordInput, setPasswordInput] = useState('');
  const [createName, setCreateName] = useState('');
  const [createPassword, setCreatePassword] = useState('');
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
    onJoin('public', '');
  };

  const joinGroup = (room) => {
    onDismissError?.();
    if (room.has_password) {
      setPasswordPrompt(room.room_id);
      setPasswordInput('');
      return;
    }
    onJoin(room.room_id, '');
  };

  const confirmPassword = () => {
    if (!passwordPrompt) return;
    onJoin(passwordPrompt, passwordInput);
  };

  const createGroup = async () => {
    const name = createName.trim();
    if (!name || creating) return;
    setCreating(true);
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/rooms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, password: createPassword || null }),
      });
      const data = await res.json();
      if (data.room_id) {
        onDismissError?.();
        onJoin(data.room_id, createPassword);
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
