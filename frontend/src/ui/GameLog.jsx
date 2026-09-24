import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

const MAX_LINES = 6;
const MAX_HISTORY = 80;

const COLORS = {
  default: '#ffffff',
  positive: '#00ff00',
  negative: '#ff4444',
  warning: '#ffcc00',
  highlight: '#ff8800',
};

/** Encapsulates a single chat channel's configuration and rendering helpers. */
class ChatChannel {
  constructor({ id, label, title, placeholder, color, colorSelf }) {
    this.id = id;
    this.label = label;
    this.title = title;
    this.placeholder = placeholder;
    this.color = color;
    this.colorSelf = colorSelf;
  }

  isActive(currentId) {
    return currentId === this.id;
  }

  nameColor(isSelf) {
    return isSelf ? this.colorSelf : this.color;
  }

  textColor() {
    return this.color;
  }
}

const CHANNELS = [
  new ChatChannel({
    id: 'global',
    label: 'G',
    title: 'Global chat — all floors',
    placeholder: 'Global\u2026',
    color: '#7fbfff',
    colorSelf: '#b8d8ff',
  }),
  new ChatChannel({
    id: 'direct',
    label: 'D',
    title: 'Direct chat — players in line of sight',
    placeholder: 'Direct\u2026',
    color: '#7fff7f',
    colorSelf: '#b8ffb8',
  }),
];

/** Lookup helpers over the CHANNELS registry. */
const channelById = (id) => CHANNELS.find(c => c.id === id) || CHANNELS[0];

export default function GameLog({ send }) {
  const { t } = useTranslation();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [channel, setChannel] = useState('direct');
  const [open, setOpen] = useState(false);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  const openChat = () => {
    setOpen(true);
    // Defer focus until the input row is rendered.
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  const toggleChat = () => {
    if (open) {
      setOpen(false);
      inputRef.current?.blur();
    } else {
      openChat();
    }
  };

  useEffect(() => {
    const append = (msg) => {
      setMessages(prev => {
        const next = [...prev, { ...msg, id: Date.now() + Math.random() }];
        if (next.length > MAX_HISTORY) next.splice(0, next.length - MAX_HISTORY);
        return next;
      });
    };

    const onLog = (e) => {
      const { text, color } = e.detail || {};
      if (!text) return;
      const c = COLORS[color] || color || '#ffffff';
      append({ kind: 'event', text, color: c });
    };

    const onChat = (e) => {
      const { channel: ch, name, text, self } = e.detail || {};
      if (!text) return;
      append({ kind: 'chat', channel: ch, name, text, self });
    };

    const onKeyDown = (e) => {
      if (e.code !== 'Enter') return;
      const tag = e.target?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'BUTTON') return;
      e.preventDefault();
      openChat();
    };

    window.addEventListener('game-log', onLog);
    window.addEventListener('chat-message', onChat);
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('game-log', onLog);
      window.removeEventListener('chat-message', onChat);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, []);

  // Keep the newest lines in view.
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const preventBlur = (e) => {
    e.preventDefault();
  };

  const switchChannel = (chId) => {
    setChannel(chId);
    inputRef.current?.focus();
  };

  const cycleChannel = () => {
    const idx = CHANNELS.findIndex(c => c.id === channel);
    setChannel(CHANNELS[(idx + 1) % CHANNELS.length].id);
  };

  const sendChat = () => {
    const text = input.trim();
    if (!text || !send) return;
    send({ type: 'SEND_CHAT', channel, text });
    setInput('');
    setOpen(false);
    inputRef.current?.blur();
  };

  const activeChannel = channelById(channel);
  const visible = messages.slice(-MAX_LINES);

  return (
    <div className={`game-log${open ? ' game-log--chat' : ''}`}>
      <div className="game-log__list" ref={listRef}>
        {visible.map(m => {
          if (m.kind === 'chat') {
            const ch = channelById(m.channel);
            return (
              <div key={m.id} className="game-log__line game-log__chat">
                <span className="game-log__name" style={{ color: ch.nameColor(m.self) }}>
                  {m.self ? 'You' : m.name}:
                </span>{' '}
                <span style={{ color: ch.textColor() }}>{m.text}</span>
              </div>
            );
          }
          return (
            <div key={m.id} className="game-log__line" style={{ color: m.color }}>{m.text}</div>
          );
        })}
      </div>

      <div className="game-log__input">
        <div className="game-log__channels">
          {CHANNELS.map(ch => (
            <button
              key={ch.id}
              type="button"
              className={`game-log__chan${ch.isActive(channel) ? ' active' : ''}`}
              title={ch.title}
              onMouseDown={preventBlur}
              onClick={() => switchChannel(ch.id)}
            >
              {ch.label}
            </button>
          ))}
        </div>
        <input
          ref={inputRef}
          value={input}
          maxLength={200}
          placeholder={activeChannel.placeholder}
          onChange={e => setInput(e.target.value)}
          onFocus={() => setOpen(true)}
          onBlur={() => { if (!input) setOpen(false); }}
          onKeyDown={e => {
            e.stopPropagation();
            if (e.key === 'Enter') sendChat();
            if (e.key === 'Escape') e.currentTarget.blur();
            if (e.key === 'Tab') {
              e.preventDefault();
              cycleChannel();
            }
          }}
        />
        <button
          type="button"
          className="game-log__send"
          onMouseDown={preventBlur}
          onClick={sendChat}
        >
          Send
        </button>
      </div>

      <div className="game-log__footer">
        {!open && (
          <>
            <span className="game-log__hint game-log__hint--desktop">{t('ui.chatHintDesktop')}</span>
            <span className="game-log__hint game-log__hint--mobile">{t('ui.chatHintMobile')}</span>
          </>
        )}
        <button
          type="button"
          className="game-log__toggle"
          title={open ? t('ui.close') : t('ui.openChat')}
          aria-label={open ? t('ui.close') : t('ui.openChat')}
          onClick={toggleChat}
          onMouseDown={preventBlur}
        >
          {open ? '\u2715' : '\u{1F4AC}'}
        </button>
      </div>
    </div>
  );
}
