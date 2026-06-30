import { useEffect, useRef, memo } from 'react';

const DPR = Math.min(window.devicePixelRatio || 1, 2);


const BAR_SRC = { x: 0, y: 16, w: 128, h: 30 };
const HP_SRC = { x: 0, y: 46, w: 96, h: 9 };
const SHIELD_SRC = { x: 0, y: 55, w: 96, h: 9 };
const SKULL_ICON_SRC = { x: 64, y: 0, w: 6, h: 6 };

const SMALL_BAR_SRC = { x: 0, y: 0, w: 64, h: 16 };
const SMALL_HP_SRC = { x: 71, y: 0, w: 47, h: 4 };
const SMALL_SHIELD_SRC = { x: 71, y: 5, w: 47, h: 4 };
const SMALL_LEFT_PANE_W = 16;

const BUFF_SIZE = 7;
const BUFF_COLS = 18;
const MAX_BUFFS = 6;

const BOSS_SPRITE_KEYS = {
  Goo: { fw: 20, fh: 14, key: 'goo' },
  Tengu: { fw: 14, fh: 16, key: 'tengu' },
  'DM-300': { fw: 25, fh: 22, key: 'dm300' },
  'Dwarf King': { fw: 16, fh: 16, key: 'king' },
  'Yog-Dzewa': { fw: 20, fh: 19, key: 'yog' },
};

function bossScale() {
  return Math.min(3, Math.max(2, Math.floor(window.innerWidth / 160)));
}

function BossHealthBar({ boss, bleeding, interfaceSize, assetImages }) {
  const canvasRef = useRef(null);
  const bossRef = useRef(boss);
  const bleedingRef = useRef(bleeding);
  const isLargeRef = useRef((interfaceSize || 0) > 0);
  const bossHpRef = useRef(null);
  const buffsSheetRef = useRef(null);
  const spriteRef = useRef(null);
  const spriteInfoRef = useRef(null);
  const bloodPartsRef = useRef([]);
  const scaleRef = useRef(bossScale());

  useEffect(() => { bossRef.current = boss; }, [boss]);
  useEffect(() => { bleedingRef.current = bleeding; }, [bleeding]);
  useEffect(() => { isLargeRef.current = (interfaceSize || 0) > 0; }, [interfaceSize]);

  useEffect(() => {
    if (!assetImages) return;
    bossHpRef.current = assetImages.bossHp;
    buffsSheetRef.current = assetImages.buffs;
    const info = BOSS_SPRITE_KEYS[boss?.name];
    if (info && assetImages[info.key]) {
      spriteRef.current = assetImages[info.key];
      spriteInfoRef.current = info;
    } else {
      spriteRef.current = null;
      spriteInfoRef.current = null;
    }
  }, [assetImages, boss?.name]);

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
      const isLarge = isLargeRef.current;

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

      const barW = isLarge ? BAR_SRC.w : SMALL_BAR_SRC.w;
      const barH = isLarge ? BAR_SRC.h : SMALL_BAR_SRC.h;
      const hpFillX = isLarge ? 30 : SMALL_LEFT_PANE_W;
      const paneSize = isLarge ? 30 : SMALL_LEFT_PANE_W;

      ctx.drawImage(bossHp,
        isLarge ? BAR_SRC.x : SMALL_BAR_SRC.x,
        isLarge ? BAR_SRC.y : SMALL_BAR_SRC.y,
        isLarge ? BAR_SRC.w : SMALL_BAR_SRC.w,
        isLarge ? BAR_SRC.h : SMALL_BAR_SRC.h,
        0, 0, barW * s, barH * s);

      if (drawShieldPct > 0) {
        if (isLarge) {
          ctx.drawImage(bossHp,
            SHIELD_SRC.x, SHIELD_SRC.y, SHIELD_SRC.w, SHIELD_SRC.h,
            hpFillX * s, 2 * s, SHIELD_SRC.w * drawShieldPct * s, SHIELD_SRC.h * s);
        } else {
          ctx.drawImage(bossHp,
            SMALL_SHIELD_SRC.x, SMALL_SHIELD_SRC.y, SMALL_SHIELD_SRC.w, SMALL_SHIELD_SRC.h,
            hpFillX * s, 3 * s, SMALL_SHIELD_SRC.w * drawShieldPct * s, SMALL_SHIELD_SRC.h * s);
        }
      }

      if (healthPct > 0) {
        if (isLarge) {
          ctx.drawImage(bossHp,
            HP_SRC.x, HP_SRC.y, HP_SRC.w, HP_SRC.h,
            hpFillX * s, 2 * s, HP_SRC.w * healthPct * s, HP_SRC.h * s);
        } else {
          ctx.drawImage(bossHp,
            SMALL_HP_SRC.x, SMALL_HP_SRC.y, SMALL_HP_SRC.w, SMALL_HP_SRC.h,
            hpFillX * s, 3 * s, SMALL_HP_SRC.w * healthPct * s, SMALL_HP_SRC.h * s);
        }
      }

      if (isLarge) {
        ctx.font = `${5 * s}px monospace`;
        ctx.textAlign = 'center';
      } else {
        ctx.font = `${2.5 * s}px monospace`;
        ctx.textAlign = 'left';
      }
      ctx.textBaseline = 'middle';
      ctx.globalAlpha = 0.6;
      ctx.fillStyle = '#ffffff';
      const hpText = shieldAmt > 0 ? `${hp}+${shieldAmt}/${maxHp}` : `${hp}/${maxHp}`;
      if (isLarge) {
        ctx.fillText(hpText, (hpFillX + 48) * s, (2 + 4.5) * s);
      } else {
        ctx.fillText(hpText, (hpFillX + 1) * s, (3 + 2) * s);
      }
      ctx.globalAlpha = 1;

      const spriteImg = spriteRef.current;
      const sInfo = spriteInfoRef.current;
      if (isLarge && spriteImg && sInfo) {
        const sw = sInfo.fw * s;
        const sh = sInfo.fh * s;
        const sx = (paneSize * s - sw) / 2;
        const sy = (paneSize * s - sh) / 2;
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
        const iconW = 6 * s;
        const iconH = 6 * s;
        const skullX = (paneSize - 6) / 2 * s;
        const skullY = (paneSize - 6) / 2 * s;
        ctx.drawImage(bossHp,
          SKULL_ICON_SRC.x, SKULL_ICON_SRC.y, SKULL_ICON_SRC.w, SKULL_ICON_SRC.h,
          skullX, skullY, iconW, iconH);
        if (isBleeding) {
          ctx.save();
          ctx.globalCompositeOperation = 'source-atop';
          ctx.fillStyle = `rgba(204, 0, 0, ${isLarge ? 0.3 : 0.6})`;
          ctx.fillRect(skullX, skullY, iconW, iconH);
          ctx.restore();
        }
      }

      if (isBleeding) {
        const cx = isLarge ? 15 * s : 8 * s;
        const cy = isLarge ? 15 * s : 8 * s;
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
          const bx = (hpFillX + 1 + i * (BUFF_SIZE + 1)) * s;
          const by = isLarge ? (BAR_SRC.h - 10) * s : (SMALL_BAR_SRC.h - 8) * s;
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

  const isLarge = (interfaceSize || 0) > 0;
  const barW = isLarge ? BAR_SRC.w : SMALL_BAR_SRC.w;
  const barH = isLarge ? BAR_SRC.h : SMALL_BAR_SRC.h;

  return (
    <div className="boss-health-bar">
      <canvas
        ref={canvasRef}
        width={barW * bossScale() * DPR}
        height={barH * bossScale() * DPR}
        style={{ width: barW * bossScale(), height: barH * bossScale() }}
      />
    </div>
  );
}

export default memo(BossHealthBar);
