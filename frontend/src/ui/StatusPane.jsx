import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import { MAX_DPR } from '../constants';
import WndHero from './WndHero';

const DPR = Math.min(window.devicePixelRatio || 1, MAX_DPR);

const PANE_W_LARGE = 160;
const PANE_H_LARGE = 39;
const PANE_W_SMALL = 82;
const PANE_H_SMALL = 38;

const BG_LARGE = { y: 64, h: 39, left: 33, right: 4, stretchSrcW: 4 };
const BG_SMALL = { y: 0,  h: 38, left: 32, right: 5, stretchSrcW: 45 };

const HP_FILL_LARGE   = { x: 0, y: 103, w: 128, h: 9 };
const HP_SHIELD_LARGE = { x: 0, y: 112, w: 128, h: 9 };
const EXP_FILL_LARGE  = { x: 0, y: 121, w: 128, h: 7 };
const HP_FILL_SMALL   = { x: 0, y: 40, w: 50, h: 4 };
const HP_SHIELD_SMALL = { x: 0, y: 44, w: 50, h: 4 };
const EXP_FILL_SMALL  = { x: 0, y: 48, w: 17, h: 4 };

const FRAME_W = 12;
const FRAME_H = 15;

// The HUD portrait is the hero avatar (walking sheet col 1), cropped to the row
// matching the equipped armor tier so it reflects the gear actually worn —
// mirrors SPD HeroSprite.avatar(), which shifts the frame by tiers().get(tier).
const MAX_ARMOR_TIER = 6;

const BUFF_SIZE = 7;
const BUFF_COLS = 18;
const MAX_BUFFS = 14; // matches SPD's BuffIndicator.maxBuffs default

const FLASH_RATE = Math.PI * 1.5;
const WARNING_COLORS = ['#660000', '#cc0000', '#660000'];

function lerpColor(t, colors) {
  // t in [0,1] across the colors array (matches ColorMath.interpolate).
  if (!Number.isFinite(t)) t = 0;
  t = Math.max(0, Math.min(1, t));
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

export default function StatusPane({ myStats, depth, exitPos, isAdmin, onSearch, hasTalentPoints, gold, onOpenTalentPane, onTeleport, isBusy, onBuffClick, interfaceSize, assetImages }) {
  const [showHeroInfo, setShowHeroInfo] = useState(false);
  const isLarge = interfaceSize > 0;
  const SCALE = isLarge ? 3 : 2;
  const PANE_W = isLarge ? PANE_W_LARGE : PANE_W_SMALL;
  const PANE_H = isLarge ? PANE_H_LARGE : PANE_H_SMALL;
  const hpFill = isLarge ? HP_FILL_LARGE : HP_FILL_SMALL;
  const hpShield = isLarge ? HP_SHIELD_LARGE : HP_SHIELD_SMALL;
  const expFill = isLarge ? EXP_FILL_LARGE : EXP_FILL_SMALL;
  const BG = isLarge ? BG_LARGE : BG_SMALL;
  const { t } = useTranslation();
  const [showFloorPicker, setShowFloorPicker] = useState(false);
  const canvasRef = useRef(null);
  const imagesRef = useRef({});
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
    const imgs = imagesRef.current;
    if (assetImages?.statusPane) imgs.status = assetImages.statusPane;
    if (assetImages?.buffs) imgs.buffs = assetImages.buffs;
    if (assetImages?.warrior) imgs.warrior = assetImages.warrior;
    if (assetImages?.mage) imgs.mage = assetImages.mage;
    if (assetImages?.rogue) imgs.rogue = assetImages.rogue;
    if (assetImages?.huntress) imgs.huntress = assetImages.huntress;
  }, [assetImages]);

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
        const rawHpPct = Math.min(1, hp / maxHp);
        const rawShieldPct = Math.min(1, (hp + shield) / maxHp);
        const hpPct = rawHpPct;
        const drawShieldPct = rawShieldPct;
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
          const leftW = BG.left * SCALE;
          const rightW = BG.right * SCALE;
          const stretchW = (PANE_W - BG.left - BG.right) * SCALE;
          const srcStretchX = BG.left;
          const srcRightX = BG.left + BG.stretchSrcW;
          ctx.drawImage(statusImg, 0, BG.y, BG.left, BG.h, 0, 0, leftW, PANE_H * SCALE);
          ctx.drawImage(statusImg, srcStretchX, BG.y, BG.stretchSrcW, BG.h, leftW, 0, stretchW, PANE_H * SCALE);
          ctx.drawImage(statusImg, srcRightX, BG.y, BG.right, BG.h, leftW + stretchW, 0, rightW, PANE_H * SCALE);
        }

        ctx.fillStyle = '#161616';
        ctx.fillRect(9 * SCALE, 8 * SCALE, FRAME_W * SCALE, FRAME_H * SCALE);

        if (sheet?.complete && sheet?.naturalWidth > 0) {
          const ac = avatarCanvas.getContext('2d');
          ac.imageSmoothingEnabled = false;
          ac.clearRect(0, 0, FRAME_W, FRAME_H);
          const armorRow = Math.max(0, Math.min(s.armorTier || 0, MAX_ARMOR_TIER)) * FRAME_H;
          ac.drawImage(sheet, FRAME_W, armorRow, FRAME_W, FRAME_H, 0, 0, FRAME_W, FRAME_H);

          if (s.isDowned) {
            ac.globalCompositeOperation = 'source-atop';
            ac.fillStyle = 'rgba(0,0,0,0.5)';
            ac.fillRect(0, 0, FRAME_W, FRAME_H);
            ac.globalCompositeOperation = 'source-over';
          } else if (rawHpPct < 0.334) {
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

        // --- BusyIndicator (rotating dots around center when busy) ---
        if (isBusy) {
          const busyX = isLarge ? (9 + FRAME_W / 2) * SCALE : 6 * SCALE;
          const busyY = isLarge ? (8 + FRAME_H / 2) * SCALE : 35 * SCALE;
          const angle = nowSec * 3;
          ctx.save();
          ctx.translate(busyX, busyY);
          for (let i = 0; i < 4; i++) {
            const a = angle + (i / 4) * Math.PI * 2;
            const r = isLarge ? 22 * SCALE / 3 : 5 * SCALE;
            const dx = Math.cos(a) * r;
            const dy = Math.sin(a) * r;
            const dotSize = isLarge ? 1.5 * SCALE / 3 : 1.5 * SCALE;
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
          effects.slice(0, MAX_BUFFS).forEach((eff, i) => {
            const idx = eff.icon ?? 0;
            const col = idx % BUFF_COLS;
            const row = Math.floor(idx / BUFF_COLS);
            const bx = (31 + i * (BUFF_SIZE + 1)) * SCALE;
            const by = isLarge ? 0 : 8 * SCALE;
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
          if (isLarge) {
            if (drawShieldPct > 0) {
              ctx.drawImage(statusImg,
                hpShield.x, hpShield.y, hpShield.w, hpShield.h,
                30 * SCALE, 19 * SCALE, hpShield.w * drawShieldPct * SCALE, hpShield.h * SCALE);
            }
            if (hpPct > 0) {
              ctx.drawImage(statusImg,
                hpFill.x, hpFill.y, hpFill.w, hpFill.h,
                30 * SCALE, 19 * SCALE, hpFill.w * hpPct * SCALE, hpFill.h * SCALE);
            }
          } else {
            if (drawShieldPct > 0) {
              ctx.drawImage(statusImg,
                hpShield.x, hpShield.y, hpShield.w, hpShield.h,
                33 * SCALE, 2 * SCALE, hpShield.w * drawShieldPct * SCALE, hpShield.h * SCALE);
            }
            if (hpPct > 0) {
              ctx.drawImage(statusImg,
                hpFill.x, hpFill.y, hpFill.w, hpFill.h,
                33 * SCALE, 2 * SCALE, hpFill.w * hpPct * SCALE, hpFill.h * SCALE);
            }
          }
        }

        const hpLabel = shield > 0 ? `${hp}+${shield}/${maxHp}` : `${hp}/${maxHp}`;
        ctx.font = `${(isLarge ? 4 : 2.5) * SCALE}px monospace`;
        ctx.textBaseline = 'middle';
        ctx.globalAlpha = 0.6;
        ctx.fillStyle = '#ffffff';
        if (isLarge) {
          ctx.textAlign = 'center';
          ctx.fillText(hpLabel, (30 + 64) * SCALE, (19 + 4.5) * SCALE);
        } else {
          ctx.textAlign = 'left';
          ctx.fillText(hpLabel, (30 + 1) * SCALE, (2 + 2) * SCALE);
        }
        ctx.globalAlpha = 1;

        if (statusImg?.complete && statusImg?.naturalWidth > 0 && expPct > 0) {
          ctx.drawImage(statusImg,
            expFill.x, expFill.y, expFill.w, expFill.h,
            isLarge ? 30 * SCALE : 2 * SCALE,
            isLarge ? 30 * SCALE : 30 * SCALE,
            expFill.w * expPct * SCALE, expFill.h * SCALE);
        }

        ctx.globalAlpha = 0.6;
        ctx.fillStyle = '#ffffaa';
        ctx.font = `${(isLarge ? 4 : 2.5) * SCALE}px monospace`;
        ctx.textAlign = isLarge ? 'center' : 'left';
        ctx.fillText(`${exp}/${maxExp}`, isLarge ? (30 + 64) * SCALE : (2 + 1) * SCALE, (30 + 3.5) * SCALE);
        ctx.globalAlpha = 1;

        ctx.fillStyle = '#ffffaa';
        if (isLarge) {
          ctx.fillText(t('ui.lv', { level }), 15 * SCALE, 34 * SCALE);
        } else {
          ctx.font = `${(isLarge ? 4 : 3) * SCALE}px monospace`;
          ctx.textAlign = 'center';
          ctx.fillText(level.toString(), 25.5 * SCALE, 31.5 * SCALE);
        }

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
      } catch {
        ctx?.restore();
      }
      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [t, isBusy, SCALE, isLarge, PANE_W, PANE_H, hpFill, hpShield, expFill, BG]);

  const floorNumbers = [];
  for (let i = 1; i <= 26; i++) floorNumbers.push(i);

  return (
  <>
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
            setShowHeroInfo(true);
            return;
          }
          // Buff icon hit test — icons are at y = (isLarge ? 0 : 8*SCALE), x = (31 + i*(BUFF_SIZE+1))*SCALE
          const effects = statsRef.current?.effects || [];
          const buffsYOffset = isLarge ? 0 : 8 * SCALE;
          for (let i = 0; i < Math.min(effects.length, MAX_BUFFS); i++) {
            const bx = (31 + i * (BUFF_SIZE + 1)) * SCALE;
            const by = buffsYOffset;
            const bw = BUFF_SIZE * SCALE;
            const bh = BUFF_SIZE * SCALE;
            if (x >= bx && x < bx + bw && y >= by && y < by + bh) {
              AudioManager.play('CLICK');
              onBuffClick?.(effects[i]);
              return;
            }
          }
        }}
      />
    </div>
    {showHeroInfo && (
      <WndHero
        myStats={myStats}
        depth={depth}
        gold={gold}
        onOpenTalents={onOpenTalentPane}
        onClose={() => setShowHeroInfo(false)}
      />
    )}
  </>
  );
}
