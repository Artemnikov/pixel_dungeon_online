import { TILE_SIZE } from '../../constants';

// SPD's Torch (PrisonLevel.Torch): a flame Emitter + light Halo mounted on a
// wall tile. This renderer has no particle/light system, so we approximate it
// with a small looping flame sprite (reusing the title screen's fireball
// asset) anchored above the wall tile's base, gated by current FOV like the
// original (Torch.update() only runs while heroFOV[pos] is true).
const FB_SIZE = 47;
const FB_COLS = 5;
const FB_FPS = 24;
const FB_COUNT = 24;
const DEST_SIZE = TILE_SIZE * 0.85;

export function drawTorches(ctx, { torches, assetImages, visionRef }) {
  if (!torches || !torches.length) return;
  const img = assetImages.fireball;
  if (!img) return;

  const frame = Math.floor((performance.now() / 1000) * FB_FPS) % FB_COUNT;
  const sx = (frame % FB_COLS) * FB_SIZE;
  const sy = Math.floor(frame / FB_COLS) * FB_SIZE;

  for (const [x, y] of torches) {
    if (!visionRef.current.visible.has(`${x},${y}`)) continue;
    const cx = x * TILE_SIZE + TILE_SIZE / 2;
    const baseY = y * TILE_SIZE + TILE_SIZE * 0.85;
    ctx.drawImage(
      img, sx, sy, FB_SIZE, FB_SIZE,
      cx - DEST_SIZE / 2, baseY - DEST_SIZE, DEST_SIZE, DEST_SIZE,
    );
  }
}
