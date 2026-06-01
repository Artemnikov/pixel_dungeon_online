// White hit-flash overlay.
//
// Canvas2D can't additively tint a drawImage call, so we build a solid-white
// silhouette of the current sprite frame on a cached offscreen canvas and draw
// that over the sprite. This mirrors the 50ms full-sprite white blink from the
// original Shattered Pixel Dungeon (CharSprite.flash()).
//
// The caller is responsible for any flip/transform on `ctx` before calling this
// (we draw into the same transformed space, so flips are respected).

let offCanvas = null;
let offCtx = null;

function ensureOffscreen(w, h) {
  if (!offCanvas) {
    offCanvas = document.createElement('canvas');
    offCtx = offCanvas.getContext('2d');
  }
  if (offCanvas.width < w || offCanvas.height < h) {
    offCanvas.width = Math.max(offCanvas.width, w);
    offCanvas.height = Math.max(offCanvas.height, h);
  }
  return offCtx;
}

export function drawWhiteSilhouette(ctx, sprite, sx, sy, fw, fh, dx, dy, dw, dh) {
  if (!sprite) return;
  const octx = ensureOffscreen(fw, fh);
  octx.save();
  octx.clearRect(0, 0, fw, fh);
  octx.globalCompositeOperation = 'source-over';
  octx.imageSmoothingEnabled = false;
  octx.drawImage(sprite, sx, sy, fw, fh, 0, 0, fw, fh);
  // Keep only the sprite's opaque pixels, recolored solid white.
  octx.globalCompositeOperation = 'source-in';
  octx.fillStyle = '#ffffff';
  octx.fillRect(0, 0, fw, fh);
  octx.restore();

  ctx.drawImage(offCanvas, 0, 0, fw, fh, dx, dy, dw, dh);
}
