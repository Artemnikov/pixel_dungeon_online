// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Helper for the socket handler to dispatch a log entry.
export function addGameLog(text, color = 'default') {
  window.dispatchEvent(new CustomEvent('game-log', { detail: { text, color } }));
}
