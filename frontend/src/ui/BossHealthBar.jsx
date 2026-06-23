import { useEffect, useRef } from 'react';

const DPR = Math.min(window.devicePixelRatio || 1, 2);

import bossHpImg from '../assets/pixel-dungeon/interfaces/boss_hp.png';
import gooSprite from '../assets/pixel-dungeon/sprites/goo.png';
import tenguSprite from '../assets/pixel-dungeon/sprites/tengu.png';
import dm300Sprite from '../assets/pixel-dungeon/sprites/dm300.png';
import kingSprite from '../assets/pixel-dungeon/sprites/king.png';
import yogSprite from '../assets/pixel-dungeon/sprites/yog.png';
import buffsImg from '../assets/pixel-dungeon/interfaces/buffs.png';

const BAR_SRC = { x: 0, y: 16, w: 128, h: 30 };
const HP_SRC = { x: 0, y: 46, w: 96, h: 9 };
const SHIELD_SRC = { x: 0, y: 55, w: 96, h: 9 };
const SKULL_ICON_SRC = { x: 64, y: 0, w: 6, h: 6 };

const BUFF_SIZE = 7;
const BUFF_COLS = 18;
const MAX_BUFFS = 6;

const BOSS_SPRITES = {
  Goo: { fw: 20, fh: 14, src: gooSprite },
  Tengu: { fw: 14, fh: 16, src: tenguSprite },
  'DM-300': { fw: 25, fh: 22, src: dm300Sprite },
  'Dwarf King': { fw: 16, fh: 16, src: kingSprite },
  'Yog-Dzewa': { fw: 20, fh: 19, src: yogSprite },
};

function bossScale() {
  return Math.min(3, Math.max(2, Math.floor(window.innerWidth / 160)));
}

export default function BossHealthBar({ boss, bleeding }) {
  const canvasRef = useRef(null);
  const bossRef = useRef(boss);
  const bleedingRef = useRef(bleeding);
  const bossHpRef = useRef(null);
  const buffsSheetRef = useRef(null);
  const spriteRef = useRef(null);
  const spriteInfoRef = useRef(null);
  const bloodPartsRef = useRef([]);
  const scaleRef = useRef(bossScale());

  useEffect(() => { bossRef.current = boss; }, [boss]);
  useEffect(() => { bleedingRef.current = bleeding; }, [bleeding]);

  useEffect(() => {
    const loadImg = (src) => new Promise(resolve => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = src;
      if (img.complete && img.naturalWidth > 0) { img.onload = null; resolve(img); }
      else if (img.complete && img.naturalWidth === 0) { img.onerror = null; resolve(null); }
    });

    const loadAll = async () => {
      const [bossHp, buffs] = await Promise.all([
        loadImg(bossHpImg),
        loadImg(buffsImg),
      ]);
      bossHpRef.current = bossHp;
      buffsSheetRef.current = buffs;

      const info = BOSS_SPRITES[boss?.name];
      if (info) {
        const sprite = await loadImg(info.src);
        spriteRef.current = sprite;
        spriteInfoRef.current = info;
      } else {
        spriteRef.current = null;
        spriteInfoRef.current = null;
      }
    };
    loadAll();
  }, [boss?.name]);

  useEffect(() => {
    const onResize = () => { scaleRef.current = bossScale(); };
    window.addEventListener('resize', onResize);

    let raf;

    const draw = (now, prev) => {
      const dt = prev ? (now - prev) / 1000 : 0.016;
      const canvas = canvasRef.current;
      if (!canvas) { raf = requestAnimationFrame(t => draw(t, now)); return; }
      const ctx = canvas.getContext('2d');
      if (!ctx) { raf = requestAnimationFrame(t => draw(t, now)); return; }

      const b = bossRef.current;
      const bossHp = bossHpRef.current;
      const isBleeding = bleedingRef.current;

      if (!b || !bossHp) { raf = requestAnimationFrame(t => draw(t, now)); return; }

      const s = scaleRef.current;

      const hp = Math.max(0, b.hp || 0);
      const shieldAmt = Math.max(0, b.shield || 0);
      const maxHp = Math.max(1, b.maxHp || 1);

      const healthPct = Math.min(1, hp / maxHp);
      const drawShieldPct = Math.min(1, (hp + shieldAmt) / maxHp);

      ctx.imageSmoothingEnabled = false;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.save();
      ctx.scale(DPR, DPR);

      ctx.drawImage(bossHp,
        BAR_SRC.x, BAR_SRC.y, BAR_SRC.w, BAR_SRC.h,
        0, 0, BAR_SRC.w * s, BAR_SRC.h * s);

      if (drawShieldPct > 0) {
        ctx.drawImage(bossHp,
          SHIELD_SRC.x, SHIELD_SRC.y, SHIELD_SRC.w, SHIELD_SRC.h,
          30 * s, 2 * s, SHIELD_SRC.w * drawShieldPct * s, SHIELD_SRC.h * s);
      }

      if (healthPct > 0) {
        ctx.drawImage(bossHp,
          HP_SRC.x, HP_SRC.y, HP_SRC.w, HP_SRC.h,
          30 * s, 2 * s, HP_SRC.w * healthPct * s, HP_SRC.h * s);
      }

      ctx.font = `${5 * s}px monospace`;
      ctx.textBaseline = 'middle';
      ctx.textAlign = 'center';
      ctx.globalAlpha = 0.6;
      ctx.fillStyle = '#ffffff';
      const hpText = shieldAmt > 0 ? `${hp}+${shieldAmt}/${maxHp}` : `${hp}/${maxHp}`;
      ctx.fillText(hpText, (30 + 48) * s, (2 + 4.5) * s);
      ctx.globalAlpha = 1;

      const spriteImg = spriteRef.current;
      const sInfo = spriteInfoRef.current;
      const paneSize = 30 * s;
      if (spriteImg && sInfo) {
        const sw = sInfo.fw * s;
        const sh = sInfo.fh * s;
        const sx = (paneSize - sw) / 2;
        const sy = (paneSize - sh) / 2;
        if (isBleeding) {
          ctx.save();
          ctx.drawImage(spriteImg, 0, 0, sInfo.fw, sInfo.fh, sx, sy, sw, sh);
          ctx.globalCompositeOperation = 'source-atop';
          ctx.fillStyle = 'rgba(204, 0, 0, 0.3)';
          ctx.fillRect(sx, sy, sw, sh);
          ctx.restore();
        } else {
          ctx.drawImage(spriteImg, 0, 0, sInfo.fw, sInfo.fh, sx, sy, sw, sh);
        }
      } else {
        ctx.drawImage(bossHp,
          SKULL_ICON_SRC.x, SKULL_ICON_SRC.y, SKULL_ICON_SRC.w, SKULL_ICON_SRC.h,
          (30 - 6) / 2 * s, (30 - 6) / 2 * s, 6 * s, 6 * s);
        if (isBleeding) {
          ctx.fillStyle = 'rgba(204, 0, 0, 0.3)';
          ctx.fillRect((30 - 6) / 2 * s, (30 - 6) / 2 * s, 6 * s, 6 * s);
        }
      }

      if (isBleeding) {
        const cx = 15 * s;
        const cy = 15 * s;
        if (Math.random() < 0.3) {
          const ang = Math.random() * Math.PI * 2;
          const spd = 10 + Math.random() * 20;
          bloodPartsRef.current.push({
            x: cx, y: cy,
            vx: Math.cos(ang) * spd,
            vy: Math.sin(ang) * spd - 15,
            life: 0.4 + Math.random() * 0.3,
          });
        }
        const parts = bloodPartsRef.current;
        for (let i = parts.length - 1; i >= 0; i--) {
          const p = parts[i];
          p.x += p.vx * dt;
          p.y += p.vy * dt;
          p.vy += 60 * dt;
          p.life -= dt;
          if (p.life <= 0) { parts.splice(i, 1); continue; }
          ctx.globalAlpha = Math.min(1, p.life * 3);
          ctx.fillStyle = '#cc0000';
          ctx.fillRect(p.x, p.y, 2 * s, 2 * s);
        }
        ctx.globalAlpha = 1;
      } else {
        bloodPartsRef.current = [];
      }

      const buffsSheet = buffsSheetRef.current;
      const effects = b.effects || [];
      if (buffsSheet && effects.length > 0) {
        effects.slice(0, MAX_BUFFS).forEach((eff, i) => {
          const idx = eff.icon ?? 0;
          const col = idx % BUFF_COLS;
          const row = Math.floor(idx / BUFF_COLS);
          const bw = BUFF_SIZE * s;
          const bh = BUFF_SIZE * s;
          const bx = (31 + i * (BUFF_SIZE + 1)) * s;
          const by = (BAR_SRC.h - 10) * s;
          ctx.globalAlpha = 0.85;
          ctx.drawImage(buffsSheet,
            col * BUFF_SIZE, row * BUFF_SIZE, BUFF_SIZE, BUFF_SIZE,
            bx, by, bw, bh);
          ctx.globalAlpha = 1;
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

      ctx.restore();
      raf = requestAnimationFrame(t => draw(t, now));
    };
    raf = requestAnimationFrame(t => draw(t, t));
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
    };
  }, []);

  if (!boss) return null;

  return (
    <div className="boss-health-bar">
      <canvas
        ref={canvasRef}
        width={BAR_SRC.w * bossScale() * DPR}
        height={BAR_SRC.h * bossScale() * DPR}
        style={{ width: BAR_SRC.w * bossScale(), height: BAR_SRC.h * bossScale() }}
      />
    </div>
  );
}
