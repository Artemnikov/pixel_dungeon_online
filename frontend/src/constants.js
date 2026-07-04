export const TILE_SIZE = 32;
export const TILE_SCALE = 2;
export const ENTITY_LIFT = 12;
export const MOVE_DURATION = 150;
export const CAMERA_LERP = 0.1;
export const INVIS_ALPHA = 0.4;
export const FADE_DURATION = 400;
export const MIN_ZOOM = 0.5;
export const MAX_ZOOM = 2.5;
export const MAX_DPR = 2;
export const PROJECTILE_SPEED = 0.5;

// Melee attack animation timing (mirrors Shattered Pixel Dungeon)
export const PLAYER_ATTACK_DURATION = 270; // 4 frames @ ~15fps
export const PLAYER_OPERATE_DURATION = 500; // drink/operate: 4 frames @ 8fps (SPD)
export const PLAYER_READ_DURATION = 500; // read: 10 frames @ 20fps (SPD HeroSprite.read)
export const HIT_CONNECT_DELAY = 130;      // delay before swing "connects" and damage shows
export const FLASH_DURATION = 50;          // white hit-flash duration

export const easeOutQuad = t => 1 - (1 - t) * (1 - t);

// Floor transition fade (stairs/chasm). SPD's InterlevelScene has 3 fade-time tiers
// (slow/norm/fast, up to 2s) timed against a background level-gen thread; floors here
// are already generated server-side with no load delay, so we collapse to one simple
// out/hold/in cycle just long enough to mask the instant grid+position swap.
export const FLOOR_FADE_OUT_MS = 330;
export const FLOOR_FADE_HOLD_MS = 80;
export const FLOOR_FADE_IN_MS = 330;
