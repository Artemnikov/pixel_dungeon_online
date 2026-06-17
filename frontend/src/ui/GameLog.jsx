// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// GameLog — SPD's bottom-left message log showing the last few lines of game text.
import { useEffect, useState } from 'react';

const MAX_LINES = 5;

const COLORS = {
  default: '#ffffff',
  positive: '#00ff00',
  negative: '#ff4444',
  warning: '#ffcc00',
  highlight: '#ff8800',
};

export default function GameLog() {
  const [messages, setMessages] = useState([]);

  // Listen for custom game-log events dispatched by the socket handler
  useEffect(() => {
    const handler = (e) => {
      const { text, color } = e.detail || {};
      if (!text) return;
      const c = COLORS[color] || color || '#ffffff';
      setMessages(prev => {
        const next = [...prev, { text, color: c, id: Date.now() + Math.random() }];
        if (next.length > MAX_LINES) next.splice(0, next.length - MAX_LINES);
        return next;
      });
    };
    window.addEventListener('game-log', handler);
    return () => window.removeEventListener('game-log', handler);
  }, []);

  if (messages.length === 0) return null;

  return (
    <div className="game-log">
      {messages.map(m => (
        <div key={m.id} className="game-log__line" style={{ color: m.color }}>{m.text}</div>
      ))}
    </div>
  );
}
