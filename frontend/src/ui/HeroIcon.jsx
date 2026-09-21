import { isHeroClass, getCharacterDescriptor } from '../rendering/characterDescriptors';
import ratSheet from '../assets/pixel-dungeon/sprites/rat.png';
import gnollSheet from '../assets/pixel-dungeon/sprites/gnoll.png';
import skeletonSheet from '../assets/pixel-dungeon/sprites/skeleton.png';
import thiefSheet from '../assets/pixel-dungeon/sprites/thief.png';
import necromancerSheet from '../assets/pixel-dungeon/sprites/necromancer.png';

const MOB_SHEETS = {
  rat: ratSheet,
  gnoll: gnollSheet,
  skeleton: skeletonSheet,
  thief: thiefSheet,
  necromancer: necromancerSheet,
};

const COLS = 8;
const ICON_SIZE = 16;
const SHEET_W = 128;
const SHEET_H = 256;

export default function HeroIcon({ index, size, className, classType }) {
  const s = size || ICON_SIZE;

  if (classType && !isHeroClass(classType)) {
    const desc = getCharacterDescriptor(classType);
    const spriteUrl = MOB_SHEETS[desc.assetKey];
    const f = desc.defaultFrame;
    const scale = s / Math.max(f.w, f.h, 16);
    return (
      <div
        className={`hero-icon ${className || ''}`}
        style={{
          width: s,
          height: s,
          backgroundImage: spriteUrl ? `url(${spriteUrl})` : 'none',
          backgroundPosition: `-${f.x * scale}px -${f.y * scale}px`,
          backgroundSize: `${256 * scale}px auto`,
          backgroundRepeat: 'no-repeat',
          imageRendering: 'pixelated',
          flexShrink: 0,
        }}
      />
    );
  }

  const idx = index ?? 0;
  const col = idx % COLS;
  const row = Math.floor(idx / COLS);
  const scale = s / ICON_SIZE;

  return (
    <div
      className={`hero-icon ${className || ''}`}
      style={{
        width: s,
        height: s,
        backgroundImage: 'url(/assets/hero_icons.png)',
        backgroundPosition: `-${col * s}px -${row * s}px`,
        backgroundSize: `${SHEET_W * scale}px ${SHEET_H * scale}px`,
        imageRendering: 'pixelated',
        flexShrink: 0,
      }}
    />
  );
}
