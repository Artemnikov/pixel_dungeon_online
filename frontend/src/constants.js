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

// Custom cursor scales with game viewport so it reads the same size on any screen,
// instead of staying pinned to the source asset's raw pixel dimensions.
export const CURSOR_SIZE_PCT = 0.048; // % of min(viewport width, height)
export const CURSOR_MIN_PX = 28;
export const CURSOR_MAX_PX = 80;
export const CURSOR_SIZE_STEP_PX = 2; // bucket size to avoid re-rastering every resize tick
export const PROJECTILE_SPEED = 0.5;

export const PLAYER_ATTACK_DURATION = 270; // 4 frames @ ~15fps
export const PLAYER_OPERATE_DURATION = 500; // drink/operate: 4 frames @ 8fps (SPD)
export const PLAYER_READ_DURATION = 500; // read: 10 frames @ 20fps (SPD HeroSprite.read)
export const HIT_CONNECT_DELAY = 130;      // delay before swing "connects" and damage shows
export const FLASH_DURATION = 50;          // white hit-flash duration

export const DEATH_ANIMATION_DURATION = 3000;
export const DEATH_FADE_START_MS = 1000;   // longest native die anim (Tengu/DM-300 = 1000ms)

export const easeOutQuad = t => 1 - (1 - t) * (1 - t);

export const FLOOR_FADE_OUT_MS = 330;
export const FLOOR_FADE_HOLD_MS = 80;
export const FLOOR_FADE_IN_MS = 330;

export const ATLAS_COLUMNS = 16;
export const atlasIndex = (x, y) => y * ATLAS_COLUMNS + x;

const tileBlock = (tileId) => ({ kind: 'wall', tile: tileId, action: 'none' });
const tilePassable = () => null;
const tileOpenAlchemy = () => ({ kind: 'alchemy-table', action: 'open-alchemy' });
const tileVoidJump = (tileId) => ({ kind: 'chasm', tile: tileId, action: 'chasm-jump' });
const tileUnlockDoor = (tileId) => ({ kind: 'door', tile: tileId, action: 'unlock-door' });

export const BACKEND_TILE = {
  VOID: { id: 0, atlasIndex: null, seethrough: true, passable: false, onInteract: tileVoidJump },
  WALL: { id: 1, atlasIndex: atlasIndex(0, 5), seethrough: false, passable: false, onInteract: tileBlock },
  FLOOR: { id: 2, atlasIndex: null, seethrough: true, passable: true, onInteract: tilePassable },
  DOOR: { id: 3, atlasIndex: atlasIndex(8, 3), seethrough: false, passable: true, onInteract: tilePassable },
  OPEN_DOOR: { id: 22, atlasIndex: atlasIndex(9, 3), seethrough: true, passable: true, onInteract: tilePassable },
  STAIRS_UP: { id: 4, atlasIndex: atlasIndex(0, 1), seethrough: true, passable: true, onInteract: tilePassable },
  STAIRS_DOWN: { id: 5, atlasIndex: atlasIndex(1, 1), seethrough: true, passable: true, onInteract: tilePassable },
  FLOOR_WOOD: { id: 6, atlasIndex: atlasIndex(4, 0), seethrough: true, passable: true, onInteract: tilePassable },
  FLOOR_WATER: { id: 7, atlasIndex: null, seethrough: true, passable: true, onInteract: tilePassable },
  FLOOR_COBBLE: { id: 8, atlasIndex: atlasIndex(12, 0), seethrough: true, passable: true, onInteract: tilePassable },
  FLOOR_GRASS: { id: 9, atlasIndex: null, seethrough: true, passable: true, onInteract: tilePassable },
  LOCKED_DOOR: { id: 10, atlasIndex: atlasIndex(8, 3), seethrough: false, passable: false, onInteract: tileUnlockDoor },
  HERO_LKD_DR: { id: 35, atlasIndex: atlasIndex(8, 3), seethrough: false, passable: false, onInteract: tileUnlockDoor },
  SECRET_TRAP: { id: 11, atlasIndex: null, seethrough: true, passable: false, onInteract: tilePassable },
  TRAP: { id: 12, atlasIndex: null, seethrough: true, passable: false, onInteract: tilePassable },
  INACTIVE_TRAP: { id: 13, atlasIndex: null, seethrough: true, passable: true, onInteract: tilePassable },
  EMBERS: { id: 14, atlasIndex: atlasIndex(3, 0), seethrough: true, passable: true, onInteract: tilePassable },
  REGION_DECO: { id: 15, atlasIndex: atlasIndex(10, 4), seethrough: true, passable: false, onInteract: tileBlock },
  REGION_DECO_ALT: { id: 16, atlasIndex: atlasIndex(11, 4), seethrough: true, passable: false, onInteract: tileBlock },
  WALL_DECO: { id: 17, atlasIndex: atlasIndex(1, 3), seethrough: false, passable: false, onInteract: tileBlock },
  EMPTY_DECO: { id: 18, atlasIndex: atlasIndex(3, 0), seethrough: true, passable: true, onInteract: tilePassable },
  HIGH_GRASS: { id: 19, atlasIndex: null, seethrough: false, passable: true, onInteract: tilePassable },
  SECRET_DOOR: { id: 20, atlasIndex: atlasIndex(0, 5), seethrough: false, passable: false, onInteract: tileBlock },
  LOCKED_EXIT: { id: 21, atlasIndex: atlasIndex(8, 3), seethrough: false, passable: false, onInteract: tileUnlockDoor },
  ALCHEMY: { id: 23, atlasIndex: atlasIndex(8, 7), seethrough: true, overhangIndex: atlasIndex(8, 14), passable: false, onInteract: tileOpenAlchemy },
  WELL: { id: 24, atlasIndex: null, seethrough: true, passable: false, onInteract: tileBlock },
  STATUE: { id: 25, atlasIndex: atlasIndex(8, 4), seethrough: true, passable: false, onInteract: tileBlock },
  PEDESTAL: { id: 34, atlasIndex: atlasIndex(4, 1), seethrough: true, passable: true, onInteract: tilePassable },
  BOOKSHELF: { id: 27, atlasIndex: atlasIndex(12, 5), seethrough: false, passable: false, onInteract: tileBlock },
  FURROWED_GRASS: { id: 30, atlasIndex: null, seethrough: false, passable: true, onInteract: tilePassable },
  CRYSTAL_DOOR: { id: 31, atlasIndex: atlasIndex(3, 7), seethrough: false, passable: false, onInteract: tileUnlockDoor },
  BARRICADE: { id: 32, atlasIndex: atlasIndex(0, 5), seethrough: false, passable: false, onInteract: tileBlock },
  CHASM: { id: 33, atlasIndex: atlasIndex(8, 1), seethrough: true, passable: false, onInteract: tileVoidJump },
};

export const OUT_OF_BOUNDS_TILE = {
  id: -1,
  passable: false,
  onInteract: tileBlock,
};

export const TILE_BY_ID = Object.values(BACKEND_TILE).reduce((acc, tile) => {
  acc[tile.id] = tile;
  return acc;
}, {});

export const getTileDescriptor = (tileId) => {
  if (tileId === undefined || tileId === null) return OUT_OF_BOUNDS_TILE;
  return TILE_BY_ID[tileId] ?? OUT_OF_BOUNDS_TILE;
};

export const hashCell = (x, y) => ((x * 73856093) ^ (y * 19349663)) >>> 0;

export const isWallTile = (tile) =>
  tile === BACKEND_TILE.WALL.id ||
  tile === BACKEND_TILE.WALL_DECO.id ||
  tile === BACKEND_TILE.SECRET_DOOR.id ||
  tile === BACKEND_TILE.BOOKSHELF.id;

// Used ONLY by wall-autotile stitching: any tile that should visually
// continue a wall surface. Out-of-bounds (-1) and unpainted VOID cells
// count as walls so the outer frame of the map stitches cleanly instead
// of showing jagged edges. Mirrors SPD's DungeonTileSheet.wallStitcheable.
export const isWallStitcheable = (tile) =>
  tile === -1 ||
  tile === BACKEND_TILE.VOID.id ||
  tile === BACKEND_TILE.WALL.id ||
  tile === BACKEND_TILE.WALL_DECO.id ||
  tile === BACKEND_TILE.SECRET_DOOR.id ||
  tile === BACKEND_TILE.LOCKED_EXIT.id ||
  tile === BACKEND_TILE.BOOKSHELF.id;

export const isDoorTile = (tile) =>
  tile === BACKEND_TILE.DOOR.id ||
  tile === BACKEND_TILE.OPEN_DOOR.id ||
  tile === BACKEND_TILE.LOCKED_DOOR.id ||
  tile === BACKEND_TILE.LOCKED_EXIT.id ||
  tile === BACKEND_TILE.CRYSTAL_DOOR.id ||
  tile === BACKEND_TILE.HERO_LKD_DR.id;

export const isSidewaysDoor = (grid, x, y, getTile) =>
  isWallStitcheable(getTile(grid, x, y - 1));

export const isWaterTile = (tile) => tile === BACKEND_TILE.FLOOR_WATER.id;

export const isWaterStitcheable = (tile) => !isWaterTile(tile) && !isWallTile(tile);
export const isGrassTile = (tile) =>
  tile === BACKEND_TILE.FLOOR_GRASS.id ||
  tile === BACKEND_TILE.HIGH_GRASS.id ||
  tile === BACKEND_TILE.FURROWED_GRASS.id;

export const TRAP_VISUAL = {
  worn_dart: { color: 7, shape: 5 },
  tengu_dart: { color: 3, shape: 5 },
  burning_trap: { color: 1, shape: 0 },
  blazing_trap: { color: 1, shape: 3 },
  shocking_trap: { color: 2, shape: 0 },
  storm_trap: { color: 2, shape: 3 },
  chilling_trap: { color: 6, shape: 0 },
  toxic_trap: { color: 3, shape: 2 },
  poison_dart_trap: { color: 3, shape: 5 },
  confusion_trap: { color: 4, shape: 2 },
  flock_trap: { color: 6, shape: 1 },
  summoning_trap: { color: 4, shape: 1 },
  teleportation_trap: { color: 4, shape: 0 },
  gateway_trap: { color: 4, shape: 5 },
  alarm_trap: { color: 0, shape: 0 },
  ooze_trap: { color: 3, shape: 0 },
  gripping_trap: { color: 7, shape: 0 },
  geyser_trap: { color: 4, shape: 4 },
  frost_trap: { color: 6, shape: 3 },
  corrosion_trap: { color: 7, shape: 2 },
  rockfall_trap: { color: 7, shape: 4 },
  guardian_trap: { color: 0, shape: 3 },
  warping_trap: { color: 4, shape: 3 },
  pitfall_trap: { color: 0, shape: 4 },
  disintegration_trap: { color: 5, shape: 5 },
  flashing_trap: { color: 7, shape: 3 },
  weakening_trap: { color: 3, shape: 1 },
  disarming_trap: { color: 0, shape: 6 },
  cursing_trap: { color: 5, shape: 1 },
  distortion_trap: { color: 4, shape: 6 },
  grim_trap: { color: 7, shape: 6 },
  explosive_trap: { color: 1, shape: 4 },
};

export const trapSpriteIndex = (trapType) => {
  const v = TRAP_VISUAL[trapType];
  if (!v) return null;
  return v.color + v.shape * 16;
};

export const trapDisarmedIndex = (trapType) => {
  const v = TRAP_VISUAL[trapType];
  if (!v) return null;
  return 8 + v.shape * 16;
};

export const PLANT_SPRITE_INDEX = {
  rotberry: 112,
  firebloom: 113,
  swiftthistle: 114,
  sungrass: 115,
  icecap: 116,
  stormvine: 117,
  sorrowmoss: 118,
  mageroyal: 119,
  dreamfoil: 119,
  earthroot: 120,
  starflower: 121,
  fadeleaf: 122,
  blindweed: 123,
  blandfruit_bush: 124,
  blandfruit: 124,
  dewcatcher: 125,
  seedpod: 126,
};

export const plantSpriteIndex = (plantType) => {
  if (!plantType) return PLANT_SPRITE_INDEX.sungrass;
  const key = String(plantType).toLowerCase();
  return PLANT_SPRITE_INDEX[key] ?? PLANT_SPRITE_INDEX.sungrass;
};
