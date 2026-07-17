// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// Full-screen alchemy station (SPD scenes/AlchemyScene.java):
//   scrolling water background, dark gradient overlay, 3-column workspace
//   (vertical inputs | combine arrows | output slots), continuous bubble
//   particles, semi-transparent TOAST_TR-style panels.
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import ItemIcon from './ItemIcon';
import WndBag from './WndBag';
import { coordsForKind } from '../rendering/sprites';
import WndAlchemyGuide from './WndAlchemyGuide';
import specksSrc from '../assets/pixel-dungeon/effects/specks.png';
import water0 from '../assets/pixel-dungeon/environment/water0.png';
import water1 from '../assets/pixel-dungeon/environment/water1.png';
import water2 from '../assets/pixel-dungeon/environment/water2.png';
import water3 from '../assets/pixel-dungeon/environment/water3.png';
import water4 from '../assets/pixel-dungeon/environment/water4.png';

const EMPTY_SLOTS = [null, null, null];
const WATER_FRAMES = [water0, water1, water2, water3, water4];

// Serialized `type`s of SPD EquipableItems that Recipe.usableInRecipe rejects
// outright. Wands and trinkets are equipment too but are allowed (handled
// explicitly below), so they are deliberately not in this set.
const EQUIP_TYPES = new Set(['weapon', 'wearable', 'ring', 'artifact']);

export default function AlchemyOverlay({
  belongings, gold, energy, strength, depth,
  itemsById, preview, brewed, send, onClose,
}) {
  const { t } = useTranslation();
  const [slots, setSlots] = useState(EMPTY_SLOTS);
  const [pickingSlot, setPickingSlot] = useState(null);
  const [energizePick, setEnergizePick] = useState(false);
  const [energizeItem, setEnergizeItem] = useState(null);
  const [guideOpen, setGuideOpen] = useState(false);

  const ids = slots.filter(Boolean);

  const counts = useMemo(() => {
    const c = {};
    ids.forEach(id => { c[id] = (c[id] || 0) + 1; });
    return c;
  }, [slots]);

  useEffect(() => {
    const next = [];
    const seen = {};
    for (const id of slots) {
      if (!id) { next.push(null); continue; }
      const item = itemsById[id];
      seen[id] = (seen[id] || 0) + 1;
      next.push(item && seen[id] <= item.quantity ? id : null);
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot reconcile
    if (next.some((v, i) => v !== slots[i])) setSlots(next);
  }, [slots, itemsById]);

  useEffect(() => {
    if (ids.length > 0) send({ type: 'ALCHEMY_PREVIEW', ingredient_ids: ids });
  }, [slots]);

  // Mirror the server's Recipe.usableInRecipe (backend usable_in_recipe /
  // SPD Recipe.usableInRecipe) so the picker only offers what will actually
  // brew: wands (identified + uncursed) and trinkets (uncursed) are the only
  // valid equipment; weapons/armor/rings/artifacts are never valid; everything
  // else is valid unless cursed. The stack-cap and bag/gold/key guards are
  // remake-UI conveniences with no SPD equivalent (the server re-validates).
  const usableFilter = (item) => {
    if (item.category === 'bag' || item.kind === 'gold' || item.kind === 'key') return false;
    if ((counts[item.id] || 0) >= item.quantity) return false;
    if (item.type === 'trinket') return !item.cursed;
    if (item.type === 'wand') return item.cursed_known && !item.cursed;
    if (EQUIP_TYPES.has(item.type)) return false;
    return !item.cursed;
  };

  const setSlot = (idx, id) => {
    AudioManager.play('CLICK');
    setSlots(s => s.map((v, i) => (i === idx ? id : v)));
  };

  const clearSlots = () => {
    AudioManager.play('CLICK');
    setSlots(EMPTY_SLOTS);
  };

  const recipes = ids.length > 0 && preview
    && JSON.stringify(preview.ingredient_ids) === JSON.stringify(ids)
    ? preview.recipes : [];

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const waterRegion = Math.min(4, Math.max(0, Math.floor(((depth ?? 1) - 1) / 5)));

  return (
    <div
      className="alchemy-overlay"
      style={{ backgroundImage: `url(${WATER_FRAMES[waterRegion]})` }}
    >
      <div className="alchemy-gradient" />
      <BubbleCanvas />

      <button className="alchemy-exit-btn" onClick={onClose}>✕</button>

      <div className="alchemy-scene">
        {recipes.length === 0 && (
          <div className="alchemy-hint-text">
            {ids.length > 0 ? t('alchemy.noRecipe') : t('alchemy.hint')}
          </div>
        )}

        <div className="alchemy-workspace">
          {/* ── Column 1: input slots ── */}
          <div className="alchemy-input-panel">
            {slots.map((id, i) => (
              <button
                key={i}
                className="alchemy-input-slot"
                onClick={() => (id ? setSlot(i, null) : setPickingSlot(i))}
              >
                {id && itemsById[id]
                  ? <ItemIcon item={itemsById[id]} size={40} />
                  : <span className="alchemy-input-slot-glyph">?</span>}
              </button>
            ))}
          </div>

          {/* ── Column 2: combine / arrow buttons ── */}
          <div className="alchemy-combines-col">
            {recipes.length > 0 ? recipes.map((r) => (
              <button
                key={r.recipe_index}
                className="alchemy-combine-btn"
                disabled={!r.affordable}
                onClick={() => send({
                  type: 'ALCHEMY_BREW', ingredient_ids: ids, recipe_index: r.recipe_index,
                })}
              >
                <span className="alchemy-combine-icon">▶</span>
                {r.cost > 0 && (
                  <span className={`alchemy-combine-cost${r.affordable ? '' : ' alchemy-combine-cost-bad'}`}>
                    {r.cost}
                  </span>
                )}
              </button>
            )) : <div className="alchemy-combine-hint">▶</div>}
          </div>

          {/* ── Column 3: output slots ── */}
          <div className="alchemy-outputs-col">
            {recipes.length > 0 ? recipes.map((r) => (
              <div className="alchemy-output-slot" key={r.recipe_index}>
                <div className="alchemy-output-icon">
                  {r.output_kind
                    ? <ItemIcon item={{ kind: r.output_kind }} coords={coordsForKind(r.output_kind)} size={32} />
                    : <span className="alchemy-unknown">?</span>}
                </div>
                <span className="alchemy-output-name">
                  {r.output_name}{r.output_quantity > 1 ? ` x${r.output_quantity}` : ''}
                </span>
              </div>
            )) : <div className="alchemy-output-slot alchemy-output-empty" />}
            {brewed && (
              <div className="alchemy-output-slot alchemy-brewed" key={brewed.item_id}>
                <div className="alchemy-output-icon">
                  <ItemIcon item={{ kind: brewed.item_kind }} coords={coordsForKind(brewed.item_kind)} size={32} />
                </div>
                <span className="alchemy-output-name">
                  {brewed.item_name}{brewed.quantity > 1 ? ` x${brewed.quantity}` : ''}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* ── Controls (cancel / repeat) ── */}
        <div className="alchemy-controls">
          <button
            className="alchemy-control-btn"
            onClick={clearSlots}
            title={t('alchemy.cancel')}
          >✕</button>
          <button
            className="alchemy-control-btn alchemy-control-disabled"
            title={t('alchemy.repeat')}
          >↻</button>
        </div>

        {/* ── Guide button (SPD AlchemyScene btnGuide, above energy) ── */}
        <button
          className="alchemy-guide-btn"
          onClick={() => { AudioManager.play('CLICK'); setGuideOpen(true); }}
        >
          {t('alchemy.guide.btn')}
        </button>

        {/* ── Energy display ── */}
        <div className="alchemy-energy">
          <span className="inv-energy-icon" />
          <span className="alchemy-energy-text">
            {t('alchemy.energy')}: {preview ? preview.available_energy : energy}
          </span>
          <button className="alchemy-energize-btn" onClick={() => setEnergizePick(true)}>+</button>
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
          onSelectItem={(item) => {
            setSlot(pickingSlot, item.id);
            setPickingSlot(null);
          }}
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

      {guideOpen && <WndAlchemyGuide onClose={() => setGuideOpen(false)} />}
    </div>
  );
}

// Full-screen rising-bubble canvas (SPD bubbleEmitter + lowerBubbles
// pouring Speck.BUBBLE).  Speck cell 12 of the 128×8 specks sheet (8px cells).
function BubbleCanvas() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const img = new Image();
    img.src = specksSrc;

    let raf;
    const bubbles = [];
    let last = performance.now();

    const tick = (now) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;

      if (Math.random() < dt * 16) {
        bubbles.push({
          x: Math.random() * canvas.width,
          y: canvas.height + 8,
          life: 0,
          speed: 30 + Math.random() * 30,
          size: 12 + Math.random() * 8,
        });
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (let i = bubbles.length - 1; i >= 0; i--) {
        const b = bubbles[i];
        b.y -= dt * b.speed;
        b.life += dt;
        if (b.y < -16 || b.life > 5) { bubbles.splice(i, 1); continue; }
        ctx.globalAlpha = Math.max(0, 0.7 * (1 - b.life / 5));
        ctx.drawImage(img, 96, 0, 8, 8, b.x, b.y, b.size, b.size);
      }
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return <canvas ref={canvasRef} className="alchemy-bubble-canvas" />;
}
