// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// Full-screen alchemy station (SPD scenes/AlchemyScene.java): three input
// slots, energy readout, server-authoritative preview via ALCHEMY_PREVIEW
// round-trips, brew + energize flows, bubbling ambience.
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';
import WndBag from './WndBag';
import { coordsForKind } from '../rendering/sprites';
import specksSrc from '../assets/pixel-dungeon/effects/specks.png';

const EMPTY_SLOTS = [null, null, null];

export default function AlchemyOverlay({
  belongings, gold, energy, strength,
  itemsById, preview, brewed, send, onClose,
}) {
  const { t } = useTranslation();
  const [slots, setSlots] = useState(EMPTY_SLOTS);     // item ids or null
  const [pickingSlot, setPickingSlot] = useState(null); // slot index being filled
  const [energizePick, setEnergizePick] = useState(false);
  const [energizeItem, setEnergizeItem] = useState(null);

  const ids = slots.filter(Boolean);

  // Occurrences per id, to cap repeated selection at the stack quantity.
  const counts = useMemo(() => {
    const c = {};
    ids.forEach(id => { c[id] = (c[id] || 0) + 1; });
    return c;
  }, [slots]);

  // Drop slots whose stacks vanished or shrank below their occurrence count
  // (post-brew state refresh), then re-request the preview.
  useEffect(() => {
    const next = [];
    const seen = {};
    for (const id of slots) {
      if (!id) { next.push(null); continue; }
      const item = itemsById[id];
      seen[id] = (seen[id] || 0) + 1;
      next.push(item && seen[id] <= item.quantity ? id : null);
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot reconcile of slots with server inventory, guarded by inequality
    if (next.some((v, i) => v !== slots[i])) setSlots(next);
  }, [itemsById]);

  useEffect(() => {
    if (ids.length > 0) send({ type: 'ALCHEMY_PREVIEW', ingredient_ids: ids });
  }, [slots]);

  // Client-side convenience filter only — the server re-validates everything.
  const usableFilter = (item) =>
    !(item.cursed_known && item.cursed)
    && (counts[item.id] || 0) < item.quantity
    && item.category !== 'bag' && item.kind !== 'gold' && item.kind !== 'key';

  const setSlot = (idx, id) => {
    AudioManager.play('CLICK');
    setSlots(s => s.map((v, i) => (i === idx ? id : v)));
  };

  const recipes = ids.length > 0 && preview
    && JSON.stringify(preview.ingredient_ids) === JSON.stringify(ids)
    ? preview.recipes : [];

  return (
    <div className="alchemy-overlay">
      <BubbleColumn side="left" />
      <BubbleColumn side="right" />
      <div className="alchemy-panel">
        <h2 className="alchemy-title">{t('alchemy.title')}</h2>

        <div className="alchemy-slots">
          {slots.map((id, i) => (
            <button
              key={i}
              className="alchemy-slot"
              onClick={() => (id ? setSlot(i, null) : setPickingSlot(i))}
            >
              {id && itemsById[id] ? <ItemIcon item={itemsById[id]} size={40} /> : <span>+</span>}
            </button>
          ))}
        </div>

        <div className="alchemy-arrow">▼</div>

        <div className="alchemy-outputs">
          {recipes.length === 0 && (
            <div className="alchemy-output-row alchemy-output-empty">
              {ids.length > 0 ? t('alchemy.noRecipe') : t('alchemy.hint')}
            </div>
          )}
          {recipes.map((r) => (
            <div className="alchemy-output-row" key={r.recipe_index}>
              <span className="alchemy-output-icon">
                {r.output_kind
                  ? <ItemIcon item={{ kind: r.output_kind }} coords={coordsForKind(r.output_kind)} size={32} />
                  : <span className="alchemy-unknown">?</span>}
              </span>
              <span className="alchemy-output-name">
                {r.output_name}{r.output_quantity > 1 ? ` x${r.output_quantity}` : ''}
              </span>
              <span className={r.affordable ? 'alchemy-cost' : 'alchemy-cost alchemy-cost-bad'}>
                {r.cost > 0 ? `⚡${r.cost}` : ''}
              </span>
              <button
                className="alchemy-brew-btn"
                disabled={!r.affordable}
                onClick={() => send({
                  type: 'ALCHEMY_BREW', ingredient_ids: ids, recipe_index: r.recipe_index,
                })}
              >
                {t('alchemy.brew')}
              </button>
            </div>
          ))}
          {brewed && (
            <div className="alchemy-output-row alchemy-brewed" key={brewed.item_id}>
              <ItemIcon item={{ kind: brewed.item_kind }} coords={coordsForKind(brewed.item_kind)} size={32} />
              <span className="alchemy-output-name">
                {brewed.item_name}{brewed.quantity > 1 ? ` x${brewed.quantity}` : ''}
              </span>
            </div>
          )}
        </div>

        <div className="alchemy-footer">
          <span className="alchemy-energy">
            {t('alchemy.energy')}: <b>{preview ? preview.available_energy : energy}</b>
            <i className="inv-energy-icon" />
            <button className="alchemy-energize-btn" onClick={() => setEnergizePick(true)}>+</button>
          </span>
          <button className="alchemy-close-btn" onClick={onClose}>{t('alchemy.close')}</button>
        </div>
      </div>

      {pickingSlot !== null && (
        <WndBag
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={strength}
          selectMode
          itemFilter={usableFilter}
          title={t('alchemy.selectIngredient')}
          onSelectItem={(item) => { setSlot(pickingSlot, item.id); setPickingSlot(null); }}
          onClose={() => setPickingSlot(null)}
        />
      )}

      {energizePick && (
        <WndBag
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={strength}
          selectMode
          itemFilter={(item) => (item.energy_value || 0) > 0}
          title={t('alchemy.energizeSelect')}
          onSelectItem={(item) => { setEnergizeItem(item); setEnergizePick(false); }}
          onClose={() => setEnergizePick(false)}
        />
      )}

      {energizeItem && (
        <div className="choice-modal-backdrop" onClick={() => setEnergizeItem(null)}>
          <div className="choice-modal" onClick={e => e.stopPropagation()}>
            <h3>{energizeItem.name}</h3>
            <button onClick={() => {
              send({ type: 'ALCHEMY_ENERGIZE', item_id: energizeItem.id, all_items: false });
              setEnergizeItem(null);
            }}>
              {t('alchemy.energizeOne', { value: energizeItem.energy_value_one ?? (energizeItem.energy_value || 0) })}
            </button>
            {energizeItem.quantity > 1 && (
              <button onClick={() => {
                send({ type: 'ALCHEMY_ENERGIZE', item_id: energizeItem.id, all_items: true });
                setEnergizeItem(null);
              }}>
                {t('alchemy.energizeAll', { value: energizeItem.energy_value || 0 })}
              </button>
            )}
            <button onClick={() => setEnergizeItem(null)}>{t('alchemy.cancel')}</button>
          </div>
        </div>
      )}
    </div>
  );
}

// Two columns of rising bubbles (SPD bubbleEmitter/lowerBubbles pouring
// Speck.BUBBLE). Speck cell 12 of the 128x8 specks sheet (8px cells).
function BubbleColumn({ side }) {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    const img = new Image();
    img.src = specksSrc;
    let raf;
    const bubbles = [];
    let last = performance.now();
    const tick = (now) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      if (Math.random() < dt * 12) {
        bubbles.push({ x: Math.random() * canvas.width, y: canvas.height + 8, life: 0 });
      }
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (let i = bubbles.length - 1; i >= 0; i--) {
        const b = bubbles[i];
        b.y -= dt * 40;
        b.life += dt;
        if (b.y < -8 || b.life > 4) { bubbles.splice(i, 1); continue; }
        ctx.globalAlpha = Math.max(0, 1 - b.life / 4);
        ctx.drawImage(img, 96, 0, 8, 8, b.x, b.y, 16, 16);
      }
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);
  return <canvas ref={canvasRef} width={64} height={400} className={`alchemy-bubbles alchemy-bubbles-${side}`} />;
}
