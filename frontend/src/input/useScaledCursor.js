import { useEffect, useMemo, useState } from 'react';
import cursorMouse2xUrl from '../assets/cursors/cursor_mouse@2x.png';
import cursorController2xUrl from '../assets/cursors/cursor_controller@2x.png';
import { CURSOR_SIZE_PCT, CURSOR_MIN_PX, CURSOR_MAX_PX, CURSOR_SIZE_STEP_PX } from '../constants';

// Both source assets are 16x16 (32x32 @2x) with the pointer tip at (1,1)/(2,2) and
// the crosshair center at (8,8)/(16,16) — i.e. tip at 6.25% and center at 50% of the
// asset's edge. Rasterizing to an arbitrary size preserves those hotspot fractions.
const MOUSE_HOTSPOT_FRAC = 1 / 16;
const CONTROLLER_HOTSPOT_FRAC = 0.5;

function loadImage(src) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.src = src;
  });
}

// Draws `img` onto an offscreen canvas at the requested CSS size (times `resScale`
// device pixels per CSS px) with nearest-neighbor scaling to keep the pixel-art look.
function rasterize(img, sizeCss, resScale) {
  const px = Math.max(1, Math.round(sizeCss * resScale));
  const canvas = document.createElement('canvas');
  canvas.width = px;
  canvas.height = px;
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(img, 0, 0, px, px);
  return canvas.toDataURL('image/png');
}

// Builds `cursor` property values for the mouse/controller reticles, re-rastered from
// the source PNGs so their on-screen size stays a constant % of the game viewport
// instead of a fixed pixel count of the source asset.
export default function useScaledCursor(gameWidth, gameHeight, dpr, isMac) {
  const [images, setImages] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([loadImage(cursorMouse2xUrl), loadImage(cursorController2xUrl)]).then(([mouse, controller]) => {
      if (cancelled) return;
      setImages({ mouse, controller });
    });
    return () => { cancelled = true; };
  }, []);

  const sizeCss = useMemo(() => {
    const base = Math.min(gameWidth, gameHeight) * CURSOR_SIZE_PCT;
    const clamped = Math.min(Math.max(base, CURSOR_MIN_PX), CURSOR_MAX_PX);
    return Math.round(clamped / CURSOR_SIZE_STEP_PX) * CURSOR_SIZE_STEP_PX;
  }, [gameWidth, gameHeight]);

  return useMemo(() => {
    if (!images) return { mouseCursorVal: 'pointer', controllerCursorVal: 'crosshair' };
    const { mouse, controller } = images;
    const mHot = Math.round(sizeCss * MOUSE_HOTSPOT_FRAC);
    const cHot = Math.round(sizeCss * CONTROLLER_HOTSPOT_FRAC);

    if (isMac) {
      // Safari doesn't reliably support image-set() in `cursor`; raster a single
      // bitmap at the exact display size instead.
      const mouseUrl = rasterize(mouse, sizeCss, 1);
      const controllerUrl = rasterize(controller, sizeCss, 1);
      return {
        mouseCursorVal: `url(${mouseUrl}) ${mHot} ${mHot}, pointer`,
        controllerCursorVal: `url(${controllerUrl}) ${cHot} ${cHot}, crosshair`,
      };
    }

    const resScale = Math.min(Math.max(Math.round(dpr) || 1, 1), 2);
    const mouseUrl = rasterize(mouse, sizeCss, resScale);
    const controllerUrl = rasterize(controller, sizeCss, resScale);
    return {
      mouseCursorVal: `image-set(url(${mouseUrl}) ${resScale}x) ${mHot} ${mHot}, pointer`,
      controllerCursorVal: `image-set(url(${controllerUrl}) ${resScale}x) ${cHot} ${cHot}, crosshair`,
    };
  }, [images, sizeCss, dpr, isMac]);
}
