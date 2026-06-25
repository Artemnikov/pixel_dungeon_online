import { TILE_SIZE } from '../../constants';
import textIconsSrc from '../../assets/pixel-dungeon/effects/text_icons.png';

const LIFESPAN = 1.0;
const RISE = TILE_SIZE;
const ICON_W = 7;
const ICON_H = 8;

let lastNow = null;
let textIconsImg = null;
const _iconLoad = new Promise(resolve => {
  const img = new Image();
  img.onload = () => { textIconsImg = img; resolve(); };
  img.onerror = () => resolve();
  img.src = textIconsSrc;
});

export const TEXT_ICON = {
  PHYS_DMG: 0,
  PHYS_DMG_NO_BLOCK: 1,
  MAGIC_DMG: 2,
  PICK_DMG: 3,
  HUNGER: 5,
  BURNING: 6,
  SHOCKING: 7,
  FROST: 8,
  WATER: 9,
  BLEEDING: 10,
  TOXIC: 11,
  CORROSION: 12,
  POISON: 13,
  OOZE: 14,
  DEFERRED: 15,
  CORRUPTION: 16,
  AMULET: 17,
  HEALING: 18,
  SHIELDING: 19,
  EXPERIENCE: 20,
  STRENGTH: 21,
  GOLD: 23,
  ENERGY: 24,

  // Hit reason icons (row 5: 35-47)
  HIT_WEP: 36,
  HIT_ARM: 37,
  HIT_BLS: 38,
  HIT_HEX: 39,
  HIT_DAZE: 40,
  HIT_ACC: 41,
  HIT_EVA: 42,
  HIT_LIQ: 43,
  HIT_DANCE: 44,
  HIT_SUPR: 45,
  HIT_PRES: 46,
  HIT_MOMEN: 47,

  // Miss reason icons (row 10: 70-82)
  MISS_WEP: 72,
  MISS_ARM: 73,
  MISS_BLS: 74,
  MISS_HEX: 75,
  MISS_DAZE: 76,
  MISS_ACC: 77,
  MISS_EVA: 78,
  MISS_LIQ: 79,
  MISS_DEF: 80,
  MISS_TUFT: 81,
  MISS_RUN: 82,
};

const stacks = new Map();

export function spawnFloatingText(floatingTextRef, cx, cy, text, color = '#ffffff', iconIndex = -1, key = -1) {
  const entry = {
    x: cx,
    y: cy,
    text,
    color,
    life: LIFESPAN,
    maxLife: LIFESPAN,
    iconIndex,
    key,
    origY: cy,
  };
  floatingTextRef.current.push(entry);

  if (key !== -1) {
    let stack = stacks.get(key);
    if (!stack) {
      stack = [];
      stacks.set(key, stack);
    }
    if (stack.length > 0) {
      let below = entry;
      let aboveIndex = stack.length - 1;
      let numBelow = 0;
      while (aboveIndex >= 0) {
        numBelow++;
        const above = stack[aboveIndex];
        const aboveBottom = above.y;
        const belowTop = below.y;
        if (aboveBottom + 4 * 2 > belowTop) {
          above.y = belowTop - TILE_SIZE / 2 - 4 * 2;
          above.life = Math.min(above.life, LIFESPAN - (numBelow / 5));
          above.life = Math.max(above.life, 0);
          below = above;
          aboveIndex--;
        } else {
          break;
        }
      }
    }
    stack.push(entry);
  }
}

export function advanceAndDrawFloatingText(ctx, { floatingTextRef }) {
  const now = performance.now();
  if (lastNow == null) lastNow = now;
  const dt = Math.min((now - lastNow) / 1000, 0.05);
  lastNow = now;

  const items = floatingTextRef.current;
  const img = textIconsImg;

  for (let i = items.length - 1; i >= 0; i--) {
    const t = items[i];
    t.life -= dt;
    if (t.life <= 0) {
      if (t.key !== -1) {
        const stack = stacks.get(t.key);
        if (stack) {
          const idx = stack.indexOf(t);
          if (idx !== -1) stack.splice(idx, 1);
          if (stack.length === 0) stacks.delete(t.key);
        }
      }
      items.splice(i, 1);
      continue;
    }
    t.y -= (RISE / t.maxLife) * dt;

    const alpha = t.life > t.maxLife / 2 ? 1 : Math.max(0, t.life / (t.maxLife / 2));

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.imageSmoothingEnabled = false;

    const textX = Math.round(t.x);
    const textY = Math.round(t.y);

    if (t.iconIndex >= 0 && img?.complete && img?.naturalWidth > 0) {
      const cols = Math.floor(img.naturalWidth / ICON_W);
      const col = t.iconIndex % cols;
      const row = Math.floor(t.iconIndex / cols);
      const iconScale = 2;
      const iw = ICON_W * iconScale;
      const ih = ICON_H * iconScale;
      const textWidth = ctx.measureText(t.text).width;
      const totalW = iw + 2 + textWidth;
      const ix = textX - totalW / 2;
      const iy = textY - ih / 2;
      ctx.drawImage(img,
        col * ICON_W, row * ICON_H, ICON_W, ICON_H,
        ix, iy, iw, ih);
    }

    ctx.font = '9px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineWidth = 2;
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.strokeText(t.text, textX, textY);
    ctx.fillStyle = t.color;
    ctx.fillText(t.text, textX, textY);
    ctx.restore();
  }
}
