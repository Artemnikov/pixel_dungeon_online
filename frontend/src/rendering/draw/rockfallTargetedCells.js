import { TILE_SIZE } from '../../constants';
import { spawnFallingEarth } from './particles';

// Icons.TARGET in icons.png (Icons.java): uvRect(0, 32, 16, 16).
// Faithful port of SPD's TargetedCell (TargetedCell.java): red-tinted (0xFF0000)
// target crosshair that scales down and fades out over the 2-second telegraph,
// combined with a highlighted red warning tile base for web viewport clarity.
const TARGET_X = 0;
const TARGET_Y = 32;
const TARGET_W = 16;
const TARGET_H = 16;

let redIconCanvas = null;
let redIconCtx = null;

function getRedTargetIcon(iconsImage) {
  if (!iconsImage) return null;
  if (!redIconCanvas) {
    redIconCanvas = document.createElement('canvas');
    redIconCanvas.width = TARGET_W;
    redIconCanvas.height = TARGET_H;
    redIconCtx = redIconCanvas.getContext('2d');
  }
  redIconCtx.clearRect(0, 0, TARGET_W, TARGET_H);
  redIconCtx.imageSmoothingEnabled = false;
  redIconCtx.globalCompositeOperation = 'source-over';
  redIconCtx.drawImage(iconsImage, TARGET_X, TARGET_Y, TARGET_W, TARGET_H, 0, 0, TARGET_W, TARGET_H);
  redIconCtx.globalCompositeOperation = 'source-in';
  redIconCtx.fillStyle = '#ff2222';
  redIconCtx.fillRect(0, 0, TARGET_W, TARGET_H);
  return redIconCanvas;
}

export function drawRockfallTargetedCells(ctx, { rockfallTelegraphRef, particlesRef, visionRef, assetImages }) {
  const tele = rockfallTelegraphRef?.current;
  if (!tele || !tele.cells?.length) return;

  const now = performance.now();
  if (now >= tele.untilMs) {
    rockfallTelegraphRef.current = null;
    return;
  }

  const durationMs = tele.durationMs || 2000;
  const remaining = tele.untilMs - now;
  // SPD TargetedCell: alpha = 1f, alpha -= Game.elapsed / 2f, scale.set(alpha)
  const progress = Math.max(0, Math.min(1, remaining / durationMs));
  const pulse = 0.8 + 0.2 * Math.sin(now * 0.008);

  const visible = visionRef?.current?.visible;
  const redTarget = assetImages?.icons ? getRedTargetIcon(assetImages.icons) : null;

  ctx.save();

  // 1. Tile Base Warning Highlight (semi-transparent red fill + glowing border)
  tele.cells.forEach(([tx, ty]) => {
    const cellKey = `${tx},${ty}`;
    if (visible && !visible.has(cellKey)) return;

    const x = tx * TILE_SIZE;
    const y = ty * TILE_SIZE;

    ctx.fillStyle = `rgba(220, 30, 20, ${0.28 * progress * pulse})`;
    ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);

    ctx.strokeStyle = `rgba(255, 70, 50, ${0.75 * progress * pulse})`;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(x + 0.75, y + 0.75, TILE_SIZE - 1.5, TILE_SIZE - 1.5);
  });

  // 2. Shrinking Red TargetedCell Reticle
  const baseScale = 2; // 16px icon -> 32px tile
  const scale = baseScale * progress;
  const dw = TARGET_W * scale;
  const dh = TARGET_H * scale;

  ctx.globalAlpha = Math.max(0.2, progress);
  ctx.imageSmoothingEnabled = true;

  tele.cells.forEach(([tx, ty]) => {
    const cellKey = `${tx},${ty}`;
    if (visible && !visible.has(cellKey)) return;

    const cx = tx * TILE_SIZE + TILE_SIZE / 2;
    const cy = ty * TILE_SIZE + TILE_SIZE / 2;

    if (redTarget && dw > 2) {
      ctx.drawImage(redTarget, 0, 0, TARGET_W, TARGET_H, cx - dw / 2, cy - dh / 2, dw, dh);
    } else if (dw > 2) {
      // Procedural red reticle fallback if icon asset is not yet ready
      const r = (dw / 2) * 0.8;
      ctx.strokeStyle = '#ff2222';
      ctx.lineWidth = Math.max(1, 1.5 * progress);
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.moveTo(cx - r * 1.3, cy);
      ctx.lineTo(cx + r * 1.3, cy);
      ctx.moveTo(cx, cy - r * 1.3);
      ctx.lineTo(cx, cy + r * 1.3);
      ctx.stroke();
    }

    // 3. DelayedRockFall.fx: pour(EarthParticle.FALLING, 0.1f)
    if (particlesRef && Math.random() < 0.22) {
      spawnFallingEarth(particlesRef, cx, cy, 1);
    }
  });

  ctx.restore();
}
