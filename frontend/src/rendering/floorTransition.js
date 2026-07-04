import { FLOOR_FADE_OUT_MS, FLOOR_FADE_HOLD_MS, FLOOR_FADE_IN_MS } from '../constants';

// Mirrors SPD's InterlevelScene fade (FADE_IN -> STATIC -> FADE_OUT), collapsed to one
// timing tier since there's no background level-gen thread to wait on here — the floor
// swap itself is applied by the caller once the "out" half completes (see
// useGameSocket.ts's stashed-INIT logic), then this plays the fade back in.
// `direction` is 'down' | 'up', kept for callers (camera snap direction lives in the
// renderer, not here) and so a future CHASM_FALL_START call site can pass 'down' too.

export function startFloorFade(fadeRef, direction) {
  const now = performance.now();
  fadeRef.current = {
    direction,
    startedAt: now,
    outUntil: now + FLOOR_FADE_OUT_MS,
    holdUntil: now + FLOOR_FADE_OUT_MS + FLOOR_FADE_HOLD_MS,
    inUntil: now + FLOOR_FADE_OUT_MS + FLOOR_FADE_HOLD_MS + FLOOR_FADE_IN_MS,
  };
}

// Black-dim overlay technique reused from useGameRenderer's death-dim/screen-flash
// blocks (full-screen ctx.fillRect drawn in screen space, after ctx.restore()).
export function advanceAndDrawFloorFade(ctx, canvas, { fadeRef }) {
  if (!fadeRef?.current) return;
  const fade = fadeRef.current;
  const now = performance.now();

  if (now >= fade.inUntil) {
    fadeRef.current = null;
    return;
  }

  let alpha;
  if (now < fade.outUntil) {
    alpha = (now - fade.startedAt) / FLOOR_FADE_OUT_MS;
  } else if (now < fade.holdUntil) {
    alpha = 1;
  } else {
    alpha = 1 - (now - fade.holdUntil) / FLOOR_FADE_IN_MS;
  }
  alpha = Math.max(0, Math.min(1, alpha));

  ctx.fillStyle = `rgba(0,0,0,${alpha})`;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}

// True from the moment the fade starts until it's fully faded back in — used to gate
// player input client-side while the transition plays.
export function isFloorFadeActive(fadeRef) {
  return !!fadeRef?.current;
}
