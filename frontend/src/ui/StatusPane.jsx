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
import { useEffect, useRef, useState } from 'react';
import AudioManager from '../audio/AudioManager';
import { MAX_DPR } from '../constants';

const DPR = Math.min(window.devicePixelRatio || 1, MAX_DPR);

import statusPaneImg from '../assets/pixel-dungeon/interfaces/status_pane.png';
import buffsImg from '../assets/pixel-dungeon/interfaces/buffs.png';
import warriorSheet from '../assets/pixel-dungeon/sprites/warrior.png';
import mageSheet from '../assets/pixel-dungeon/sprites/mage.png';
import rogueSheet from '../assets/pixel-dungeon/sprites/rogue.png';
import huntressSheet from '../assets/pixel-dungeon/sprites/huntress.png';

// Pixel-faithful reproduction of SPD's StatusPane (large / PC layout).
// Native coordinates from StatusPane.java (large=true branch), scaled by SCALE.
const SCALE = 3;
const PANE_W = 160;  // portrait (30) + bars (128) + 2px right margin
const PANE_H = 39;

// NinePatch source for large background: (0, 64, 41, 39, left=33, right=0, top=4, bottom=0)
// Fixed left 33px (portrait frame), stretchable right 8px.
const BG_FIXED_W  = 33;
const BG_STRETCH_W = 8;
const BG_Y        = 64;

// Large-layout bar sprite regions (status_pane.png)
const HP_FILL   = { x: 0, y: 103, w: 128, h: 9 };  // green HP bar
const HP_SHIELD = { x: 0, y: 112, w: 128, h: 9 };  // white shield overlay
const EXP_FILL  = { x: 0, y: 121, w: 128, h: 7 };  // gold EXP bar

// Avatar: 12x15 crop at column 1 of the class spritesheet (frame index 1).
const FRAME_W = 12;
const FRAME_H = 15;

// buffs.png — 7x7 cells, 18 columns.
const BUFF_SIZE = 7;
const BUFF_COLS = 18;

// 1.5 blinks/sec matching StatusPane.FLASH_RATE.
const FLASH_RATE = Math.PI * 1.5;
const WARNING_COLORS = ['#660000', '#cc0000', '#660000'];

const CLASS_SHEETS = {
  warrior: warriorSheet,
  mage: mageSheet,
  rogue: rogueSheet,
  huntress: huntressSheet,
};

function lerpColor(t, colors) {
  const seg = Math.min(Math.floor(t * (colors.length - 1)), colors.length - 2);
  const local = t * (colors.length - 1) - seg;
  const a = parseInt(colors[seg].slice(1), 16);
  const b = parseInt(colors[seg + 1].slice(1), 16);
  const ar = (a >> 16) & 0xff, ag = (a >> 8) & 0xff, ab = a & 0xff;
  const br = (b >> 16) & 0xff, bg = (b >> 8) & 0xff, bb = b & 0xff;
  const r = Math.round(ar + (br - ar) * local);
  const g = Math.round(ag + (bg - ag) * local);
  const bl = Math.round(ab + (bb - ab) * local);
  return `rgb(${r},${g},${bl})`;
}

export default function StatusPane({ myStats, depth, isAdmin, onSearch, hasTalentPoints, onOpenTalents, onTeleport }) {
  const [showFloorPicker, setShowFloorPicker] = useState(false);
  const canvasRef = useRef(null);
  const imagesRef = useRef({});
  const imgsLoadedRef = useRef(false);
  const statsRef = useRef(myStats);
  const starsRef = useRef([]);
  const prevLevelRef = useRef(myStats.level || 1);
  const warningRef = useRef(0);
  const talentBlinkRef = useRef(0);
  const hasPtsRef = useRef(false);
  useEffect(() => { hasPtsRef.current = !!hasTalentPoints; }, [hasTalentPoints]);

  useEffect(() => { statsRef.current = myStats; }, [myStats]);

  useEffect(() => {
    const sources = { status: statusPaneImg, buffs: buffsImg, ...CLASS_SHEETS };
    const entries = Object.entries(sources);
    let loaded = 0;
    let errored = 0;
    const total = entries.length;
    const checkDone = () => {
      if (loaded + errored === total) imgsLoadedRef.current = true;
    };
    entries.forEach(([key, src]) => {
      const img = new Image();
      img.onload = () => { loaded++; checkDone(); };
      img.onerror = () => {
        errored++;
        console.error(`[StatusPane] failed to load image: ${key} (${src})`);
        checkDone();
      };
      img.src = src;
      if (img.complete && img.naturalWidth > 0) {
        img.onload = null;
        loaded++;
        checkDone();
      } else if (img.complete && img.naturalWidth === 0) {
        img.onerror = null;
        errored++;
        console.error(`[StatusPane] broken image: ${key} (${src})`);
        checkDone();
      }
      imagesRef.current[key] = img;
    });
  }, []);

  useEffect(() => {
    let raf;
    let last = performance.now();
    const avatarCanvas = document.createElement('canvas');
    avatarCanvas.width = FRAME_W;
    avatarCanvas.height = FRAME_H;

    const draw = (now) => {
      let ctx;
      try {
        const dt = (now - last) / 1000;
        last = now;
        const canvas = canvasRef.current;
        ctx = canvas?.getContext('2d');
        const imgs = imagesRef.current;
        if (!ctx) { raf = requestAnimationFrame(draw); return; }

        const s = statsRef.current || {};
        const hp = Math.max(0, Math.ceil(s.hp ?? 0));
        const shield = Math.max(0, Math.floor(s.shield ?? 0));
        const maxHp = Math.max(1, s.maxHp ?? 1);
        const hpPct = Math.min(1, hp / maxHp);
        const shieldPct = Math.min(1, (hp + shield) / maxHp);
        const exp = s.exp ?? 0;
        const maxExp = Math.max(1, s.maxExp ?? 10);
        const expPct = Math.min(1, exp / maxExp);
        const level = s.level ?? 1;
        const effects = s.effects ?? [];
        const sheet = imgs[s.classType] || imgs.warrior;

        if (level > prevLevelRef.current) {
          // Spawn level-up star particles from avatar center
          const cx = (9 + FRAME_W / 2) * SCALE;
          const cy = (8 + FRAME_H / 2) * SCALE;
          for (let i = 0; i < 12; i++) {
            const ang = (Math.PI * 2 * i) / 12 + Math.random() * 0.4;
            const spd = (20 + Math.random() * 30) * SCALE;
            starsRef.current.push({ x: cx, y: cy, vx: Math.cos(ang) * spd, vy: Math.sin(ang) * spd, life: 1 });
          }
          AudioManager.play('LEVELUP');
        }
        prevLevelRef.current = level;

        if (hasPtsRef.current) {
          talentBlinkRef.current = (talentBlinkRef.current + dt * FLASH_RATE) % 2;
        } else {
          talentBlinkRef.current = 0;
        }

        ctx.imageSmoothingEnabled = false;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.save();
        ctx.scale(DPR, DPR);

        // --- Background (NinePatch: fixed left 33px + stretched right) ---
        const statusImg = imgs.status;
        if (statusImg?.complete && statusImg?.naturalWidth > 0) {
          ctx.drawImage(statusImg,
            0, BG_Y, BG_FIXED_W, PANE_H,
            0, 0, BG_FIXED_W * SCALE, PANE_H * SCALE);
          ctx.drawImage(statusImg,
            BG_FIXED_W, BG_Y, BG_STRETCH_W, PANE_H,
            BG_FIXED_W * SCALE, 0, (PANE_W - BG_FIXED_W) * SCALE, PANE_H * SCALE);
        }

        // --- Avatar ---
        ctx.fillStyle = '#161616';
        ctx.fillRect(9 * SCALE, 8 * SCALE, FRAME_W * SCALE, FRAME_H * SCALE);

        if (sheet?.complete && sheet?.naturalWidth > 0) {
          const ac = avatarCanvas.getContext('2d');
          ac.imageSmoothingEnabled = false;
          ac.clearRect(0, 0, FRAME_W, FRAME_H);
          ac.drawImage(sheet, FRAME_W, 0, FRAME_W, FRAME_H, 0, 0, FRAME_W, FRAME_H);

          if (s.isDowned) {
            ac.globalCompositeOperation = 'source-atop';
            ac.fillStyle = 'rgba(0,0,0,0.5)';
            ac.fillRect(0, 0, FRAME_W, FRAME_H);
            ac.globalCompositeOperation = 'source-over';
          } else if (hpPct < 0.334) {
            warningRef.current = (warningRef.current + dt * 5 * (0.4 - hpPct)) % 1;
            ac.globalCompositeOperation = 'source-atop';
            ac.fillStyle = lerpColor(warningRef.current, WARNING_COLORS);
            ac.globalAlpha = 0.5;
            ac.fillRect(0, 0, FRAME_W, FRAME_H);
            ac.globalAlpha = 1;
            ac.globalCompositeOperation = 'source-over';
          } else if (hasPtsRef.current && talentBlinkRef.current > 0) {
            // Golden blink when talent points are available
            ac.globalCompositeOperation = 'source-atop';
            ac.fillStyle = '#ffff00';
            ac.globalAlpha = Math.abs(Math.cos(talentBlinkRef.current * FLASH_RATE)) * 0.5;
            ac.fillRect(0, 0, FRAME_W, FRAME_H);
            ac.globalAlpha = 1;
            ac.globalCompositeOperation = 'source-over';
          }
          ctx.drawImage(avatarCanvas, 9 * SCALE, 8 * SCALE, FRAME_W * SCALE, FRAME_H * SCALE);
        }

        // --- Buff indicators (top of pane, above HP bar) ---
        const buffsSheet = imgs.buffs;
        if (buffsSheet?.complete && buffsSheet?.naturalWidth > 0) {
          effects.forEach((eff, i) => {
            const idx = eff.icon ?? 0;
            const col = idx % BUFF_COLS;
            const row = Math.floor(idx / BUFF_COLS);
            ctx.globalAlpha = 0.85;
            ctx.drawImage(buffsSheet,
              col * BUFF_SIZE, row * BUFF_SIZE, BUFF_SIZE, BUFF_SIZE,
              (31 + i * (BUFF_SIZE + 1)) * SCALE, 0, BUFF_SIZE * SCALE, BUFF_SIZE * SCALE);
            ctx.globalAlpha = 1;
          });
        }

        // --- Shield + HP bars at (30, 19) ---
        if (statusImg?.complete && statusImg?.naturalWidth > 0) {
          // Shield drawn first (white, behind HP)
          if (shieldPct > 0) {
            ctx.drawImage(statusImg,
              HP_SHIELD.x, HP_SHIELD.y, HP_SHIELD.w, HP_SHIELD.h,
              30 * SCALE, 19 * SCALE, HP_SHIELD.w * shieldPct * SCALE, HP_SHIELD.h * SCALE);
          }
          // HP drawn on top (green)
          if (hpPct > 0) {
            ctx.drawImage(statusImg,
              HP_FILL.x, HP_FILL.y, HP_FILL.w, HP_FILL.h,
              30 * SCALE, 19 * SCALE, HP_FILL.w * hpPct * SCALE, HP_FILL.h * SCALE);
          }
        }

        // HP text — centered on 128px bar, alpha 0.6
        const hpLabel = shield > 0 ? `${hp}+${shield}/${maxHp}` : `${hp}/${maxHp}`;
        ctx.font = `${4 * SCALE}px monospace`;
        ctx.textBaseline = 'middle';
        ctx.textAlign = 'center';
        ctx.globalAlpha = 0.6;
        ctx.fillStyle = '#ffffff';
        ctx.fillText(hpLabel, (30 + 64) * SCALE, (19 + 4.5) * SCALE);
        ctx.globalAlpha = 1;

        // --- EXP bar at (30, 30), 128x7 ---
        if (statusImg?.complete && statusImg?.naturalWidth > 0 && expPct > 0) {
          ctx.drawImage(statusImg,
            EXP_FILL.x, EXP_FILL.y, EXP_FILL.w, EXP_FILL.h,
            30 * SCALE, 30 * SCALE, EXP_FILL.w * expPct * SCALE, EXP_FILL.h * SCALE);
        }

        // EXP text — centered on bar, gold, alpha 0.6
        ctx.globalAlpha = 0.6;
        ctx.fillStyle = '#ffffaa';
        ctx.fillText(`${exp}/${maxExp}`, (30 + 64) * SCALE, (30 + 3.5) * SCALE);
        ctx.globalAlpha = 1;

        // Level "lv. X" — centered in 30px portrait zone at y+33
        ctx.fillStyle = '#ffffaa';
        ctx.fillText(`lv. ${level}`, 15 * SCALE, 34 * SCALE);

        // --- Level-up star particles ---
        const stars = starsRef.current;
        for (let i = stars.length - 1; i >= 0; i--) {
          const st = stars[i];
          st.x += st.vx * dt;
          st.y += st.vy * dt;
          st.vy += 40 * SCALE * dt;
          st.life -= dt * 1.4;
          if (st.life <= 0) { stars.splice(i, 1); continue; }
          ctx.globalAlpha = Math.max(0, st.life);
          ctx.fillStyle = '#ffff88';
          ctx.fillRect(st.x, st.y, 2 * SCALE, 2 * SCALE);
          ctx.globalAlpha = 1;
        }
        ctx.restore();
      } catch (err) {
        ctx?.restore();
        console.error('[StatusPane] render error:', err);
      }
      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, []);

  const floorNumbers = [];
  for (let i = 1; i <= 50; i++) floorNumbers.push(i);

  return (
    <div className="top-left-hud">
      <div className="status-pane-footer">
        <span
          className={`status-floor-label${isAdmin ? ' status-floor-label--admin' : ''}`}
          onClick={(e) => {
            if (!isAdmin) return;
            e.stopPropagation();
            AudioManager.play('CLICK');
            setShowFloorPicker(v => !v);
          }}
        >
          floor: {depth}{isAdmin ? ' ▾' : ''}
        </span>
        {showFloorPicker && (
          <div className="floor-picker" onClick={(e) => e.stopPropagation()}>
            {floorNumbers.map(f => (
              <div
                key={f}
                className={`floor-picker__item${f === depth ? ' floor-picker__item--current' : ''}`}
                onClick={() => {
                  AudioManager.play('CLICK');
                  onTeleport?.(f);
                  setShowFloorPicker(false);
                }}
              >
                {f}
              </div>
            ))}
          </div>
        )}
        <button
          type="button"
          className="search-btn"
          onClick={(e) => { e.stopPropagation(); AudioManager.play('CLICK'); onSearch(); }}
        >
          Search (E)
        </button>
      </div>
      <canvas
        ref={canvasRef}
        width={PANE_W * SCALE * DPR}
        height={PANE_H * SCALE * DPR}
        style={{ width: PANE_W * SCALE, height: PANE_H * SCALE }}
        className="status-pane-canvas"
        onClick={(e) => {
          const x = e.nativeEvent.offsetX;
          const y = e.nativeEvent.offsetY;
          const ax = 9 * SCALE, ay = 8 * SCALE;
          const aw = FRAME_W * SCALE, ah = FRAME_H * SCALE;
          if (x >= ax && x < ax + aw && y >= ay && y < ay + ah) {
            AudioManager.play('CLICK');
            onOpenTalents?.();
          }
        }}
      />
    </div>
  );
}
