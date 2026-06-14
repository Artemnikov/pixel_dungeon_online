// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
// See the GNU General Public License for more details.
//
import { useState, useMemo } from 'react';
import ItemIcon from './ItemIcon';

// Admin-only debug panel (press U): browse every item kind in the game and
// give one to yourself. `catalog` is the list fetched from /api/items/catalog.
export default function AdminItemBrowser({ catalog, onClose, onGiveItem }) {
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return catalog;
    return catalog.filter(
      (entry) => entry.name.toLowerCase().includes(q) || entry.category.toLowerCase().includes(q)
    );
  }, [catalog, query]);

  return (
    <div className="talent-overlay" onClick={onClose}>
      <div className="talent-pane item-browser-pane" onClick={(e) => e.stopPropagation()}>
        <div className="talent-header">
          <h2 className="talent-title">Give Item</h2>
          <button className="talent-close" onClick={onClose}>&times;</button>
        </div>
        <div className="item-browser-search">
          <input
            type="text"
            placeholder="Search items..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
        </div>
        <div className="talent-body item-browser-list">
          {filtered.map((entry) => (
            <div
              key={entry.kind}
              className="item-browser-row"
              onClick={() => onGiveItem(entry.kind)}
            >
              <ItemIcon item={{ kind: entry.kind, name: entry.name }} size={28} />
              <span className="item-browser-name">{entry.name}</span>
              <span className="item-browser-category">{entry.category}</span>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="item-browser-empty">No items match "{query}"</div>
          )}
        </div>
      </div>
    </div>
  );
}
