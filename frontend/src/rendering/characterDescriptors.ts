export interface CharacterFrameDef {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface CharacterDescriptor {
  id: string;
  isHero: boolean;
  frameWidth: number;
  frameHeight: number;
  assetKey: string;
  defaultFrame: CharacterFrameDef;
}

export const HERO_CLASSES = ['warrior', 'mage', 'rogue', 'huntress', 'duelist', 'cleric'] as const;
export type HeroClass = typeof HERO_CLASSES[number];

export function isHeroClass(classType?: string): boolean {
  if (!classType) return false;
  return (HERO_CLASSES as readonly string[]).includes(classType.toLowerCase());
}

const KNOWN_MOBS: Record<string, CharacterFrameDef> = {
  gnoll: { x: 0, y: 0, w: 12, h: 15 },
  skeleton: { x: 0, y: 0, w: 12, h: 15 },
  thief: { x: 0, y: 0, w: 12, h: 15 },
  rat: { x: 0, y: 0, w: 16, h: 15 },
  necromancer: { x: 0, y: 0, w: 16, h: 16 },
  crab: { x: 0, y: 0, w: 16, h: 15 },
  slime: { x: 0, y: 0, w: 14, h: 12 },
  snake: { x: 0, y: 0, w: 12, h: 11 },
  bat: { x: 0, y: 0, w: 16, h: 16 },
  goo: { x: 0, y: 0, w: 20, h: 14 },
  wraith: { x: 0, y: 0, w: 14, h: 15 },
  piranha: { x: 0, y: 0, w: 12, h: 16 },
  statue: { x: 0, y: 0, w: 12, h: 15 },
  ghoul: { x: 0, y: 0, w: 12, h: 14 },
  monk: { x: 0, y: 0, w: 15, h: 14 },
  warlock: { x: 0, y: 0, w: 12, h: 15 },
  golem: { x: 0, y: 0, w: 16, h: 16 },
  tengu: { x: 0, y: 0, w: 14, h: 16 },
  dm300: { x: 0, y: 0, w: 24, h: 22 },
  brute: { x: 0, y: 0, w: 14, h: 16 },
  shaman: { x: 0, y: 0, w: 12, h: 15 },
  dm100: { x: 0, y: 0, w: 16, h: 14 },
  dm200: { x: 0, y: 0, w: 21, h: 18 },
  guard: { x: 0, y: 0, w: 12, h: 16 },
  scorpio: { x: 0, y: 0, w: 17, h: 17 },
  ripper: { x: 0, y: 0, w: 16, h: 16 },
  spawner: { x: 0, y: 0, w: 20, h: 20 },
  succubus: { x: 0, y: 0, w: 14, h: 16 },
  eye: { x: 0, y: 0, w: 16, h: 16 },
  yog: { x: 0, y: 0, w: 20, h: 19 },
};

export function getCharacterDescriptor(classType?: string): CharacterDescriptor {
  const normalized = (classType || 'warrior').toLowerCase();

  if (isHeroClass(normalized)) {
    return {
      id: normalized,
      isHero: true,
      frameWidth: 12,
      frameHeight: 15,
      assetKey: normalized,
      defaultFrame: { x: 0, y: 90, w: 12, h: 15 },
    };
  }

  const mobFrame = KNOWN_MOBS[normalized] || { x: 0, y: 0, w: 16, h: 16 };
  return {
    id: normalized,
    isHero: false,
    frameWidth: mobFrame.w,
    frameHeight: mobFrame.h,
    assetKey: normalized,
    defaultFrame: mobFrame,
  };
}

export function getAvatarCropRect(
  classType?: string,
  armorTier: number = 0,
): { sx: number; sy: number; sw: number; sh: number } {
  const desc = getCharacterDescriptor(classType);
  if (desc.isHero) {
    const tier = Math.max(0, Math.min(armorTier || 0, 6));
    return {
      sx: desc.frameWidth,
      sy: tier * desc.frameHeight,
      sw: desc.frameWidth,
      sh: desc.frameHeight,
    };
  }

  return {
    sx: desc.defaultFrame.x,
    sy: desc.defaultFrame.y,
    sw: desc.defaultFrame.w,
    sh: desc.defaultFrame.h,
  };
}

