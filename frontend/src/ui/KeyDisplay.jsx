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
import ItemIcon from './ItemIcon';

// Mirrors SPD's KeyDisplay: a small icon+count row for keys held on the
// current floor. Keys never enter the inventory grid (see Player.add_key in
// the backend) — this is their only visual representation.
export default function KeyDisplay({ keys, depth }) {
  const held = (keys || []).filter((k) => k.depth === depth && k.quantity > 0);
  if (held.length === 0) return null;

  return (
    <div className="key-display">
      {held.map((k) => (
        <div className="key-display__pill" key={`${k.key_id}:${k.depth}`} title={k.name || k.key_id}>
          <ItemIcon item={{ name: k.name, type: 'key' }} size={20} />
          {k.quantity > 1 && <span className="inv-qty">{k.quantity}</span>}
        </div>
      ))}
    </div>
  );
}
