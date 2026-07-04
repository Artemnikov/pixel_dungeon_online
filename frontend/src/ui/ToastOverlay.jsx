// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// ToastOverlay — brief center-screen notices (mob alerts, item notices, etc.)
import { useEffect, useState } from 'react';

const DISMISS_MS = 3000;
const FADE_MS = 500;

export default function ToastOverlay() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    const handler = (e) => {
      const { text } = e.detail || {};
      if (!text) return;
      const id = Date.now() + Math.random();
      setToasts(prev => [...prev, { id, text, fadeOut: false }]);
      setTimeout(() => {
        setToasts(prev => prev.map(t => t.id === id ? { ...t, fadeOut: true } : t));
        setTimeout(() => {
          setToasts(prev => prev.filter(t => t.id !== id));
        }, FADE_MS);
      }, DISMISS_MS);
    };
    window.addEventListener('game-toast', handler);
    return () => window.removeEventListener('game-toast', handler);
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-overlay">
      {toasts.map(t => (
        <div key={t.id} className={`toast-overlay__item${t.fadeOut ? ' toast-overlay__item--fade' : ''}`}>
          {t.text}
        </div>
      ))}
    </div>
  );
}
