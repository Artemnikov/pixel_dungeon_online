import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import { MAX_DPR } from '../constants';

const DPR = Math.min(window.devicePixelRatio || 1, MAX_DPR);

import statusPaneImg from '../assets/pixel-dungeon/interfaces/status_pane.png';
import buffsImg from '../assets/pixel-dungeon/interfaces/buffs.png';
import warriorSheet from '../assets/pixel-dungeon/sprites/warrior.png';
import mageSheet from '../assets/pixel-dungeon/sprites/mage.png';
import rogueSheet from '../assets/pixel-dungeon/sprites/rogue.png';
import huntressSheet from '../assets/pixel-dungeon/sprites/huntress.png';

const SCALE = 3;
const PANE_W = 160;
const PANE_H = 39;

const BG_FIXED_W  = 33;
const BG_STRETCH_W = 8;
const BG_Y        = 64;

const HP_FILL   = { x: 0, y: 103, w: 128, h: 9 };
const HP_SHIELD = { x: 0, y: 112, w: 128, h: 9 };
const EXP_FILL  = { x: 0, y: 121, w: 128, h: 7 };

const FRAME_W = 12;
const FRAME_H = 15;

const BUFF_SIZE = 7;
const BUFF_COLS = 18;

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

export default function StatusPane({ myStats, depth, exitPos, isAdmin, onSearch, hasTalentPoints, onOpenTalents, onTeleport, isBusy }) {
  const { t } = useTranslation();
  const [showFloorPicker, setShowFloorPicker] = useState(false);
  const canvasRef = useRef(null);
  const imagesRef = useRef({});
  const imgsLoadedRef = useRef(false);
  const statsRef = useRef(myStats);
  const exitPosRef = useRef(exitPos);
  const starsRef = useRef([]);
  const prevLevelRef = useRef(myStats.level || 1);
  const warningRef = useRef(0);
  const talentBlinkRef = useRef(0);
  const hasPtsRef = useRef(false);
  useEffect(() => { hasPtsRef.current = !!hasTalentPoints; }, [hasTalentPoints]);

  useEffect(() => { statsRef.current = myStats; }, [myStats]);
  useEffect(() => { exitPosRef.current = exitPos; }, [exitPos]);

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

        const statusImg = imgs.status;
        if (statusImg?.complete && statusImg?.naturalWidth > 0) {
          ctx.drawImage(statusImg,
            0, BG_Y, BG_FIXED_W, PANE_H,
            0, 0, BG_FIXED_W * SCALE, PANE_H * SCALE);
          ctx.drawImage(statusImg,
            BG_FIXED_W, BG_Y, BG_STRETCH_W, PANE_H,
            BG_FIXED_W * SCALE, 0, (PANE_W - BG_FIXED_W) * SCALE, PANE_H * SCALE);
        }

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
            ac.globalCompositeOperation = 'source-atop';
            ac.fillStyle = '#ffff00';
            ac.globalAlpha = Math.abs(Math.cos(talentBlinkRef.current * FLASH_RATE)) * 0.5;
            ac.fillRect(0, 0, FRAME_W, FRAME_H);
            ac.globalAlpha = 1;
            ac.globalCompositeOperation = 'source-over';
          }
          ctx.drawImage(avatarCanvas, 9 * SCALE, 8 * SCALE, FRAME_W * SCALE, FRAME_H * SCALE);
        }

        // --- Compass needle pointing toward floor exit ---
        const ep = exitPosRef.current;
        const heroPos = statsRef.current?.pos;
        if (ep && heroPos) {
          const angle = Math.atan2(ep[1] - heroPos.y, ep[0] - heroPos.x);
          const cx = (9 + FRAME_W / 2) * SCALE;
          const cy = (8 + FRAME_H / 2) * SCALE;
          ctx.save();
          ctx.translate(cx, cy);
          ctx.rotate(angle);
          ctx.strokeStyle = '#ffff00';
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.moveTo(0, 0);
          ctx.lineTo(6 * SCALE / 3, 0);
          ctx.stroke();
          ctx.fillStyle = '#ffff00';
          ctx.beginPath();
          ctx.arc(0, 0, 1.2, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
        }

        // --- CircleArc (action timer around avatar) ---
        const nowSec = performance.now() / 1000;
        const sweep = 1 - (nowSec % 1);
        ctx.save();
        ctx.strokeStyle = '#808080';
        ctx.lineWidth = 4.25 * SCALE / 3;
        ctx.translate((9 + FRAME_W / 2) * SCALE, (8 + FRAME_H / 2) * SCALE);
        ctx.rotate(-Math.PI / 2);
        ctx.beginPath();
        ctx.arc(0, 0, 18 * SCALE / 3, 0, Math.PI * 2 * sweep);
        ctx.stroke();
        ctx.restore();

        // --- BusyIndicator (rotating dots around avatar when busy) ---
        if (isBusy) {
          const angle = nowSec * 3;
          ctx.save();
          ctx.translate((9 + FRAME_W / 2) * SCALE, (8 + FRAME_H / 2) * SCALE);
          for (let i = 0; i < 4; i++) {
            const a = angle + (i / 4) * Math.PI * 2;
            const r = 22 * SCALE / 3;
            const dx = Math.cos(a) * r;
            const dy = Math.sin(a) * r;
            const dotSize = 1.5 * SCALE / 3;
            ctx.fillStyle = '#808080';
            ctx.globalAlpha = 0.3 + 0.7 * (0.5 + 0.5 * Math.sin(a - angle));
            ctx.beginPath();
            ctx.arc(dx, dy, dotSize, 0, Math.PI * 2);
            ctx.fill();
          }
          ctx.restore();
          ctx.globalAlpha = 1;
        }

        const buffsSheet = imgs.buffs;
        if (buffsSheet?.complete && buffsSheet?.naturalWidth > 0) {
          effects.forEach((eff, i) => {
            const idx = eff.icon ?? 0;
            const col = idx % BUFF_COLS;
            const row = Math.floor(idx / BUFF_COLS);
            const bx = (31 + i * (BUFF_SIZE + 1)) * SCALE;
            const by = 0;
            const bw = BUFF_SIZE * SCALE;
            const bh = BUFF_SIZE * SCALE;
            ctx.globalAlpha = 0.85;
            ctx.drawImage(buffsSheet,
              col * BUFF_SIZE, row * BUFF_SIZE, BUFF_SIZE, BUFF_SIZE,
              bx, by, bw, bh);
            ctx.globalAlpha = 1;
            // Duration fade overlay (grey from bottom, SPD BuffIcon.iconFadePercent)
            if (eff.duration > 0 && eff.remaining != null) {
              const fade = Math.max(0, Math.min(1, eff.remaining / eff.duration));
              if (fade < 1) {
                ctx.fillStyle = '#000';
                ctx.globalAlpha = 0.35 * (1 - fade);
                ctx.fillRect(bx, by + bh * (1 - fade), bw, bh * fade);
                ctx.globalAlpha = 1;
              }
            }
          });
        }

        if (statusImg?.complete && statusImg?.naturalWidth > 0) {
          if (shieldPct > 0) {
            ctx.drawImage(statusImg,
              HP_SHIELD.x, HP_SHIELD.y, HP_SHIELD.w, HP_SHIELD.h,
              30 * SCALE, 19 * SCALE, HP_SHIELD.w * shieldPct * SCALE, HP_SHIELD.h * SCALE);
          }
          if (hpPct > 0) {
            ctx.drawImage(statusImg,
              HP_FILL.x, HP_FILL.y, HP_FILL.w, HP_FILL.h,
              30 * SCALE, 19 * SCALE, HP_FILL.w * hpPct * SCALE, HP_FILL.h * SCALE);
          }
        }

        const hpLabel = shield > 0 ? `${hp}+${shield}/${maxHp}` : `${hp}/${maxHp}`;
        ctx.font = `${4 * SCALE}px monospace`;
        ctx.textBaseline = 'middle';
        ctx.textAlign = 'center';
        ctx.globalAlpha = 0.6;
        ctx.fillStyle = '#ffffff';
        ctx.fillText(hpLabel, (30 + 64) * SCALE, (19 + 4.5) * SCALE);
        ctx.globalAlpha = 1;

        if (statusImg?.complete && statusImg?.naturalWidth > 0 && expPct > 0) {
          ctx.drawImage(statusImg,
            EXP_FILL.x, EXP_FILL.y, EXP_FILL.w, EXP_FILL.h,
            30 * SCALE, 30 * SCALE, EXP_FILL.w * expPct * SCALE, EXP_FILL.h * SCALE);
        }

        ctx.globalAlpha = 0.6;
        ctx.fillStyle = '#ffffaa';
        ctx.fillText(`${exp}/${maxExp}`, (30 + 64) * SCALE, (30 + 3.5) * SCALE);
        ctx.globalAlpha = 1;

        ctx.fillStyle = '#ffffaa';
        ctx.fillText(t('ui.lv', { level }), 15 * SCALE, 34 * SCALE);

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
      }
      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [t]);

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
          {t('ui.floor', { depth })}{isAdmin ? ' ▾' : ''}
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
          {t('ui.search')}
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
